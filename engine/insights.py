"""Simulation outcome analytics: stance mix, themes, quotes and action mix."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

STANCES = ("positive", "negative", "neutral", "undecided")

POSITIVE_ACTIONS = {
    "like",
    "recommend",
    "purchase",
    "adopt",
    "accept",
    "endorse",
    "support",
    "share",
    "save",
    "promote",
}
NEGATIVE_ACTIONS = {
    "dislike",
    "abandon",
    "churn",
    "oppose",
    "objection",
    "reject",
    "mute",
    "block",
    "report",
    "skip",
}
NEUTRAL_ACTIONS = {
    "browse",
    "compare",
    "comment",
    "post",
    "try",
    "rate",
    "write",
    "counter_offer",
    "silent",
    "ignore",
}

POSITIVE_WORDS = {
    "sevdim",
    "severim",
    "beğendim",
    "beğeniyorum",
    "beğen",
    "güzel",
    "harika",
    "mükemmel",
    "olumlu",
    "destek",
    "destekliyorum",
    "iyi",
    "başarılı",
    "faydalı",
    "güvenilir",
    "mantıklı",
    "öneririm",
    "tavsiye",
    "yararlı",
    "kaliteli",
    "ilgi",
    "ilginç",
    "umut",
    "umutlu",
    "mutlu",
    "memnun",
    "heyecan",
    "ilham",
    "onay",
    "like",
    "love",
    "good",
    "great",
    "useful",
    "recommend",
    "impressive",
    "happy",
    "excellent",
    "helpful",
}
NEGATIVE_WORDS = {
    "sevmedim",
    "beğenmedim",
    "beğenmiyorum",
    "kötü",
    "berbat",
    "rezalet",
    "olumsuz",
    "karşıyım",
    "gereksiz",
    "pahalı",
    "yetersiz",
    "güvenmiyorum",
    "güvensiz",
    "riskli",
    "aldatıcı",
    "sinir",
    "kızgın",
    "öfkeli",
    "üzgün",
    "hayal",
    "kırıklığı",
    "kaygı",
    "endişe",
    "korku",
    "sorun",
    "sorunlu",
    "eksik",
    "zayıf",
    "saçma",
    "anlamsız",
    "başarısız",
    "dislike",
    "bad",
    "hate",
    "overpriced",
    "useless",
    "scam",
    "disappointing",
    "poor",
    "angry",
    "worry",
}
UNCERTAIN_WORDS = {
    "kararsız",
    "kararsızım",
    "emin",
    "bilemiyorum",
    "bilmiyorum",
    "belki",
    "şüphe",
    "şüpheli",
    "muallak",
    "tartışılır",
    "uncertain",
    "unsure",
    "maybe",
}
POSITIVE_EMOTIONS = {
    "memnun",
    "mutlu",
    "mutluluk",
    "sevinç",
    "umut",
    "pozitif",
    "güven",
    "heyecan",
    "ilham",
    "onay",
    "destek",
    "sevgi",
    "huzur",
    "gurur",
    "iyi",
    "optimist",
    "hopeful",
    "happy",
    "positive",
    "enthusiastic",
    "motivated",
}
NEGATIVE_EMOTIONS = {
    "öfke",
    "öfkeli",
    "kız",
    "sinir",
    "kaygı",
    "endişe",
    "korku",
    "üzgün",
    "üzüntü",
    "sıkıntı",
    "olumsuz",
    "şüphe",
    "kuşku",
    "eleştirel",
    "saldırgan",
    "isyan",
    "düşük",
    "kırgın",
    "skeptik",
    "skeptical",
    "critical",
    "angry",
    "anxious",
    "negative",
}
UNCERTAIN_EMOTIONS = {"kararsız", "nötr", "neutral", "neutro", "neutal", "belirsiz"}

STOPWORDS = {
    "acaba",
    "ama",
    "ancak",
    "artık",
    "aslında",
    "bana",
    "bazı",
    "belki",
    "ben",
    "bence",
    "beni",
    "bile",
    "bir",
    "biraz",
    "birçok",
    "biri",
    "biz",
    "bu",
    "buna",
    "bunu",
    "bunun",
    "çok",
    "çünkü",
    "da",
    "daha",
    "de",
    "değil",
    "diye",
    "en",
    "gibi",
    "hem",
    "her",
    "hiç",
    "için",
    "ile",
    "ise",
    "kadar",
    "ki",
    "kim",
    "mı",
    "mi",
    "mu",
    "mü",
    "nasıl",
    "ne",
    "neden",
    "nerede",
    "o",
    "olarak",
    "oldu",
    "olduğu",
    "olan",
    "onu",
    "onun",
    "öyle",
    "sadece",
    "şey",
    "şu",
    "tabii",
    "tüm",
    "ve",
    "veya",
    "ya",
    "yani",
    "yine",
    "zaten",
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "have",
    "will",
    "about",
    "just",
    "very",
    "they",
    "their",
    "what",
    "when",
    "your",
    "you",
    "but",
    "not",
    "are",
    "was",
    "were",
    "can",
    "would",
    "could",
    "should",
    "our",
    "out",
    "all",
    "its",
    "it's",
    "into",
    "than",
    "then",
}

_WORD_RE = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+")
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def normalize_stance(value) -> str | None:
    text = str(value or "").strip().casefold().replace("i̇", "i")
    if text in {"positive", "pos", "olumlu", "destek", "destekliyor", "beğendim", "like"}:
        return "positive"
    if text in {"negative", "neg", "olumsuz", "karşı", "beğenmedim", "dislike"}:
        return "negative"
    if text in {"neutral", "nötr", "notr", "karışık"}:
        return "neutral"
    if text in {"undecided", "kararsız", "kararsiz", "belirsiz", "bilmiyorum"}:
        return "undecided"
    return None


def _normalize_text(value) -> str:
    return str(value or "").casefold().replace("i̇", "i")


def _words(value) -> list[str]:
    return [word for word in _WORD_RE.findall(_normalize_text(value)) if len(word) >= 3]


def _text_signal(value) -> int:
    words = _words(value)
    positive = sum(1 for word in words if word in POSITIVE_WORDS)
    negative = sum(1 for word in words if word in NEGATIVE_WORDS)
    uncertain = sum(1 for word in words if word in UNCERTAIN_WORDS)
    if uncertain > max(positive, negative) and uncertain >= 2:
        return 0
    return positive - negative


def _has_uncertainty(value) -> bool:
    return any(word in UNCERTAIN_WORDS for word in _words(value))


def _emotion_signal(value) -> int:
    text = _normalize_text(value)
    if not text:
        return 0
    if any(key in text for key in ("onaylamayan", "olumsuz", "karşı", "nefret")):
        return -1
    if any(key in text for key in NEGATIVE_EMOTIONS):
        return -1
    if any(key in text for key in UNCERTAIN_EMOTIONS):
        return 0
    if any(key in text for key in POSITIVE_EMOTIONS):
        return 1
    return 0


def _event_signal(event) -> tuple[str, float, bool]:
    payload = getattr(event, "payload", None) or {}
    explicit = normalize_stance(payload.get("stance"))
    if explicit:
        return explicit, 4.0, True
    action = str(getattr(event, "event_type", "") or "")
    content = payload.get("content")
    emotion = payload.get("emotion")
    score = 0.0
    evidence = False
    if action in POSITIVE_ACTIONS:
        score += 1.6
        evidence = True
    elif action in NEGATIVE_ACTIONS:
        score -= 1.6
        evidence = True
    elif action in NEUTRAL_ACTIONS and action not in {"silent", "ignore"}:
        evidence = True
    emo = _emotion_signal(emotion)
    if emo:
        score += emo * 1.1
        evidence = True
    text = _text_signal(content)
    if text:
        score += max(-1.5, min(1.5, text * 0.55))
        evidence = True
    if not evidence:
        return "undecided", 0.0, False
    if score == 0 and _has_uncertainty(content):
        return "undecided", 0.0, True
    if score >= 0.6:
        return "positive", score, True
    if score <= -0.6:
        return "negative", score, True
    return "neutral", score, True


def _agent_stances(events) -> dict:
    by_agent: dict = defaultdict(list)
    for event in events:
        key = getattr(event, "agent_id", None)
        if key is None:
            key = f"event-{getattr(event, 'id', id(event))}"
        by_agent[key].append(event)
    result = {}
    for key, agent_events in by_agent.items():
        explicit = [
            (idx, normalize_stance((getattr(ev, "payload", None) or {}).get("stance")))
            for idx, ev in enumerate(agent_events)
        ]
        explicit = [(idx, stance) for idx, stance in explicit if stance]
        if explicit:
            result[key] = explicit[-1][1]
            continue
        score = 0.0
        evidence = 0
        uncertain = 0
        for ev in agent_events:
            stance, value, has_evidence = _event_signal(ev)
            if has_evidence:
                score += value
                evidence += 1
                if stance == "undecided":
                    uncertain += 1
        if evidence == 0:
            result[key] = "undecided"
        elif score >= 0.8:
            result[key] = "positive"
        elif score <= -0.8:
            result[key] = "negative"
        elif uncertain == evidence:
            result[key] = "undecided"
        else:
            result[key] = "neutral"
    return result


def _round_label(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _keywords(events, stance: str) -> list[dict]:
    counter: Counter = Counter()
    for event in events:
        event_stance, _score, evidence = _event_signal(event)
        if not evidence or event_stance != stance:
            continue
        content = (getattr(event, "payload", None) or {}).get("content")
        for word in _words(content):
            if word in STOPWORDS or word in POSITIVE_WORDS or word in NEGATIVE_WORDS:
                continue
            counter[word] += 1
    return [{"label": word, "count": count} for word, count in counter.most_common(7)]


def _quotes(events, names: dict, stance: str) -> list[dict]:
    rows = []
    seen = set()
    for event in events:
        event_stance, _score, evidence = _event_signal(event)
        if not evidence or event_stance != stance:
            continue
        payload = getattr(event, "payload", None) or {}
        content = str(payload.get("content") or "").strip()
        if len(content) < 30:
            continue
        key = content[:140]
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "agent": names.get(getattr(event, "agent_id", None)) or "Ajan",
                "content": content[:320],
                "emotion": payload.get("emotion"),
                "round": _round_label(getattr(event, "round", 0)),
                "action": getattr(event, "event_type", ""),
            }
        )
        if len(rows) >= 4:
            break
    return rows


def build_run_insights(
    events,
    agent_names: dict | None = None,
    language: str = "tr",
    rounds: int = 0,
) -> dict:
    names = agent_names or {}
    rows = [event for event in events if getattr(event, "event_type", "") != "system"]
    stances = {key: "undecided" for key in names}
    stances.update(_agent_stances(rows))
    counts = {stance: 0 for stance in STANCES}
    for stance in stances.values():
        counts[stance] += 1
    total = sum(counts.values())
    percentages = {
        stance: round((counts[stance] * 100 / total), 1) if total else 0.0
        for stance in STANCES
    }
    positive_negative = counts["positive"] + counts["negative"]
    action_counts = Counter(str(getattr(event, "event_type", "") or "") for event in rows)
    emotion_counts = Counter(
        str((getattr(event, "payload", None) or {}).get("emotion") or "").strip()
        for event in rows
    )
    emotion_counts.pop("", None)

    platform_rows: dict = defaultdict(lambda: {stance: 0 for stance in STANCES})
    for event in rows:
        platform = str(getattr(event, "platform", "") or "bilinmiyor")
        stance, _score, evidence = _event_signal(event)
        if evidence:
            platform_rows[platform][stance] += 1

    round_rows: dict = defaultdict(lambda: {stance: 0 for stance in STANCES})
    for event in rows:
        stance, _score, evidence = _event_signal(event)
        if evidence:
            round_rows[_round_label(getattr(event, "round", 0))][stance] += 1

    return {
        "language": "en" if language == "en" else "tr",
        "rounds": int(rounds or max((_round_label(getattr(ev, "round", 0)) for ev in rows), default=0)),
        "events": len(rows),
        "participants": total,
        "audience_size": len(names) or total,
        "summary": {
            **counts,
            "total": total,
            "percentages": percentages,
            "approval_rate": (
                round(counts["positive"] * 100 / positive_negative, 1)
                if positive_negative
                else None
            ),
        },
        "platforms": [
            {"platform": platform, **values, "total": sum(values.values())}
            for platform, values in sorted(
                platform_rows.items(), key=lambda item: -sum(item[1].values())
            )
        ],
        "trend": [
            {"round": round_no, **values}
            for round_no, values in sorted(round_rows.items())
        ],
        "actions": [
            {
                "action": action,
                "count": count,
                "percentage": round(count * 100 / len(rows), 1) if rows else 0.0,
            }
            for action, count in action_counts.most_common(12)
        ],
        "emotions": [
            {"label": label, "count": count}
            for label, count in emotion_counts.most_common(10)
        ],
        "keywords": {stance: _keywords(rows, stance) for stance in STANCES},
        "quotes": {stance: _quotes(rows, names, stance) for stance in STANCES},
    }


def format_insights_markdown(insights: dict, language: str = "tr") -> str:
    summary = insights.get("summary") or {}
    percentages = summary.get("percentages") or {}
    if language == "en":
        labels = {
            "positive": "Positive",
            "negative": "Negative",
            "neutral": "Neutral",
            "undecided": "Undecided",
        }
        title = "Metric summary"
        intro = (
            f"{summary.get('total', 0)} participants expressed a simulated stance. "
            "These are synthetic signals, not a real survey."
        )
        action_title = "Most frequent actions"
        reason_title = "Repeating themes"
    else:
        labels = {
            "positive": "Olumlu",
            "negative": "Olumsuz",
            "neutral": "Nötr",
            "undecided": "Kararsız",
        }
        title = "Özet metrikler"
        intro = (
            f"{summary.get('total', 0)} katılımcı simüle edilmiş bir görüş bildirdi. "
            "Bunlar sentetik sinyallerdir; gerçek anket sonucu değildir."
        )
        action_title = "En sık aksiyonlar"
        reason_title = "Öne çıkan temalar"
    lines = [f"**{title}**", "", intro, ""]
    unit = "people" if language == "en" else "kişi"
    for stance in STANCES:
        lines.append(
            f"- {labels[stance]}: {summary.get(stance, 0)} {unit} "
            f"(%{percentages.get(stance, 0)})"
        )
    actions = insights.get("actions") or []
    if actions:
        lines.extend(["", f"**{action_title}**", ""])
        lines.append(", ".join(f"{a['action']} ({a['count']})" for a in actions[:8]))
    keywords = insights.get("keywords") or {}
    themes = [
        f"{labels[stance]}: " + ", ".join(k["label"] for k in keywords.get(stance, [])[:4])
        for stance in STANCES
        if keywords.get(stance)
    ]
    if themes:
        lines.extend(["", f"**{reason_title}**", ""])
        lines.extend(f"- {line}" for line in themes)
    return "\n".join(lines)
