"""Report helper tests (offline)."""
from engine.report import compose_markdown, markdown_to_html, parse_outline


def test_parse_outline_json():
    text = '{"sections": ["Özet", "Bulgular", "Öneriler"]}'
    assert parse_outline(text, ["X"]) == ["Özet", "Bulgular", "Öneriler"]


def test_parse_outline_bullets():
    text = "1. Özet\n2. Bulgular\n- Yöntem"
    assert parse_outline(text, ["X"]) == ["Özet", "Bulgular", "Yöntem"]


def test_parse_outline_fallback():
    assert parse_outline("bu bir JSON degil", ["X"]) == ["X"]


def test_markdown_to_html_escapes():
    out = markdown_to_html("## Başlık\n\n**kalın** <script>")
    assert "<h2>Başlık</h2>" in out
    assert "<strong>kalın</strong>" in out
    assert "&lt;script&gt;" in out
    assert "<script>" not in out


def test_compose_markdown_includes_bibliography_and_disclaimer():
    md = compose_markdown(
        title="T",
        meta_lines=["Proje: X"],
        sections=[{"title": "S", "body": "B"}],
        bibliography=["[K1] Belge"],
        disclaimer="UYARI",
    )
    assert "## S" in md
    assert "[K1] Belge" in md
    assert "UYARI" in md
