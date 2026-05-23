import pandas as pd

from trading_project.research.cointegration import (
    align_pair_prices,
    calculate_residuals,
    estimate_hedge_ratio_no_intercept,
    primary_pairs,
    run_cadf_test,
)
from trading_project.research.relationships import Relationship


def test_align_pair_prices_starts_on_later_first_date():
    prices = pd.DataFrame(
        {
            "AAA": [1.0, 2.0, 3.0, 4.0],
            "BBB": [None, None, 30.0, 40.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
    )

    aligned = align_pair_prices(prices, "AAA", "BBB")

    assert aligned.index.min().date().isoformat() == "2024-01-04"
    assert aligned.shape == (2, 2)


def test_estimate_hedge_ratio_and_residuals_no_intercept():
    prices = pd.DataFrame(
        {
            "AAA": [2.0, 4.0, 6.0],
            "BBB": [1.0, 2.0, 3.0],
        }
    )

    beta = estimate_hedge_ratio_no_intercept(prices["AAA"], prices["BBB"])
    residuals = calculate_residuals(prices, "AAA", "BBB", beta)

    assert beta == 2.0
    assert residuals.abs().sum() == 0.0


def test_primary_pairs_use_first_explanatory_ticker():
    relationships = [
        Relationship(name="aaa_bbb_ccc", target="AAA", explanatory=("BBB", "CCC")),
    ]

    pair = primary_pairs(relationships)[0]

    assert pair.relationship == "aaa_bbb_ccc"
    assert pair.target == "AAA"
    assert pair.explanatory == "BBB"


def test_run_cadf_test_returns_summary_fields():
    dates = pd.bdate_range("2024-01-02", periods=80)
    explanatory = pd.Series(range(80), index=dates, dtype=float) + 50.0
    target = 1.5 * explanatory
    # Add a small deterministic wiggle so the residual is valid but stationary.
    target = target + pd.Series([(-1) ** idx * 0.1 for idx in range(80)], index=dates)
    prices = pd.DataFrame({"AAA": target, "BBB": explanatory})
    pair = primary_pairs([Relationship(name="aaa_bbb", target="AAA", explanatory=("BBB",))])[0]

    result, residuals = run_cadf_test(pair, prices, autolag=None)

    assert result.relationship == "aaa_bbb"
    assert result.target == "AAA"
    assert result.explanatory == "BBB"
    assert result.observations == 80
    assert result.critical_value_5pct < 0
    assert result.conclusion in {
        "Reject no-cointegration null at 5%",
        "Reject no-cointegration null at 10%, not 5%",
        "Fail to reject no-cointegration null",
    }
    assert residuals.name == "residual"
