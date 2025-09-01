"""
Content Intelligence Platform - Authentication Service

Handles user authentication, JWT token management, and user operations.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..models.auth import User, UserCreate, UserUpdate, UserInDB, TokenData, UserRole
from ..config import SECURITY_CONFIG
from ..database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service for user management and JWT operations"""
    
    def __init__(self):
        self.secret_key = SECURITY_CONFIG["SECRET_KEY"]
        self.algorithm = SECURITY_CONFIG["ALGORITHM"]
        self.access_token_expire_minutes = SECURITY_CONFIG["ACCESS_TOKEN_EXPIRE_MINUTES"]
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            token_data = TokenData(username=username)
            return token_data
        except JWTError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password"""
        # In a real implementation, this would query the database
        # For demo purposes, we'll use a simple in-memory user store
        fake_users_db = self._get_fake_users()
        
        if username not in fake_users_db:
            return None
        
        user = fake_users_db[username]
        if not self.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def create_user(self, user: UserCreate) -> User:
        """Create a new user"""
        # In a real implementation, this would save to database
        hashed_password = self.get_password_hash(user.password)
        
        # Generate a unique user ID
        user_id = secrets.token_urlsafe(16)
        
        db_user = UserInDB(
            id=user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role=user.role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Convert to User model for response
        return User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        fake_users_db = self._get_fake_users()
        return fake_users_db.get(username)
    
    def update_user(self, username: str, user_update: UserUpdate) -> Optional[User]:
        """Update a user"""
        fake_users_db = self._get_fake_users()
        
        if username not in fake_users_db:
            return None
        
        user = fake_users_db[username]
        
        # Update fields
        if user_update.email is not None:
            user.email = user_update.email
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        if user_update.role is not None:
            user.role = user_update.role
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        
        user.updated_at = datetime.utcnow()
        
        return user
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change a user's password"""
        fake_users_db = self._get_fake_users()
        
        if username not in fake_users_db:
            return False
        
        user = fake_users_db[username]
        
        # Verify old password
        if not self.verify_password(old_password, user.hashed_password):
            return False
        
        # Hash new password
        user.hashed_password = self.get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        return True
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user"""
        fake_users_db = self._get_fake_users()
        
        if username not in fake_users_db:
            return False
        
        user = fake_users_db[username]
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        return True
    
    def _get_fake_users(self) -> Dict[str, UserInDB]:
        """Get fake users for demo purposes"""
        # In production, this would be replaced with database queries
        return {
            "admin": UserInDB(
                id="admin-001",
                username="admin",
                email="admin@company.com",
                full_name="System Administrator",
                hashed_password=self.get_password_hash("admin123"),
                role=UserRole.finance_admin,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            "analyst": UserInDB(
                id="analyst-001",
                username="analyst",
                email="analyst@company.com",
                full_name="Strategy Analyst",
                hashed_password=self.get_password_hash("analyst123"),
                role=UserRole.strategy_analyst,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            "marketing": UserInDB(
                id="marketing-001",
                username="marketing",
                email="marketing@company.com",
                full_name="Marketing Manager",
                hashed_password=self.get_password_hash("marketing123"),
                role=UserRole.marketing_user,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            "viewer": UserInDB(
                id="viewer-001",
                username="viewer",
                email="viewer@company.com",
                full_name="Read Only User",
                hashed_password=self.get_password_hash("viewer123"),
                role=UserRole.read_only,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        }

# Global instance
auth_service = AuthService() 