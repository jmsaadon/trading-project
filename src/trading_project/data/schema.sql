CREATE TABLE IF NOT EXISTS exchange (
    id BIGSERIAL PRIMARY KEY,
    abbrev VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(255),
    country VARCHAR(255),
    currency VARCHAR(64),
    timezone_name VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_vendor (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    website_url VARCHAR(255),
    support_email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS symbol (
    id BIGSERIAL PRIMARY KEY,
    exchange_id BIGINT REFERENCES exchange(id),
    ticker VARCHAR(32) NOT NULL UNIQUE,
    instrument VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    category VARCHAR(64),
    sector VARCHAR(255),
    currency VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS index_symbol_exchange_id ON symbol(exchange_id);
CREATE INDEX IF NOT EXISTS index_symbol_category ON symbol(category);

CREATE TABLE IF NOT EXISTS daily_price (
    id BIGSERIAL PRIMARY KEY,
    data_vendor_id BIGINT NOT NULL REFERENCES data_vendor(id),
    symbol_id BIGINT NOT NULL REFERENCES symbol(id),
    price_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    open_price NUMERIC(19, 6),
    high_price NUMERIC(19, 6),
    low_price NUMERIC(19, 6),
    close_price NUMERIC(19, 6),
    adj_close_price NUMERIC(19, 6),
    volume BIGINT,
    CONSTRAINT unique_daily_price_vendor_symbol_date
        UNIQUE (data_vendor_id, symbol_id, price_date)
);

CREATE INDEX IF NOT EXISTS index_daily_price_data_vendor_id ON daily_price(data_vendor_id);
CREATE INDEX IF NOT EXISTS index_daily_price_symbol_id ON daily_price(symbol_id);
CREATE INDEX IF NOT EXISTS index_daily_price_price_date ON daily_price(price_date);

CREATE TABLE IF NOT EXISTS ingestion_run (
    id BIGSERIAL PRIMARY KEY,
    command VARCHAR(64) NOT NULL,
    data_vendor_id BIGINT REFERENCES data_vendor(id),
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    symbols_requested INTEGER NOT NULL DEFAULT 0,
    records_requested INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ingestion_run_status_check
        CHECK (status IN ('running', 'success', 'failed'))
);

CREATE INDEX IF NOT EXISTS index_ingestion_run_data_vendor_id ON ingestion_run(data_vendor_id);
CREATE INDEX IF NOT EXISTS index_ingestion_run_started_at ON ingestion_run(started_at);

CREATE TABLE IF NOT EXISTS data_quality_issue (
    id BIGSERIAL PRIMARY KEY,
    ingestion_run_id BIGINT REFERENCES ingestion_run(id),
    data_vendor_id BIGINT REFERENCES data_vendor(id),
    symbol_id BIGINT REFERENCES symbol(id),
    price_date DATE,
    issue_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT data_quality_issue_severity_check
        CHECK (severity IN ('info', 'warning', 'error'))
);

CREATE INDEX IF NOT EXISTS index_data_quality_issue_type ON data_quality_issue(issue_type);
CREATE INDEX IF NOT EXISTS index_data_quality_issue_symbol_id ON data_quality_issue(symbol_id);
CREATE INDEX IF NOT EXISTS index_data_quality_issue_unresolved
    ON data_quality_issue(resolved_at)
    WHERE resolved_at IS NULL;
