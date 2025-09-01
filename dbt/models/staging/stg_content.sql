{{
  config(
    materialized='view',
    schema='staging'
  )
}}

with source as (
    select * from {{ source('raw', 'content') }}
),

cleaned as (
    select
        -- Primary key
        id as content_id,
        
        -- Content attributes
        title,
        vertical,
        format,
        language,
        region,
        publish_dt,
        channel,
        campaign_id,
        owner_team,
        
        -- Metadata
        created_at,
        updated_at,
        
        -- Computed fields
        case 
            when format in ('video', 'blog', 'ad') then 'high_value'
            when format in ('email', 'social') then 'medium_value'
            else 'low_value'
        end as content_value_tier,
        
        case 
            when vertical in ('B2B SaaS', 'Technology', 'Finance') then 'enterprise'
            when vertical in ('E-commerce', 'Marketing', 'Sales') then 'growth'
            when vertical in ('Healthcare', 'Education') then 'specialized'
            else 'other'
        end as business_unit_category,
        
        -- Data quality flags
        case 
            when title is null or length(trim(title)) = 0 then true
            else false
        end as is_title_missing,
        
        case 
            when publish_dt > current_timestamp then true
            else false
        end as is_future_publish_date
        
    from source
),

final as (
    select
        *,
        -- Add row hash for change detection
        md5(
            coalesce(cast(content_id as varchar), '') ||
            coalesce(cast(title as varchar), '') ||
            coalesce(cast(vertical as varchar), '') ||
            coalesce(cast(format as varchar), '') ||
            coalesce(cast(publish_dt as varchar), '') ||
            coalesce(cast(channel as varchar), '')
        ) as row_hash
    from cleaned
)

select * from final 