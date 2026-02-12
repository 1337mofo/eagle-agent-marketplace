"""
Arbitrage Fulfillment API Endpoints
Trigger and manage automated fulfillment
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database.base import get_db
from services.arbitrage_fulfillment import ArbitrageFulfillmentEngine, calculate_net_profit
from models.transaction import Transaction


router = APIRouter(prefix="/api/v1/fulfillment", tags=["Fulfillment"])


# ==========================================
# Request Schemas
# ==========================================

class ManualDelivery(BaseModel):
    """Manual fulfillment completion data"""
    transaction_id: str
    delivery_type: str  # 'file', 'credentials', 'api_result', 'instructions'
    delivery_data: dict
    notes: Optional[str] = None


# ==========================================
# Automated Fulfillment
# ==========================================

@router.post("/process/{transaction_id}")
async def trigger_fulfillment(
    transaction_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger automated fulfillment for arbitrage transaction
    
    Called after buyer completes payment to:
    1. Purchase from source platform
    2. Deliver to buyer
    3. Complete transaction
    """
    # Verify transaction exists
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Create fulfillment engine
    engine = ArbitrageFulfillmentEngine(db)
    
    # Process in background
    background_tasks.add_task(engine.process_transaction, transaction_id)
    
    return {
        "success": True,
        "message": "Fulfillment started",
        "transaction_id": transaction_id,
        "status": "processing"
    }


@router.get("/status/{transaction_id}")
def get_fulfillment_status(transaction_id: str, db: Session = Depends(get_db)):
    """
    Check fulfillment status for transaction
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    metadata = transaction.metadata or {}
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "transaction_status": transaction.status.value,
        "fulfillment_status": metadata.get('fulfillment_status'),
        "fulfillment_started_at": metadata.get('fulfillment_started_at'),
        "fulfillment_completed_at": metadata.get('fulfillment_completed_at'),
        "requires_manual": metadata.get('fulfillment_status') == 'pending_manual',
        "delivery": metadata.get('delivery'),
        "error": metadata.get('fulfillment_error')
    }


# ==========================================
# Manual Fulfillment Queue
# ==========================================

@router.get("/manual/queue")
def get_manual_queue(db: Session = Depends(get_db)):
    """
    Get all pending manual fulfillment tasks
    
    Returns tasks requiring human intervention (Fiverr, Upwork, etc.)
    """
    engine = ArbitrageFulfillmentEngine(db)
    queue = engine.get_manual_queue()
    
    return {
        "success": True,
        "pending_tasks": len(queue),
        "tasks": queue
    }


@router.post("/manual/complete")
def complete_manual_task(
    delivery: ManualDelivery,
    db: Session = Depends(get_db)
):
    """
    Mark manual task as complete and deliver to buyer
    
    Called by human after manually purchasing from source platform
    """
    engine = ArbitrageFulfillmentEngine(db)
    
    result = engine.mark_manual_task_complete(
        transaction_id=delivery.transaction_id,
        delivery_data={
            'type': delivery.delivery_type,
            'data': delivery.delivery_data,
            'notes': delivery.notes,
            'completed_by': 'manual',
            'completed_at': None  # Engine will set
        }
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": "Manual fulfillment complete",
        "transaction_id": delivery.transaction_id
    }


# ==========================================
# Profit Calculator
# ==========================================

@router.post("/calculate-profit")
def calculate_arbitrage_profit(
    buyer_paid: float,
    source_cost: float,
    platform: str = 'fiverr'
):
    """
    Calculate net profit for arbitrage deal
    
    Shows all fees and margins
    """
    result = calculate_net_profit(buyer_paid, source_cost, platform)
    
    return {
        "success": True,
        **result
    }


# ==========================================
# Analytics
# ==========================================

@router.get("/stats")
def get_fulfillment_stats(db: Session = Depends(get_db)):
    """
    Get fulfillment statistics
    
    Shows success rate, avg profit, etc.
    """
    # Query transactions with arbitrage metadata
    transactions = db.query(Transaction).filter(
        Transaction.metadata.contains({'fulfillment_status': 'delivered'})
    ).all()
    
    total_fulfilled = len(transactions)
    total_revenue = sum(t.amount_usd for t in transactions)
    
    # Count by platform
    platforms = {}
    for t in transactions:
        listing = db.query(Listing).filter(Listing.id == t.listing_id).first()
        if listing and listing.metadata:
            platform = listing.metadata.get('source_platform', 'unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
    
    return {
        "success": True,
        "total_fulfilled": total_fulfilled,
        "total_revenue": total_revenue,
        "by_platform": platforms
    }


# ==========================================
# Webhook for Source Platform Events
# ==========================================

@router.post("/webhook/source-complete")
async def handle_source_completion(
    transaction_id: str,
    platform: str,
    result_data: dict,
    db: Session = Depends(get_db)
):
    """
    Webhook for when source platform completes delivery
    
    Some platforms (like Fiverr) could notify us when order is complete
    """
    engine = ArbitrageFulfillmentEngine(db)
    
    # Deliver to buyer
    result = await engine.deliver_to_buyer(transaction_id, {
        'type': 'webhook_delivery',
        'platform': platform,
        'data': result_data
    })
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": "Delivery processed",
        "transaction_id": transaction_id
    }
