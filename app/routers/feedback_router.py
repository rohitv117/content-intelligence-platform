from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import structlog

from app.database import get_db
from app.models.auth import User, get_current_user, UserRole
from app.models.feedback import (
    FeedbackSubmission, FeedbackResponse, FeedbackEvent, FeedbackReview,
    FeedbackApplication, RuleOverride, AuditTrail, FeedbackSummary,
    FeedbackSearchRequest, FeedbackSearchResponse, FeedbackStatus
)
from app.services.feedback_service import (
    submit_feedback, review_feedback, apply_feedback, search_feedback,
    get_feedback_summary, get_audit_trail
)
from app.services.permission_service import check_permission

logger = structlog.get_logger()

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback_endpoint(
    feedback_data: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit stakeholder feedback for review"""
    try:
        # Check if user has permission to submit feedback
        check_permission(current_user, "write:feedback")
        
        # Submit feedback
        response = submit_feedback(db, feedback_data, current_user)
        
        logger.info("Feedback submitted", user_id=current_user.id, feedback_id=response.feedback_id, type=feedback_data.feedback_type)
        
        return response
        
    except Exception as e:
        logger.error("Failed to submit feedback", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )

@router.get("/feedback", response_model=FeedbackSearchResponse)
async def search_feedback_endpoint(
    query: Optional[str] = Query(None, description="Search query"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    actor_role: Optional[str] = Query(None, description="Filter by actor role"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search and filter feedback items"""
    try:
        check_permission(current_user, "read:feedback")
        
        # Parse dates if provided
        from datetime import datetime
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            try:
                parsed_date_from = datetime.strptime(date_from, "%Y-%m-%D").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        
        if date_to:
            try:
                parsed_date_to = datetime.strptime(date_to, "%Y-%m-%D").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        # Build search request
        search_request = FeedbackSearchRequest(
            query=query,
            feedback_type=feedback_type,
            status=status,
            actor_role=actor_role,
            target_type=target_type,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            priority=priority,
            page=page,
            page_size=page_size
        )
        
        # Search feedback
        search_response = search_feedback(db, search_request, current_user)
        
        logger.info("Feedback search completed", user_id=current_user.id, results_count=len(search_response.results))
        
        return search_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to search feedback", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search feedback"
        )

@router.get("/feedback/{feedback_id}", response_model=FeedbackEvent)
async def get_feedback_details(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific feedback item"""
    try:
        check_permission(current_user, "read:feedback")
        
        # Get feedback details
        feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).first()
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback not found: {feedback_id}"
            )
        
        logger.info("Feedback details retrieved", user_id=current_user.id, feedback_id=feedback_id)
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get feedback details", user_id=current_user.id, feedback_id=feedback_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback details"
        )

@router.post("/feedback/{feedback_id}/review", response_model=FeedbackEvent)
async def review_feedback_endpoint(
    feedback_id: str,
    review_data: FeedbackReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Review and approve/reject feedback (admin only)"""
    try:
        # Only finance_admin and strategy_analyst can review feedback
        if current_user.role not in [UserRole.FINANCE_ADMIN, UserRole.STRATEGY_ANALYST]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to review feedback"
            )
        
        # Review feedback
        updated_feedback = review_feedback(db, feedback_id, review_data, current_user)
        
        logger.info("Feedback reviewed", reviewer_id=current_user.id, feedback_id=feedback_id, decision=review_data.decision)
        
        return updated_feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to review feedback", reviewer_id=current_user.id, feedback_id=feedback_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review feedback"
        )

@router.post("/feedback/{feedback_id}/apply", response_model=FeedbackApplication)
async def apply_feedback_endpoint(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply approved feedback (admin only)"""
    try:
        # Only finance_admin can apply feedback
        if current_user.role != UserRole.FINANCE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only finance administrators can apply feedback"
            )
        
        # Apply feedback
        application = apply_feedback(db, feedback_id, current_user)
        
        logger.info("Feedback applied", applier_id=current_user.id, feedback_id=feedback_id)
        
        return application
        
    except Exception as e:
        logger.error("Failed to apply feedback", applier_id=current_user.id, feedback_id=feedback_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply feedback"
        )

@router.get("/feedback/summary", response_model=FeedbackSummary)
async def get_feedback_summary_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback summary for dashboard"""
    try:
        check_permission(current_user, "read:feedback")
        
        summary = get_feedback_summary(db)
        
        logger.info("Feedback summary retrieved", user_id=current_user.id)
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get feedback summary", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback summary"
        )

@router.get("/audit-trail", response_model=List[AuditTrail])
async def get_audit_trail_endpoint(
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    record_id: Optional[str] = Query(None, description="Filter by record ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    changed_by: Optional[str] = Query(None, description="Filter by user who made changes"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit trail for data changes"""
    try:
        # Only finance_admin and strategy_analyst can view audit trail
        if current_user.role not in [UserRole.FINANCE_ADMIN, UserRole.STRATEGY_ANALYST]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view audit trail"
            )
        
        # Parse dates if provided
        from datetime import datetime
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            try:
                parsed_date_from = datetime.strptime(date_from, "%Y-%m-%D").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        
        if date_to:
            try:
                parsed_date_to = datetime.strptime(date_to, "%Y-%m-%D").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        # Get audit trail
        audit_trail = get_audit_trail(
            db, table_name, record_id, action, changed_by, 
            parsed_date_from, parsed_date_to, limit
        )
        
        logger.info("Audit trail retrieved", user_id=current_user.id, count=len(audit_trail))
        
        return audit_trail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audit trail", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail"
        )

@router.get("/rule-overrides", response_model=List[RuleOverride])
async def get_rule_overrides(
    override_type: Optional[str] = Query(None, description="Filter by override type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active rule overrides"""
    try:
        check_permission(current_user, "read:feedback")
        
        # Build query
        query = db.query(RuleOverride)
        
        if override_type:
            query = query.filter(RuleOverride.override_type == override_type)
        
        if is_active is not None:
            query = query.filter(RuleOverride.is_active == is_active)
        
        # Get overrides
        overrides = query.order_by(RuleOverride.created_at.desc()).all()
        
        logger.info("Rule overrides retrieved", user_id=current_user.id, count=len(overrides))
        
        return overrides
        
    except Exception as e:
        logger.error("Failed to get rule overrides", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rule overrides"
        )

@router.post("/feedback/{feedback_id}/withdraw")
async def withdraw_feedback(
    feedback_id: str,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Withdraw submitted feedback (only by original submitter)"""
    try:
        check_permission(current_user, "write:feedback")
        
        # Get feedback
        feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).first()
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback not found: {feedback_id}"
            )
        
        # Check if user is the original submitter
        if feedback.actor_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the original submitter can withdraw feedback"
            )
        
        # Check if feedback can be withdrawn
        if feedback.status not in [FeedbackStatus.PENDING, FeedbackStatus.UNDER_REVIEW]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback cannot be withdrawn in its current status"
            )
        
        # Update status
        feedback.status = FeedbackStatus.REJECTED
        feedback.updated_at = datetime.utcnow()
        
        # Add withdrawal note to payload
        if not feedback.payload:
            feedback.payload = {}
        feedback.payload["withdrawal_reason"] = reason
        feedback.payload["withdrawn_by"] = str(current_user.id)
        feedback.payload["withdrawn_at"] = datetime.utcnow().isoformat()
        
        db.commit()
        
        logger.info("Feedback withdrawn", user_id=current_user.id, feedback_id=feedback_id, reason=reason)
        
        return {"message": "Feedback withdrawn successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to withdraw feedback", user_id=current_user.id, feedback_id=feedback_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to withdraw feedback"
        )

@router.get("/feedback/status/{status}", response_model=List[FeedbackEvent])
async def get_feedback_by_status(
    status: FeedbackStatus,
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback items by status"""
    try:
        check_permission(current_user, "read:feedback")
        
        # Get feedback by status
        feedback_items = db.query(FeedbackEvent).filter(
            FeedbackEvent.status == status
        ).order_by(
            FeedbackEvent.created_at.desc()
        ).limit(limit).all()
        
        logger.info("Feedback by status retrieved", user_id=current_user.id, status=status, count=len(feedback_items))
        
        return feedback_items
        
    except Exception as e:
        logger.error("Failed to get feedback by status", user_id=current_user.id, status=status, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback by status"
        ) 