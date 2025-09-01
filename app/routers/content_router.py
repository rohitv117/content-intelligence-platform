from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import structlog

from app.database import get_db
from app.models.auth import User, get_current_user
from app.models.content import (
    ContentKPIRequest, ContentKPIs, LeaderboardRequest, LeaderboardResponse,
    ROIPredictionRequest, ROIPrediction, ContentSummary, MetricDefinition,
    MetricDefinitionsResponse, TimeGrain, SortBy, SortOrder
)
from app.services.content_service import (
    get_content_kpis, get_content_leaderboard, predict_roi,
    get_content_summary, get_metric_definitions
)
from app.services.permission_service import check_permission

logger = structlog.get_logger()

router = APIRouter()

@router.get("/definitions", response_model=MetricDefinitionsResponse)
async def get_canonical_metric_definitions(
    current_user: User = Depends(get_current_user)
):
    """Get canonical metric definitions and formulas"""
    try:
        check_permission(current_user, "read:reports")
        
        definitions = get_metric_definitions()
        
        logger.info("Metric definitions retrieved", user_id=current_user.id, count=len(definitions))
        
        return MetricDefinitionsResponse(
            definitions=definitions,
            total_count=len(definitions),
            last_updated=definitions[0].last_updated if definitions else None,
            version="1.0"
        )
        
    except Exception as e:
        logger.error("Failed to get metric definitions", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metric definitions"
        )

@router.get("/content/{content_id}/kpis", response_model=List[ContentKPIs])
async def get_content_kpis_endpoint(
    content_id: str,
    grain: TimeGrain = Query(TimeGrain.DAY, description="Time granularity"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_breakdown: bool = Query(False, description="Include cost and revenue breakdown"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content KPIs for a specific content piece"""
    try:
        check_permission(current_user, "read:content")
        
        # Parse dates if provided
        from datetime import datetime
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        kpis = get_content_kpis(
            db, content_id, grain, parsed_start_date, parsed_end_date, include_breakdown
        )
        
        if not kpis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No KPIs found for content ID: {content_id}"
            )
        
        logger.info("Content KPIs retrieved", user_id=current_user.id, content_id=content_id, count=len(kpis))
        
        return kpis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get content KPIs", user_id=current_user.id, content_id=content_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve content KPIs"
        )

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_content_leaderboard(
    sort_by: SortBy = Query(SortBy.ROI, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    
    # Filters
    channel: Optional[str] = Query(None, description="Filter by channel"),
    vertical: Optional[str] = Query(None, description="Filter by vertical"),
    format: Optional[str] = Query(None, description="Filter by format"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    roi_min: Optional[float] = Query(None, description="Minimum ROI percentage"),
    roi_max: Optional[float] = Query(None, description="Maximum ROI percentage"),
    
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content leaderboard with filtering and sorting"""
    try:
        check_permission(current_user, "read:reports")
        
        # Parse dates if provided
        from datetime import datetime
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            try:
                parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        
        if date_to:
            try:
                parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        # Build filter dict
        filters = {
            "channel": channel,
            "vertical": vertical,
            "format": format,
            "date_from": parsed_date_from,
            "date_to": parsed_date_to,
            "roi_min": roi_min,
            "roi_max": roi_max
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        leaderboard = get_content_leaderboard(
            db, sort_by, sort_order, limit, offset, filters
        )
        
        logger.info("Content leaderboard retrieved", user_id=current_user.id, filters=filters, count=len(leaderboard.entries))
        
        return leaderboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get content leaderboard", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve content leaderboard"
        )

@router.post("/roi/predict", response_model=ROIPrediction)
async def predict_content_roi(
    prediction_request: ROIPredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Predict ROI for content based on attributes"""
    try:
        check_permission(current_user, "read:reports")
        
        prediction = predict_roi(db, prediction_request.content_attributes)
        
        logger.info("ROI prediction generated", user_id=current_user.id, predicted_roi=prediction.predicted_roi)
        
        return prediction
        
    except Exception as e:
        logger.error("Failed to predict ROI", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ROI prediction"
        )

@router.get("/summary", response_model=ContentSummary)
async def get_content_summary_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content performance summary for dashboard"""
    try:
        check_permission(current_user, "read:reports")
        
        summary = get_content_summary(db)
        
        logger.info("Content summary retrieved", user_id=current_user.id)
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get content summary", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve content summary"
        )

@router.get("/channels")
async def get_supported_channels(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported content channels"""
    try:
        check_permission(current_user, "read:content")
        
        from app.config import CONTENT_INTELLIGENCE_CONFIG
        
        return {
            "channels": CONTENT_INTELLIGENCE_CONFIG["supported_channels"],
            "total_count": len(CONTENT_INTELLIGENCE_CONFIG["supported_channels"])
        }
        
    except Exception as e:
        logger.error("Failed to get supported channels", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported channels"
        )

@router.get("/verticals")
async def get_supported_verticals(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported business verticals"""
    try:
        check_permission(current_user, "read:content")
        
        from app.config import CONTENT_INTELLIGENCE_CONFIG
        
        return {
            "verticals": CONTENT_INTELLIGENCE_CONFIG["supported_verticals"],
            "total_count": len(CONTENT_INTELLIGENCE_CONFIG["supported_verticals"])
        }
        
    except Exception as e:
        logger.error("Failed to get supported verticals", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported verticals"
        )

@router.get("/formats")
async def get_supported_formats(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported content formats"""
    try:
        check_permission(current_user, "read:content")
        
        from app.config import CONTENT_INTELLIGENCE_CONFIG
        
        return {
            "formats": CONTENT_INTELLIGENCE_CONFIG["supported_formats"],
            "total_count": len(CONTENT_INTELLIGENCE_CONFIG["supported_formats"])
        }
        
    except Exception as e:
        logger.error("Failed to get supported formats", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported formats"
        )

@router.get("/performance-tiers")
async def get_performance_tiers(
    current_user: User = Depends(get_current_user)
):
    """Get performance tier definitions"""
    try:
        check_permission(current_user, "read:reports")
        
        return {
            "roi_tiers": {
                "exceptional": {"min": 100, "description": "ROI >= 100%"},
                "excellent": {"min": 50, "max": 99, "description": "ROI 50-99%"},
                "good": {"min": 20, "max": 49, "description": "ROI 20-49%"},
                "positive": {"min": 0, "max": 19, "description": "ROI 0-19%"},
                "neutral": {"min": -20, "max": -1, "description": "ROI -20% to -1%"},
                "negative": {"max": -20, "description": "ROI < -20%"}
            },
            "performance_tiers": {
                "high_performing": {"min": 0.1, "description": "View rate >= 10%"},
                "medium_performing": {"min": 0.05, "max": 0.099, "description": "View rate 5-9.9%"},
                "low_performing": {"max": 0.049, "description": "View rate < 5%"}
            },
            "engagement_tiers": {
                "high_engagement": {"min": 0.15, "description": "Engagement rate >= 15%"},
                "medium_engagement": {"min": 0.08, "max": 0.149, "description": "Engagement rate 8-14.9%"},
                "low_engagement": {"max": 0.079, "description": "Engagement rate < 8%"}
            }
        }
        
    except Exception as e:
        logger.error("Failed to get performance tiers", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance tiers"
        ) 