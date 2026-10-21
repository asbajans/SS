"""Simulation loop helpers: agent prompts + recent-event digests."""
import json


def build_agent_messages(
    agent,
    template,
    round_no: int,
    simulated_hour: int,
    recent: list[dict],
    language: str = "tr",
    brief: str = "",
) -> list[dict]:
    actions = ", ".join(template.action_space)
    system = (
        "You are role-playing a synthetic community member inside an agent-based "
        "simulation. Stay in character, stay consistent with your persona, and react to "
        "what happened recently. Respond as strict JSON with keys: action (one of the "
        f"given actions), content (short text in language '{language}'), "
        "target (optional agent index or topic), emotion (short label), "
        "stance (one of positive, negative, neutral, undecided) expressing your view of "
        "the tested subject. Do not mention being an AI. Do not break the JSON contract."
    )
    lines = []
    for ev in recent[-10:]:
        who = ev.get("agent_name") or "topluluk"
        text = (ev.get("content") or "")[:220]
        lines.append(f"- {who}: {ev.get('event_type')} / {text}")
    subject = f"\nTest material / brief:\n{brief[:1800]}\n" if brief else "\n"
    user = (
        f"Persona: {agent.persona or agent.bio or agent.name}\n"
        f"Platform: {agent.platform}\n"
        f"Round {round_no} (simulated hour {simulated_hour:02d}:00).\n"
        f"Available actions: {actions}\n"
        f"{subject}"
        f"Recent timeline:\n" + ("\n".join(lines) if lines else "- (empty timeline)")
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def digest_text(content: str | None, limit: int = 240) -> str:
    if not content:
        return ""
    text = content.strip()
    if len(text) <= limit:
        return text
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("content"):
            text = str(data["content"])
    except (json.JSONDecodeError, TypeError):
        pass
    return text[:limit]
