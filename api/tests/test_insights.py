"""Outcome analytics and blog editor helpers."""
from types import SimpleNamespace

from app.blog_editor import build_blog_messages, parse_generated_post, slugify
from engine.insights import build_run_insights, format_insights_markdown
from engine.templates import get_template


def event(agent, text="", action="comment", stance=None, emotion="", platform="forum", round_no=1):
    payload = {"content": text}
    if stance:
        payload["stance"] = stance
    if emotion:
        payload["emotion"] = emotion
    return SimpleNamespace(
        id=f"{agent}-{round_no}-{text[:8]}",
        agent_id=agent,
        event_type=action,
        payload=payload,
        platform=platform,
        round=round_no,
    )


def test_explicit_stance_wins_over_negative_text():
    events = [event("a1", "kötü ve gereksiz", stance="positive")]
    result = build_run_insights(events, {"a1": "Ada"})
    assert result["summary"]["positive"] == 1
    assert result["summary"]["percentages"]["positive"] == 100.0


def test_fallback_classifies_actions_and_text():
    events = [
        event("a1", "harika ve faydalı", action="like"),
        event("a2", "kötü, güvenmiyorum", action="dislike"),
        event("a3", "bilmiyorum belki", action="comment"),
    ]
    result = build_run_insights(events, {"a1": "Ada", "a2": "Bora", "a3": "Cem"})
    assert result["summary"]["positive"] == 1
    assert result["summary"]["negative"] == 1
    assert result["summary"]["undecided"] == 1
    assert result["summary"]["total"] == 3
    assert result["summary"]["approval_rate"] == 50.0


def test_inactive_agents_count_as_undecided():
    result = build_run_insights([], {"a1": "Ada", "a2": "Bora"})
    assert result["summary"]["undecided"] == 2
    assert result["summary"]["total"] == 2


def test_breakdowns_and_markdown():
    events = [
        event("a1", "harika", action="like", platform="x", round_no=1),
        event("a2", "kötü", action="dislike", platform="x", round_no=2),
    ]
    result = build_run_insights(events, {"a1": "Ada", "a2": "Bora"}, language="tr", rounds=2)
    assert result["platforms"][0]["platform"] == "x"
    assert [row["round"] for row in result["trend"]] == [1, 2]
    assert result["actions"][0]["count"] == 1
    markdown = format_insights_markdown(result, "tr")
    assert "Özet metrikler" in markdown
    assert "Olumlu" in markdown


def test_social_post_template_available():
    tpl = get_template("social_post_test")
    assert "dislike" in tpl.action_space
    assert tpl.sim_defaults["agents_n"] == 80
    assert "gönderi" in tpl.description.lower()


def test_slugify_turkish():
    assert slugify("Sosyal Medya İçin Ölçüm Rehberi") == "sosyal-medya-icin-olcum-rehberi"
    assert slugify("!!!") == "yazi"


def test_parse_generated_post():
    raw = """```json
    {"title_tr": "Başlık", "title_en": "Title", "excerpt_tr": "Kısa özet",
     "excerpt_en": "Short summary", "body_tr": "## Bölüm\\nMetin", "body_en": "## Section\\nText"}
    ```"""
    post = parse_generated_post(raw, "konu")
    assert post["title_tr"] == "Başlık"
    assert post["body_en"].startswith("## Section")


def test_parse_generated_post_rejects_incomplete_json():
    try:
        parse_generated_post('{"title_tr": "x"}', "konu")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_blog_messages_include_topic_and_recent_titles():
    messages = build_blog_messages("Konu", "kelime", ["Eski yazı"])
    assert messages[0]["role"] == "system"
    assert "Konu" in messages[1]["content"]
    assert "Eski yazı" in messages[1]["content"]
