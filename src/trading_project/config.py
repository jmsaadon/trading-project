from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = ROOT_DIR / "config" / "settings.yaml"
DEFAULT_UNIVERSE_PATH = ROOT_DIR / "config" / "universe.yaml"


@dataclass(frozen=True)
class DataVendorConfig:
    name: str
    website_url: str | None = None
    support_email: str | None = None


@dataclass(frozen=True)
class DataConfig:
    frequency: str
    universe_path: Path
    default_backfill_start: str
    stale_days: int


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    data_vendor: DataVendorConfig
    data: DataConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in YAML file: {path}")
    return payload


def resolve_project_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def load_config(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppConfig:
    settings_path = resolve_project_path(path)
    raw = _read_yaml(settings_path)

    database_url = os.environ.get("DATABASE_URL") or raw.get("database", {}).get("url")
    if not database_url:
        raise ValueError("DATABASE_URL or database.url must be configured")

    vendor = raw.get("data_vendor", {})
    data = raw.get("data", {})

    return AppConfig(
        database_url=database_url,
        data_vendor=DataVendorConfig(
            name=vendor.get("name", "yfinance"),
            website_url=vendor.get("website_url"),
            support_email=vendor.get("support_email"),
        ),
        data=DataConfig(
            frequency=data.get("frequency", "daily"),
            universe_path=resolve_project_path(data.get("universe_path", DEFAULT_UNIVERSE_PATH)),
            default_backfill_start=data.get("default_backfill_start", "1990-01-01"),
            stale_days=int(data.get("stale_days", 7)),
        ),
    )
