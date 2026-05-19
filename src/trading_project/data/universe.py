from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from trading_project.config import DEFAULT_UNIVERSE_PATH, resolve_project_path


@dataclass(frozen=True)
class Exchange:
    abbrev: str
    name: str
    city: str | None
    country: str | None
    currency: str | None
    timezone_name: str | None


@dataclass(frozen=True)
class UniverseSymbol:
    ticker: str
    name: str
    category: str
    exchange: str
    instrument: str = "etf"
    sector: str | None = None
    currency: str = "USD"


@dataclass(frozen=True)
class Universe:
    exchanges: tuple[Exchange, ...]
    symbols: tuple[UniverseSymbol, ...]

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(symbol.ticker for symbol in self.symbols)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in universe YAML file: {path}")
    return payload


def load_universe(path: str | Path = DEFAULT_UNIVERSE_PATH) -> Universe:
    universe_path = resolve_project_path(path)
    raw = _read_yaml(universe_path)

    exchanges = tuple(
        Exchange(
            abbrev=abbrev,
            name=values["name"],
            city=values.get("city"),
            country=values.get("country"),
            currency=values.get("currency"),
            timezone_name=values.get("timezone_name"),
        )
        for abbrev, values in sorted((raw.get("exchanges") or {}).items())
    )

    symbols: list[UniverseSymbol] = []
    for category, rows in (raw.get("symbols") or {}).items():
        if not isinstance(rows, Iterable):
            raise ValueError(f"Universe category must contain a list: {category}")
        for row in rows:
            symbols.append(
                UniverseSymbol(
                    ticker=str(row["ticker"]).upper(),
                    name=row["name"],
                    category=category,
                    exchange=row.get("exchange", "NYSEARCA"),
                    instrument=row.get("instrument", "etf"),
                    sector=row.get("sector"),
                    currency=row.get("currency", "USD"),
                )
            )

    if not exchanges:
        raise ValueError("Universe must define at least one exchange")
    if not symbols:
        raise ValueError("Universe must define at least one symbol")

    duplicate_tickers = sorted({ticker for ticker in [s.ticker for s in symbols] if [s.ticker for s in symbols].count(ticker) > 1})
    if duplicate_tickers:
        raise ValueError(f"Duplicate tickers in universe: {duplicate_tickers}")

    exchange_abbrevs = {exchange.abbrev for exchange in exchanges}
    missing_exchanges = sorted({symbol.exchange for symbol in symbols} - exchange_abbrevs)
    if missing_exchanges:
        raise ValueError(f"Symbols reference unknown exchanges: {missing_exchanges}")

    return Universe(exchanges=exchanges, symbols=tuple(symbols))
