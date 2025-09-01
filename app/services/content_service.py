"""
Content Intelligence Platform - Content Service

Handles content-related business logic including KPIs, leaderboards, and ROI predictions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.content import (
    ContentKPIRequest, ContentKPIs, LeaderboardRequest, LeaderboardResponse,
    LeaderboardEntry, ROIPredictionRequest, ROIPrediction, ContentSummary,
    MetricDefinition, MetricDefinitionsResponse, TimeGrain, SortBy, SortOrder
)
from ..config import CONTENT_INTELLIGENCE_CONFIG, ML_CONFIG
from ..database import get_db

logger = logging.getLogger(__name__)

class ContentService:
    """Service for content-related operations"""
    
    def __init__(self):
        self.config = CONTENT_INTELLIGENCE_CONFIG
        self.ml_config = ML_CONFIG
    
    async def get_content_kpis(self, content_id: str, request: ContentKPIRequest) -> ContentKPIs:
        """Get KPIs for a specific content item"""
        logger.info(f"Getting KPIs for content {content_id}")
        
        # In a real implementation, this would query the database
        # For demo purposes, we'll return mock data
        mock_kpis = self._generate_mock_kpis(content_id, request)
        
        return mock_kpis
    
    async def get_leaderboard(self, request: LeaderboardRequest) -> LeaderboardResponse:
        """Get content leaderboard based on criteria"""
        logger.info("Getting content leaderboard")
        
        # In a real implementation, this would query the database
        # For demo purposes, we'll return mock data
        mock_entries = self._generate_mock_leaderboard(request)
        
        return LeaderboardResponse(
            entries=mock_entries,
            total_count=len(mock_entries),
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
    
    async def predict_roi(self, request: ROIPredictionRequest) -> ROIPrediction:
        """Predict ROI for content attributes"""
        logger.info("Predicting ROI for content")
        
        # In a real implementation, this would call the ML model
        # For demo purposes, we'll return mock predictions
        mock_prediction = self._generate_mock_roi_prediction(request)
        
        return mock_prediction
    
    async def get_content_summary(self) -> ContentSummary:
        """Get high-level content summary for dashboards"""
        logger.info("Getting content summary")
        
        # In a real implementation, this would aggregate from database
        # For demo purposes, we'll return mock data
        mock_summary = self._generate_mock_content_summary()
        
        return mock_summary
    
    async def get_metric_definitions(self) -> MetricDefinitionsResponse:
        """Get canonical metric definitions"""
        logger.info("Getting metric definitions")
        
        definitions = [
            MetricDefinition(
                name="ROI",
                description="Return on Investment: (Revenue - Cost) / Cost * 100",
                formula="(attributed_revenue - allocated_cost) / allocated_cost * 100",
                unit="percentage",
                category="financial",
                caveats=["Costs must be fully allocated", "Revenue must be properly attributed"]
            ),
            MetricDefinition(
                name="CPM",
                description="Cost Per Mille: Cost per 1000 impressions",
                formula="allocated_cost / (impressions / 1000)",
                unit="currency per 1000 impressions",
                category="efficiency",
                caveats=["Impressions must be valid", "Costs must be allocated"]
            ),
            MetricDefinition(
                name="CPC",
                description="Cost Per Click: Cost per click-through",
                formula="allocated_cost / click_throughs",
                unit="currency per click",
                category="efficiency",
                caveats=["Click-throughs must be valid", "Costs must be allocated"]
            ),
            MetricDefinition(
                name="CPA",
                description="Cost Per Acquisition: Cost per conversion",
                formula="allocated_cost / conversions",
                unit="currency per conversion",
                category="efficiency",
                caveats=["Conversions must be valid", "Costs must be allocated"]
            ),
            MetricDefinition(
                name="ROAS",
                description="Return on Ad Spend: Revenue / Cost",
                formula="attributed_revenue / allocated_cost",
                unit="ratio",
                category="financial",
                caveats=["Revenue must be attributed", "Costs must be allocated"]
            ),
            MetricDefinition(
                name="Engagement Rate",
                description="Engagement interactions per view",
                formula="(likes + shares + comments) / views * 100",
                unit="percentage",
                category="quality",
                caveats=["Views must be valid", "All engagement types counted equally"]
            ),
            MetricDefinition(
                name="View Rate",
                description="Views per impression",
                formula="views / impressions * 100",
                unit="percentage",
                category="reach",
                caveats=["Impressions must be valid", "Views must be unique"]
            ),
            MetricDefinition(
                name="CTR",
                description="Click-Through Rate: Clicks per impression",
                formula="click_throughs / impressions * 100",
                unit="percentage",
                category="conversion",
                caveats=["Impressions must be valid", "Clicks must be valid"]
            ),
            MetricDefinition(
                name="CVR",
                description="Conversion Rate: Conversions per click",
                formula="conversions / click_throughs * 100",
                unit="percentage",
                category="conversion",
                caveats=["Click-throughs must be valid", "Conversions must be valid"]
            )
        ]
        
        return MetricDefinitionsResponse(
            definitions=definitions,
            total_count=len(definitions),
            last_updated=datetime.utcnow().isoformat()
        )
    
    async def get_channels(self) -> List[str]:
        """Get available channels"""
        return self.config["SUPPORTED_CHANNELS"]
    
    async def get_verticals(self) -> List[str]:
        """Get available verticals"""
        return self.config["SUPPORTED_VERTICALS"]
    
    async def get_formats(self) -> List[str]:
        """Get available formats"""
        return self.config["SUPPORTED_FORMATS"]
    
    async def get_performance_tiers(self) -> List[str]:
        """Get performance tier definitions"""
        return ["Top Performer", "High Performer", "Medium Performer", "Low Performer", "Underperformer"]
    
    def _generate_mock_kpis(self, content_id: str, request: ContentKPIRequest) -> ContentKPIs:
        """Generate mock KPIs for demo purposes"""
        # Base metrics
        base_metrics = {
            "impressions": 50000,
            "views": 15000,
            "unique_viewers": 12000,
            "dwell_seconds_median": 45,
            "likes": 750,
            "shares": 300,
            "comments": 200,
            "click_throughs": 1200,
            "conversions": 180,
            "conversion_value": 9000
        }
        
        # Calculate derived metrics
        view_rate = (base_metrics["views"] / base_metrics["impressions"]) * 100
        ctr = (base_metrics["click_throughs"] / base_metrics["impressions"]) * 100
        cvr = (base_metrics["conversions"] / base_metrics["click_throughs"]) * 100
        engagement_rate = ((base_metrics["likes"] + base_metrics["shares"] + base_metrics["comments"]) / base_metrics["views"]) * 100
        
        # Mock costs and revenue
        allocated_cost = 5000
        attributed_revenue = 9000
        
        # Calculate financial metrics
        roi = ((attributed_revenue - allocated_cost) / allocated_cost) * 100
        roas = attributed_revenue / allocated_cost
        cpm = allocated_cost / (base_metrics["impressions"] / 1000)
        cpc = allocated_cost / base_metrics["click_throughs"]
        cpa = allocated_cost / base_metrics["conversions"]
        
        return ContentKPIs(
            content_id=content_id,
            title="Sample Content Title",
            channel="YouTube",
            vertical="B2B SaaS",
            format="video",
            publish_date=datetime.now() - timedelta(days=30),
            time_grain=request.time_grain,
            start_date=request.start_date,
            end_date=request.end_date,
            reach_metrics=base_metrics,
            quality_metrics={
                "view_rate_pct": view_rate,
                "engagement_rate_pct": engagement_rate,
                "dwell_seconds_median": base_metrics["dwell_seconds_median"]
            },
            conversion_metrics={
                "ctr_pct": ctr,
                "cvr_pct": cvr,
                "conversion_value": base_metrics["conversion_value"]
            },
            cost_metrics={
                "allocated_cost": allocated_cost,
                "cpm": cpm,
                "cpc": cpc,
                "cpa": cpa
            },
            financial_metrics={
                "attributed_revenue": attributed_revenue,
                "roi_pct": roi,
                "roas": roas,
                "net_profit": attributed_revenue - allocated_cost
            },
            performance_tier="High Performer",
            calculated_at=datetime.utcnow()
        )
    
    def _generate_mock_leaderboard(self, request: LeaderboardRequest) -> List[LeaderboardEntry]:
        """Generate mock leaderboard entries for demo purposes"""
        mock_entries = []
        
        # Generate sample content entries
        sample_content = [
            {"id": "content-001", "title": "B2B SaaS Growth Strategies", "channel": "YouTube", "vertical": "B2B SaaS", "roi": 85.5, "engagement": 92.3, "views": 25000},
            {"id": "content-002", "title": "Marketing Automation Guide", "channel": "Blog", "vertical": "Marketing", "roi": 67.2, "engagement": 78.9, "views": 18000},
            {"id": "content-003", "title": "Sales Process Optimization", "channel": "LinkedIn", "vertical": "Sales", "roi": 73.8, "engagement": 81.2, "views": 22000},
            {"id": "content-004", "title": "Customer Success Best Practices", "channel": "Email", "vertical": "B2B SaaS", "roi": 91.2, "engagement": 88.7, "views": 30000},
            {"id": "content-005", "title": "Product Launch Strategy", "channel": "TikTok", "vertical": "Technology", "roi": 58.9, "engagement": 95.1, "views": 45000}
        ]
        
        # Apply filters
        filtered_content = sample_content
        if request.filters and request.filters.get("channel"):
            filtered_content = [c for c in filtered_content if c["channel"] == request.filters["channel"]]
        if request.filters and request.filters.get("vertical"):
            filtered_content = [c for c in filtered_content if c["vertical"] == request.filters["vertical"]]
        
        # Sort by requested criteria
        if request.sort_by == SortBy.roi:
            filtered_content.sort(key=lambda x: x["roi"], reverse=(request.sort_order == SortOrder.desc))
        elif request.sort_by == SortBy.engagement:
            filtered_content.sort(key=lambda x: x["engagement"], reverse=(request.sort_order == SortOrder.desc))
        elif request.sort_by == SortBy.views:
            filtered_content.sort(key=lambda x: x["views"], reverse=(request.sort_order == SortOrder.desc))
        
        # Apply pagination
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_content = filtered_content[start_idx:end_idx]
        
        # Convert to LeaderboardEntry objects
        for i, content in enumerate(paginated_content):
            entry = LeaderboardEntry(
                rank=start_idx + i + 1,
                content_id=content["id"],
                title=content["title"],
                channel=content["channel"],
                vertical=content["vertical"],
                roi_pct=content["roi"],
                engagement_rate_pct=content["engagement"],
                views=content["views"],
                performance_tier=self._get_performance_tier(content["roi"])
            )
            mock_entries.append(entry)
        
        return mock_entries
    
    def _generate_mock_roi_prediction(self, request: ROIPredictionRequest) -> ROIPrediction:
        """Generate mock ROI prediction for demo purposes"""
        # Simple heuristic-based prediction
        base_roi = 50.0  # Base 50% ROI
        
        # Channel adjustments
        channel_multipliers = {
            "YouTube": 1.2, "TikTok": 1.3, "Blog": 1.0, 
            "Email": 0.8, "LinkedIn": 1.1, "Twitter": 0.9
        }
        channel_mult = channel_multipliers.get(request.channel, 1.0)
        
        # Vertical adjustments
        vertical_multipliers = {
            "B2B SaaS": 1.4, "Technology": 1.3, "Finance": 1.2,
            "E-commerce": 1.1, "Marketing": 1.0, "Sales": 1.1
        }
        vertical_mult = vertical_multipliers.get(request.vertical, 1.0)
        
        # Format adjustments
        format_multipliers = {"video": 1.3, "blog": 1.0, "ad": 0.9, "email": 0.8}
        format_mult = format_multipliers.get(request.format, 1.0)
        
        # Calculate predicted ROI
        predicted_roi = base_roi * channel_mult * vertical_mult * format_mult
        
        # Add some randomness for demo
        import random
        predicted_roi += random.uniform(-10, 10)
        predicted_roi = max(0, predicted_roi)  # Ensure non-negative
        
        # Mock feature importance
        feature_importance = {
            "channel": 0.25,
            "vertical": 0.30,
            "format": 0.20,
            "region": 0.15,
            "publish_date": 0.10
        }
        
        return ROIPrediction(
            predicted_roi=round(predicted_roi, 2),
            confidence_score=0.75,
            feature_importance=feature_importance,
            model_version="v1.0",
            model_type="heuristic",
            prediction_timestamp=datetime.utcnow()
        )
    
    def _generate_mock_content_summary(self) -> ContentSummary:
        """Generate mock content summary for demo purposes"""
        return ContentSummary(
            total_content_items=1250,
            active_channels=8,
            total_views=2500000,
            total_engagement=125000,
            total_conversions=15000,
            total_revenue=750000,
            total_cost=450000,
            overall_roi=66.7,
            top_performing_channel="YouTube",
            top_performing_vertical="B2B SaaS",
            content_growth_rate=15.5,
            engagement_trend="increasing",
            roi_trend="stable",
            last_updated=datetime.utcnow()
        )
    
    def _get_performance_tier(self, roi: float) -> str:
        """Get performance tier based on ROI"""
        if roi >= 100:
            return "Top Performer"
        elif roi >= 75:
            return "High Performer"
        elif roi >= 50:
            return "Medium Performer"
        elif roi >= 25:
            return "Low Performer"
        else:
            return "Underperformer"

# Global instance
content_service = ContentService() 