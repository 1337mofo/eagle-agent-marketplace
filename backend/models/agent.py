"""
Agent Model - Represents AI agents on the marketplace
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from database.base import Base


class AgentType(str, enum.Enum):
    """Types of agents on the marketplace"""
    CAPABILITY = "capability"  # Offers services/capabilities
    OUTPUT = "output"  # Sells completed work
    API = "api"  # Provides API access
    HYBRID = "hybrid"  # Multiple types


class VerificationStatus(str, enum.Enum):
    """Agent verification levels"""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    TOP_RATED = "top_rated"
    EAGLE_OFFICIAL = "eagle_official"


class Agent(Base):
    """
    AI Agent registered on the marketplace
    
    Can be a seller (offers capabilities/outputs) or buyer (purchases from others)
    """
    __tablename__ = "agents"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    agent_type = Column(Enum(AgentType), nullable=False, default=AgentType.HYBRID)
    
    # Owner
    owner_user_id = Column(UUID(as_uuid=True), index=True)  # Links to user account
    owner_email = Column(String(255), index=True)
    
    # Authentication
    api_key = Column(String(255), unique=True, index=True)
    api_key_created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Capabilities (for capability-type agents)
    capabilities = Column(JSON)  # ["cost_estimation", "market_analysis"]
    pricing_model = Column(JSON)  # {"per_query": 2.99, "bulk_discount": 0.2}
    
    # Performance Metrics
    rating_avg = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    transaction_count = Column(Integer, default=0)
    revenue_total_usd = Column(Float, default=0.0)
    
    # Quality Metrics
    response_time_avg_ms = Column(Integer)
    quality_score = Column(Integer, default=50)  # 0-100 scale
    success_rate = Column(Float, default=1.0)  # 0.0-1.0
    
    # Verification & Trust
    verification_status = Column(
        Enum(VerificationStatus),
        default=VerificationStatus.UNVERIFIED
    )
    verification_date = Column(DateTime)
    badges = Column(JSON)  # ["top_rated", "fast_response", "high_accuracy"]
    
    # Subscription
    subscription_tier = Column(String(50), default="free")  # free/basic/pro/enterprise
    subscription_expires_at = Column(DateTime)
    
    # Technical Details
    api_endpoint = Column(String(500))  # External API endpoint if applicable
    webhook_url = Column(String(500))  # For notifications
    rate_limit_per_hour = Column(Integer, default=100)
    
    # Metadata
    metadata = Column(JSON)  # Flexible storage for agent-specific data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert agent to dictionary for API responses"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "capabilities": self.capabilities,
            "pricing_model": self.pricing_model,
            "rating_avg": self.rating_avg,
            "rating_count": self.rating_count,
            "transaction_count": self.transaction_count,
            "response_time_avg_ms": self.response_time_avg_ms,
            "quality_score": self.quality_score,
            "verification_status": self.verification_status.value if self.verification_status else None,
            "badges": self.badges,
            "subscription_tier": self.subscription_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None
        }
    
    def calculate_reputation_score(self) -> int:
        """
        Calculate overall reputation score (0-100)
        
        Weights:
        - Transaction success rate: 40%
        - Average rating: 30%
        - Response time: 15%
        - Quality score: 15%
        """
        score = 0
        
        # Success rate (40 points max)
        score += self.success_rate * 40
        
        # Average rating (30 points max)
        if self.rating_count > 0:
            score += (self.rating_avg / 5.0) * 30
        
        # Response time (15 points max)
        if self.response_time_avg_ms:
            # Faster is better: <10s = full points, >60s = no points
            if self.response_time_avg_ms < 10000:
                score += 15
            elif self.response_time_avg_ms < 60000:
                score += 15 * (1 - (self.response_time_avg_ms - 10000) / 50000)
        
        # Quality score (15 points max)
        score += (self.quality_score / 100) * 15
        
        return int(score)
