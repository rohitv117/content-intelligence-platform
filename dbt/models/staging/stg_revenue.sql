{{
  config(
    materialized='view',
    schema='staging'
  )
}}

with source as (
    select * from {{ source('raw', 'revenue') }}
),

cleaned as (
    select
        -- Primary key
        id as revenue_id,
        content_id,
        campaign_id,
        
        -- Revenue details
        rev_dt,
        amount,
        currency,
        source,
        attribution_model,
        
        -- Metadata
        created_at,
        
        -- Computed fields
        case 
            when source = 'direct' then 'immediate'
            when source = 'assisted' then 'influenced'
            when source = 'attributed' then 'modeled'
            else 'unknown'
        end as revenue_timing,
        
        case 
            when attribution_model = 'last_touch' then 'single_touch'
            when attribution_model = 'linear' then 'multi_touch'
            when attribution_model = 'time_decay' then 'multi_touch'
            else 'unknown'
        end as attribution_type,
        
        -- Data quality flags
        case 
            when amount <= 0 then true
            else false
        end as is_invalid_amount,
        
        case 
            when rev_dt > current_timestamp then true
            else false
        end as is_future_revenue_date,
        
        case 
            when currency not in ('USD', 'EUR', 'GBP', 'CAD', 'AUD') then true
            else false
        end as is_invalid_currency,
        
        case 
            when source not in ('direct', 'assisted', 'attributed') then true
            else false
        end as is_invalid_source
        
    from source
),

final as (
    select
        *,
        -- Add row hash for change detection
        md5(
            coalesce(cast(revenue_id as varchar), '') ||
            coalesce(cast(content_id as varchar), '') ||
            coalesce(cast(amount as varchar), '') ||
            coalesce(cast(currency as varchar), '') ||
            coalesce(cast(rev_dt as varchar), '') ||
            coalesce(cast(source as varchar), '')
        ) as row_hash
    from cleaned
)

select * from final 