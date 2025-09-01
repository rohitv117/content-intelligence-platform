"""
Content Intelligence Platform - Permission Service

Handles role-based access control (RBAC) and permission checks.
"""

from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth import User, UserRole, get_user_permissions, has_permission
from ..services.auth_service import auth_service

# Security scheme
security = HTTPBearer()

class PermissionService:
    """Service for handling permissions and RBAC"""
    
    def __init__(self):
        self.role_permissions = {
            UserRole.finance_admin: [
                "content:read", "content:write", "content:delete",
                "feedback:read", "feedback:write", "feedback:apply",
                "definitions:read", "definitions:write",
                "users:read", "users:write", "users:delete",
                "audit:read", "metrics:read", "ml:read", "ml:write"
            ],
            UserRole.strategy_analyst: [
                "content:read", "content:write",
                "feedback:read", "feedback:write",
                "definitions:read", "definitions:write",
                "metrics:read", "ml:read", "ml:write"
            ],
            UserRole.marketing_user: [
                "content:read", "content:write",
                "feedback:read", "feedback:write",
                "definitions:read", "metrics:read", "ml:read"
            ],
            UserRole.read_only: [
                "content:read", "definitions:read", "metrics:read"
            ]
        }
    
    def get_user_permissions(self, user: User) -> List[str]:
        """Get permissions for a user based on their role"""
        return self.role_permissions.get(user.role, [])
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if a user has a specific permission"""
        user_permissions = self.get_user_permissions(user)
        return permission in user_permissions
    
    def require_permission(self, permission: str):
        """Decorator to require a specific permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # This would be used in route handlers
                # The actual user would be passed via dependency injection
                pass
            return wrapper
        return decorator
    
    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user has permission, raise HTTPException if not"""
        if not self.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return True
    
    def check_role(self, user: User, required_role: UserRole) -> bool:
        """Check if user has required role, raise HTTPException if not"""
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {required_role.value}"
            )
        return True
    
    def check_admin_access(self, user: User) -> bool:
        """Check if user has admin access"""
        return self.check_role(user, UserRole.finance_admin)
    
    def check_analyst_access(self, user: User) -> bool:
        """Check if user has analyst or admin access"""
        if user.role in [UserRole.finance_admin, UserRole.strategy_analyst]:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or admin access required"
        )
    
    def check_content_write_access(self, user: User) -> bool:
        """Check if user can write content"""
        return self.check_permission(user, "content:write")
    
    def check_feedback_apply_access(self, user: User) -> bool:
        """Check if user can apply feedback"""
        return self.check_permission(user, "feedback:apply")
    
    def check_definitions_write_access(self, user: User) -> bool:
        """Check if user can write definitions"""
        return self.check_permission(user, "definitions:write")
    
    def check_ml_write_access(self, user: User) -> bool:
        """Check if user can write ML models"""
        return self.check_permission(user, "ml:write")

# Global instance
permission_service = PermissionService()

# Dependency functions for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_username(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def require_permission(permission: str, user: User = Depends(get_current_user)):
    """Dependency to require a specific permission"""
    permission_service.check_permission(user, permission)
    return user

async def require_admin(user: User = Depends(get_current_user)):
    """Dependency to require admin access"""
    permission_service.check_admin_access(user)
    return user

async def require_analyst(user: User = Depends(get_current_user)):
    """Dependency to require analyst access"""
    permission_service.check_analyst_access(user)
    return user

async def require_content_write(user: User = Depends(get_current_user)):
    """Dependency to require content write access"""
    permission_service.check_content_write_access(user)
    return user

async def require_feedback_apply(user: User = Depends(get_current_user)):
    """Dependency to require feedback apply access"""
    permission_service.check_feedback_apply_access(user)
    return user

async def require_definitions_write(user: User = Depends(get_current_user)):
    """Dependency to require definitions write access"""
    permission_service.check_definitions_write_access(user)
    return user

async def require_ml_write(user: User = Depends(get_current_user)):
    """Dependency to require ML write access"""
    permission_service.check_ml_write_access(user)
    return user 