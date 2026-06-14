import logging
import stripe
from fastapi import APIRouter, Request, HTTPException, status, Header, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Stripe Billing"])

# Configure stripe API key
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY not found in configuration. Stripe functions running in simulated offline mode.")

class CheckoutPayload(BaseModel):
    userId: str
    plan: Optional[str] = "premium"
    successUrl: str
    cancelUrl: str

@router.post("/checkout", status_code=status.HTTP_200_OK)
async def create_checkout_session(payload: CheckoutPayload):
    """
    Creates a Stripe Checkout Session for upgrading to the premium tier.
    """
    if not settings.STRIPE_SECRET_KEY:
        # Fallback offline simulation checkout URL
        logger.info(f"Simulating Stripe checkout session for user {payload.userId}")
        # Automatically update database status to premium immediately for mock ease
        await db.execute(
            "UPDATE users SET subscription = $1, updated_at = NOW() WHERE id = $2",
            payload.plan, payload.userId
        )
        return {
            "status": "success",
            "url": f"{payload.successUrl}?session_id=mock_stripe_session_123456",
            "is_simulated": True
        }

    try:
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"InterviewOS - {payload.plan.capitalize()} Plan",
                        'description': 'Real-time interview copilot, speech analytics, and premium AImock practice.',
                    },
                    'unit_amount': 2900,  # $29.00 USD
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=payload.successUrl + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancelUrl,
            client_reference_id=payload.userId,
            metadata={
                "user_id": payload.userId,
                "plan": payload.plan
            }
        )
        return {"status": "success", "url": session.url, "is_simulated": False}
    except Exception as e:
        logger.error(f"Failed to create Stripe checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe session generation failed: {e}"
        )

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Stripe Webhook listener to handle events like subscription updates.
    """
    payload_bytes = await request.body()
    payload = payload_bytes.decode("utf-8")

    # Offline simulation trigger
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe credentials missing. Ignoring webhook signature validation.")
        try:
            import json
            event_data = json.loads(payload)
            event_type = event_data.get("type")
            if event_type == "checkout.session.completed":
                session_obj = event_data.get("data", {}).get("object", {})
                user_id = session_obj.get("client_reference_id") or session_obj.get("metadata", {}).get("user_id")
                plan = session_obj.get("metadata", {}).get("plan", "premium")
                if user_id:
                    await db.execute(
                        "UPDATE users SET subscription = $1, updated_at = NOW() WHERE id = $2",
                        plan, user_id
                    )
                    logger.info(f"Simulated Webhook completed. Upgraded user {user_id} to {plan}.")
            return {"status": "simulated_success"}
        except Exception as e:
            logger.error(f"Error handling simulated webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid simulated webhook payload")

    try:
        # Validate event signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature verification")

    event_type = event.get("type")
    
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        user_id = session.get("client_reference_id")
        plan = session.get("metadata", {}).get("plan", "premium")
        
        if user_id:
            await db.execute(
                "UPDATE users SET subscription = $1, updated_at = NOW() WHERE id = $2",
                plan, user_id
            )
            logger.info(f"Stripe Webhook: Upgraded user {user_id} to subscription tier '{plan}'.")
            
    elif event_type in ["customer.subscription.deleted", "customer.subscription.updated"]:
        subscription_obj = event.get("data", {}).get("object", {})
        # Stripe metadata or retrieve user_id by mapping customer ID
        # For simplicity, if metadata is present:
        user_id = subscription_obj.get("metadata", {}).get("user_id")
        status_val = subscription_obj.get("status")
        
        if user_id:
            plan = "premium" if status_val == "active" else "free"
            await db.execute(
                "UPDATE users SET subscription = $1, updated_at = NOW() WHERE id = $2",
                plan, user_id
            )
            logger.info(f"Stripe Webhook: Updated user {user_id} subscription tier to '{plan}' based on status '{status_val}'.")

    return {"status": "success"}

@router.get("/status/{user_id}", status_code=status.HTTP_200_OK)
async def check_billing_status(user_id: str):
    """
    Checks the user's subscription tier directly from the database.
    """
    try:
        user_row = await db.fetch_row(
            "SELECT subscription FROM users WHERE id = $1",
            user_id
        )
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found."
            )
        return {"userId": user_id, "subscription": user_row.get("subscription", "free")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user subscription: {e}"
        )
