"""Stripe billing endpoints for checkout, customer portal and webhook handling."""
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


class CheckoutRequest(BaseModel):
    """Payload used to start a Stripe Checkout session for a paid plan."""

    plano_id: int


class CheckoutResponse(BaseModel):
    """Response payload containing the Stripe Checkout URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response payload containing the Stripe customer portal URL."""

    portal_url: str


class BillingRequestService:
    """Request-scoped billing service responsible for Stripe checkout and webhooks."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Bind the billing service to the current request database session."""
        self._session = session

    @staticmethod
    def _get_stripe_client():
        """Return the configured Stripe SDK client for the current environment."""
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe nao esta configurado neste ambiente.",
            )
        stripe.api_key = settings.STRIPE_SECRET_KEY
        return stripe

    def create_checkout(self, *, payload: CheckoutRequest, current_user: models.User) -> CheckoutResponse:
        """Create a Stripe Checkout session for the selected paid plan."""
        stripe_client = self._get_stripe_client()
        plano = self._session.query(models.Plano).filter(models.Plano.id == payload.plano_id).first()
        if not plano:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano nao encontrado.")
        if plano.preco_mensal <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plano gratuito nao requer checkout. Use /planos/mudar diretamente.",
            )

        price_id = settings.STRIPE_PRO_PRICE_ID
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="STRIPE_PRO_PRICE_ID nao configurado.",
            )

        db_user = self._session.query(models.User).filter(models.User.id == current_user.id).first()
        customer_id = db_user.stripe_customer_id
        if not customer_id:
            customer = stripe_client.Customer.create(
                email=db_user.email,
                name=db_user.nome_completo or db_user.email,
                metadata={"user_id": str(db_user.id)},
            )
            customer_id = customer.id
            db_user.stripe_customer_id = customer_id
            self._session.commit()

        checkout_session = stripe_client.checkout.Session.create(
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

    def create_customer_portal(self, *, current_user: models.User) -> PortalResponse:
        """Create a Stripe Customer Portal session for the authenticated user."""
        stripe_client = self._get_stripe_client()
        db_user = self._session.query(models.User).filter(models.User.id == current_user.id).first()
        if not db_user or not db_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma assinatura Stripe encontrada para este usuario.",
            )

        portal_session = stripe_client.billing_portal.Session.create(
            customer=db_user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/plano",
        )
        return PortalResponse(portal_url=portal_session.url)

    async def handle_webhook(self, *, request: Request) -> dict[str, str]:
        """Validate and process a Stripe webhook request."""
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook secret nao configurado.",
            )

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assinatura invalida.",
            ) from exc

        event_type = event["type"]
        data_obj = event["data"]["object"]
        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data_obj)
        elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
            self._handle_subscription_cancelled(data_obj)
        elif event_type == "customer.subscription.updated":
            self._handle_subscription_updated(data_obj)

        return {"status": "ok"}

    def _handle_checkout_completed(self, data_obj: dict) -> None:
        """Apply the paid plan to the user after a successful checkout session."""
        user_id = int(data_obj.get("metadata", {}).get("user_id", 0))
        plano_id = int(data_obj.get("metadata", {}).get("plano_id", 0))
        subscription_id = data_obj.get("subscription")
        if not user_id or not plano_id:
            logger.warning("checkout.session.completed sem user_id/plano_id em metadata.")
            return

        db_user = self._session.query(models.User).filter(models.User.id == user_id).first()
        plano = self._session.query(models.Plano).filter(models.Plano.id == plano_id).first()
        if not db_user or not plano:
            logger.warning("Usuario %s ou plano %s nao encontrado.", user_id, plano_id)
            return

        db_user.plano_id = plano.id
        if subscription_id:
            db_user.stripe_subscription_id = subscription_id
        self._session.commit()
        logger.info("Usuario %s migrado para plano %s via Stripe.", user_id, plano.nome)

    def _handle_subscription_cancelled(self, data_obj: dict) -> None:
        """Downgrade the user to the free plan after subscription cancellation."""
        customer_id = data_obj.get("customer")
        if not customer_id:
            return

        db_user = self._session.query(models.User).filter(
            models.User.stripe_customer_id == customer_id
        ).first()
        if not db_user:
            return

        plano_free = self._session.query(models.Plano).filter(models.Plano.preco_mensal == 0).first()
        if plano_free:
            db_user.plano_id = plano_free.id
        db_user.stripe_subscription_id = None
        self._session.commit()
        logger.info("Assinatura cancelada para customer %s; downgrade para plano gratuito.", customer_id)

    def _handle_subscription_updated(self, data_obj: dict) -> None:
        """Keep the stored Stripe subscription id in sync with active subscriptions."""
        customer_id = data_obj.get("customer")
        sub_id = data_obj.get("id")
        sub_status = data_obj.get("status")
        if not customer_id or not sub_id:
            return

        db_user = self._session.query(models.User).filter(
            models.User.stripe_customer_id == customer_id
        ).first()
        if not db_user:
            return

        if sub_status == "active":
            db_user.stripe_subscription_id = sub_id
            self._session.commit()


@router.post("/checkout", response_model=CheckoutResponse)
def criar_checkout(
    payload: CheckoutRequest,
    request_service: BillingRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Start a Stripe Checkout session for a paid plan."""
    return request_service.create_checkout(payload=payload, current_user=current_user)


@router.get("/portal", response_model=PortalResponse)
def portal_cliente(
    request_service: BillingRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Open the Stripe customer portal for the authenticated user."""
    return request_service.create_customer_portal(current_user=current_user)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    request_service: BillingRequestService = Depends(),
):
    """Receive and process Stripe webhook events."""
    return await request_service.handle_webhook(request=request)
