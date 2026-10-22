"""SEO helpers: sitemap, robots, llms.txt, RSS, duplicate detection (F11)."""
from datetime import UTC, datetime

from app.seo import (
    AI_BOT_TOKENS,
    SimilarityIndex,
    abs_url,
    article_jsonld,
    is_indexable,
    keyword_density,
    llms_txt,
    normalize_base_url,
    robots_txt,
    rss_xml,
    sitemap_index_xml,
    strip_markup,
    urlset_xml,
)

BASE = "https://socialsimulator.com.tr"


def test_normalize_base_url():
    assert normalize_base_url("https://a.com/") == "https://a.com"
    assert normalize_base_url("a.com") == "https://a.com"
    assert normalize_base_url("https://a.com/sub/") == "https://a.com/sub"
    assert normalize_base_url("", "https://fallback.com") == "https://fallback.com"


def test_abs_url():
    assert abs_url(BASE, "/blog/x") == "https://socialsimulator.com.tr/blog/x"
    assert abs_url(BASE, "blog/x") == "https://socialsimulator.com.tr/blog/x"


def test_is_indexable_blocks_app_routes():
    assert is_indexable("/")
    assert is_indexable("/blog")
    assert not is_indexable("/app")
    assert not is_indexable("/app/settings")
    assert not is_indexable("/login")


def test_sitemap_index_and_urlset():
    index = sitemap_index_xml(BASE, [{"path": "sitemap-pages.xml", "lastmod": "2026-01-01T00:00:00Z"}])
    assert index.startswith("<?xml")
    assert "<sitemapindex" in index
    assert "https://socialsimulator.com.tr/sitemap-pages.xml" in index

    urls = urlset_xml([
        {
            "url": "https://socialsimulator.com.tr/blog/a",
            "lastmod": "2026-01-01T00:00:00Z",
            "changefreq": "monthly",
            "priority": 0.8,
            "images": ["https://socialsimulator.com.tr/og.png"],
        }
    ])
    assert "<urlset" in urls
    assert "<loc>https://socialsimulator.com.tr/blog/a</loc>" in urls
    assert "<priority>0.8</priority>" in urls
    assert "<image:loc>https://socialsimulator.com.tr/og.png</image:loc>" in urls


def test_robots_txt_contains_sitemap_and_ai_rules():
    txt = robots_txt(BASE, block_ai_bots=False, allow_ai_bots="GPTBot, ClaudeBot")
    assert "Sitemap: https://socialsimulator.com.tr/sitemap.xml" in txt
    # whitelisted bots always get an explicit Allow
    assert "User-agent: GPTBot\nAllow: /" in txt
    assert "User-agent: ClaudeBot\nAllow: /" in txt
    # not whitelisted + block switch off -> falls back to "User-agent: *"
    assert "User-agent: PerplexityBot" not in txt


def test_robots_txt_blocks_non_whitelisted_ai_bots_when_enabled():
    txt = robots_txt(BASE, block_ai_bots=True, allow_ai_bots="GPTBot")
    # whitelisted bots stay allowed even in strict mode
    assert "User-agent: GPTBot\nAllow: /" in txt
    # everything else is blocked
    assert "User-agent: PerplexityBot\nDisallow: /" in txt
    assert "User-agent: ClaudeBot\nDisallow: /" in txt
    for token in AI_BOT_TOKENS:
        assert f"User-agent: {token}" in txt


def test_robots_txt_extra_rules_appended():
    txt = robots_txt(BASE, extra="Disallow: /secret")
    assert txt.rstrip().endswith("Disallow: /secret")


def test_llms_txt_lists_sections():
    out = llms_txt(BASE, [{
        "title": "Site",
        "description": "desc",
        "items": [{"title": "Blog", "url": "https://socialsimulator.com.tr/blog", "note": "yazılar"}],
    }])
    assert out.startswith("# Site")
    assert "## Site" in out
    assert "- [Blog](https://socialsimulator.com.tr/blog): yazılar" in out


def test_rss_xml_contains_items():
    out = rss_xml(BASE, "Site", [{
        "title": "Yazı",
        "url": "https://socialsimulator.com.tr/blog/a",
        "description": "özet",
        "pubdate": "Mon, 01 Jan 2026 00:00:00 +0000",
    }])
    assert "<rss version=\"2.0\"" in out
    assert "<title>Yazı</title>" in out
    assert "https://socialsimulator.com.tr/blog/a" in out


def test_article_jsonld_shape():
    data = article_jsonld(
        base_url=BASE,
        title="Başlık",
        description="Açıklama",
        path="/blog/a",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="Social Simulator",
        image="/og.png",
        keywords="test",
    )
    assert data["@type"] == "BlogPosting"
    assert data["url"] == "https://socialsimulator.com.tr/blog/a"
    assert data["datePublished"].startswith("2026-01-01")
    assert data["image"] == "https://socialsimulator.com.tr/og.png"
    assert data["author"]["name"] == "Social Simulator"


def test_duplicate_detection_flags_identical_content():
    body = "sentetik topluluk simulasyonu ile kampanya etkisini olcuyor ve davranis analizi yapiyoruz"
    idx = SimilarityIndex()
    idx.add("/a", body, "Başlık A")
    idx.add("/b", body, "Başlık A")
    pairs = idx.pairs(threshold=0.3)
    assert len(pairs) == 1
    assert pairs[0].similarity > 0.9


def test_duplicate_detection_ignores_distinct_content():
    idx = SimilarityIndex()
    idx.add("/a", "simulasyon metodolojisi ve raporlama yaklasimi", "A")
    idx.add("/b", "fiyat artisi ve kriz yonetimi senaryolari", "B")
    assert idx.pairs(threshold=0.3) == []


def test_keyword_density():
    text = "simulasyon simulasyon rapor rapor rapor"
    assert keyword_density(text, "simulasyon") == 40.0
    assert keyword_density(text, "yok") == 0.0


def test_strip_markup_removes_syntax():
    out = strip_markup("## Başlık\n\n**kalın** metin `kod` [bağlantı](https://x.com)")
    assert "##" not in out
    assert "**" not in out
    assert "Başlık" in out
