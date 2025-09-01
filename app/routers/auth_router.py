from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.database import get_db
from app.models.auth import (
    UserCreate, User, UserLogin, Token, TokenData, 
    UserUpdate, PasswordChange, UserPermissions, UserRole
)
from app.services.auth_service import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, verify_password, create_user, update_user,
    change_password, get_user_permissions
)
from app.config import SECURITY_CONFIG

logger = structlog.get_logger()

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = create_user(db, user_data)
        
        logger.info("New user registered", username=user_data.username, role=user_data.role)
        
        return user
        
    except Exception as e:
        logger.error("User registration failed", username=user_data.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    try:
        # Authenticate user
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Check if user is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is temporarily locked"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=SECURITY_CONFIG["access_token_expire_minutes"])
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.failed_login_attempts = 0
        db.commit()
        
        logger.info("User logged in successfully", username=user.username, role=user.role)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": SECURITY_CONFIG["access_token_expire_minutes"] * 60,
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", username=form_data.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.get("/me/permissions", response_model=UserPermissions)
async def get_current_user_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user permissions"""
    permissions = get_user_permissions(current_user.role)
    
    return UserPermissions(
        user_id=current_user.id,
        role=current_user.role,
        permissions=permissions
    )

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    try:
        updated_user = update_user(db, current_user.id, user_update)
        
        logger.info("User updated", user_id=current_user.id, fields_updated=list(user_update.dict(exclude_unset=True).keys()))
        
        return updated_user
        
    except Exception as e:
        logger.error("User update failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.post("/me/change-password")
async def change_current_user_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user password"""
    try:
        # Verify current password
        if not verify_password(password_change.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Change password
        change_password(db, current_user.id, password_change.new_password)
        
        logger.info("User password changed", user_id=current_user.id)
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.post("/refresh")
async def refresh_access_token(
    current_user: User = Depends(get_current_user)
):
    """Refresh access token"""
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=SECURITY_CONFIG["access_token_expire_minutes"])
        access_token = create_access_token(
            data={"sub": current_user.username, "user_id": current_user.id, "role": current_user.role},
            expires_delta=access_token_expires
        )
        
        logger.info("Access token refreshed", username=current_user.username)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": SECURITY_CONFIG["access_token_expire_minutes"] * 60,
            "user_id": current_user.id,
            "username": current_user.username,
            "role": current_user.role
        }
        
    except Exception as e:
        logger.error("Token refresh failed", username=current_user.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (client should discard token)"""
    logger.info("User logged out", username=current_user.username)
    
    return {"message": "Successfully logged out"}

# Admin endpoints (only for finance_admin role)
@router.get("/users", response_model=list[User])
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    if current_user.role != UserRole.FINANCE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    try:
        users = db.query(User).all()
        return users
        
    except Exception as e:
        logger.error("Failed to get users", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )

@router.put("/users/{user_id}", response_model=User)
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    if current_user.role != UserRole.FINANCE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    try:
        updated_user = update_user(db, user_id, user_update)
        
        logger.info("User updated by admin", admin_id=current_user.id, user_id=user_id)
        
        return updated_user
        
    except Exception as e:
        logger.error("Admin user update failed", admin_id=current_user.id, user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate user (admin only)"""
    if current_user.role != UserRole.FINANCE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-deactivation
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        user.is_active = False
        db.commit()
        
        logger.info("User deactivated by admin", admin_id=current_user.id, user_id=user_id)
        
        return {"message": "User deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User deactivation failed", admin_id=current_user.id, user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        ) 