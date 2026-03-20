"""Billing com Stripe — checkout, webhook e portal do cliente."""
from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.config import settings

from . import auth_utils

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


def _get_stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe não está configurado neste ambiente.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


# ---------------------------------------------------------------------------
# POST /billing/checkout  — cria sessão de checkout para o plano Pro
# ---------------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    plano_id: int


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
def criar_checkout(
    payload: CheckoutRequest,
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Cria sessão Stripe Checkout para o plano solicitado."""
    s = _get_stripe()

    plano = session.query(models.Plano).filter(models.Plano.id == payload.plano_id).first()
    if not plano:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
    if plano.preco_mensal <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plano gratuito não requer checkout. Use /planos/mudar diretamente.",
        )

    price_id = settings.STRIPE_PRO_PRICE_ID
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_PRO_PRICE_ID não configurado.",
        )

    db_user = session.query(models.User).filter(models.User.id == current_user.id).first()

    # Cria ou recupera customer no Stripe
    customer_id = db_user.stripe_customer_id
    if not customer_id:
        customer = s.Customer.create(
            email=db_user.email,
            name=db_user.nome_completo or db_user.email,
            metadata={"user_id": str(db_user.id)},
        )
        customer_id = customer.id
        db_user.stripe_customer_id = customer_id
        session.commit()

    checkout_session = s.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.FRONTEND_URL}/plano?checkout=success&plano={plano.id}",
        cancel_url=f"{settings.FRONTEND_URL}/plano?checkout=cancel",
        metadata={"user_id": str(db_user.id), "plano_id": str(plano.id)},
        subscription_data={"metadata": {"user_id": str(db_user.id), "plano_id": str(plano.id)}},
    )

    return CheckoutResponse(checkout_url=checkout_session.url)


# ---------------------------------------------------------------------------
# GET /billing/portal  — portal do cliente Stripe para gerenciar assinatura
# ---------------------------------------------------------------------------
class PortalResponse(BaseModel):
    portal_url: str


@router.get("/portal", response_model=PortalResponse)
def portal_cliente(
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Cria sessão do Stripe Customer Portal para gerenciar assinatura."""
    s = _get_stripe()

    db_user = session.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user or not db_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma assinatura Stripe encontrada para este usuário.",
        )

    portal_session = s.billing_portal.Session.create(
        customer=db_user.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/plano",
    )
    return PortalResponse(portal_url=portal_session.url)


# ---------------------------------------------------------------------------
# POST /billing/webhook  — eventos Stripe (sem autenticação JWT)
# ---------------------------------------------------------------------------
@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session)):
    """Recebe e processa eventos do webhook Stripe."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook secret não configurado.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assinatura inválida.")

    event_type = event["type"]
    data_obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(session, data_obj)
    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        _handle_subscription_cancelled(session, data_obj)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(session, data_obj)

    return {"status": "ok"}


def _handle_checkout_completed(session: Session, data_obj: dict):
    """Ao finalizar checkout com sucesso, associa o plano pago ao usuário."""
    user_id = int(data_obj.get("metadata", {}).get("user_id", 0))
    plano_id = int(data_obj.get("metadata", {}).get("plano_id", 0))
    subscription_id = data_obj.get("subscription")

    if not user_id or not plano_id:
        logger.warning("checkout.session.completed sem user_id/plano_id em metadata.")
        return

    db_user = session.query(models.User).filter(models.User.id == user_id).first()
    plano = session.query(models.Plano).filter(models.Plano.id == plano_id).first()

    if not db_user or not plano:
        logger.warning("Usuário %s ou plano %s não encontrado.", user_id, plano_id)
        return

    db_user.plano_id = plano.id
    if subscription_id:
        db_user.stripe_subscription_id = subscription_id
    session.commit()
    logger.info("Usuário %s migrado para plano %s via Stripe.", user_id, plano.nome)


def _handle_subscription_cancelled(session: Session, data_obj: dict):
    """Ao cancelar/pausar assinatura, volta o usuário para o plano gratuito."""
    customer_id = data_obj.get("customer")
    if not customer_id:
        return

    db_user = session.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
    if not db_user:
        return

    plano_free = session.query(models.Plano).filter(models.Plano.preco_mensal == 0).first()
    if plano_free:
        db_user.plano_id = plano_free.id
    db_user.stripe_subscription_id = None
    session.commit()
    logger.info("Assinatura cancelada para customer %s — downgrade para plano gratuito.", customer_id)


def _handle_subscription_updated(session: Session, data_obj: dict):
    """Ao atualizar assinatura ativa, garante subscription_id atualizado."""
    customer_id = data_obj.get("customer")
    sub_id = data_obj.get("id")
    sub_status = data_obj.get("status")

    if not customer_id or not sub_id:
        return

    db_user = session.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
    if not db_user:
        return

    if sub_status == "active":
        db_user.stripe_subscription_id = sub_id
        session.commit()
