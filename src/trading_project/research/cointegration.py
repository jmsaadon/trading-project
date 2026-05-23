from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from trading_project.research.relationships import Relationship


@dataclass(frozen=True)
class PrimaryPair:
    relationship: str
    target: str
    explanatory: str
    description: str | None = None


@dataclass(frozen=True)
class CADFResult:
    relationship: str
    target: str
    explanatory: str
    start_date: str
    end_date: str
    observations: int
    hedge_ratio: float
    adf_statistic: float
    p_value: float
    used_lag: int
    nobs: int
    critical_value_1pct: float
    critical_value_5pct: float
    critical_value_10pct: float
    reject_1pct: bool
    reject_5pct: bool
    reject_10pct: bool

    @property
    def rejection_level(self) -> str:
        if self.reject_1pct:
            return "1%"
        if self.reject_5pct:
            return "5%"
        if self.reject_10pct:
            return "10%"
        return "none"

    @property
    def conclusion(self) -> str:
        if self.reject_5pct:
            return "Reject no-cointegration null at 5%"
        if self.reject_10pct:
            return "Reject no-cointegration null at 10%, not 5%"
        return "Fail to reject no-cointegration null"

    def to_record(self) -> dict[str, object]:
        return {
            "relationship": self.relationship,
            "target": self.target,
            "explanatory": self.explanatory,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "observations": self.observations,
            "hedge_ratio": self.hedge_ratio,
            "adf_statistic": self.adf_statistic,
            "p_value": self.p_value,
            "used_lag": self.used_lag,
            "nobs": self.nobs,
            "critical_value_1pct": self.critical_value_1pct,
            "critical_value_5pct": self.critical_value_5pct,
            "critical_value_10pct": self.critical_value_10pct,
            "reject_1pct": self.reject_1pct,
            "reject_5pct": self.reject_5pct,
            "reject_10pct": self.reject_10pct,
            "rejection_level": self.rejection_level,
            "conclusion": self.conclusion,
        }


def primary_pairs(relationships: Iterable[Relationship]) -> tuple[PrimaryPair, ...]:
    return tuple(
        PrimaryPair(
            relationship=relationship.name,
            target=relationship.target,
            explanatory=relationship.explanatory[0],
            description=relationship.description,
        )
        for relationship in relationships
    )


def align_pair_prices(price_matrix: pd.DataFrame, target: str, explanatory: str) -> pd.DataFrame:
    pair = price_matrix[[target, explanatory]].copy().dropna()
    if pair.empty:
        return pair
    return pair.sort_index()


def estimate_hedge_ratio_no_intercept(target_prices: pd.Series, explanatory_prices: pd.Series) -> float:
    target_values = target_prices.to_numpy(dtype=float)
    explanatory_values = explanatory_prices.to_numpy(dtype=float)
    denominator = float(np.dot(explanatory_values, explanatory_values))
    if denominator == 0:
        raise ValueError("Cannot estimate hedge ratio when explanatory series has zero variance around zero")
    return float(np.dot(explanatory_values, target_values) / denominator)


def calculate_residuals(pair_prices: pd.DataFrame, target: str, explanatory: str, hedge_ratio: float) -> pd.Series:
    residuals = pair_prices[target] - hedge_ratio * pair_prices[explanatory]
    residuals.name = "residual"
    return residuals


def run_cadf_test(
    pair: PrimaryPair,
    pair_prices: pd.DataFrame,
    autolag: str | None = "AIC",
) -> tuple[CADFResult, pd.Series]:
    if pair_prices.empty:
        raise ValueError(f"No overlapping prices for {pair.relationship}")
    if len(pair_prices) < 20:
        raise ValueError(f"At least 20 overlapping observations are required for {pair.relationship}")

    hedge_ratio = estimate_hedge_ratio_no_intercept(pair_prices[pair.target], pair_prices[pair.explanatory])
    residuals = calculate_residuals(pair_prices, pair.target, pair.explanatory, hedge_ratio)
    adf_statistic, p_value, used_lag, nobs, critical_values, *_ = adfuller(residuals, autolag=autolag)
    result = CADFResult(
        relationship=pair.relationship,
        target=pair.target,
        explanatory=pair.explanatory,
        start_date=pair_prices.index.min().date().isoformat(),
        end_date=pair_prices.index.max().date().isoformat(),
        observations=int(len(pair_prices)),
        hedge_ratio=float(hedge_ratio),
        adf_statistic=float(adf_statistic),
        p_value=float(p_value),
        used_lag=int(used_lag),
        nobs=int(nobs),
        critical_value_1pct=float(critical_values["1%"]),
        critical_value_5pct=float(critical_values["5%"]),
        critical_value_10pct=float(critical_values["10%"]),
        reject_1pct=bool(adf_statistic < critical_values["1%"]),
        reject_5pct=bool(adf_statistic < critical_values["5%"]),
        reject_10pct=bool(adf_statistic < critical_values["10%"]),
    )
    return result, residuals


def summarize_cadf_tests(
    price_matrix: pd.DataFrame,
    relationships: Iterable[Relationship],
    autolag: str | None = "AIC",
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for pair in primary_pairs(relationships):
        pair_prices = align_pair_prices(price_matrix, pair.target, pair.explanatory)
        result, _ = run_cadf_test(pair, pair_prices, autolag=autolag)
        records.append(result.to_record())
    return pd.DataFrame(records).sort_values(["p_value", "relationship"]).reset_index(drop=True)


def plot_price_series(pair_prices: pd.DataFrame, target: str, explanatory: str, ax=None):
    if ax is None:
        import matplotlib.pyplot as plt

        _, ax = plt.subplots(figsize=(10, 4))
    pair_prices[[target, explanatory]].plot(ax=ax, linewidth=1.2)
    ax.set_title(f"{target} and {explanatory} adjusted close")
    ax.set_ylabel("Adjusted close")
    ax.grid(True, alpha=0.25)
    return ax


def plot_scatter_series(pair_prices: pd.DataFrame, target: str, explanatory: str, ax=None):
    if ax is None:
        import matplotlib.pyplot as plt

        _, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(pair_prices[explanatory], pair_prices[target], s=8, alpha=0.45)
    ax.set_title(f"{target} vs {explanatory}")
    ax.set_xlabel(f"{explanatory} adjusted close")
    ax.set_ylabel(f"{target} adjusted close")
    ax.grid(True, alpha=0.25)
    return ax


def plot_residuals(residuals: pd.Series, relationship: str, ax=None):
    if ax is None:
        import matplotlib.pyplot as plt

        _, ax = plt.subplots(figsize=(10, 4))
    residuals.plot(ax=ax, linewidth=1.0, color="#9f3f2f")
    ax.axhline(0, color="#444444", linewidth=0.8)
    ax.set_title(f"{relationship} linear-combination residuals")
    ax.set_ylabel("Residual")
    ax.grid(True, alpha=0.25)
    return ax
