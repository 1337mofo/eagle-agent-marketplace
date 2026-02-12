"""
Listing Model - Products/services/outputs that agents sell
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database.base import Base


class ListingType(str, enum.Enum):
    """Types of listings"""
    CAPABILITY = "capability"  # Service/skill (e.g., "cost estimation")
    OUTPUT = "output"  # Completed work product (e.g., "market research report")
    API_ACCESS = "api_access"  # API endpoint access
    DATASET = "dataset"  # Data/information
    MODEL = "model"  # Trained AI model


class ListingStatus(str, enum.Enum):
    """Listing availability status"""
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD_OUT = "sold_out"
    ARCHIVED = "archived"


class Listing(Base):
    """
    A product/service/output listed by an agent for sale
    """
    __tablename__ = "listings"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Seller
    seller_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    
    # Listing Details
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=False)
    listing_type = Column(Enum(ListingType), nullable=False, index=True)
    
    # Categorization
    category = Column(String(100), index=True)  # "sourcing", "analysis", "research"
    tags = Column(JSON)  # ["cost_estimation", "manufacturing", "b2b"]
    
    # Pricing
    price_usd = Column(Float, nullable=False, index=True)
    pricing_model = Column(String(50))  # "one_time", "per_query", "subscription"
    bulk_pricing = Column(JSON)  # {"10+": 0.9, "50+": 0.8}  # Discounts by volume
    
    # For Capability Listings
    capability_name = Column(String(255), index=True)  # "cost_estimation"
    expected_response_time_seconds = Column(Integer)
    input_schema = Column(JSON)  # JSON schema for required inputs
    output_schema = Column(JSON)  # JSON schema for expected outputs
    
    # For Output Listings
    output_format = Column(String(50))  # "json", "pdf", "csv"
    file_size_kb = Column(Integer)
    data_url = Column(String(500))  # Secure download URL
    sample_url = Column(String(500))  # Preview/sample data
    
    # For API Access Listings
    api_endpoint = Column(String(500))
    api_documentation_url = Column(String(500))
    rate_limit = Column(String(100))  # "100 calls/hour"
    
    # Quality Metrics
    quality_score = Column(Integer, default=50)  # 0-100
    purchase_count = Column(Integer, default=0)
    rating_avg = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Availability
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE, index=True)
    stock_quantity = Column(Integer)  # For limited outputs
    max_concurrent_buyers = Column(Integer)  # For capability limits
    
    # SEO & Discovery
    search_keywords = Column(JSON)  # Keywords for search optimization
    featured = Column(Boolean, default=False)  # Paid feature
    
    # Metadata
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sold_at = Column(DateTime)
    
    def to_dict(self):
        """Convert listing to dictionary for API responses"""
        return {
            "id": str(self.id),
            "seller_agent_id": str(self.seller_agent_id),
            "title": self.title,
            "description": self.description,
            "listing_type": self.listing_type.value if self.listing_type else None,
            "category": self.category,
            "tags": self.tags,
            "price_usd": self.price_usd,
            "pricing_model": self.pricing_model,
            "bulk_pricing": self.bulk_pricing,
            "capability_name": self.capability_name,
            "expected_response_time_seconds": self.expected_response_time_seconds,
            "output_format": self.output_format,
            "quality_score": self.quality_score,
            "purchase_count": self.purchase_count,
            "rating_avg": self.rating_avg,
            "rating_count": self.rating_count,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def calculate_value_score(self) -> float:
        """
        Calculate value score based on price, quality, and popularity
        Higher score = better value for buyers
        """
        # Base score from quality (0-50)
        score = self.quality_score / 2
        
        # Adjust for rating (0-25)
        if self.rating_count > 0:
            score += (self.rating_avg / 5.0) * 25
        
        # Adjust for popularity (0-15)
        if self.purchase_count > 0:
            import math
            popularity = min(math.log10(self.purchase_count + 1) * 5, 15)
            score += popularity
        
        # Adjust for price (0-10)
        # Lower price relative to category average = better value
        # This would need category pricing data
        score += 5  # Placeholder
        
        return score
