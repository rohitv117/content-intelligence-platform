from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class FeedbackType(str, Enum):
    """Types of feedback that can be submitted"""
    DEFINITION_CORRECTION = "definition_correction"
    MISATTRIBUTION = "misattribution"
    OVERRIDE = "override"
    RULE_CHANGE = "rule_change"
    METRIC_UPDATE = "metric_update"
    COST_ALLOCATION = "cost_allocation"
    REVENUE_ATTRIBUTION = "revenue_attribution"

class FeedbackStatus(str, Enum):
    """Status of feedback items"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"

class FeedbackTargetType(str, Enum):
    """Types of targets for feedback"""
    METRIC = "metric"
    CONTENT_ID = "content_id"
    RULE_ID = "rule_id"
    DEFINITION = "definition"
    COST_ALLOCATION = "cost_allocation"
    REVENUE_ATTRIBUTION = "revenue_attribution"

class ActorRole(str, Enum):
    """Roles of feedback actors"""
    FINANCE = "Finance"
    STRATEGY = "Strategy"
    MARKETING = "Marketing"
    SALESOPS = "SalesOps"
    DATA = "Data"
    OPERATIONS = "Operations"

class FeedbackSubmission(BaseModel):
    """Model for submitting feedback"""
    actor_id: str = Field(..., description="Unique identifier for the actor")
    actor_role: ActorRole = Field(..., description="Role of the person submitting feedback")
    feedback_type: FeedbackType = Field(..., description="Type of feedback being submitted")
    
    # Target information
    target_type: FeedbackTargetType = Field(..., description="Type of target for the feedback")
    target_id: Optional[str] = Field(None, description="Specific ID of the target (if applicable)")
    
    # Feedback details
    payload: Dict[str, Any] = Field(..., description="Detailed feedback payload")
    description: str = Field(..., min_length=10, max_length=1000, description="Human-readable description of the feedback")
    priority: str = Field("medium", description="Priority level: low, medium, high, critical")
    
    # Business context
    business_impact: Optional[str] = Field(None, description="Description of business impact")
    expected_outcome: Optional[str] = Field(None, description="Expected outcome from this feedback")
    
    # Supporting evidence
    evidence: Optional[List[str]] = Field(None, description="List of evidence or references")
    attachments: Optional[List[str]] = Field(None, description="List of attachment URLs or references")
    
    @validator('payload')
    def validate_payload(cls, v):
        """Validate payload structure based on feedback type"""
        if not isinstance(v, dict):
            raise ValueError("Payload must be a dictionary")
        
        # Add type-specific validation here if needed
        return v

class FeedbackEvent(BaseModel):
    """Feedback event model for database storage"""
    id: str
    actor_id: str
    actor_role: ActorRole
    feedback_type: FeedbackType
    target_type: FeedbackTargetType
    target_id: Optional[str]
    payload: Dict[str, Any]
    description: str
    priority: str
    business_impact: Optional[str]
    expected_outcome: Optional[str]
    evidence: Optional[List[str]]
    attachments: Optional[List[str]]
    
    # Status and workflow
    status: FeedbackStatus = FeedbackStatus.PENDING
    impact_analysis: Optional[Dict[str, Any]] = None
    applied_by: Optional[str] = None
    applied_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    feedback_id: str
    status: FeedbackStatus
    message: str
    estimated_review_time: Optional[str] = None
    next_steps: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "feedback_id": "fb_12345",
                "status": "pending",
                "message": "Feedback submitted successfully and is under review",
                "estimated_review_time": "2-3 business days",
                "next_steps": [
                    "Finance team will review the feedback",
                    "Impact analysis will be performed",
                    "You will be notified of the decision"
                ]
            }
        }

class FeedbackReview(BaseModel):
    """Model for reviewing feedback"""
    feedback_id: str
    reviewer_id: str
    reviewer_role: ActorRole
    
    # Review decision
    decision: str = Field(..., description="Decision: approve, reject, request_changes")
    decision_reason: str = Field(..., min_length=10, description="Reason for the decision")
    
    # Impact analysis
    impact_analysis: Dict[str, Any] = Field(..., description="Detailed impact analysis")
    risk_assessment: str = Field(..., description="Risk assessment of applying the feedback")
    
    # Implementation details
    implementation_notes: Optional[str] = Field(None, description="Notes for implementation")
    rollback_plan: Optional[str] = Field(None, description="Rollback plan if needed")
    
    # Timeline
    target_implementation_date: Optional[datetime] = Field(None, description="Target date for implementation")
    estimated_effort: Optional[str] = Field(None, description="Estimated effort for implementation")

class FeedbackApplication(BaseModel):
    """Model for applying approved feedback"""
    feedback_id: str
    applier_id: str
    applier_role: ActorRole
    
    # Application details
    application_method: str = Field(..., description="Method used to apply the feedback")
    changes_made: List[Dict[str, Any]] = Field(..., description="List of changes made")
    
    # Validation
    validation_results: Dict[str, Any] = Field(..., description="Results of validation after application")
    rollback_triggered: bool = Field(False, description="Whether rollback was triggered")
    
    # Metadata
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    application_duration_seconds: Optional[float] = Field(None, description="Time taken to apply changes")

class RuleOverride(BaseModel):
    """Model for rule overrides created from feedback"""
    id: str
    feedback_event_id: str
    
    # Override details
    override_type: str = Field(..., description="Type of override")
    original_value: Dict[str, Any] = Field(..., description="Original value before override")
    new_value: Dict[str, Any] = Field(..., description="New value after override")
    
    # Effectiveness
    effective_from: datetime = Field(..., description="When the override becomes effective")
    effective_to: Optional[datetime] = Field(None, description="When the override expires (if applicable)")
    is_active: bool = Field(True, description="Whether the override is currently active")
    
    # Metadata
    created_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True

class AuditTrail(BaseModel):
    """Model for audit trail entries"""
    id: str
    table_name: str
    record_id: str
    action: str = Field(..., description="Action performed: INSERT, UPDATE, DELETE")
    
    # Change details
    old_values: Optional[Dict[str, Any]] = Field(None, description="Values before the change")
    new_values: Optional[Dict[str, Any]] = Field(None, description="Values after the change")
    
    # Actor information
    changed_by: str = Field(..., description="User who made the change")
    changed_at: datetime = Field(..., description="When the change was made")
    change_reason: Optional[str] = Field(None, description="Reason for the change")
    
    # Context
    session_id: Optional[str] = Field(None, description="Session ID when change was made")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User agent string")
    
    class Config:
        from_attributes = True

class FeedbackSummary(BaseModel):
    """Summary model for feedback dashboard"""
    total_feedback: int
    pending_review: int
    approved: int
    rejected: int
    applied: int
    
    # By type
    by_type: Dict[FeedbackType, int]
    
    # By status
    by_status: Dict[FeedbackStatus, int]
    
    # By role
    by_role: Dict[ActorRole, int]
    
    # Recent activity
    recent_feedback: List[FeedbackEvent]
    recent_applications: List[FeedbackApplication]
    
    # Performance metrics
    avg_review_time_hours: float
    approval_rate: float
    application_success_rate: float

class FeedbackSearchRequest(BaseModel):
    """Request model for searching feedback"""
    query: Optional[str] = Field(None, description="Search query")
    feedback_type: Optional[FeedbackType] = Field(None, description="Filter by feedback type")
    status: Optional[FeedbackStatus] = Field(None, description="Filter by status")
    actor_role: Optional[ActorRole] = Field(None, description="Filter by actor role")
    target_type: Optional[FeedbackTargetType] = Field(None, description="Filter by target type")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    priority: Optional[str] = Field(None, description="Filter by priority")
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Page size")

class FeedbackSearchResponse(BaseModel):
    """Response model for feedback search"""
    results: List[FeedbackEvent]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    
    # Search metadata
    query_executed: str
    filters_applied: Dict[str, Any]
    search_duration_ms: float 