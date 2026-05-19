# ETF Data Collection And Storage Plan

## Summary

Build the first project milestone: a Postgres-backed daily ETF securities master for research and later paper trading.

The design follows Chapter 7 of the attached algo trading book, especially the securities-master pattern around `exchange`, `data_vendor`, `symbol`, and `daily_price`, while modernizing the stack from MySQL/Yahoo CSV endpoints to Dockerized Postgres and `yfinance`.

## Key Changes

- Use Docker Compose for local Postgres.
- Use SQL-first database code with explicit Postgres DDL and `psycopg`, not an ORM.
- Store the README ETF universe, not just a tiny pilot set.
- Use `yfinance` as the first data vendor.
- Support both historical backfill and daily incremental updates.
- Store OHLCV plus adjusted close; do not create a separate corporate-actions table in v1.
- Add practical ingestion metadata and quality checks:
  - duplicate price rows
  - bad OHLC rows
  - missing trading dates after ETF inception
  - stale latest prices
  - null adjusted close
  - unexpected zero or null volume

## Book Conventions To Preserve

- Treat the database as a small securities master, not loose CSV files.
- Keep vendor, exchange, symbol, and price data normalized.
- Use precise numeric types for prices and `BIGINT` for volume.
- Store `created_at` and `updated_at` timestamps on core records.
- Make data retrieval easy from pandas via SQL queries.
- Prefer automated scripts for repeatable download, storage, and validation.
- Keep the attached PDF path referenced in the plan: `/Users/JMSaadon/Downloads/Algo_20Trading_20Overview_20Book_20(Start_20Here).pdf`, especially PDF pages 56-69.

## Implementation Plan

- Create `docs/data_collection_storage_plan.md` with this plan once writing is approved.
- Add config for the ETF universe from the README, grouped by category: equity index, sector, rates/credit, commodities, international.
- Create Postgres schema with:
  - `exchange`
  - `data_vendor`
  - `symbol`
  - `daily_price`
  - `ingestion_run`
  - `data_quality_issue`
- Add unique constraints on `(data_vendor_id, symbol_id, price_date)` so repeated updates are idempotent.
- Seed initial exchange/vendor/symbol rows.
- Implement `yfinance` fetch logic for backfill and incremental update.
- Store all available data from ETF inception onward, with research start dates handled later by strategy config.
- Add SQL/pandas retrieval helpers for adjusted close, OHLCV, and wide price matrices.

## Public Interfaces

- CLI/script commands:
  - `init-db`: create schema and seed static rows.
  - `load-universe`: load ETF symbols from config.
  - `backfill-prices`: fetch historical ETF data.
  - `update-prices`: fetch latest missing daily bars.
  - `check-data-quality`: run validation checks and log issues.
- Config:
  - universe tickers and categories
  - database connection string
  - default vendor: `yfinance`
  - default frequency: daily
- Data contract:
  - research modules consume prices from Postgres, preferably adjusted close for signals and OHLCV for execution/backtest assumptions.

## Test Plan

- Schema test: all expected tables, indexes, and unique constraints exist.
- Seed test: vendor, exchange, and ETF symbols load idempotently.
- Fetch test: mocked `yfinance` data converts into canonical rows correctly.
- Upsert test: rerunning the same price load does not duplicate rows.
- Incremental test: update fetches only missing dates after the latest stored bar.
- Quality test: bad OHLC, missing adjusted close, duplicate rows, and stale symbols are detected.
- Retrieval test: pandas query returns clean daily adjusted-close series and wide ETF matrices.

## Assumptions

- Database choice: Postgres.
- Local runtime: Docker Compose.
- DB access style: explicit SQL plus `psycopg`.
- First data vendor: `yfinance`.
- First universe: README ETF universe.
- First milestone includes backfill plus daily updates.
- Corporate actions are deferred; adjusted close is stored and used for research.
- No trading, signal generation, or backtesting is implemented until this data milestone plan is accepted.
