{{
  config(
    materialized='view',
    schema='staging'
  )
}}

with source as (
    select * from {{ source('raw', 'costs') }}
),

cleaned as (
    select
        -- Primary key
        id as cost_id,
        content_id,
        
        -- Cost details
        cost_type,
        amount,
        currency,
        cost_dt,
        vendor,
        description,
        
        -- Metadata
        created_at,
        
        -- Computed fields
        case 
            when cost_type = 'production' then 'content_creation'
            when cost_type = 'licensing' then 'rights'
            when cost_type = 'paid_media' then 'advertising'
            when cost_type = 'tooling' then 'infrastructure'
            when cost_type = 'distribution' then 'promotion'
            else 'other'
        end as cost_category,
        
        case 
            when cost_type in ('production', 'tooling') then true
            else false
        end as is_capitalizable,
        
        case 
            when cost_type = 'paid_media' then true
            else false
        end as is_media_cost,
        
        -- Data quality flags
        case 
            when amount <= 0 then true
            else false
        end as is_invalid_amount,
        
        case 
            when cost_dt > current_timestamp then true
            else false
        end as is_future_cost_date,
        
        case 
            when currency not in ('USD', 'EUR', 'GBP', 'CAD', 'AUD') then true
            else false
        end as is_invalid_currency
        
    from source
),

final as (
    select
        *,
        -- Add row hash for change detection
        md5(
            coalesce(cast(cost_id as varchar), '') ||
            coalesce(cast(content_id as varchar), '') ||
            coalesce(cast(cost_type as varchar), '') ||
            coalesce(cast(amount as varchar), '') ||
            coalesce(cast(currency as varchar), '') ||
            coalesce(cast(cost_dt as varchar), '')
        ) as row_hash
    from cleaned
)

select * from final 