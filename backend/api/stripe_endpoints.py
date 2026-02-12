"""
Stripe Integration API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.base import get_db
from models.agent import Agent
from models.transaction import Transaction, TransactionStatus
from payments.stripe_handler import stripe_handler

router = APIRouter(prefix="/api/v1", tags=["Payments"])


# ==========================================
# Request Schemas
# ==========================================

class StripeConnectSetup(BaseModel):
    """Setup Stripe Connect for agent to receive payouts"""
    agent_id: str
    email: str
    country: str = "US"


class WebhookPayload(BaseModel):
    """Stripe webhook payload"""
    pass  # Will be raw bytes


# ==========================================
# Agent Stripe Connect
# ==========================================

@router.post("/agents/{agent_id}/stripe/connect")
def setup_stripe_connect(
    agent_id: str,
    setup_data: StripeConnectSetup,
    db: Session = Depends(get_db)
):
    """
    Setup Stripe Connect account for agent to receive payouts
    
    Agent must complete Stripe onboarding to receive payments
    """
    # Verify agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create Stripe Connect account
    result = stripe_handler.create_connected_account(
        agent_email=setup_data.email,
        agent_name=agent.name,
        country=setup_data.country
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Stripe account: {result['error']}"
        )
    
    # Save Stripe account ID to agent
    agent.metadata = agent.metadata or {}
    agent.metadata['stripe_account_id'] = result['account_id']
    db.commit()
    
    return {
        "success": True,
        "message": "Stripe Connect account created. Complete onboarding to receive payments.",
        "onboarding_url": result['onboarding_url'],
        "account_id": result['account_id']
    }


@router.get("/agents/{agent_id}/stripe/status")
def get_stripe_status(agent_id: str, db: Session = Depends(get_db)):
    """
    Check agent's Stripe Connect status
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    stripe_account_id = agent.metadata.get('stripe_account_id') if agent.metadata else None
    
    if not stripe_account_id:
        return {
            "success": True,
            "connected": False,
            "message": "No Stripe account connected"
        }
    
    # Check account status with Stripe
    import stripe
    try:
        account = stripe.Account.retrieve(stripe_account_id)
        
        return {
            "success": True,
            "connected": True,
            "account_id": stripe_account_id,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "details_submitted": account.details_submitted
        }
    except stripe.error.StripeError as e:
        return {
            "success": False,
            "error": str(e)
        }


# ==========================================
# Payment Processing
# ==========================================

@router.post("/transactions/{transaction_id}/process-payment")
def process_payment(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Process payment for transaction using Stripe
    
    This is called after transaction is created to handle actual payment
    """
    # Get transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Get seller's Stripe account
    seller = db.query(Agent).filter(Agent.id == transaction.seller_agent_id).first()
    seller_stripe_account = seller.metadata.get('stripe_account_id') if seller.metadata else None
    
    if not seller_stripe_account:
        raise HTTPException(
            status_code=400,
            detail="Seller has not connected Stripe account"
        )
    
    # Process payment
    # Note: In production, buyer would provide payment_method_id from frontend
    # For now, we create a PaymentIntent that buyer will complete
    
    result = stripe_handler.create_payment_intent(
        amount_usd=transaction.amount_usd,
        buyer_agent_id=str(transaction.buyer_agent_id),
        seller_agent_id=str(transaction.seller_agent_id),
        transaction_id=str(transaction.id),
        metadata={
            'commission_rate': transaction.commission_rate,
            'seller_payout': transaction.seller_payout_usd
        }
    )
    
    if not result['success']:
        transaction.status = TransactionStatus.FAILED
        transaction.status_message = f"Payment failed: {result['error']}"
        db.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Payment processing failed: {result['error']}"
        )
    
    # Update transaction
    transaction.stripe_payment_intent_id = result['payment_intent_id']
    transaction.status = TransactionStatus.PROCESSING
    db.commit()
    
    return {
        "success": True,
        "message": "Payment initiated. Buyer must complete payment.",
        "payment_intent_id": result['payment_intent_id'],
        "client_secret": result['client_secret'],
        "amount": result['amount']
    }


# ==========================================
# Stripe Webhooks
# ==========================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events
    
    Stripe sends events like:
    - payment_intent.succeeded (payment received)
    - payment_intent.payment_failed (payment failed)
    - transfer.created (payout sent)
    """
    # Get webhook payload and signature
    payload = await request.body()
    signature = request.headers.get('stripe-signature')
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify and process webhook
    result = stripe_handler.handle_webhook(payload, signature)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    # Take action based on event type
    if result.get('action') == 'update_transaction_status':
        transaction_id = result.get('transaction_id')
        if transaction_id:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = result['processed_at']
                
                # Now transfer to seller
                seller = db.query(Agent).filter(Agent.id == transaction.seller_agent_id).first()
                seller_stripe = seller.metadata.get('stripe_account_id') if seller.metadata else None
                
                if seller_stripe:
                    transfer_result = stripe_handler.create_transfer(
                        amount_usd=transaction.seller_payout_usd,
                        destination_stripe_account=seller_stripe,
                        transaction_id=str(transaction.id),
                        description=f"Payout for transaction {transaction.id}"
                    )
                    
                    if transfer_result['success']:
                        transaction.stripe_transfer_id = transfer_result['transfer_id']
                
                db.commit()
    
    elif result.get('action') == 'mark_transaction_failed':
        transaction_id = result.get('transaction_id')
        if transaction_id:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if transaction:
                transaction.status = TransactionStatus.FAILED
                transaction.status_message = result.get('error', 'Payment failed')
                db.commit()
    
    return {"success": True, "event_processed": result['event_type']}


# ==========================================
# Platform Balance
# ==========================================

@router.get("/admin/stripe/balance")
def get_platform_balance():
    """
    Get Agent Exchange Stripe balance
    
    Admin only - shows platform earnings
    """
    result = stripe_handler.get_balance()
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return result
