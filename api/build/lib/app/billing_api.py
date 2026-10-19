"""Stripe-related endpoints; full billing in F5 (see agent.md)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/plans")
async def plans() -> list[dict]:
    return [
        {"key": "free", "price": 0, "token_budget": 1_000_000, "agents": 50, "rounds": 20},
        {"key": "starter", "price": 29, "token_budget": 8_000_000, "agents": 150, "rounds": 40},
        {"key": "pro", "price": 99, "token_budget": 25_000_000, "agents": 300, "rounds": 90},
    ]


@router.post("/webhook")
async def stripe_webhook() -> dict:
    # TODO: signature verification + checkout.session.completed etc. (F5)
    return {"received": False, "message": "Stripe integration pending (F5)"}
