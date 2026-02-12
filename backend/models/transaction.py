"""
Transaction Model - Records of agent-to-agent commerce
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from database.base import Base


class TransactionStatus(str, enum.Enum):
    """Transaction lifecycle status"""
    PENDING = "pending"  # Payment initiated
    PROCESSING = "processing"  # Agent executing work
    COMPLETED = "completed"  # Successfully delivered
    FAILED = "failed"  # Execution failed
    REFUNDED = "refunded"  # Money returned
    DISPUTED = "disputed"  # Under dispute resolution


class TransactionType(str, enum.Enum):
    """Types of transactions"""
    CAPABILITY_PURCHASE = "capability_purchase"  # Buying agent service
    OUTPUT_PURCHASE = "output_purchase"  # Buying completed work
    API_CALL = "api_call"  # API usage charge
    SUBSCRIPTION = "subscription"  # Recurring subscription


class Transaction(Base):
    """
    Record of a purchase/sale between two agents
    """
    __tablename__ = "transactions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parties
    buyer_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    seller_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    
    # Transaction Details
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)
    
    # Financial
    amount_usd = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)  # Percentage (e.g., 0.15 = 15%)
    commission_usd = Column(Float, nullable=False)
    seller_payout_usd = Column(Float, nullable=False)
    
    # Payment Processing
    payment_method = Column(String(100))  # "stripe", "agent_balance"
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    stripe_transfer_id = Column(String(255))  # Payout to seller
    
    # Status
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    status_message = Column(Text)  # Error messages or notes
    
    # Input/Output Data
    input_data = Column(JSON)  # What buyer sent to seller
    output_data = Column(JSON)  # What seller returned to buyer
    output_url = Column(String(500))  # Download URL for outputs
    
    # Execution Metrics
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime, index=True)
    execution_time_seconds = Column(Integer)
    
    # Quality & Feedback
    buyer_rating = Column(Integer)  # 1-5 stars
    buyer_review = Column(Text)
    seller_rating = Column(Integer)  # Seller can rate buyer too
    seller_review = Column(Text)
    
    # Dispute Resolution
    dispute_reason = Column(Text)
    dispute_opened_at = Column(DateTime)
    dispute_resolved_at = Column(DateTime)
    dispute_resolution = Column(Text)
    
    # Metadata
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert transaction to dictionary for API responses"""
        return {
            "id": str(self.id),
            "buyer_agent_id": str(self.buyer_agent_id),
            "seller_agent_id": str(self.seller_agent_id),
            "transaction_type": self.transaction_type.value if self.transaction_type else None,
            "listing_id": str(self.listing_id) if self.listing_id else None,
            "amount_usd": self.amount_usd,
            "commission_usd": self.commission_usd,
            "seller_payout_usd": self.seller_payout_usd,
            "status": self.status.value if self.status else None,
            "status_message": self.status_message,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "buyer_rating": self.buyer_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def calculate_commission(self):
        """Calculate commission based on agent subscription tier"""
        # This would be enhanced with seller's subscription tier
        # For now, use the commission_rate already set
        self.commission_usd = self.amount_usd * self.commission_rate
        self.seller_payout_usd = self.amount_usd - self.commission_usd
