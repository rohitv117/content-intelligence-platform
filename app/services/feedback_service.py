"""
Content Intelligence Platform - Feedback Service

Handles stakeholder feedback processing, rule overrides, and audit trail management.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.feedback import (
    FeedbackSubmission, FeedbackEvent, FeedbackResponse, FeedbackReview,
    FeedbackApplication, RuleOverride, AuditTrail, FeedbackSummary,
    FeedbackSearchRequest, FeedbackSearchResponse, FeedbackType, FeedbackStatus,
    FeedbackTargetType, ActorRole
)
from ..models.auth import User, UserRole
from ..config import CONTENT_INTELLIGENCE_CONFIG

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service for feedback processing and audit trail management"""
    
    def __init__(self):
        self.config = CONTENT_INTELLIGENCE_CONFIG
        # In a real implementation, this would be a database connection
        self.feedback_store = {}
        self.rule_overrides = {}
        self.audit_trail = []
    
    async def submit_feedback(self, feedback: FeedbackSubmission, actor: User) -> FeedbackEvent:
        """Submit new feedback from stakeholder"""
        logger.info(f"Processing feedback submission from {actor.username}")
        
        # Generate feedback ID
        feedback_id = self._generate_feedback_id(feedback, actor)
        
        # Create feedback event
        feedback_event = FeedbackEvent(
            id=feedback_id,
            actor_id=actor.id,
            actor_role=actor.role,
            feedback_type=feedback.feedback_type,
            target_type=feedback.target_type,
            target_id=feedback.target_id,
            payload=feedback.payload,
            status=FeedbackStatus.pending,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={
                "actor_username": actor.username,
                "actor_email": actor.email,
                "submission_hash": self._hash_payload(feedback.payload)
            }
        )
        
        # Store feedback
        self.feedback_store[feedback_id] = feedback_event
        
        # Add to audit trail
        self._add_audit_entry(
            action="feedback_submitted",
            actor_id=actor.id,
            target_type="feedback",
            target_id=feedback_id,
            old_value=None,
            new_value=feedback_event.dict(),
            description=f"Feedback submitted by {actor.username}"
        )
        
        logger.info(f"Feedback {feedback_id} submitted successfully")
        return feedback_event
    
    async def get_feedback(self, feedback_id: str) -> Optional[FeedbackEvent]:
        """Get feedback by ID"""
        return self.feedback_store.get(feedback_id)
    
    async def search_feedback(self, request: FeedbackSearchRequest) -> FeedbackSearchResponse:
        """Search feedback based on criteria"""
        logger.info("Searching feedback")
        
        # Filter feedback based on search criteria
        filtered_feedback = []
        
        for feedback in self.feedback_store.values():
            # Apply filters
            if request.status and feedback.status != request.status:
                continue
            if request.feedback_type and feedback.feedback_type != request.feedback_type:
                continue
            if request.target_type and feedback.target_type != request.target_type:
                continue
            if request.actor_role and feedback.actor_role != request.actor_role:
                continue
            if request.start_date and feedback.created_at < request.start_date:
                continue
            if request.end_date and feedback.created_at > request.end_date:
                continue
            
            filtered_feedback.append(feedback)
        
        # Sort results
        if request.sort_by == "created_at":
            filtered_feedback.sort(key=lambda x: x.created_at, reverse=request.sort_order == "desc")
        elif request.sort_by == "status":
            filtered_feedback.sort(key=lambda x: x.status.value, reverse=request.sort_order == "desc")
        
        # Apply pagination
        total_count = len(filtered_feedback)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_feedback = filtered_feedback[start_idx:end_idx]
        
        return FeedbackSearchResponse(
            feedback=paginated_feedback,
            total_count=total_count,
            page=request.page,
            page_size=request.page_size
        )
    
    async def review_feedback(self, feedback_id: str, review: FeedbackReview, reviewer: User) -> FeedbackEvent:
        """Review feedback (admin/analyst only)"""
        logger.info(f"Reviewing feedback {feedback_id} by {reviewer.username}")
        
        if feedback_id not in self.feedback_store:
            raise ValueError(f"Feedback {feedback_id} not found")
        
        feedback = self.feedback_store[feedback_id]
        
        # Update feedback status
        feedback.status = review.status
        feedback.review_notes = review.notes
        feedback.reviewed_by = reviewer.id
        feedback.reviewed_at = datetime.utcnow()
        feedback.updated_at = datetime.utcnow()
        
        # Add to audit trail
        self._add_audit_entry(
            action="feedback_reviewed",
            actor_id=reviewer.id,
            target_type="feedback",
            target_id=feedback_id,
            old_value={"status": "pending"},
            new_value={"status": review.status, "notes": review.notes},
            description=f"Feedback reviewed by {reviewer.username}"
        )
        
        logger.info(f"Feedback {feedback_id} reviewed successfully")
        return feedback
    
    async def apply_feedback(self, feedback_id: str, application: FeedbackApplication, applier: User) -> RuleOverride:
        """Apply feedback to create rule override (admin only)"""
        logger.info(f"Applying feedback {feedback_id} by {applier.username}")
        
        if feedback_id not in self.feedback_store:
            raise ValueError(f"Feedback {feedback_id} not found")
        
        feedback = self.feedback_store[feedback_id]
        
        # Validate feedback can be applied
        if feedback.status != FeedbackStatus.approved:
            raise ValueError(f"Feedback {feedback_id} must be approved before application")
        
        # Create rule override
        override_id = self._generate_override_id(feedback, application)
        
        rule_override = RuleOverride(
            id=override_id,
            feedback_id=feedback_id,
            rule_type=application.rule_type,
            rule_name=application.rule_name,
            old_value=application.old_value,
            new_value=application.new_value,
            applied_by=applier.id,
            applied_at=datetime.utcnow(),
            effective_from=application.effective_from or datetime.utcnow(),
            effective_until=application.effective_until,
            description=application.description,
            metadata={
                "feedback_type": feedback.feedback_type.value,
                "target_type": feedback.target_type.value,
                "target_id": feedback.target_id,
                "applier_username": applier.username
            }
        )
        
        # Store rule override
        self.rule_overrides[override_id] = rule_override
        
        # Update feedback status
        feedback.status = FeedbackStatus.applied
        feedback.applied_at = datetime.utcnow()
        feedback.updated_at = datetime.utcnow()
        
        # Add to audit trail
        self._add_audit_entry(
            action="feedback_applied",
            actor_id=applier.id,
            target_type="rule_override",
            target_id=override_id,
            old_value=application.old_value,
            new_value=application.new_value,
            description=f"Feedback applied as rule override by {applier.username}"
        )
        
        logger.info(f"Feedback {feedback_id} applied successfully as override {override_id}")
        return rule_override
    
    async def withdraw_feedback(self, feedback_id: str, actor: User) -> FeedbackEvent:
        """Withdraw feedback (only by original submitter or admin)"""
        logger.info(f"Withdrawing feedback {feedback_id} by {actor.username}")
        
        if feedback_id not in self.feedback_store:
            raise ValueError(f"Feedback {feedback_id} not found")
        
        feedback = self.feedback_store[feedback_id]
        
        # Check permissions
        if actor.role != UserRole.finance_admin and feedback.actor_id != actor.id:
            raise ValueError("Only original submitter or admin can withdraw feedback")
        
        # Update status
        old_status = feedback.status
        feedback.status = FeedbackStatus.withdrawn
        feedback.updated_at = datetime.utcnow()
        
        # Add to audit trail
        self._add_audit_entry(
            action="feedback_withdrawn",
            actor_id=actor.id,
            target_type="feedback",
            target_id=feedback_id,
            old_value={"status": old_status},
            new_value={"status": "withdrawn"},
            description=f"Feedback withdrawn by {actor.username}"
        )
        
        logger.info(f"Feedback {feedback_id} withdrawn successfully")
        return feedback
    
    async def get_feedback_summary(self) -> FeedbackSummary:
        """Get feedback summary for dashboards"""
        logger.info("Generating feedback summary")
        
        total_feedback = len(self.feedback_store)
        pending_feedback = len([f for f in self.feedback_store.values() if f.status == FeedbackStatus.pending])
        approved_feedback = len([f for f in self.feedback_store.values() if f.status == FeedbackStatus.approved])
        applied_feedback = len([f for f in self.feedback_store.values() if f.status == FeedbackStatus.applied])
        withdrawn_feedback = len([f for f in self.feedback_store.values() if f.status == FeedbackStatus.withdrawn])
        
        # Count by type
        type_counts = {}
        for feedback in self.feedback_store.values():
            feedback_type = feedback.feedback_type.value
            type_counts[feedback_type] = type_counts.get(feedback_type, 0) + 1
        
        # Count by role
        role_counts = {}
        for feedback in self.feedback_store.values():
            actor_role = feedback.actor_role.value
            role_counts[actor_role] = role_counts.get(actor_role, 0) + 1
        
        # Recent activity
        recent_feedback = sorted(
            self.feedback_store.values(),
            key=lambda x: x.created_at,
            reverse=True
        )[:10]
        
        return FeedbackSummary(
            total_feedback=total_feedback,
            pending_count=pending_feedback,
            approved_count=approved_feedback,
            applied_count=applied_feedback,
            withdrawn_count=withdrawn_feedback,
            type_distribution=type_counts,
            role_distribution=role_counts,
            recent_feedback=[f.id for f in recent_feedback],
            last_updated=datetime.utcnow()
        )
    
    async def get_audit_trail(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             actor_id: Optional[str] = None,
                             action: Optional[str] = None,
                             limit: int = 100) -> List[AuditTrail]:
        """Get audit trail entries"""
        logger.info("Retrieving audit trail")
        
        # Filter audit trail
        filtered_entries = []
        
        for entry in self.audit_trail:
            # Apply filters
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            if actor_id and entry.actor_id != actor_id:
                continue
            if action and entry.action != action:
                continue
            
            filtered_entries.append(entry)
        
        # Sort by timestamp (newest first)
        filtered_entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit
        return filtered_entries[:limit]
    
    async def get_rule_overrides(self, 
                                rule_type: Optional[str] = None,
                                active_only: bool = True) -> List[RuleOverride]:
        """Get rule overrides"""
        logger.info("Retrieving rule overrides")
        
        filtered_overrides = []
        current_time = datetime.utcnow()
        
        for override in self.rule_overrides.values():
            # Apply filters
            if rule_type and override.rule_type != rule_type:
                continue
            if active_only:
                if override.effective_until and override.effective_until < current_time:
                    continue
                if override.effective_from > current_time:
                    continue
            
            filtered_overrides.append(override)
        
        # Sort by effective date
        filtered_overrides.sort(key=lambda x: x.effective_from, reverse=True)
        
        return filtered_overrides
    
    def _generate_feedback_id(self, feedback: FeedbackSubmission, actor: User) -> str:
        """Generate unique feedback ID"""
        timestamp = datetime.utcnow().isoformat()
        content = f"{actor.id}:{feedback.feedback_type.value}:{feedback.target_type.value}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_override_id(self, feedback: FeedbackEvent, application: FeedbackApplication) -> str:
        """Generate unique override ID"""
        timestamp = datetime.utcnow().isoformat()
        content = f"{feedback.id}:{application.rule_type}:{application.rule_name}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        """Hash payload for integrity checking"""
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    def _add_audit_entry(self, action: str, actor_id: str, target_type: str, 
                         target_id: str, old_value: Any, new_value: Any, description: str):
        """Add entry to audit trail"""
        audit_entry = AuditTrail(
            id=len(self.audit_trail) + 1,
            action=action,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            description=description,
            timestamp=datetime.utcnow(),
            metadata={
                "session_id": f"session-{datetime.utcnow().timestamp()}",
                "ip_address": "127.0.0.1"  # In production, this would come from request
            }
        )
        
        self.audit_trail.append(audit_entry)

# Global instance
feedback_service = FeedbackService() 