from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """User roles for RBAC"""
    FINANCE_ADMIN = "finance_admin"
    STRATEGY_ANALYST = "strategy_analyst"
    MARKETING_USER = "marketing_user"
    READ_ONLY = "read_only"

class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    role: UserRole = Field(..., description="User role for access control")
    is_active: bool = Field(True, description="Whether the user account is active")

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    """User model as stored in database"""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

class User(UserBase):
    """User model for API responses"""
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """User login model"""
    username: str = Field(..., description="Username for login")
    password: str = Field(..., description="Password for login")

class Token(BaseModel):
    """JWT token model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: UserRole = Field(..., description="User role")

class TokenData(BaseModel):
    """Token data model for JWT payload"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None
    exp: Optional[datetime] = None

class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_new_password_strength(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserPermissions(BaseModel):
    """User permissions model"""
    user_id: int
    role: UserRole
    permissions: List[str] = Field(..., description="List of user permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "role": "finance_admin",
                "permissions": [
                    "read:content",
                    "write:content",
                    "read:costs",
                    "write:costs",
                    "read:revenue",
                    "write:revenue",
                    "read:feedback",
                    "write:feedback",
                    "apply:feedback",
                    "read:reports",
                    "write:reports"
                ]
            }
        }

# Permission definitions
PERMISSIONS = {
    UserRole.FINANCE_ADMIN: [
        "read:content", "write:content",
        "read:costs", "write:costs",
        "read:revenue", "write:revenue",
        "read:feedback", "write:feedback", "apply:feedback",
        "read:reports", "write:reports",
        "read:users", "write:users",
        "read:finance_rules", "write:finance_rules"
    ],
    UserRole.STRATEGY_ANALYST: [
        "read:content", "write:content",
        "read:costs", "read:revenue",
        "read:feedback", "write:feedback",
        "read:reports", "write:reports",
        "read:finance_rules"
    ],
    UserRole.MARKETING_USER: [
        "read:content", "write:content",
        "read:costs", "read:revenue",
        "read:feedback", "write:feedback",
        "read:reports"
    ],
    UserRole.READ_ONLY: [
        "read:content", "read:costs", "read:revenue",
        "read:reports"
    ]
}

def get_user_permissions(role: UserRole) -> List[str]:
    """Get permissions for a given user role"""
    return PERMISSIONS.get(role, [])

def has_permission(user_role: UserRole, required_permission: str) -> bool:
    """Check if user has a specific permission"""
    user_permissions = get_user_permissions(user_role)
    return required_permission in user_permissions 