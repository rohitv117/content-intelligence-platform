{{
  config(
    materialized='view',
    schema='staging'
  )
}}

with source as (
    select * from {{ source('raw', 'engagement_events') }}
),

cleaned as (
    select
        -- Primary key
        id as engagement_id,
        content_id,
        
        -- Event details
        event_dt,
        
        -- Engagement metrics
        coalesce(impressions, 0) as impressions,
        coalesce(views, 0) as views,
        coalesce(unique_viewers, 0) as unique_viewers,
        coalesce(dwell_seconds_median, 0) as dwell_seconds_median,
        coalesce(likes, 0) as likes,
        coalesce(shares, 0) as shares,
        coalesce(comments, 0) as comments,
        coalesce(click_throughs, 0) as click_throughs,
        coalesce(conversions, 0) as conversions,
        coalesce(conversion_value, 0) as conversion_value,
        
        -- Metadata
        created_at,
        
        -- Computed fields
        case 
            when impressions > 0 then round(cast(views as decimal) / impressions * 100, 2)
            else 0
        end as view_rate_pct,
        
        case 
            when views > 0 then round(cast(click_throughs as decimal) / views * 100, 2)
            else 0
        end as ctr_pct,
        
        case 
            when click_throughs > 0 then round(cast(conversions as decimal) / click_throughs * 100, 2)
            else 0
        end as cvr_pct,
        
        case 
            when views > 0 then round(cast(likes + shares + comments as decimal) / views * 100, 2)
            else 0
        end as engagement_rate_pct,
        
        case 
            when conversions > 0 then round(conversion_value / conversions, 2)
            else 0
        end as avg_conversion_value,
        
        -- Data quality flags
        case 
            when event_dt > current_timestamp then true
            else false
        end as is_future_event_date,
        
        case 
            when impressions < views then true
            else false
        end as is_impressions_less_than_views,
        
        case 
            when views < unique_viewers then true
            else false
        end as is_views_less_than_unique_viewers
        
    from source
),

final as (
    select
        *,
        -- Add row hash for change detection
        md5(
            coalesce(cast(engagement_id as varchar), '') ||
            coalesce(cast(content_id as varchar), '') ||
            coalesce(cast(event_dt as varchar), '') ||
            coalesce(cast(impressions as varchar), '') ||
            coalesce(cast(views as varchar), '') ||
            coalesce(cast(conversions as varchar), '')
        ) as row_hash
    from cleaned
)

select * from final 