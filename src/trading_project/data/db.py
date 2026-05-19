from __future__ import annotations

from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(database_url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required for database access. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    return psycopg.connect(database_url, row_factory=dict_row)


def execute_sql_file(conn: Any, path: Path = SCHEMA_PATH) -> None:
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def fetch_one_value(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


def jsonb_param(value: dict[str, Any] | None):
    try:
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required for JSONB database parameters. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    return Jsonb(value or {})
