from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.config import DATABASE_CONFIG
import structlog

logger = structlog.get_logger()

# Create database engine
engine = create_engine(
    DATABASE_CONFIG["url"],
    poolclass=QueuePool,
    pool_size=DATABASE_CONFIG["pool_size"],
    max_overflow=DATABASE_CONFIG["max_overflow"],
    pool_timeout=DATABASE_CONFIG["pool_timeout"],
    pool_recycle=DATABASE_CONFIG["pool_recycle"],
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

def check_db_connection():
    """Check database connection"""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False

# Database health check
def get_db_health():
    """Get database health status"""
    try:
        with engine.connect() as connection:
            # Check basic connectivity
            connection.execute("SELECT 1")
            
            # Check table count
            result = connection.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = result.scalar()
            
            return {
                "status": "healthy",
                "connection": "connected",
                "tables": table_count,
                "pool_size": DATABASE_CONFIG["pool_size"],
                "pool_overflow": DATABASE_CONFIG["max_overflow"]
            }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "connection": "disconnected",
            "error": str(e)
        } 