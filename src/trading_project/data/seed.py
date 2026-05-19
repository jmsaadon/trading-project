from __future__ import annotations

from typing import Any

from trading_project.config import DataVendorConfig
from trading_project.data.universe import Exchange, UniverseSymbol


def seed_vendor(conn: Any, vendor: DataVendorConfig) -> int:
    sql = """
        INSERT INTO data_vendor (name, website_url, support_email)
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            website_url = EXCLUDED.website_url,
            support_email = EXCLUDED.support_email,
            updated_at = NOW()
        RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (vendor.name, vendor.website_url, vendor.support_email))
        row = cur.fetchone()
    conn.commit()
    return int(row["id"])


def seed_exchanges(conn: Any, exchanges: tuple[Exchange, ...]) -> None:
    sql = """
        INSERT INTO exchange (abbrev, name, city, country, currency, timezone_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (abbrev) DO UPDATE SET
            name = EXCLUDED.name,
            city = EXCLUDED.city,
            country = EXCLUDED.country,
            currency = EXCLUDED.currency,
            timezone_name = EXCLUDED.timezone_name,
            updated_at = NOW();
    """
    records = [
        (
            exchange.abbrev,
            exchange.name,
            exchange.city,
            exchange.country,
            exchange.currency,
            exchange.timezone_name,
        )
        for exchange in exchanges
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, records)
    conn.commit()


def load_symbols(conn: Any, symbols: tuple[UniverseSymbol, ...]) -> None:
    sql = """
        INSERT INTO symbol (
            exchange_id, ticker, instrument, name, category, sector, currency, is_active
        )
        SELECT
            ex.id, %s, %s, %s, %s, %s, %s, TRUE
        FROM exchange AS ex
        WHERE ex.abbrev = %s
        ON CONFLICT (ticker) DO UPDATE SET
            exchange_id = EXCLUDED.exchange_id,
            instrument = EXCLUDED.instrument,
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            sector = EXCLUDED.sector,
            currency = EXCLUDED.currency,
            is_active = TRUE,
            updated_at = NOW();
    """
    records = [
        (
            symbol.ticker,
            symbol.instrument,
            symbol.name,
            symbol.category,
            symbol.sector,
            symbol.currency,
            symbol.exchange,
        )
        for symbol in symbols
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, records)
    conn.commit()
