"""Scheduler: activation sampling per round (peak/off-peak aware)."""
import random
from dataclasses import dataclass


@dataclass
class ScheduleConfig:
    agents_n: int
    rounds: int
    platforms: int = 1
    peak_hours: tuple[int, ...] = (19, 20, 21, 22)
    off_peak_hours: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    peak_multiplier: float = 1.5
    off_peak_multiplier: float = 0.3
    activity_level: float = 0.5


def pick_active_agents(cfg: ScheduleConfig, agent_indices: list[int], simulated_hour: int,
                       rng: random.Random | None = None) -> list[int]:
    """Port-free clean implementation: sample a target size multiplier-adjusted
    towards peak/off-peak, then filter by agent availability."""
    rng = rng or random
    if simulated_hour in cfg.off_peak_hours:
        mult = cfg.off_peak_multiplier
    elif simulated_hour in cfg.peak_hours:
        mult = cfg.peak_multiplier
    else:
        mult = 1.0

    target = int(rng.uniform(cfg.agents_per_hour_min, cfg.agents_per_hour_max) * mult)
    candidates = [
        i for i in agent_indices if rng.random() < cfg.activity_level
    ]
    if not candidates:
        return []
    k = min(max(target, 0), len(candidates))
    return rng.sample(candidates, k)
