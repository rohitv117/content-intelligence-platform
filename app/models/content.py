from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

class TimeGrain(str, Enum):
    """Time granularity for KPI aggregation"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class SortBy(str, Enum):
    """Sort options for leaderboard"""
    ROI = "roi"
    REVENUE = "revenue"
    ENGAGEMENT = "engagement"
    PERFORMANCE_SCORE = "performance_score"
    VIEWS = "views"
    CONVERSIONS = "conversions"
    COST = "cost"

class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"

class ContentKPIRequest(BaseModel):
    """Request model for content KPIs"""
    content_id: str = Field(..., description="Content ID")
    grain: TimeGrain = Field(TimeGrain.DAY, description="Time granularity")
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")
    include_breakdown: bool = Field(False, description="Include cost and revenue breakdown")

class ContentKPIs(BaseModel):
    """Content KPIs response model"""
    content_id: str
    title: str
    vertical: str
    format: str
    channel: str
    publish_date: datetime
    owner_team: str
    
    # Engagement metrics
    impressions: int
    views: int
    unique_viewers: int
    likes: int
    shares: int
    comments: int
    click_throughs: int
    conversions: int
    conversion_value: float
    
    # Calculated rates
    view_rate_pct: float
    ctr_pct: float
    cvr_pct: float
    engagement_rate_pct: float
    dwell_seconds_median: float
    
    # Cost metrics
    allocated_cost: float
    production_cost: float
    media_cost: float
    tooling_cost: float
    licensing_cost: float
    distribution_cost: float
    
    # Unit economics
    cpm: float
    cpc: float
    cpa: float
    roi_pct: float
    roas: float
    net_profit: float
    
    # Performance indicators
    performance_tier: str
    engagement_tier: str
    roi_tier: str
    performance_score: float
    lifecycle_stage: str
    channel_performance_tier: str
    business_impact_tier: str
    
    # Time context
    event_date: date
    days_since_publish: int
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "content_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "10 Ways to Boost Your SaaS Conversion Rate",
                "vertical": "B2B SaaS",
                "format": "blog",
                "channel": "Blog",
                "publish_date": "2024-01-15T09:00:00Z",
                "owner_team": "Marketing",
                "impressions": 5000,
                "views": 1200,
                "roi_pct": 25.5,
                "performance_score": 78.3
            }
        }

class LeaderboardRequest(BaseModel):
    """Request model for content leaderboard"""
    sort_by: SortBy = Field(SortBy.ROI, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    limit: int = Field(50, ge=1, le=100, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    # Filters
    channel: Optional[str] = Field(None, description="Filter by channel")
    vertical: Optional[str] = Field(None, description="Filter by vertical")
    format: Optional[str] = Field(None, description="Filter by format")
    date_from: Optional[date] = Field(None, description="Filter from date")
    date_to: Optional[date] = Field(None, description="Filter to date")
    roi_min: Optional[float] = Field(None, description="Minimum ROI percentage")
    roi_max: Optional[float] = Field(None, description="Maximum ROI percentage")

class LeaderboardEntry(BaseModel):
    """Leaderboard entry model"""
    rank: int
    content_id: str
    title: str
    vertical: str
    format: str
    channel: str
    publish_date: datetime
    owner_team: str
    
    # Key metrics
    roi_pct: float
    revenue: float
    cost: float
    net_profit: float
    views: int
    conversions: int
    performance_score: float
    
    # Performance indicators
    roi_tier: str
    performance_tier: str
    engagement_tier: str
    
    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    """Leaderboard response model"""
    entries: List[LeaderboardEntry]
    total_count: int
    page: int
    page_size: int
    sort_by: str
    sort_order: str
    filters_applied: Dict[str, Any]

class ROIPredictionRequest(BaseModel):
    """Request model for ROI prediction"""
    content_attributes: Dict[str, Any] = Field(..., description="Content attributes for prediction")
    
    @validator('content_attributes')
    def validate_attributes(cls, v):
        """Validate required attributes"""
        required_fields = ['channel', 'vertical', 'format', 'region']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        return v

class ROIPrediction(BaseModel):
    """ROI prediction response model"""
    content_id: Optional[str] = None
    predicted_roi: float = Field(..., description="Predicted ROI percentage")
    confidence_score: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    prediction_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Feature importance
    feature_importance: Dict[str, float] = Field(..., description="Feature importance scores")
    
    # Model metadata
    model_version: str
    model_type: str
    features_used: List[str]
    
    # Prediction context
    input_features: Dict[str, Any] = Field(..., description="Input features used for prediction")
    
    class Config:
        schema_extra = {
            "example": {
                "predicted_roi": 35.2,
                "confidence_score": 0.85,
                "model_version": "v1.0",
                "model_type": "lightgbm",
                "feature_importance": {
                    "channel": 0.25,
                    "vertical": 0.20,
                    "format": 0.15
                }
            }
        }

class ContentSummary(BaseModel):
    """Content summary for dashboard overview"""
    total_content: int
    total_revenue: float
    total_cost: float
    total_roi: float
    avg_performance_score: float
    
    # By channel
    by_channel: Dict[str, Dict[str, Any]]
    
    # By vertical
    by_vertical: Dict[str, Dict[str, Any]]
    
    # By format
    by_format: Dict[str, Dict[str, Any]]
    
    # Performance distribution
    roi_distribution: Dict[str, int]
    performance_distribution: Dict[str, int]
    
    # Time trends
    daily_metrics: List[Dict[str, Any]]
    weekly_metrics: List[Dict[str, Any]]
    monthly_metrics: List[Dict[str, Any]]

class MetricDefinition(BaseModel):
    """Metric definition for canonical metrics"""
    metric_name: str
    display_name: str
    description: str
    formula: str
    unit: str
    data_source: str
    calculation_frequency: str
    business_owner: str
    last_updated: datetime
    version: str
    
    # Validation rules
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    expected_range: Optional[str] = None
    
    # Related metrics
    related_metrics: List[str] = []
    
    # Business context
    business_context: str
    use_cases: List[str]
    caveats: List[str]

class MetricDefinitionsResponse(BaseModel):
    """Response model for metric definitions"""
    definitions: List[MetricDefinition]
    total_count: int
    last_updated: datetime
    version: str 