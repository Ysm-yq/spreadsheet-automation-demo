import pytest
from src.cleaner import process_files
from src.reporter import build_report


@pytest.mark.parametrize("bad", [("empty.csv", b""), ("bad.xlsx", b"abc"),
    ("broken.csv", b'a,b\n"unclosed'), ("missing.csv", b"Customer,Total\nTest,12"),
    ("encoding.csv", b"\xff\xfe"), ("control.csv", b"a,b\n\x00,1"),
    ("header.csv", b"a,b\n")])
def test_bad_file_does_not_block_valid_file(bad, csv_file):
    r = process_files([bad, csv_file()])
    assert r.metrics["output_rows"] == 1
    assert r.metrics["failed_files"] == 1
    assert len(r.errors) == 1
    assert "File skipped" in set(r.quality.issue)


@pytest.mark.parametrize("field,value", [("quantity", "-1"), ("quantity", "1.5"),
    ("quantity", "0"), ("total_amount", "NaN"), ("total_amount", "-10"),
    ("order_date", "2026-02-30"), ("order_date", "31/08/2026"),
    ("order_id", ""), ("unit_price", "")])
def test_invalid_rows_quarantined(field, value, csv_file):
    r = process_files([csv_file(**{field: value})])
    assert r.metrics["invalid_rows"] == 1
    assert r.cleaned.empty
    assert not r.errors
    assert build_report(r).startswith(b"PK")


def test_all_empty():
    r = process_files([("a.csv", b""), ("b.csv", b" ")])
    assert r.cleaned.empty
    assert r.metrics["total_revenue"] == 0
    assert build_report(r).startswith(b"PK")


def test_optional_columns_absent():
    r = process_files([("a.csv", b"ID,Date,Qty,Price,Total\n0001,2026-08-01,1,10,10")])
    assert r.cleaned.iloc[0].order_id == "0001"
    assert r.metrics["missing_values"] == 4


def test_bad_row_width_skipped(csv_file):
    name, data = csv_file()
    r = process_files([(name, data + b"extra,broken,row\n")])
    assert r.metrics["input_rows"] == 2
    assert r.metrics["invalid_rows"] == 1
    assert r.metrics["output_rows"] == 1


def test_utf8_bom(csv_file):
    name, data = csv_file(customer_name="测试 客户")
    r = process_files([(name, b"\xef\xbb\xbf" + data)])
    assert r.cleaned.iloc[0].customer_name == "测试 客户"


def test_file_limit(csv_file):
    with pytest.raises(ValueError, match="10 files"):
        process_files([csv_file()] * 11)
