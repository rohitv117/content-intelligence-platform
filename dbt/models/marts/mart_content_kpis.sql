{{
  config(
    materialized='table',
    schema='marts',
    indexes=[
      {'columns': ['content_id'], 'type': 'btree'},
      {'columns': ['event_date'], 'type': 'btree'},
      {'columns': ['channel', 'vertical'], 'type': 'btree'},
      {'columns': ['roi_tier'], 'type': 'btree'}
    ]
  )
}}

with daily_engagement as (
    select
        content_id,
        event_date,
        daily_impressions,
        daily_views,
        daily_unique_viewers,
        daily_likes,
        daily_shares,
        daily_comments,
        daily_click_throughs,
        daily_conversions,
        daily_conversion_value,
        daily_view_rate,
        daily_ctr,
        daily_cvr,
        daily_engagement_rate,
        avg_dwell_seconds,
        performance_tier,
        engagement_tier,
        title,
        vertical,
        format,
        channel,
        publish_dt,
        owner_team,
        content_value_tier,
        business_unit_category,
        days_since_publish
    from {{ ref('int_engagement_daily') }}
),

daily_costs as (
    select
        content_id,
        event_date,
        sum(allocated_cost) as daily_allocated_cost,
        sum(case when cost_type = 'production' then allocated_cost else 0 end) as daily_production_cost,
        sum(case when cost_type = 'paid_media' then allocated_cost else 0 end) as daily_media_cost,
        sum(case when cost_type = 'tooling' then allocated_cost else 0 end) as daily_tooling_cost,
        sum(case when cost_type = 'licensing' then allocated_cost else 0 end) as daily_licensing_cost,
        sum(case when cost_type = 'distribution' then allocated_cost else 0 end) as daily_distribution_cost,
        sum(original_cost) as daily_original_cost,
        string_agg(distinct amortization_method, ', ') as amortization_methods_used
    from {{ ref('int_cost_allocations') }}
    group by 1, 2
),

daily_revenue as (
    select
        content_id,
        revenue_date as event_date,
        sum(last_touch_revenue) as daily_last_touch_revenue,
        sum(linear_revenue) as daily_linear_revenue,
        sum(time_decay_revenue) as daily_time_decay_revenue,
        sum(total_revenue) as daily_total_revenue,
        sum(revenue_event_count) as daily_revenue_events
    from {{ ref('int_revenue_attribution') }}
    group by 1, 2
),

-- Combine all daily metrics
daily_kpis as (
    select
        coalesce(de.content_id, dc.content_id, dr.content_id) as content_id,
        coalesce(de.event_date, dc.event_date, dr.event_date) as event_date,
        
        -- Content metadata
        de.title,
        de.vertical,
        de.format,
        de.channel,
        de.publish_dt,
        de.owner_team,
        de.content_value_tier,
        de.business_unit_category,
        de.days_since_publish,
        
        -- Engagement metrics
        coalesce(de.daily_impressions, 0) as impressions,
        coalesce(de.daily_views, 0) as views,
        coalesce(de.daily_unique_viewers, 0) as unique_viewers,
        coalesce(de.daily_likes, 0) as likes,
        coalesce(de.daily_shares, 0) as shares,
        coalesce(de.daily_comments, 0) as comments,
        coalesce(de.daily_click_throughs, 0) as click_throughs,
        coalesce(de.daily_conversions, 0) as conversions,
        coalesce(de.daily_conversion_value, 0) as conversion_value,
        coalesce(de.avg_dwell_seconds, 0) as dwell_seconds_median,
        
        -- Calculated engagement rates
        coalesce(de.daily_view_rate, 0) as view_rate_pct,
        coalesce(de.daily_ctr, 0) as ctr_pct,
        coalesce(de.daily_cvr, 0) as cvr_pct,
        coalesce(de.daily_engagement_rate, 0) as engagement_rate_pct,
        
        -- Performance indicators
        de.performance_tier,
        de.engagement_tier,
        
        -- Cost metrics
        coalesce(dc.daily_allocated_cost, 0) as allocated_cost,
        coalesce(dc.daily_production_cost, 0) as production_cost,
        coalesce(dc.daily_media_cost, 0) as media_cost,
        coalesce(dc.daily_tooling_cost, 0) as tooling_cost,
        coalesce(dc.daily_licensing_cost, 0) as licensing_cost,
        coalesce(dc.daily_distribution_cost, 0) as distribution_cost,
        coalesce(dc.daily_original_cost, 0) as original_cost,
        dc.amortization_methods_used,
        
        -- Revenue metrics
        coalesce(dr.daily_last_touch_revenue, 0) as last_touch_revenue,
        coalesce(dr.daily_linear_revenue, 0) as linear_revenue,
        coalesce(dr.daily_time_decay_revenue, 0) as time_decay_revenue,
        coalesce(dr.daily_total_revenue, 0) as total_revenue,
        coalesce(dr.daily_revenue_events, 0) as revenue_events
        
    from daily_engagement de
    full outer join daily_costs dc on de.content_id = dc.content_id and de.event_date = dc.event_date
    full outer join daily_revenue dr on de.content_id = dr.content_id and de.event_date = dr.event_date
),

-- Calculate KPIs and unit economics
final as (
    select
        *,
        
        -- Unit economics
        case 
            when impressions > 0 then round(allocated_cost / impressions * 1000, 2)
            else 0
        end as cpm,
        
        case 
            when click_throughs > 0 then round(allocated_cost / click_throughs, 2)
            else 0
        end as cpc,
        
        case 
            when conversions > 0 then round(allocated_cost / conversions, 2)
            else 0
        end as cpa,
        
        case 
            when allocated_cost > 0 then round((total_revenue - allocated_cost) / allocated_cost * 100, 2)
            else 0
        end as roi_pct,
        
        case 
            when allocated_cost > 0 then round(total_revenue / allocated_cost, 2)
            else 0
        end as roas,
        
        case 
            when allocated_cost > 0 then total_revenue - allocated_cost
            else 0
        end as net_profit,
        
        -- ROI tiers
        case 
            when roi_pct >= 100 then 'exceptional'
            when roi_pct >= 50 then 'excellent'
            when roi_pct >= 20 then 'good'
            when roi_pct >= 0 then 'positive'
            when roi_pct >= -20 then 'neutral'
            else 'negative'
        end as roi_tier,
        
        -- Performance score (0-100)
        case 
            when view_rate_pct > 0 and engagement_rate_pct > 0 and roi_pct > 0 then
                round(
                    (view_rate_pct * 0.3) + 
                    (engagement_rate_pct * 0.3) + 
                    (least(roi_pct, 100) * 0.4), 1
                )
            else 0
        end as performance_score,
        
        -- Content lifecycle stage
        case 
            when days_since_publish <= 7 then 'launch'
            when days_since_publish <= 30 then 'growth'
            when days_since_publish <= 90 then 'mature'
            when days_since_publish <= 365 then 'established'
            else 'legacy'
        end as lifecycle_stage,
        
        -- Channel performance tier
        case 
            when channel in ('YouTube', 'TikTok') and roi_pct > 50 then 'high_performing_video'
            when channel in ('Blog', 'Email') and roi_pct > 30 then 'high_performing_content'
            when channel in ('LinkedIn', 'Twitter') and engagement_rate_pct > 0.1 then 'high_engagement_social'
            when channel = 'Paid Social' and roas > 3 then 'high_roas_paid'
            else 'standard_performance'
        end as channel_performance_tier,
        
        -- Business impact score
        case 
            when business_unit_category = 'enterprise' and roi_pct > 20 then 'high_enterprise_impact'
            when business_unit_category = 'growth' and roi_pct > 40 then 'high_growth_impact'
            when business_unit_category = 'specialized' and roi_pct > 30 then 'high_specialized_impact'
            else 'standard_impact'
        end as business_impact_tier,
        
        -- Data freshness
        current_timestamp as calculated_at
        
    from daily_kpis
)

select * from final 