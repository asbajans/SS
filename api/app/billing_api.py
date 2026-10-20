"""Stripe-related endpoints; full billing in F5 (see agent.md)."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutIn(BaseModel):
    price_id: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None


@router.get("/plans")
async def plans() -> list[dict]:
    return [
        {"key": "free", "price": 0, "token_budget": 1_000_000, "agents": 50, "rounds": 20},
        {"key": "starter", "price": 29, "token_budget": 8_000_000, "agents": 150, "rounds": 40},
        {"key": "pro", "price": 99, "token_budget": 25_000_000, "agents": 300, "rounds": 90},
    ]


@router.post("/checkout")
async def checkout(body: CheckoutIn) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=501,
            detail="Stripe not configured (F5). Set STRIPE_SECRET_KEY to enable checkout.",
        )
    # F5: real stripe.checkout.Session.create here.
    raise HTTPException(status_code=501, detail="Stripe checkout pending (F5)")


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    if not settings.stripe_webhook_secret:
        return {"received": False, "message": "Stripe integration pending (F5)"}
    # F5: verify signature, handle checkout.session.completed → activate plan.
    return {"received": False, "message": "Stripe webhook pending (F5)"}
