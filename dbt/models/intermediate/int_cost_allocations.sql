{{
  config(
    materialized='view',
    schema='intermediate'
  )
}}

with content_costs as (
    select
        content_id,
        cost_type,
        amount,
        currency,
        cost_dt,
        is_capitalizable,
        is_media_cost,
        cost_category
    from {{ ref('stg_costs') }}
),

content_metadata as (
    select
        content_id,
        publish_dt,
        format,
        channel,
        vertical
    from {{ ref('stg_content') }}
),

daily_engagement as (
    select
        content_id,
        event_date,
        daily_views,
        daily_conversions,
        daily_impressions
    from {{ ref('int_engagement_daily') }}
),

-- Calculate total engagement for performance-based amortization
content_engagement_totals as (
    select
        content_id,
        sum(daily_views) as total_views,
        sum(daily_conversions) as total_conversions,
        sum(daily_impressions) as total_impressions,
        count(distinct event_date) as active_days
    from daily_engagement
    group by 1
),

-- Straight-line amortization
straight_line_costs as (
    select
        cc.content_id,
        cc.cost_type,
        cc.amount,
        cc.currency,
        cc.cost_dt,
        cc.is_capitalizable,
        cc.is_media_cost,
        cc.cost_category,
        cm.publish_dt,
        cm.format,
        cm.channel,
        cm.vertical,
        
        -- Default amortization period (12 months)
        case 
            when cc.cost_type = 'production' then 12
            when cc.cost_type = 'tooling' then 12
            when cc.cost_type = 'licensing' then 12
            else 1  -- Media and distribution costs are not amortized
        end as amortization_period_months,
        
        -- Daily amortization amount
        case 
            when cc.cost_type in ('production', 'tooling', 'licensing') then
                cc.amount / (12 * 30.44)  -- 365.25 days / 12 months
            else cc.amount
        end as daily_amortized_amount
        
    from content_costs cc
    left join content_metadata cm on cc.content_id = cm.content_id
),

-- Performance-based amortization for production costs
performance_based_costs as (
    select
        slc.*,
        cet.total_views,
        cet.total_conversions,
        cet.total_impressions,
        cet.active_days,
        
        -- Performance-based daily allocation
        case 
            when slc.cost_type = 'production' and cet.total_views > 0 then
                slc.amount * (de.daily_views / nullif(cet.total_views, 0))
            when slc.cost_type = 'production' and cet.total_conversions > 0 then
                slc.amount * (de.daily_conversions / nullif(cet.total_conversions, 0))
            else slc.daily_amortized_amount
        end as performance_based_daily_amount
        
    from straight_line_costs slc
    left join content_engagement_totals cet on slc.content_id = cet.content_id
    left join daily_engagement de on slc.content_id = de.content_id
),

-- Final cost allocation by day
daily_cost_allocation as (
    select
        pbc.content_id,
        de.event_date,
        pbc.cost_type,
        pbc.cost_category,
        pbc.is_capitalizable,
        pbc.is_media_cost,
        pbc.currency,
        pbc.format,
        pbc.channel,
        pbc.vertical,
        
        -- Cost allocation for the day
        case 
            when pbc.cost_type = 'paid_media' then
                -- Media costs are allocated to the day they were spent
                case when pbc.cost_dt::date = de.event_date then pbc.amount else 0 end
            else
                -- Other costs use performance-based or straight-line amortization
                coalesce(pbc.performance_based_daily_amount, pbc.daily_amortized_amount)
        end as allocated_cost,
        
        -- Original cost amount
        pbc.amount as original_cost,
        
        -- Amortization method used
        case 
            when pbc.cost_type = 'paid_media' then 'immediate'
            when pbc.cost_type = 'production' and pbc.total_views > 0 then 'performance_based'
            else 'straight_line'
        end as amortization_method
        
    from performance_based_costs pbc
    left join daily_engagement de on pbc.content_id = de.content_id
    where de.event_date is not null
),

final as (
    select
        *,
        -- Calculate cumulative allocated cost
        sum(allocated_cost) over (
            partition by content_id, cost_type 
            order by event_date 
            rows unbounded preceding
        ) as cumulative_allocated_cost,
        
        -- Calculate remaining unallocated cost
        original_cost - sum(allocated_cost) over (
            partition by content_id, cost_type 
            order by event_date 
            rows unbounded preceding
        ) as remaining_unallocated_cost
        
    from daily_cost_allocation
)

select * from final 