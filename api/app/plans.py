"""Plan catalog and per-plan simulation limits."""
from app.config import settings

PLANS = (
    {"key": "free", "price": 0, "token_budget": 1_000_000, "agents": 80, "rounds": 24},
    {"key": "starter", "price": 29, "token_budget": 8_000_000, "agents": 150, "rounds": 40},
    {"key": "pro", "price": 99, "token_budget": 25_000_000, "agents": 300, "rounds": 80},
)


def _price_id(key: str) -> str:
    if key == "starter":
        return settings.stripe_price_starter or settings.stripe_monthly_price_id
    if key == "pro":
        return settings.stripe_price_pro
    return ""


def plan_catalog() -> list[dict]:
    rows = []
    for plan in PLANS:
        row = dict(plan)
        row["price_id"] = _price_id(plan["key"])
        row["checkout_enabled"] = bool(settings.stripe_secret_key and row["price_id"])
        rows.append(row)
    return rows


def plan_limits(key: str | None) -> dict:
    row = next((p for p in PLANS if p["key"] == key), PLANS[0])
    return {
        "plan": row["key"],
        "token_budget": row["token_budget"],
        "agents": row["agents"],
        "rounds": row["rounds"],
    }


def plan_by_price(price_id: str | None) -> dict | None:
    if not price_id:
        return None
    return next((p for p in plan_catalog() if p["price_id"] == price_id), None)
