from trading_project.data.universe import load_universe
from trading_project.research.relationships import load_relationships


def test_load_relationships_contains_readme_candidates():
    relationships = load_relationships()

    assert len(relationships) == 10
    assert [relationship.name for relationship in relationships] == [
        "gdx_gld_spy",
        "xle_uso_spy",
        "xlf_kre",
        "qqq_xlk_spy",
        "iwm_spy",
        "tlt_ief",
        "hyg_lqd_spy",
        "eem_efa_spy",
        "xly_xlp",
        "xlu_tlt_spy",
    ]


def test_relationship_tickers_are_in_universe():
    universe = load_universe()
    relationships = load_relationships(universe=universe)
    universe_tickers = set(universe.tickers)

    assert "KRE" in universe_tickers
    for relationship in relationships:
        assert set(relationship.tickers) <= universe_tickers
