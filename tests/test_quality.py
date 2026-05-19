import datetime as dt

from trading_project.data.quality import find_missing_business_day_gaps


def test_find_missing_business_day_gaps_reports_multi_day_gaps():
    dates = [
        dt.date(2024, 1, 2),
        dt.date(2024, 1, 8),
    ]

    gaps = find_missing_business_day_gaps(1, "SPY", dates)

    assert len(gaps) == 1
    assert gaps[0].missing_dates == (
        dt.date(2024, 1, 3),
        dt.date(2024, 1, 4),
        dt.date(2024, 1, 5),
    )


def test_find_missing_business_day_gaps_ignores_single_day_holiday_like_gaps():
    dates = [
        dt.date(2024, 1, 12),
        dt.date(2024, 1, 16),
    ]

    assert find_missing_business_day_gaps(1, "SPY", dates) == []
