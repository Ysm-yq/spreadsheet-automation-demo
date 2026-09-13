from decimal import Decimal
from src.cleaner import process_files


def test_sample_reconciliation(sample_files):
    result = process_files(sample_files)
    m = result.metrics
    assert not result.errors
    assert m["files"] == 3
    assert m["input_rows"] == 22
    assert m["output_rows"] == 15
    assert m["duplicates_removed"] == 3
    assert m["invalid_rows"] == 4
    assert m["input_rows"] == m["output_rows"] + m["duplicates_removed"] + m["invalid_rows"]
    assert m["total_revenue"] == Decimal("4545.00")
    assert m["average_order_value"] == Decimal("303.00")
    assert m["missing_values"] == 6
    assert result.cleaned.order_id.is_unique
    assert dict(zip(result.by_source.source, result.by_source.revenue)) == {
        "Shopify": Decimal("1923.00"), "Stripe": Decimal("848.00"), "Manual": Decimal("1774.00")}
    assert result.by_category.revenue.sum() == m["total_revenue"]


def test_duplicate_conflict_and_audit(sample_files):
    result = process_files(sample_files)
    conflicts = result.quality[result.quality.details.str.contains("CONFLICT", na=False)]
    assert len(conflicts) == 1
    assert conflicts.iloc[0].order_id == "ORD-1013"
    assert result.cleaned.set_index("order_id").loc["ORD-1013", "total_amount"] == Decimal("250")
    assert len(result.quality[result.quality.issue == "Rows skipped"]) == 4
    assert len(result.quality[result.quality.issue == "Amount mismatch"]) == 1


def test_optional_missing_and_cleanup(csv_file):
    result = process_files([csv_file(customer_name=" JOHN   SMITH ", customer_email="", category="", product="")])
    row = result.cleaned.iloc[0]
    assert row.customer_name == "John Smith"
    assert row.customer_email == ""
    assert row["category"] == row["product"] == "Unknown"
    assert result.metrics["missing_values"] == 3
    assert "Cleanup actions" in set(result.quality.issue)


def test_invalid_first_does_not_shadow_later_valid(csv_file):
    result = process_files([csv_file(total_amount="bad"), csv_file()])
    assert result.metrics["invalid_rows"] == 1
    assert result.metrics["output_rows"] == 1
    assert result.metrics["duplicates_removed"] == 0


def test_money_uses_decimal(csv_file):
    r = process_files([csv_file(order_id="A", unit_price="0.10", total_amount="0.10"),
                       csv_file(order_id="B", unit_price="0.20", total_amount="0.20")])
    assert r.metrics["total_revenue"] == Decimal("0.30")
