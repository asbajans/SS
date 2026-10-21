"""Agent action schema + parsing."""
import json
from dataclasses import dataclass
from typing import Any

STANCES = ("positive", "negative", "neutral", "undecided")


def normalize_stance(value) -> str | None:
    text = str(value or "").strip().casefold().replace("i̇", "i")
    mapping = {
        "positive": "positive",
        "olumlu": "positive",
        "destek": "positive",
        "beğendim": "positive",
        "negative": "negative",
        "olumsuz": "negative",
        "karşı": "negative",
        "beğenmedim": "negative",
        "neutral": "neutral",
        "nötr": "neutral",
        "notr": "neutral",
        "undecided": "undecided",
        "kararsız": "undecided",
        "kararsiz": "undecided",
        "belirsiz": "undecided",
    }
    return mapping.get(text)


@dataclass
class AgentAction:
    action: str          # one of TopicTemplate.action_space or "silent"
    content: str | None = None
    target: Any = None
    emotion: str | None = None
    stance: str | None = None


def parse_agent_action(raw_text: str, action_space: list[str]) -> AgentAction:
    """Gateway guarantees max_tokens; we still tolerate malformed output."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return AgentAction(action="silent", content=raw_text[:500])

    action = data.get("action", "silent")
    if action not in action_space and action != "silent":
        action = "silent"
    return AgentAction(
        action=action,
        content=data.get("content"),
        target=data.get("target"),
        emotion=data.get("emotion"),
        stance=normalize_stance(data.get("stance")),
    )
