"""
Content Intelligence Platform - SQLAlchemy Models

Defines the database schema using SQLAlchemy ORM models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class Content(Base):
    """Content table model"""
    __tablename__ = "content"
    
    id = Column(String(50), primary_key=True)
    title = Column(String(500), nullable=False)
    vertical = Column(String(100), nullable=False)
    format = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False, default="en")
    region = Column(String(50), nullable=False, default="global")
    publish_dt = Column(DateTime, nullable=False)
    channel = Column(String(100), nullable=False)
    campaign_id = Column(String(100))
    owner_team = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    engagement_events = relationship("EngagementEvent", back_populates="content")
    costs = relationship("Cost", back_populates="content")
    revenue = relationship("Revenue", back_populates="content")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_channel', 'channel'),
        Index('idx_content_vertical', 'vertical'),
        Index('idx_content_publish_dt', 'publish_dt'),
        Index('idx_content_campaign', 'campaign_id'),
    )

class EngagementEvent(Base):
    """Engagement events table model"""
    __tablename__ = "engagement_events"
    
    id = Column(String(50), primary_key=True)
    content_id = Column(String(50), ForeignKey("content.id"), nullable=False)
    event_dt = Column(DateTime, nullable=False)
    impressions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    dwell_seconds_median = Column(Float)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    click_throughs = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    conversion_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="engagement_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_engagement_content_dt', 'content_id', 'event_dt'),
        Index('idx_engagement_event_dt', 'event_dt'),
    )

class Cost(Base):
    """Costs table model"""
    __tablename__ = "costs"
    
    id = Column(String(50), primary_key=True)
    content_id = Column(String(50), ForeignKey("content.id"), nullable=False)
    cost_type = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    cost_dt = Column(DateTime, nullable=False)
    vendor = Column(String(200))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="costs")
    
    # Indexes
    __table_args__ = (
        Index('idx_cost_content_type', 'content_id', 'cost_type'),
        Index('idx_cost_dt', 'cost_dt'),
        Index('idx_cost_type', 'cost_type'),
    )

class Revenue(Base):
    """Revenue table model"""
    __tablename__ = "revenue"
    
    id = Column(String(50), primary_key=True)
    content_id = Column(String(50), ForeignKey("content.id"))
    campaign_id = Column(String(100))
    rev_dt = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    source = Column(String(100), nullable=False)
    attribution_model = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="revenue")
    
    # Indexes
    __table_args__ = (
        Index('idx_revenue_content', 'content_id'),
        Index('idx_revenue_campaign', 'campaign_id'),
        Index('idx_revenue_dt', 'rev_dt'),
        Index('idx_revenue_source', 'source'),
    )

class FinanceRule(Base):
    """Finance rules table model"""
    __tablename__ = "finance_rules"
    
    id = Column(String(50), primary_key=True)
    rule_name = Column(String(200), nullable=False, unique=True)
    rule_type = Column(String(100), nullable=False)  # amortization, attribution, allocation
    rule_config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    
    # Indexes
    __table_args__ = (
        Index('idx_finance_rules_type', 'rule_type'),
        Index('idx_finance_rules_active', 'is_active'),
    )

class FeedbackEvent(Base):
    """Feedback events table model"""
    __tablename__ = "feedback_events"
    
    id = Column(String(50), primary_key=True)
    actor_id = Column(String(100), nullable=False)
    actor_role = Column(String(100), nullable=False)
    feedback_type = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    review_notes = Column(Text)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    applied_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON)
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_actor', 'actor_id'),
        Index('idx_feedback_status', 'status'),
        Index('idx_feedback_target', 'target_type', 'target_id'),
        Index('idx_feedback_created', 'created_at'),
    )

class RuleOverride(Base):
    """Rule overrides table model"""
    __tablename__ = "rule_overrides"
    
    id = Column(String(50), primary_key=True)
    feedback_id = Column(String(50), ForeignKey("feedback_events.id"), nullable=False)
    rule_type = Column(String(100), nullable=False)
    rule_name = Column(String(200), nullable=False)
    old_value = Column(JSON)
    new_value = Column(JSON, nullable=False)
    applied_by = Column(String(100), nullable=False)
    applied_at = Column(DateTime, nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_until = Column(DateTime)
    description = Column(Text)
    metadata = Column(JSON)
    
    # Relationships
    feedback = relationship("FeedbackEvent")
    
    # Indexes
    __table_args__ = (
        Index('idx_override_rule_type', 'rule_type'),
        Index('idx_override_effective', 'effective_from', 'effective_until'),
        Index('idx_override_feedback', 'feedback_id'),
    )

class Channel(Base):
    """Channels lookup table model"""
    __tablename__ = "channels"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vertical(Base):
    """Verticals lookup table model"""
    __tablename__ = "verticals"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    business_unit = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CostType(Base):
    """Cost types lookup table model"""
    __tablename__ = "cost_types"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(100))
    is_capitalizable = Column(Boolean, default=False)
    is_media_cost = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Format(Base):
    """Content formats lookup table model"""
    __tablename__ = "formats"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(100))
    complexity_score = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Currency(Base):
    """Currencies lookup table model"""
    __tablename__ = "currencies"
    
    id = Column(String(3), primary_key=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    """Exchange rates table model"""
    __tablename__ = "exchange_rates"
    
    id = Column(String(50), primary_key=True)
    from_currency = Column(String(3), ForeignKey("currencies.id"), nullable=False)
    to_currency = Column(String(3), ForeignKey("currencies.id"), nullable=False)
    rate = Column(Float, nullable=False)
    effective_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_exchange_rate_date', 'effective_date'),
        Index('idx_exchange_rate_currencies', 'from_currency', 'to_currency'),
    )

class MLModel(Base):
    """ML models table model"""
    __tablename__ = "ml_models"
    
    id = Column(String(50), primary_key=True)
    model_name = Column(String(200), nullable=False)
    model_type = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    file_path = Column(String(500))
    model_config = Column(JSON)
    performance_metrics = Column(JSON)
    training_data_info = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_ml_model_name_version', 'model_name', 'version'),
        Index('idx_ml_model_active', 'is_active'),
    )

class MLPrediction(Base):
    """ML predictions table model"""
    __tablename__ = "ml_predictions"
    
    id = Column(String(50), primary_key=True)
    model_id = Column(String(50), ForeignKey("ml_models.id"), nullable=False)
    content_id = Column(String(50), ForeignKey("content.id"))
    input_features = Column(JSON, nullable=False)
    prediction = Column(Float, nullable=False)
    confidence_score = Column(Float)
    feature_importance = Column(JSON)
    prediction_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    model = relationship("MLModel")
    content = relationship("Content")
    
    # Indexes
    __table_args__ = (
        Index('idx_ml_prediction_model', 'model_id'),
        Index('idx_ml_prediction_content', 'content_id'),
        Index('idx_ml_prediction_timestamp', 'prediction_timestamp'),
    )

class AuditTrail(Base):
    """Audit trail table model"""
    __tablename__ = "audit_trail"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(200), nullable=False)
    actor_id = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(100), nullable=False)
    old_value = Column(JSON)
    new_value = Column(JSON)
    description = Column(Text)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata = Column(JSON)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_actor', 'actor_id'),
        Index('idx_audit_target', 'target_type', 'target_id'),
        Index('idx_audit_timestamp', 'timestamp'),
    ) 