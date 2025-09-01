-- Content Intelligence Platform Database Schema
-- This script creates all necessary tables for the platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Content dimension table
CREATE TABLE IF NOT EXISTS content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    vertical VARCHAR(100) NOT NULL,
    format VARCHAR(50) NOT NULL CHECK (format IN ('video', 'blog', 'ad', 'email', 'social')),
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    region VARCHAR(50) NOT NULL DEFAULT 'global',
    publish_dt TIMESTAMP WITH TIME ZONE NOT NULL,
    channel VARCHAR(100) NOT NULL,
    campaign_id UUID,
    owner_team VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Engagement events fact table
CREATE TABLE IF NOT EXISTS engagement_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id),
    event_dt TIMESTAMP WITH TIME ZONE NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    views INTEGER NOT NULL DEFAULT 0,
    unique_viewers INTEGER NOT NULL DEFAULT 0,
    dwell_seconds_median DECIMAL(10,2) NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    click_throughs INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    conversion_value DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Costs fact table
CREATE TABLE IF NOT EXISTS costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id),
    cost_type VARCHAR(100) NOT NULL CHECK (cost_type IN ('production', 'licensing', 'paid_media', 'tooling', 'distribution')),
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    cost_dt TIMESTAMP WITH TIME ZONE NOT NULL,
    vendor VARCHAR(200),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Revenue fact table
CREATE TABLE IF NOT EXISTS revenue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id),
    campaign_id UUID,
    rev_dt TIMESTAMP WITH TIME ZONE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    source VARCHAR(100) NOT NULL CHECK (source IN ('direct', 'assisted', 'attributed')),
    attribution_model VARCHAR(50) DEFAULT 'last_touch',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Finance rules configuration table
CREATE TABLE IF NOT EXISTS finance_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(200) NOT NULL UNIQUE,
    rule_type VARCHAR(100) NOT NULL CHECK (rule_type IN ('amortization', 'attribution', 'allocation')),
    amortization_method VARCHAR(50) CHECK (amortization_method IN ('straight_line', 'performance_based')),
    period_months INTEGER CHECK (period_months > 0),
    rev_attribution_model VARCHAR(50) CHECK (rev_attribution_model IN ('last_touch', 'linear', 'time_decay')),
    time_decay_factor DECIMAL(5,4) DEFAULT 0.5,
    channel_cost_allocation_pct DECIMAL(5,4) DEFAULT 1.0,
    currency_fx_table JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Feedback events table for stakeholder feedback loop
CREATE TABLE IF NOT EXISTS feedback_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(100) NOT NULL CHECK (actor_role IN ('Finance', 'Strategy', 'Marketing', 'SalesOps', 'Data')),
    feedback_type VARCHAR(100) NOT NULL CHECK (feedback_type IN ('definition_correction', 'misattribution', 'override', 'rule_change')),
    payload JSONB NOT NULL,
    target_type VARCHAR(100) NOT NULL CHECK (target_type IN ('metric', 'content_id', 'rule_id', 'definition')),
    target_id VARCHAR(200),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'applied')),
    impact_analysis JSONB,
    applied_by VARCHAR(100),
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Rule overrides table for applied feedback
CREATE TABLE IF NOT EXISTS rule_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feedback_event_id UUID NOT NULL REFERENCES feedback_events(id),
    original_value JSONB NOT NULL,
    new_value JSONB NOT NULL,
    override_type VARCHAR(100) NOT NULL,
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL,
    effective_to TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Lookup tables
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_name VARCHAR(100) NOT NULL UNIQUE,
    channel_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verticals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vertical_name VARCHAR(100) NOT NULL UNIQUE,
    business_unit VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cost_type_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,
    is_capitalizable BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS formats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    format_name VARCHAR(100) NOT NULL UNIQUE,
    content_type VARCHAR(100) NOT NULL,
    typical_lifespan_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS currencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    currency_code VARCHAR(3) NOT NULL UNIQUE,
    currency_name VARCHAR(100) NOT NULL,
    is_base_currency BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Exchange rates table
CREATE TABLE IF NOT EXISTS exchange_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency VARCHAR(3) NOT NULL REFERENCES currencies(currency_code),
    to_currency VARCHAR(3) NOT NULL REFERENCES currencies(currency_code),
    rate_date DATE NOT NULL,
    exchange_rate DECIMAL(15,6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_currency, to_currency, rate_date)
);

-- ML model metadata table
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_path TEXT NOT NULL,
    features JSONB NOT NULL,
    hyperparameters JSONB,
    performance_metrics JSONB,
    training_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ML predictions table
CREATE TABLE IF NOT EXISTS ml_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id),
    model_id UUID NOT NULL REFERENCES ml_models(id),
    predicted_roi DECIMAL(10,4) NOT NULL,
    confidence_score DECIMAL(5,4),
    feature_importance JSONB,
    prediction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(200) NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_publish_dt ON content(publish_dt);
CREATE INDEX IF NOT EXISTS idx_content_channel ON content(channel);
CREATE INDEX IF NOT EXISTS idx_content_vertical ON content(vertical);
CREATE INDEX IF NOT EXISTS idx_engagement_content_dt ON engagement_events(content_id, event_dt);
CREATE INDEX IF NOT EXISTS idx_costs_content_dt ON costs(content_id, cost_dt);
CREATE INDEX IF NOT EXISTS idx_revenue_content_dt ON revenue(content_id, rev_dt);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback_events(status);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_events(feedback_type);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_content ON ml_predictions(content_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_table_record ON audit_trail(table_name, record_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_finance_rules_updated_at BEFORE UPDATE ON finance_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feedback_events_updated_at BEFORE UPDATE ON feedback_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default finance rules
INSERT INTO finance_rules (rule_name, rule_type, amortization_method, period_months, rev_attribution_model, time_decay_factor) VALUES
('default_amortization', 'amortization', 'straight_line', 12, NULL, NULL),
('default_attribution', 'attribution', NULL, NULL, 'last_touch', 0.5),
('performance_amortization', 'amortization', 'performance_based', 12, NULL, NULL)
ON CONFLICT (rule_name) DO NOTHING;

-- Insert default lookup data
INSERT INTO channels (channel_name, channel_type) VALUES
('YouTube', 'video'),
('TikTok', 'social'),
('Blog', 'content'),
('Email', 'email'),
('Paid Social', 'paid_media'),
('LinkedIn', 'social'),
('Twitter', 'social'),
('Instagram', 'social')
ON CONFLICT (channel_name) DO NOTHING;

INSERT INTO verticals (vertical_name, business_unit) VALUES
('B2B SaaS', 'Enterprise'),
('E-commerce', 'Retail'),
('Healthcare', 'Health'),
('Education', 'Learning'),
('Finance', 'Banking'),
('Technology', 'Tech'),
('Marketing', 'Growth'),
('Sales', 'Revenue')
ON CONFLICT (vertical_name) DO NOTHING;

INSERT INTO cost_types (cost_type_name, category, is_capitalizable) VALUES
('production', 'content_creation', TRUE),
('licensing', 'rights', FALSE),
('paid_media', 'advertising', FALSE),
('tooling', 'infrastructure', TRUE),
('distribution', 'promotion', FALSE)
ON CONFLICT (cost_type_name) DO NOTHING;

INSERT INTO formats (format_name, content_type, typical_lifespan_days) VALUES
('video', 'visual', 365),
('blog', 'text', 730),
('ad', 'advertising', 30),
('email', 'communication', 7),
('social', 'social_media', 90)
ON CONFLICT (format_name) DO NOTHING;

INSERT INTO currencies (currency_code, currency_name, is_base_currency) VALUES
('USD', 'US Dollar', TRUE),
('EUR', 'Euro', FALSE),
('GBP', 'British Pound', FALSE),
('CAD', 'Canadian Dollar', FALSE),
('AUD', 'Australian Dollar', FALSE)
ON CONFLICT (currency_code) DO NOTHING;

-- Insert default exchange rates (1:1 for demo)
INSERT INTO exchange_rates (from_currency, to_currency, rate_date, exchange_rate) VALUES
('USD', 'EUR', CURRENT_DATE, 0.85),
('USD', 'GBP', CURRENT_DATE, 0.73),
('USD', 'CAD', CURRENT_DATE, 1.25),
('USD', 'AUD', CURRENT_DATE, 1.35)
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING; 