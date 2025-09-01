from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://content_user:content_pass123@localhost:5432/content_intelligence")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    cors_origins: list = ["*"]
    cors_credentials: bool = True
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    
    # API
    api_prefix: str = "/api"
    api_version: str = "v1"
    title: str = "Content Intelligence Platform"
    description: str = "A comprehensive data platform for content performance and ROI analysis"
    
    # Monitoring
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    metrics_port: int = int(os.getenv("METRICS_PORT", "8000"))
    
    # Content Intelligence specific
    default_amortization_period: int = int(os.getenv("DEFAULT_AMORTIZATION_PERIOD", "12"))
    default_time_decay_factor: float = float(os.getenv("DEFAULT_TIME_DECAY_FACTOR", "0.5"))
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "USD")
    
    # ML Model
    ml_model_path: Optional[str] = os.getenv("ML_MODEL_PATH")
    ml_model_version: str = os.getenv("ML_MODEL_VERSION", "v1.0")
    
    # Data Quality
    data_freshness_hours: int = int(os.getenv("DATA_FRESHNESS_HOURS", "24"))
    roi_min_threshold: float = float(os.getenv("ROI_MIN_THRESHOLD", "-10.0"))
    roi_max_threshold: float = float(os.getenv("ROI_MAX_THRESHOLD", "50.0"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

# Database configuration
DATABASE_CONFIG = {
    "url": settings.database_url,
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
    "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
}

# Security configuration
SECURITY_CONFIG = {
    "secret_key": settings.secret_key,
    "algorithm": settings.algorithm,
    "access_token_expire_minutes": settings.access_token_expire_minutes,
    "password_min_length": int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
    "max_login_attempts": int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
    "lockout_duration_minutes": int(os.getenv("LOCKOUT_DURATION_MINUTES", "15")),
}

# Content Intelligence configuration
CONTENT_INTELLIGENCE_CONFIG = {
    "default_amortization_period": settings.default_amortization_period,
    "default_time_decay_factor": settings.default_time_decay_factor,
    "default_currency": settings.default_currency,
    "supported_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
    "supported_channels": ["YouTube", "TikTok", "Blog", "Email", "Paid Social", "LinkedIn", "Twitter", "Instagram"],
    "supported_verticals": ["B2B SaaS", "E-commerce", "Healthcare", "Marketing", "Education", "Finance", "Technology", "Sales", "Retail", "Learning", "Growth", "Product", "Customer Success", "Analytics", "Health", "Banking", "Enterprise"],
    "supported_formats": ["video", "blog", "ad", "email", "social"],
}

# ML Model configuration
ML_CONFIG = {
    "model_path": settings.ml_model_path,
    "model_version": settings.ml_model_version,
    "features": ["channel", "vertical", "format", "region", "recency_days", "production_cost_ratio", "engagement_score"],
    "target_variable": "predicted_roi",
    "model_type": "lightgbm",
    "prediction_threshold": float(os.getenv("ML_PREDICTION_THRESHOLD", "0.5")),
}

# Data Quality configuration
DATA_QUALITY_CONFIG = {
    "freshness_hours": settings.data_freshness_hours,
    "roi_min_threshold": settings.roi_min_threshold,
    "roi_max_threshold": settings.roi_max_threshold,
    "cpm_min_threshold": float(os.getenv("CPM_MIN_THRESHOLD", "0.01")),
    "cpc_min_threshold": float(os.getenv("CPC_MIN_THRESHOLD", "0.01")),
    "cpa_min_threshold": float(os.getenv("CPA_MIN_THRESHOLD", "0.01")),
    "test_tolerance_pct": float(os.getenv("TEST_TOLERANCE_PCT", "1.0")),
} 