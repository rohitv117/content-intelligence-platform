from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from app.database import get_db_health
from app.config import settings

logger = structlog.get_logger()

router = APIRouter()

@router.get("/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus metrics"""
    try:
        metrics = generate_latest()
        
        logger.debug("Prometheus metrics generated")
        
        return Response(
            content=metrics,
            media_type=CONTENT_TYPE_LATEST
        )
        
    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        return Response(
            content="Error generating metrics",
            status_code=500
        )

@router.get("/health")
async def get_health_metrics():
    """Get comprehensive health metrics"""
    try:
        # Database health
        db_health = get_db_health()
        
        # Application health
        app_health = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": "running",  # This would be calculated in a real app
            "timestamp": "2024-01-01T00:00:00Z"  # This would be current time
        }
        
        # System health
        import psutil
        system_health = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        # Overall health status
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        
        if system_health["cpu_percent"] > 90 or system_health["memory_percent"] > 90:
            overall_status = "degraded"
        
        health_metrics = {
            "overall_status": overall_status,
            "database": db_health,
            "application": app_health,
            "system": system_health
        }
        
        logger.info("Health metrics retrieved", overall_status=overall_status)
        
        return health_metrics
        
    except Exception as e:
        logger.error("Failed to get health metrics", error=str(e))
        return {
            "overall_status": "unhealthy",
            "error": str(e)
        }

@router.get("/performance")
async def get_performance_metrics():
    """Get performance metrics"""
    try:
        # This would include various performance indicators
        # For now, returning placeholder data
        performance_metrics = {
            "api_latency_p95_ms": 150,
            "api_latency_p99_ms": 300,
            "database_query_time_avg_ms": 25,
            "database_connections_active": 5,
            "database_connections_pool_size": 10,
            "requests_per_minute": 120,
            "error_rate_percent": 0.1,
            "uptime_percent": 99.9
        }
        
        logger.debug("Performance metrics retrieved")
        
        return performance_metrics
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        return {
            "error": "Failed to retrieve performance metrics"
        }

@router.get("/business")
async def get_business_metrics():
    """Get business metrics"""
    try:
        # This would include business KPIs
        # For now, returning placeholder data
        business_metrics = {
            "total_content_pieces": 30,
            "active_campaigns": 5,
            "total_revenue_usd": 150000,
            "total_cost_usd": 75000,
            "overall_roi_percent": 100,
            "content_performance_score_avg": 75.5,
            "feedback_items_pending": 3,
            "feedback_approval_rate_percent": 85.7
        }
        
        logger.debug("Business metrics retrieved")
        
        return business_metrics
        
    except Exception as e:
        logger.error("Failed to get business metrics", error=str(e))
        return {
            "error": "Failed to retrieve business metrics"
        }

@router.get("/data-quality")
async def get_data_quality_metrics():
    """Get data quality metrics"""
    try:
        # This would include data quality indicators
        # For now, returning placeholder data
        data_quality_metrics = {
            "data_freshness_hours": 2,
            "data_completeness_percent": 98.5,
            "data_accuracy_percent": 99.2,
            "failed_tests_count": 0,
            "total_tests_count": 150,
            "test_success_rate_percent": 100,
            "data_lineage_completeness_percent": 95.0,
            "last_data_validation": "2024-01-01T00:00:00Z"
        }
        
        logger.debug("Data quality metrics retrieved")
        
        return data_quality_metrics
        
    except Exception as e:
        logger.error("Failed to get data quality metrics", error=str(e))
        return {
            "error": "Failed to retrieve data quality metrics"
        }

@router.get("/ml-model")
async def get_ml_model_metrics():
    """Get ML model performance metrics"""
    try:
        # This would include ML model performance indicators
        # For now, returning placeholder data
        ml_metrics = {
            "model_version": "v1.0",
            "model_type": "lightgbm",
            "prediction_accuracy_mape": 18.5,
            "prediction_accuracy_smape": 16.2,
            "model_confidence_avg": 0.82,
            "predictions_made_today": 45,
            "predictions_made_total": 1250,
            "last_model_training": "2024-01-01T00:00:00Z",
            "feature_importance_top_3": {
                "channel": 0.25,
                "vertical": 0.20,
                "format": 0.15
            }
        }
        
        logger.debug("ML model metrics retrieved")
        
        return ml_metrics
        
    except Exception as e:
        logger.error("Failed to get ML model metrics", error=str(e))
        return {
            "error": "Failed to retrieve ML model metrics"
        }

@router.get("/summary")
async def get_metrics_summary():
    """Get summary of all metrics"""
    try:
        # Get all metric categories
        health = await get_health_metrics()
        performance = await get_performance_metrics()
        business = await get_business_metrics()
        data_quality = await get_data_quality_metrics()
        ml_model = await get_ml_model_metrics()
        
        summary = {
            "timestamp": "2024-01-01T00:00:00Z",
            "overall_status": health.get("overall_status", "unknown"),
            "health": health,
            "performance": performance,
            "business": business,
            "data_quality": data_quality,
            "ml_model": ml_model
        }
        
        logger.info("Metrics summary generated", overall_status=summary["overall_status"])
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get metrics summary", error=str(e))
        return {
            "error": "Failed to generate metrics summary",
            "timestamp": "2024-01-01T00:00:00Z"
        } 