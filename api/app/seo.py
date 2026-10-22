"""SEO / marketing helpers: sitemap, robots, llms.txt, RSS, duplicate detection.

Pure functions only — no DB access — so they are easy to unit test.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import escape
from urllib.parse import urljoin, urlparse

# --------------------------------------------------------------------------
# Site catalogue: the canonical list of indexable public routes.
# --------------------------------------------------------------------------

STATIC_PAGES: list[dict] = [
    {"path": "/", "priority": 1.0, "changefreq": "weekly"},
    {"path": "/blog", "priority": 0.9, "changefreq": "daily"},
]

# Paths that must never be indexed (app shell, auth, legal noise).
NON_INDEXABLE_PREFIXES = ("/app", "/login", "/register")

# AI crawler user-agent tokens we know how to reason about.
AI_BOT_TOKENS = [
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-User",
    "anthropic-ai",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Applebot-Extended",
    "CCBot",
    "Bytespider",
    "Meta-ExternalAgent",
    "cohere-ai",
    "Amazonbot",
    "DuckAssistBot",
]


def normalize_base_url(base: str, fallback: str = "http://localhost:3900") -> str:
    """Return a scheme+host normalized base URL without trailing slash."""
    raw = (base or "").strip() or fallback
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")
    parsed = urlparse(raw)
    if not parsed.netloc:
        return fallback.rstrip("/")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def abs_url(base_url: str, path: str) -> str:
    return urljoin(normalize_base_url(base_url) + "/", path.lstrip("/"))


def is_indexable(path: str) -> bool:
    return not any(path == p or path.startswith(p + "/") for p in NON_INDEXABLE_PREFIXES)


# --------------------------------------------------------------------------
# XML builders
# --------------------------------------------------------------------------


def _xml_escape(value: str) -> str:
    return escape(value or "", quote=True)


def sitemap_index_xml(base_url: str, sitemaps: list[dict]) -> str:
    """Sitemap index pointing at child sitemaps."""
    base = normalize_base_url(base_url)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for item in sitemaps:
        loc = urljoin(base + "/", item["path"].lstrip("/"))
        parts.append("  <sitemap>")
        parts.append(f"    <loc>{_xml_escape(loc)}</loc>")
        if item.get("lastmod"):
            parts.append(f"    <lastmod>{_xml_escape(item['lastmod'])}</lastmod>")
        parts.append("  </sitemap>")
    parts.append("</sitemapindex>")
    return "\n".join(parts)


def urlset_xml(entries: list[dict]) -> str:
    """URL set. Each entry: path/url, lastmod, changefreq, priority, images."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for entry in entries:
        loc = entry.get("url") or entry.get("path", "")
        parts.append("  <url>")
        parts.append(f"    <loc>{_xml_escape(loc)}</loc>")
        if entry.get("lastmod"):
            parts.append(f"    <lastmod>{_xml_escape(entry['lastmod'])}</lastmod>")
        if entry.get("changefreq"):
            parts.append(f"    <changefreq>{_xml_escape(entry['changefreq'])}</changefreq>")
        if entry.get("priority") is not None:
            parts.append(f"    <priority>{float(entry['priority']):.1f}</priority>")
        for image in entry.get("images", []) or []:
            parts.append("    <image:image>")
            parts.append(f"      <image:loc>{_xml_escape(image)}</image:loc>")
            parts.append("    </image:image>")
        parts.append("  </url>")
    parts.append("</urlset>")
    return "\n".join(parts)


def robots_txt(
    base_url: str,
    *,
    block_ai_bots: bool = False,
    allow_ai_bots: str = "",
    extra: str = "",
    disallow_paths: list[str] | None = None,
) -> str:
    """Build robots.txt including explicit AI crawler policy."""
    base = normalize_base_url(base_url)
    lines = ["User-agent: *", "Allow: /"]
    for path in disallow_paths or ["/app", "/login", "/register", "/api/"]:
        lines.append(f"Disallow: {path}")
    lines.append("")

    allowed = [t.strip() for t in (allow_ai_bots or "").split(",") if t.strip()]
    for token in AI_BOT_TOKENS:
        if token in allowed:
            lines.append(f"User-agent: {token}")
            lines.append("Allow: /")
            lines.append("")
        elif block_ai_bots:
            lines.append(f"User-agent: {token}")
            lines.append("Disallow: /")
            lines.append("")

    lines.append(f"Sitemap: {urljoin(base + '/', 'sitemap.xml')}")
    if extra.strip():
        lines.append("")
        lines.append(extra.strip())
    return "\n".join(lines) + "\n"


def llms_txt(base_url: str, sections: list[dict], intro: str = "") -> str:
    """Build an llms.txt (llmstxt.org convention) site index."""
    base = normalize_base_url(base_url)
    lines = [f"# {sections[0]['title'] if sections else 'Site'}"]
    if intro.strip():
        lines.append("")
        lines.append("> " + intro.strip().replace("\n", "\n> "))
    for section in sections:
        lines.append("")
        lines.append(f"## {section['title']}")
        if section.get("description"):
            lines.append("")
            lines.append(section["description"].strip())
        for item in section.get("items", []) or []:
            url = item.get("url") or urljoin(base + "/", item.get("path", "").lstrip("/"))
            note = item.get("note")
            lines.append(f"- [{item['title']}]({url})" + (f": {note}" if note else ""))
    return "\n".join(lines) + "\n"


def rss_xml(base_url: str, site_name: str, items: list[dict], description: str = "") -> str:
    """RSS 2.0 feed for aggregators and feed readers."""
    base = normalize_base_url(base_url)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{_xml_escape(site_name)}</title>",
        f"    <link>{_xml_escape(base)}/</link>",
        f"    <description>{_xml_escape(description or site_name)}</description>",
        "    <language>tr</language>",
        f'    <atom:link href="{_xml_escape(base)}/feed.xml" rel="self" type="application/rss+xml" />',
    ]
    for item in items:
        url = item.get("url") or urljoin(base + "/", item.get("path", "").lstrip("/"))
        parts.append("    <item>")
        parts.append(f"      <title>{_xml_escape(item.get('title', ''))}</title>")
        parts.append(f"      <link>{_xml_escape(url)}</link>")
        parts.append(f"      <guid isPermaLink=\"true\">{_xml_escape(url)}</guid>")
        if item.get("description"):
            parts.append(f"      <description>{_xml_escape(item['description'])}</description>")
        if item.get("pubdate"):
            parts.append(f"      <pubDate>{_xml_escape(item['pubdate'])}</pubDate>")
        parts.append("    </item>")
    parts.append("  </channel>")
    parts.append("</rss>")
    return "\n".join(parts)


def rfc822(dt: datetime | None) -> str:
    if dt is None:
        dt = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return (
        f"{days[dt.weekday()]}, {dt.day:02d} {months[dt.month - 1]} {dt.year} "
        f"{dt.hour:02d}:{dt.minor:02d}:{dt.second:02d} +0000"
    )


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------
# JSON-LD (structured data) — helps both classic crawlers and AI parsers.
# --------------------------------------------------------------------------


def organization_jsonld(base_url: str, site_name: str, logo: str = "") -> dict:
    base = normalize_base_url(base_url)
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site_name,
        "url": base + "/",
        "description": "Sentetik topluluk simülasyonu platformu.",
    }
    if logo:
        org["logo"] = abs_url(base, logo)
    return org


def website_jsonld(base_url: str, site_name: str, description: str = "") -> dict:
    base = normalize_base_url(base_url)
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": base + "/",
        "inLanguage": "tr",
    }
    if description:
        data["description"] = description
    return data


def article_jsonld(
    *,
    base_url: str,
    title: str,
    description: str,
    path: str,
    published_at: datetime | None,
    updated_at: datetime | None = None,
    author: str = "",
    image: str = "",
    keywords: str = "",
) -> dict:
    base = normalize_base_url(base_url)
    url = abs_url(base, path)
    data: dict = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "tr",
    }
    if description:
        data["description"] = description
    if published_at:
        data["datePublished"] = iso(published_at)
    if updated_at:
        data["dateModified"] = iso(updated_at)
    if author:
        data["author"] = {"@type": "Organization", "name": author}
        data["publisher"] = {"@type": "Organization", "name": author}
    if image:
        data["image"] = abs_url(base, image)
    if keywords:
        data["keywords"] = keywords
    return data


def faq_jsonld(pairs: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in pairs
        ],
    }


# --------------------------------------------------------------------------
# Duplicate / thin-content detection
# --------------------------------------------------------------------------


_TOKEN_RE = re.compile(r"[a-z0-9çğıöşü]+", re.IGNORECASE)

STOPWORDS = {
    "ve", "ile", "için", "olan", "olarak", "da", "de", "bu", "her", "daha", "çok",
    "the", "and", "for", "with", "that", "this", "you", "your", "are", "was", "from",
    "bir", "gibi", "kadar", "sonra", "veya", "ancak", "ise", "tüm",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if t not in STOPWORDS and len(t) > 2]


def shingles(tokens: list[str], size: int = 4) -> set[str]:
    if len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cosine(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / ((len(a) ** 0.5) * (len(b) ** 0.5))


@dataclass
class DuplicatePair:
    left: str
    right: str
    similarity: float
    kind: str = "body"

    def as_dict(self) -> dict:
        return {
            "left": self.left,
            "right": self.right,
            "similarity": round(self.similarity, 4),
            "kind": self.kind,
        }


@dataclass
class SimilarityIndex:
    """Shingle-based similarity index for near-duplicate detection."""

    docs: dict[str, set[str]] = field(default_factory=dict)
    titles: dict[str, set[str]] = field(default_factory=dict)

    def add(self, key: str, body: str, title: str = "") -> None:
        tokens = tokenize(body)
        self.docs[key] = shingles(tokens)
        self.titles[key] = set(tokenize(title))

    def pairs(self, threshold: float = 0.25) -> list[DuplicatePair]:
        keys = list(self.docs)
        out: list[DuplicatePair] = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                body_sim = cosine(self.docs.get(a, set()), self.docs.get(b, set()))
                title_sim = cosine(self.titles.get(a, set()), self.titles.get(b, set()))
                sim = max(body_sim, title_sim * 0.9)
                if sim >= threshold:
                    out.append(
                        DuplicatePair(
                            left=a,
                            right=b,
                            similarity=sim,
                            kind="title" if title_sim > body_sim else "body",
                        )
                    )
        out.sort(key=lambda p: p.similarity, reverse=True)
        return out


def keyword_density(text: str, keyword: str) -> float:
    """Keyword density as percentage of tokens (0 when keyword absent)."""
    kw = (keyword or "").strip().lower()
    if not kw:
        return 0.0
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t == kw.lower() or kw.lower() in t)
    return round(hits / len(tokens) * 100, 2)


def strip_markup(text: str) -> str:
    """Remove markdown-ish syntax so counts reflect real content."""
    out = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    out = re.sub(r"[*_`>#\[\]()]", " ", out)
    out = re.sub(r"https?://\S+", " ", out)
    return re.sub(r"\s+", " ", out).strip()


# --------------------------------------------------------------------------
# Analytics snippet parsing (admin pastes the raw gtag tag)
# --------------------------------------------------------------------------

MEASUREMENT_ID_RE = re.compile(r"\b((?:G|GT|AW|DC|UA)-[A-Za-z0-9_-]{4,})")
SCRIPT_SRC_RE = re.compile(r"<script[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
SCRIPT_BLOCK_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def extract_measurement_id(code: str) -> str:
    """Find the GA4/GT/AW measurement id inside a pasted snippet.

    Works both for a bare id ("G-ABC123") and for a full gtag.js tag.
    """
    if not code:
        return ""
    match = MEASUREMENT_ID_RE.search(code)
    return match.group(1) if match else ""


def is_valid_measurement_id(value: str) -> bool:
    return bool(MEASUREMENT_ID_RE.fullmatch((value or "").strip()))


def parse_snippet(code: str) -> list[dict]:
    """Split a pasted <script> snippet into external and inline scripts.

    Each entry is {"src": url, "inline": body}; inline bodies are executed
    verbatim, external ones loaded with async.
    """
    if not code:
        return []
    out: list[dict] = []
    for match in SCRIPT_SRC_RE.finditer(code):
        out.append({"src": match.group(1).strip(), "inline": ""})
    for match in SCRIPT_BLOCK_RE.finditer(code):
        body = match.group(1).strip()
        if body:
            out.append({"src": "", "inline": body})
    return out


def snippet_has_inline(code: str) -> bool:
    return any(item["inline"] for item in parse_snippet(code))
