import csv
from io import StringIO
from pathlib import Path
import pytest


@pytest.fixture
def sample_files():
    root = Path(__file__).resolve().parents[1] / "sample_data"
    return [(name, (root / name).read_bytes()) for name in
            ("sales_shopify.csv", "sales_stripe.csv", "sales_manual.csv")]


@pytest.fixture
def csv_file():
    def make(rows=None, **changes):
        row = dict(order_id="ORD-1", order_date="2026-08-01", customer_name="john smith",
                   customer_email="JOHN@EXAMPLE.COM", product="Plan", category="software",
                   quantity="1", unit_price="10", total_amount="10")
        row.update(changes)
        out = StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=list(row))
        writer.writeheader()
        writer.writerows(rows if rows is not None else [row])
        return "test.csv", out.getvalue().encode()
    return make
