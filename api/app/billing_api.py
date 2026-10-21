"""Stripe billing: plans, checkout, portal and webhook sync."""
import asyncio
import uuid
from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.config import settings
from app.db import AsyncSessionLocal
from app.models import BillingEvent, CreditLedger, User
from app.plans import (
    credit_catalog,
    free_access_expired,
    free_until,
    get_plan,
    get_plan_by_price,
    get_plan_limits,
    plan_catalog,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutIn(BaseModel):
    plan: str | None = None
    credit_pack: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None


def _base_url() -> str:
    return settings.public_base_url.rstrip("/")


def _period_end(subscription) -> datetime | None:
    items = ((subscription.get("items") or {}).get("data")) or []
    ts = items[0].get("current_period_end") if items else None
    if not ts:
        ts = subscription.get("current_period_end")
    return datetime.fromtimestamp(int(ts), UTC) if ts else None


def _billing_enabled() -> bool:
    return bool(settings.stripe_secret_key)


@router.get("/plans")
async def plans(db: AsyncSession = Depends(get_db)) -> dict:
    rows = await plan_catalog(db)
    packs = await credit_catalog(db)
    return {
        "plans": rows,
        "credit_packs": packs,
        "checkout_enabled": _billing_enabled(),
        "publishable_key": settings.stripe_publishable_key,
    }


@router.get("/me")
async def billing_me(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    limits = await get_plan_limits(db, user.plan)
    return {
        "plan": user.plan,
        "billing_status": user.billing_status,
        "monthly_token_budget": user.monthly_token_budget,
        "monthly_token_used": user.monthly_token_used,
        "agents_limit": limits["agents"],
        "rounds_limit": limits["rounds"],
        "free_days": limits["free_days"],
        "free_until": (
            free_until(user.created_at, limits["free_days"]).isoformat()
            if user.plan == "free" and limits["free_days"] > 0 and user.created_at
            else None
        ),
        "free_expired": bool(
            user.plan == "free"
            and free_access_expired(user.created_at, limits["free_days"])
        ),
        "credit_balance": user.credit_balance,
        "billing_period_end": (
            user.billing_period_end.isoformat() if user.billing_period_end else None
        ),
        "has_customer": bool(user.stripe_customer_id),
        "checkout_enabled": _billing_enabled(),
        "publishable_key": settings.stripe_publishable_key,
    }


async def _ensure_customer(db: AsyncSession, user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = await asyncio.to_thread(
        stripe.Customer.create,
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


@router.post("/checkout")
async def checkout(
    body: CheckoutIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=501,
            detail="Stripe yapılandırılmadı (STRIPE_SECRET_KEY gerekli)",
        )
    stripe.api_key = settings.stripe_secret_key
    plan = await get_plan(db, body.plan) if body.plan and body.plan != "free" else None
    pack = next((p for p in await credit_catalog(db) if p["key"] == body.credit_pack), None)
    if (plan is None) == (pack is None):
        raise HTTPException(status_code=400, detail="plan veya credit_pack seçin")
    if plan is not None and not plan["price_id"]:
        raise HTTPException(status_code=400, detail="bu plan için fiyat tanımlı değil")
    if pack is not None and not pack["price_id"]:
        raise HTTPException(status_code=400, detail="kredi paketi fiyatı tanımlı değil")

    success_url = body.success_url or f"{_base_url()}/app/billing?checkout=success"
    cancel_url = body.cancel_url or f"{_base_url()}/app/billing?checkout=cancel"
    metadata = {"user_id": str(user.id)}
    try:
        customer_id = await _ensure_customer(db, user)
        if plan is not None:
            metadata.update({"kind": "plan", "plan": plan["key"]})
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                mode="subscription",
                customer=customer_id,
                client_reference_id=str(user.id),
                line_items=[{"price": plan["price_id"], "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,
                billing_address_collection="required",
                tax_id_collection={"enabled": True},
                customer_update={"name": "auto", "address": "auto"},
                metadata=metadata,
                subscription_data={"metadata": metadata},
            )
        else:
            metadata.update({"kind": "credit", "tokens": str(pack["tokens"])})
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                mode="payment",
                customer=customer_id,
                client_reference_id=str(user.id),
                line_items=[{"price": pack["price_id"], "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"url": session.url, "session_id": session.id}


@router.post("/portal")
async def portal(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=501, detail="Stripe yapılandırılmadı")
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="önce bir abonelik başlatın")
    stripe.api_key = settings.stripe_secret_key
    try:
        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            customer=user.stripe_customer_id,
            return_url=f"{_base_url()}/app/billing",
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"url": session.url}


async def _user_by_customer(db: AsyncSession, customer_id) -> User | None:
    if not customer_id:
        return None
    return (
        await db.scalars(
            select(User).where(User.stripe_customer_id == str(customer_id))
        )
    ).first()


def _apply_plan(user: User, plan: dict, subscription=None, reset_usage: bool = False) -> None:
    now = datetime.now(UTC)
    user.plan = plan["key"]
    user.monthly_token_budget = plan["token_budget"]
    user.billing_status = "active"
    if reset_usage:
        user.monthly_token_used = 0
        user.usage_period_start = now
    if subscription is not None:
        user.stripe_subscription_id = subscription.get("id")
        user.billing_period_end = _period_end(subscription)


async def _handle_checkout_completed(db: AsyncSession, session) -> None:
    metadata = session.get("metadata") or {}
    raw_user_id = metadata.get("user_id")
    if not raw_user_id:
        return
    try:
        user = await db.get(User, uuid.UUID(raw_user_id))
    except ValueError:
        return
    if user is None:
        return
    customer_id = session.get("customer")
    if customer_id:
        user.stripe_customer_id = str(customer_id)
    kind = metadata.get("kind")
    if kind == "plan":
        subscription_id = session.get("subscription")
        subscription = None
        if subscription_id:
            subscription = await asyncio.to_thread(
                stripe.Subscription.retrieve, subscription_id
            )
        price_id = None
        if subscription is not None:
            items = ((subscription.get("items") or {}).get("data")) or []
            price_id = items[0].get("price", {}).get("id") if items else None
        plan = await get_plan_by_price(db, price_id) or await get_plan(
            db, metadata.get("plan") or ""
        )
        if plan is not None:
            _apply_plan(user, plan, subscription, reset_usage=True)
    elif kind == "credit":
        tokens = int(metadata.get("tokens") or 0)
        if tokens > 0:
            user.credit_balance = (user.credit_balance or 0) + tokens
            db.add(
                CreditLedger(
                    user_id=user.id,
                    delta=tokens,
                    reason="credit_purchase",
                    stripe_ref=session.get("id"),
                )
            )


async def _handle_subscription(db: AsyncSession, subscription) -> None:
    user = await _user_by_customer(db, subscription.get("customer"))
    if user is None:
        return
    status = subscription.get("status")
    items = ((subscription.get("items") or {}).get("data")) or []
    price_id = items[0].get("price", {}).get("id") if items else None
    plan = await get_plan_by_price(db, price_id)
    user.stripe_subscription_id = subscription.get("id")
    user.billing_period_end = _period_end(subscription)
    if status in ("active", "trialing") and plan is not None:
        _apply_plan(user, plan, subscription)
    elif status == "past_due":
        user.billing_status = "past_due"
    elif status in ("canceled", "unpaid", "incomplete_expired"):
        user.billing_status = "canceled"


async def _handle_subscription_deleted(db: AsyncSession, subscription) -> None:
    user = await _user_by_customer(db, subscription.get("customer"))
    if user is None:
        return
    free = await get_plan(db, "free")
    if free is not None:
        _apply_plan(user, free)
    user.plan = "free"
    user.billing_status = "canceled"
    user.stripe_subscription_id = None
    user.billing_period_end = None


async def _handle_invoice_paid(db: AsyncSession, invoice) -> None:
    if not invoice.get("subscription"):
        return
    user = await _user_by_customer(db, invoice.get("customer"))
    if user is None:
        return
    lines = ((invoice.get("lines") or {}).get("data")) or []
    price_id = lines[0].get("price", {}).get("id") if lines else None
    plan = await get_plan_by_price(db, price_id)
    if plan is not None:
        _apply_plan(user, plan, reset_usage=True)
    else:
        user.monthly_token_used = 0
        user.usage_period_start = datetime.now(UTC)
        user.billing_status = "active"
    period_end = invoice.get("period_end")
    if period_end:
        user.billing_period_end = datetime.fromtimestamp(int(period_end), UTC)


async def _handle_event(db: AsyncSession, event) -> None:
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}
    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, obj)
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        await _handle_subscription(db, obj)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, obj)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(db, obj)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    if not settings.stripe_webhook_secret:
        return {"received": False, "message": "Stripe webhook yapılandırılmadı"}
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="geçersiz imza") from exc
    async with AsyncSessionLocal() as db:
        if await db.get(BillingEvent, event["id"]) is not None:
            return {"received": True, "duplicate": True}
        try:
            await _handle_event(db, event)
            db.add(BillingEvent(stripe_event_id=event["id"], type=event["type"]))
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise HTTPException(status_code=500, detail="webhook işlenemedi") from exc
    return {"received": True}
