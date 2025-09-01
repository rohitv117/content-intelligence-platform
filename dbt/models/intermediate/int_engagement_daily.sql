{{
  config(
    materialized='view',
    schema='intermediate'
  )
}}

with engagement_daily as (
    select
        content_id,
        date_trunc('day', event_dt) as event_date,
        
        -- Aggregated metrics
        sum(impressions) as daily_impressions,
        sum(views) as daily_views,
        sum(unique_viewers) as daily_unique_viewers,
        sum(likes) as daily_likes,
        sum(shares) as daily_shares,
        sum(comments) as daily_comments,
        sum(click_throughs) as daily_click_throughs,
        sum(conversions) as daily_conversions,
        sum(conversion_value) as daily_conversion_value,
        
        -- Calculated metrics
        avg(dwell_seconds_median) as avg_dwell_seconds,
        sum(views) / nullif(sum(impressions), 0) as daily_view_rate,
        sum(click_throughs) / nullif(sum(views), 0) as daily_ctr,
        sum(conversions) / nullif(sum(click_throughs), 0) as daily_cvr,
        (sum(likes) + sum(shares) + sum(comments)) / nullif(sum(views), 0) as daily_engagement_rate,
        
        -- Count of events
        count(*) as event_count,
        
        -- First and last event times
        min(event_dt) as first_event_time,
        max(event_dt) as last_event_time
        
    from {{ ref('stg_engagement_events') }}
    group by 1, 2
),

content_metadata as (
    select
        content_id,
        title,
        vertical,
        format,
        channel,
        publish_dt,
        owner_team,
        content_value_tier,
        business_unit_category
    from {{ ref('stg_content') }}
),

final as (
    select
        ed.*,
        cm.title,
        cm.vertical,
        cm.format,
        cm.channel,
        cm.publish_dt,
        cm.owner_team,
        cm.content_value_tier,
        cm.business_unit_category,
        
        -- Time-based features
        date_part('day', ed.event_date - cm.publish_dt) as days_since_publish,
        date_part('week', ed.event_date) as week_of_year,
        date_part('month', ed.event_date) as month_of_year,
        date_part('quarter', ed.event_date) as quarter_of_year,
        date_part('year', ed.event_date) as year,
        
        -- Performance indicators
        case 
            when ed.daily_view_rate > 0.1 then 'high_performing'
            when ed.daily_view_rate > 0.05 then 'medium_performing'
            else 'low_performing'
        end as performance_tier,
        
        case 
            when ed.daily_engagement_rate > 0.15 then 'high_engagement'
            when ed.daily_engagement_rate > 0.08 then 'medium_engagement'
            else 'low_engagement'
        end as engagement_tier
        
    from engagement_daily ed
    left join content_metadata cm on ed.content_id = cm.content_id
)

select * from final 