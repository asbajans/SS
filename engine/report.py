"""Report drafting helpers: outline -> sections -> Markdown/PDF."""
import html
import json
import re

DISCLAIMER_TR = (
    "Bu rapor, yapay zekâ ajanlarıyla gerçekleştirilmiş bir simülasyon çıktısıdır. "
    "Gerçek anket, saha araştırması veya odak grubu sonuçlarının yerini almaz; "
    "kararlar için ek doğrulama gerekir."
)
DISCLAIMER_EN = (
    "This report is the output of a simulation run by AI agents. "
    "It does not replace real surveys, field research, or focus groups; "
    "additional validation is required for decisions."
)

DEFAULT_SECTIONS_TR = [
    "Yönetici Özeti",
    "Yöntem ve Kaynaklar",
    "Ontoloji ve Aktörler",
    "Temel Bulgular",
    "Ajan Davranışları",
    "Riskler ve Belirsizlikler",
    "Öneriler",
    "Sınırlamalar",
]
DEFAULT_SECTIONS_EN = [
    "Executive Summary",
    "Method and Sources",
    "Ontology and Actors",
    "Key Findings",
    "Agent Behavior",
    "Risks and Uncertainties",
    "Recommendations",
    "Limitations",
]


def disclaimer_for(language: str) -> str:
    return DISCLAIMER_EN if language == "en" else DISCLAIMER_TR


def fallback_sections(language: str) -> list[str]:
    return list(DEFAULT_SECTIONS_EN if language == "en" else DEFAULT_SECTIONS_TR)


def parse_outline(text: str, fallback: list[str]) -> list[str]:
    if not text:
        return list(fallback)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    titles: list[str] = []
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            data = data.get("sections") or data.get("outline") or []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    titles.append(item.strip())
                elif isinstance(item, dict):
                    title = item.get("title") or item.get("name")
                    if title:
                        titles.append(str(title).strip())
    except (json.JSONDecodeError, TypeError, ValueError):
        titles = []
    if len(titles) < 3:
        titles = []
        for raw in cleaned.splitlines():
            line = raw.strip()
            if not line or line in {"{", "}", "[", "]", "```"}:
                continue
            line = re.sub(r"^#{1,6}\s*", "", line)
            line = re.sub(r"^[-*•]\s*", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            line = re.sub(r'^(title|section|başlık)\s*:\s*', "", line, flags=re.IGNORECASE)
            line = line.strip().strip('",').strip()
            if 3 <= len(line) <= 90:
                titles.append(line)
    unique: list[str] = []
    for title in titles:
        title = title.strip().strip('"').strip()
        if title and title not in unique and len(title) <= 120:
            unique.append(title)
    if len(unique) < 3:
        return list(fallback)
    return unique[:8]


def summarize_events(events, agents_n: int, rounds: int, platforms: int) -> str:
    actions: dict[str, int] = {}
    by_platform: dict[str, int] = {}
    emotions: dict[str, int] = {}
    for ev in events:
        actions[ev.event_type] = actions.get(ev.event_type, 0) + 1
        by_platform[ev.platform] = by_platform.get(ev.platform, 0) + 1
        emotion = (ev.payload or {}).get("emotion")
        if emotion:
            emotions[str(emotion)] = emotions.get(str(emotion), 0) + 1
    parts = [
        f"Ajan sayısı: {agents_n}",
        f"Tur: {rounds}",
        f"Platform: {platforms}",
        f"Toplam olay: {len(events)}",
    ]
    if actions:
        ranked = sorted(actions.items(), key=lambda kv: -kv[1])[:10]
        parts.append("Aksiyon dağılımı: " + ", ".join(f"{k}={v}" for k, v in ranked))
    if by_platform:
        ranked = sorted(by_platform.items(), key=lambda kv: -kv[1])
        parts.append("Platform dağılımı: " + ", ".join(f"{k}={v}" for k, v in ranked))
    if emotions:
        ranked = sorted(emotions.items(), key=lambda kv: -kv[1])[:6]
        parts.append("Duygu dağılımı: " + ", ".join(f"{k}={v}" for k, v in ranked))
    return "\n".join(parts)


def build_evidence(
    events,
    names: dict,
    source_files: list[str],
    max_events: int = 72,
    max_chars: int = 5600,
) -> tuple[str, list[str]]:
    bibliography: list[str] = []
    for i, filename in enumerate(source_files, start=1):
        bibliography.append(f"[K{i}] Kaynak belge: {filename}")
    total = len(events)
    if total > max_events:
        step = total / max_events
        picked = [events[min(int(i * step), total - 1)] for i in range(max_events)]
    else:
        picked = list(events)
    lines: list[str] = []
    used = 0
    for i, ev in enumerate(picked, start=1):
        payload = ev.payload or {}
        content = str(payload.get("content") or payload.get("action") or "")
        content = re.sub(r"\s+", " ", content).strip()
        if not content:
            continue
        name = names.get(ev.agent_id) or "Ajan"
        line = f"[O{i}] T{ev.round} · {name} ({ev.platform}) · {ev.event_type}: {content[:240]}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        bibliography.append(
            f"[O{i}] Simülasyon olayı · T{ev.round} · {name} ({ev.platform}) · {ev.event_type}"
        )
        used += len(line)
    doc_lines = [f"[K{i}] {filename}" for i, filename in enumerate(source_files, start=1)]
    evidence = "\n".join(
        [
            "Kaynak belgeler:",
            *(doc_lines or ["(belge yok — yalnızca proje tanımı ve şablon kullanıldı)"]),
            "",
            "Simülasyon olayları (örnek):",
            *(lines or ["(olay kaydı yok)"]),
        ]
    )
    return evidence, bibliography


def build_outline_messages(
    *,
    project_name: str,
    template_name: str,
    language: str,
    seed_summary: str,
    stats_text: str,
    source_files: list[str],
) -> list[dict[str, str]]:
    if language == "en":
        system = (
            "You are a senior research analyst. Write in English. "
            'Respond ONLY with JSON: {"sections": ["Title 1", ...]} with 5 to 7 section titles. '
            "Cover executive summary, method/sources, findings, agent behavior, risks, "
            "recommendations and limitations."
        )
    else:
        system = (
            "Sen kıdemli bir araştırma analistisin. Türkçe yaz. "
            'Yalnızca JSON döndür: {"sections": ["Başlık 1", ...]} — 5-7 bölüm başlığı. '
            "Yönetici özeti, yöntem/kaynaklar, bulgular, ajan davranışı, riskler, "
            "öneriler ve sınırlamalar kapsanmalı."
        )
    sources = ", ".join(source_files) if source_files else "yok"
    user = (
        f"Proje: {project_name}\nŞablon: {template_name}\n"
        f"Kaynak belgeler: {sources}\n\n"
        f"Bağlam:\n{seed_summary[:1500]}\n\nİstatistikler:\n{stats_text}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_section_messages(
    *,
    title: str,
    project_name: str,
    language: str,
    evidence: str,
    previous_titles: list[str],
) -> list[dict[str, str]]:
    lang = "English" if language == "en" else "Turkish"
    system = (
        f"You write a single section of a simulation report in {lang}. "
        "Ground every claim in the evidence below. Cite sources inline as [K1] for documents "
        "or [O1] for events. Never invent numbers. 180-320 words. Markdown, no top-level title."
    )
    previous = ", ".join(previous_titles) if previous_titles else "none"
    user = (
        f"Project: {project_name}\nSection: {title}\nPrevious sections: {previous}\n\n"
        f"Evidence:\n{evidence}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def fallback_section_body(title: str, stats_text: str, evidence: str, language: str) -> str:
    if language == "en":
        head = f"**{title}** — this section was generated automatically from simulation data."
        intro = "\n\nHighlights:"
    else:
        head = f"**{title}** — bu bölüm simülasyon verilerinden otomatik derlenmiştir."
        intro = "\n\nÖne çıkan gözlemler:"
    bullets = [line for line in evidence.splitlines() if line.startswith("[O")][:5]
    body = f"{head}\n\n{stats_text}"
    if bullets:
        body += intro + "\n" + "\n".join(f"- {b}" for b in bullets)
    return body


def compose_markdown(
    *,
    title: str,
    meta_lines: list[str],
    sections: list[dict],
    bibliography: list[str],
    disclaimer: str,
) -> str:
    parts: list[str] = [f"# {title}", ""]
    if meta_lines:
        parts.append("  \n".join(meta_lines))
        parts.append("")
    parts.extend([f"> {disclaimer}", ""])
    for section in sections:
        parts.extend([f"## {section['title']}", "", section["body"].strip(), ""])
    if bibliography:
        parts.extend(["## Kaynakça", ""])
        for i, ref in enumerate(bibliography, start=1):
            parts.append(f"{i}. {ref}")
        parts.append("")
    parts.extend(["---", "", f"*{disclaimer}*"])
    return "\n".join(parts).strip() + "\n"


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def markdown_to_html(md: str) -> str:
    out: list[str] = []
    list_mode: str | None = None

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            out.append(f"</{list_mode}>")
            list_mode = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if match:
            close_list()
            level = len(match.group(1))
            out.append(f"<h{level}>{_inline(match.group(2))}</h{level}>")
            continue
        if line.strip() == "---":
            close_list()
            out.append("<hr/>")
            continue
        match = re.match(r"^\s*[-*]\s+(.*)$", line)
        if match:
            if list_mode != "ul":
                close_list()
                out.append("<ul>")
                list_mode = "ul"
            out.append(f"<li>{_inline(match.group(1))}</li>")
            continue
        match = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if match:
            if list_mode != "ol":
                close_list()
                out.append("<ol>")
                list_mode = "ol"
            out.append(f"<li>{_inline(match.group(1))}</li>")
            continue
        match = re.match(r"^>\s?(.*)$", line)
        if match:
            close_list()
            out.append(f"<blockquote>{_inline(match.group(1))}</blockquote>")
            continue
        close_list()
        out.append(f"<p>{_inline(line)}</p>")
    close_list()
    return "\n".join(out)


def html_document(title: str, body_html: str, footer_text: str) -> str:
    page_footer = html.escape(footer_text)
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
@page {{ size: A4; margin: 20mm 17mm 22mm;
  @bottom-center {{ content: "{page_footer} · " counter(page) "/" counter(pages);
    font-size: 7.5pt; color: #6b7280; }} }}
body {{ font-family: "DejaVu Sans", sans-serif; font-size: 10.5pt; line-height: 1.55; color: #111827; }}
h1 {{ font-size: 20pt; margin: 0 0 6pt; color: #0f172a; }}
h2 {{ font-size: 13.5pt; margin: 18pt 0 6pt; color: #1e293b;
  border-bottom: 1px solid #e5e7eb; padding-bottom: 3pt; }}
h3 {{ font-size: 11.5pt; margin: 12pt 0 4pt; }}
p {{ margin: 0 0 8pt; text-align: justify; }}
ul, ol {{ margin: 0 0 8pt 16pt; }}
li {{ margin-bottom: 3pt; }}
blockquote {{ margin: 10pt 0; padding: 6pt 10pt; background: #f8fafc;
  border-left: 3px solid #94a3b8; font-size: 9.5pt; }}
hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 14pt 0; }}
code {{ font-family: "DejaVu Sans Mono", monospace; font-size: 9pt;
  background: #f1f5f9; padding: 0 3pt; }}
</style></head><body>{body_html}</body></html>"""


def render_pdf(markdown_text: str, title: str, disclaimer: str) -> bytes:
    from weasyprint import HTML

    html_str = html_document(title, markdown_to_html(markdown_text), disclaimer)
    return HTML(string=html_str).write_pdf()
