from trading_project.data.universe import load_universe


def test_load_universe_contains_readme_etfs():
    universe = load_universe("config/universe.yaml")

    assert len(universe.symbols) == 31
    assert "SPY" in universe.tickers
    assert "GDX" in universe.tickers
    assert "KRE" in universe.tickers
    assert "EWU" in universe.tickers


def test_universe_groups_are_preserved():
    universe = load_universe("config/universe.yaml")
    categories = {symbol.category for symbol in universe.symbols}

    assert categories == {
        "equity_index",
        "sector",
        "rates_credit",
        "commodities",
        "international",
    }
