from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from trading_project.config import ROOT_DIR, resolve_project_path
from trading_project.data.universe import Universe, load_universe


DEFAULT_RELATIONSHIPS_PATH = ROOT_DIR / "config" / "relationships.yaml"


@dataclass(frozen=True)
class Relationship:
    name: str
    target: str
    explanatory: tuple[str, ...]
    description: str | None = None

    @property
    def tickers(self) -> tuple[str, ...]:
        return (self.target, *self.explanatory)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in relationships YAML file: {path}")
    return payload


def load_relationships(
    path: str | Path = DEFAULT_RELATIONSHIPS_PATH,
    universe: Universe | None = None,
    validate_universe: bool = True,
) -> tuple[Relationship, ...]:
    relationships_path = resolve_project_path(path)
    raw = _read_yaml(relationships_path)
    rows = raw.get("relationships") or []
    if not isinstance(rows, list):
        raise ValueError("relationships YAML must contain a list named 'relationships'")

    relationships: list[Relationship] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each relationship must be a mapping")
        explanatory = tuple(str(ticker).upper() for ticker in row.get("explanatory", []))
        if not explanatory:
            raise ValueError(f"Relationship {row.get('name')} must define explanatory tickers")
        relationships.append(
            Relationship(
                name=str(row["name"]),
                target=str(row["target"]).upper(),
                explanatory=explanatory,
                description=row.get("description"),
            )
        )

    if not relationships:
        raise ValueError("At least one relationship must be configured")

    duplicate_names = sorted(
        {relationship.name for relationship in relationships if [r.name for r in relationships].count(relationship.name) > 1}
    )
    if duplicate_names:
        raise ValueError(f"Duplicate relationships configured: {duplicate_names}")

    if validate_universe:
        universe = universe or load_universe()
        universe_tickers = set(universe.tickers)
        relationship_tickers = {ticker for relationship in relationships for ticker in relationship.tickers}
        missing = sorted(relationship_tickers - universe_tickers)
        if missing:
            raise ValueError(f"Relationship tickers missing from universe: {missing}")

    return tuple(relationships)
