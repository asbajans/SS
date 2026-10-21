"""AI blog editor prompts and generated-post parsing."""
import json
import re
from datetime import UTC, datetime

_SLUG_MAP = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "Ç": "c",
        "Ğ": "g",
        "İ": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
    }
)


def slugify(value: str, fallback: str = "yazi") -> str:
    text = str(value or "").translate(_SLUG_MAP).casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:100] or fallback).strip("-")


def build_blog_messages(topic: str, keywords: str, existing_titles: list[str]) -> list[dict[str, str]]:
    system = (
        "You are the editor of the Social Simulation research blog. Write a practical, "
        "original bilingual article for product, research and marketing teams. "
        "Turkish and English versions must convey the same substance. Use Markdown with "
        "at least three '## ' subheadings in each body. Be concrete, avoid hype, never "
        "promise exact survey accuracy, and state that synthetic simulations are not a "
        "replacement for real user research. Respond ONLY with a JSON object using keys: "
        "title_tr, title_en, excerpt_tr, excerpt_en, body_tr, body_en. "
        "Titles at most 80 characters, excerpts 120-220 characters, bodies 450-700 words."
    )
    recent = "\n".join(f"- {title}" for title in existing_titles[:12]) or "- (none)"
    user = (
        f"Topic: {topic}\n"
        f"Keywords: {keywords or '(none)'}\n"
        f"Recently published titles to avoid duplicating:\n{recent}\n"
        f"Today: {datetime.now(UTC).strftime('%Y-%m-%d')}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _clean(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def parse_generated_post(raw: str, topic: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("blog model did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("blog model returned an invalid object")
    post = {
        "title_tr": _clean(data.get("title_tr") or topic, 80),
        "title_en": _clean(data.get("title_en") or topic, 80),
        "excerpt_tr": _clean(data.get("excerpt_tr"), 320),
        "excerpt_en": _clean(data.get("excerpt_en"), 320),
        "body_tr": _clean(data.get("body_tr"), 14000),
        "body_en": _clean(data.get("body_en"), 14000),
    }
    missing = [key for key, value in post.items() if not value]
    if missing:
        raise ValueError(f"blog post missing fields: {', '.join(missing)}")
    return post
