{{
  config(
    materialized='view',
    schema='intermediate'
  )
}}

with revenue_data as (
    select
        revenue_id,
        content_id,
        campaign_id,
        rev_dt,
        amount,
        currency,
        source,
        attribution_model
    from {{ ref('stg_revenue') }}
),

content_metadata as (
    select
        content_id,
        publish_dt,
        format,
        channel,
        vertical,
        owner_team
    from {{ ref('stg_content') }}
),

daily_engagement as (
    select
        content_id,
        event_date,
        daily_views,
        daily_conversions,
        daily_click_throughs,
        daily_impressions
    from {{ ref('int_engagement_daily') }}
),

-- Last-touch attribution (default)
last_touch_attribution as (
    select
        rd.*,
        cm.publish_dt,
        cm.format,
        cm.channel,
        cm.vertical,
        cm.owner_team,
        
        -- Last-touch: full credit to the last content before conversion
        case 
            when rd.source = 'direct' then rd.amount
            when rd.source = 'assisted' then rd.amount * 0.7  -- 70% credit for assisted
            else rd.amount * 0.5  -- 50% credit for attributed
        end as last_touch_amount,
        
        'last_touch' as attribution_method
        
    from revenue_data rd
    left join content_metadata cm on rd.content_id = cm.content_id
),

-- Linear attribution (equal weight across all touchpoints)
linear_attribution as (
    select
        rd.*,
        cm.publish_dt,
        cm.format,
        cm.channel,
        cm.vertical,
        cm.owner_team,
        
        -- Linear: equal weight across all touchpoints
        case 
            when rd.source = 'direct' then rd.amount
            when rd.source = 'assisted' then rd.amount * 0.5  -- Equal weight
            else rd.amount * 0.33  -- Equal weight for attributed
        end as linear_amount,
        
        'linear' as attribution_method
        
    from revenue_data rd
    left join content_metadata cm on rd.content_id = cm.content_id
),

-- Time-decay attribution (weight decays over time)
time_decay_attribution as (
    select
        rd.*,
        cm.publish_dt,
        cm.format,
        cm.channel,
        cm.vertical,
        cm.owner_team,
        
        -- Time-decay: weight decays exponentially over time
        case 
            when rd.source = 'direct' then rd.amount
            when rd.source = 'assisted' then 
                rd.amount * exp(-0.5 * extract(days from rd.rev_dt - cm.publish_dt) / 30)
            else 
                rd.amount * exp(-0.5 * extract(days from rd.rev_dt - cm.publish_dt) / 30) * 0.5
        end as time_decay_amount,
        
        'time_decay' as attribution_method,
        
        -- Days since publish for decay calculation
        extract(days from rd.rev_dt - cm.publish_dt) as days_since_publish
        
    from revenue_data rd
    left join content_metadata cm on rd.content_id = cm.content_id
),

-- Combine all attribution methods
all_attribution_methods as (
    select
        revenue_id,
        content_id,
        campaign_id,
        rev_dt,
        amount,
        currency,
        source,
        attribution_model,
        publish_dt,
        format,
        channel,
        vertical,
        owner_team,
        last_touch_amount,
        linear_amount,
        time_decay_amount,
        'last_touch' as attribution_method
    from last_touch_attribution
    
    union all
    
    select
        revenue_id,
        content_id,
        campaign_id,
        rev_dt,
        amount,
        currency,
        source,
        attribution_model,
        publish_dt,
        format,
        channel,
        vertical,
        owner_team,
        last_touch_amount,
        linear_amount,
        time_decay_amount,
        'linear' as attribution_method
    from linear_attribution
    
    union all
    
    select
        revenue_id,
        content_id,
        campaign_id,
        rev_dt,
        amount,
        currency,
        source,
        attribution_model,
        publish_dt,
        format,
        channel,
        vertical,
        owner_team,
        last_touch_amount,
        linear_amount,
        time_decay_amount,
        'time_decay' as attribution_method
    from time_decay_attribution
),

-- Daily revenue aggregation
daily_revenue as (
    select
        content_id,
        date_trunc('day', rev_dt) as revenue_date,
        attribution_method,
        
        -- Sum attributed amounts by method
        sum(case when attribution_method = 'last_touch' then last_touch_amount else 0 end) as last_touch_revenue,
        sum(case when attribution_method = 'linear' then linear_amount else 0 end) as linear_revenue,
        sum(case when attribution_method = 'time_decay' then time_decay_amount else 0 end) as time_decay_revenue,
        
        -- Total revenue
        sum(amount) as total_revenue,
        
        -- Count of revenue events
        count(*) as revenue_event_count
        
    from all_attribution_methods
    group by 1, 2, 3
),

final as (
    select
        dr.*,
        cm.publish_dt,
        cm.format,
        cm.channel,
        cm.vertical,
        cm.owner_team,
        
        -- Time-based features
        date_part('day', dr.revenue_date - cm.publish_dt) as days_since_publish,
        date_part('week', dr.revenue_date) as week_of_year,
        date_part('month', dr.revenue_date) as month_of_year,
        date_part('quarter', dr.revenue_date) as quarter_of_year,
        date_part('year', dr.revenue_date) as year,
        
        -- Attribution method comparison
        case 
            when last_touch_revenue > linear_revenue and last_touch_revenue > time_decay_revenue then 'last_touch_highest'
            when linear_revenue > last_touch_revenue and linear_revenue > time_decay_revenue then 'linear_highest'
            when time_decay_revenue > last_touch_revenue and time_decay_revenue > linear_revenue then 'time_decay_highest'
            else 'mixed'
        end as highest_attribution_method,
        
        -- Revenue performance tier
        case 
            when total_revenue > 10000 then 'high_value'
            when total_revenue > 5000 then 'medium_value'
            else 'low_value'
        end as revenue_performance_tier
        
    from daily_revenue dr
    left join content_metadata cm on dr.content_id = cm.content_id
)

select * from final 