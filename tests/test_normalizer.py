from datetime import date
from decimal import Decimal
import pytest
from src.normalizer import normalize_date, normalize_money, map_columns


@pytest.mark.parametrize("value,expected", [("2026-08-01", date(2026, 8, 1)),
    ("08/02/2026", date(2026, 8, 2)), ("Aug 03, 2026", date(2026, 8, 3))])
def test_dates(value, expected):
    assert normalize_date(value) == expected


@pytest.mark.parametrize("value", ["$1,299.00", "1299", "1,299.00", " 1299.00 "])
def test_currency(value):
    assert normalize_money(value) == Decimal("1299.00")


@pytest.mark.parametrize("value", ["NaN", "inf", "1,29.00", "EUR 10", "12.345", "1e3", ""])
def test_invalid_currency(value):
    with pytest.raises(ValueError):
        normalize_money(value)


def test_ambiguous_mapping_rejected():
    with pytest.raises(ValueError, match="More than one"):
        map_columns(["Order ID", "ID", "Date", "Qty", "Price", "Total"])
