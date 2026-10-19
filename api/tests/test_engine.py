"""Tests run fully offline (mock LLM)."""
import json
import random

from engine.actions import parse_agent_action
from engine.scheduler import ScheduleConfig, pick_active_agents


def test_scheduler_active_counts():
    cfg = ScheduleConfig(agents_n=100, rounds=30, agents_per_hour_min=5,
                         agents_per_hour_max=20)
    rng = random.Random(42)
    agents = list(range(100))
    picked = pick_active_agents(cfg, agents, simulated_hour=12, rng=rng)
    assert 0 < len(picked) <= 20


def test_action_parsing():
    space = ["post", "comment", "like", "silent"]
    a = parse_agent_action(json.dumps({"action": "post", "content": "hi"}), space)
    assert a.action == "post" and a.content == "hi"

    b = parse_agent_action("not json at all", space)
    assert b.action == "silent"
