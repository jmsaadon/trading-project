from trading_project.data.retrieval import _price_where_clause


def test_price_where_clause_adds_ticker_and_dates():
    where, params = _price_where_clause(["spy", "qqq"], "2020-01-01", "2020-12-31")

    assert "dv.name = %s" in where
    assert "sym.ticker = ANY(%s)" in where
    assert "dp.price_date >= %s" in where
    assert "dp.price_date <= %s" in where
    assert params == [["SPY", "QQQ"], "2020-01-01", "2020-12-31"]
