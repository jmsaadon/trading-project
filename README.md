# Daily ETF Relative-Value Research System

This repository starts with a Postgres-backed daily ETF securities master. The first milestone is data collection and storage only: no trading, signal generation, or backtesting code is included yet.

The data design follows the securities-master conventions from the attached algo trading book, especially Chapter 7 / PDF pages 56-69.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
docker compose up -d postgres
python -m trading_project.cli init-db
python -m trading_project.cli load-universe
python -m trading_project.cli backfill-prices
python -m trading_project.cli check-data-quality
```

You can also install the package and use the console script:

```bash
pip install -e .
etf-data init-db
```

## Core Commands

- `init-db`: create the Postgres schema and seed static exchange/vendor rows.
- `load-universe`: load the configured ETF universe into `symbol`.
- `backfill-prices`: fetch full available daily history from `yfinance`.
- `update-prices`: fetch missing daily bars after the latest stored date.
- `check-data-quality`: log practical validation issues into `data_quality_issue`.

Configuration lives in `config/settings.yaml` and `config/universe.yaml`.
