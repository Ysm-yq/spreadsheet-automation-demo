"""Pure multi-file pipeline. No Streamlit state or filesystem writes."""
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import re

import pandas as pd

from .normalizer import (SCHEMA, map_columns, normalize_date, normalize_money,
                         normalize_quantity, normalize_text)
from .validators import MAX_FILES, MAX_ROWS, read_csv_file

QUALITY_COLUMNS = ["file", "row", "order_id", "issue", "field", "original_value", "action", "details"]


@dataclass
class ProcessingResult:
    cleaned: pd.DataFrame
    quality: pd.DataFrame
    metrics: dict
    by_source: pd.DataFrame
    by_category: pd.DataFrame
    errors: list[str]


def revenue_group(data: pd.DataFrame, field: str) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=[field, "orders", "revenue"])
    return data.groupby(field, sort=True).agg(
        orders=("order_id", "size"), revenue=("total_amount", "sum")).reset_index()


def process_files(files: list[tuple[str, bytes]]) -> ProcessingResult:
    if len(files) > MAX_FILES:
        raise ValueError("Please upload no more than 10 files at a time.")
    logs, cleaned, errors = [], [], []
    seen = {}
    metrics = dict(files=len(files), processed_files=0, failed_files=0, input_rows=0,
                   output_rows=0, duplicates_removed=0, invalid_rows=0, missing_values=0)

    def log(filename, row, order_id, issue, field="", original="", action="", details=""):
        logs.append([filename, row, order_id, issue, field, str(original), action, details])

    for filename, content in files:
        filename = Path(filename).name
        try:
            headers, records = read_csv_file(filename, content)
            mapping = map_columns(headers)
            if metrics["input_rows"] + len(records) > MAX_ROWS:
                raise ValueError("Combined input exceeds 20,000 rows. Process a smaller batch.")
        except ValueError as exc:
            message = f"{filename}: {exc}"
            errors.append(message)
            metrics["failed_files"] += 1
            log(filename, None, "", "File skipped", action="File excluded", details=str(exc))
            continue
        metrics["processed_files"] += 1
        metrics["input_rows"] += len(records)
        source = {"sales_shopify": "Shopify", "sales_stripe": "Stripe", "sales_manual": "Manual"}.get(
            Path(filename).stem.lower(), Path(filename).stem)
        for field, index in mapping.items():
            if headers[index] != field:
                log(filename, None, "", "Column mapping", field, headers[index], f"Mapped to {field}")
        ignored = [h for i, h in enumerate(headers) if i not in mapping.values()]
        if ignored:
            log(filename, None, "", "Unmapped columns", original=", ".join(ignored),
                action="Excluded from canonical output", details="Source is derived from the filename.")
        for line, values in records:
            if len(values) != len(headers):
                metrics["invalid_rows"] += 1
                log(filename, line, "", "Rows skipped", original=json.dumps(values, ensure_ascii=False),
                    action="Row excluded", details="Number of values does not match the header.")
                continue
            raw = {field: values[index] for field, index in mapping.items()}
            row = {field: raw.get(field, "").strip() for field in SCHEMA[:-1]}
            order_id = row["order_id"].upper()
            row["order_id"] = order_id
            invalid = False
            for field in SCHEMA[:-1]:
                if not row[field]:
                    metrics["missing_values"] += 1
                    log(filename, line, order_id, "Missing fields", field,
                        action="Filled with Unknown" if field in ("category", "product") else "Left blank; validated below")
            if not order_id:
                invalid = True
                log(filename, line, order_id, "Invalid values", "order_id", action="Row excluded", details="An order ID is required.")
            row["customer_name"] = normalize_text(row["customer_name"]).title()
            row["customer_email"] = row["customer_email"].lower()
            row["product"] = normalize_text(row["product"]) or "Unknown"
            row["category"] = normalize_text(row["category"]).title() or "Unknown"
            if row["customer_email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", row["customer_email"]):
                log(filename, line, order_id, "Invalid values", "customer_email", row["customer_email"],
                    "Kept for review", "Email format is unusual; no deliverability check was performed.")
            for field, parser in (("order_date", normalize_date), ("quantity", normalize_quantity),
                                  ("unit_price", normalize_money), ("total_amount", normalize_money)):
                try:
                    row[field] = parser(row[field])
                    if field in ("unit_price", "total_amount") and row[field] < 0:
                        raise ValueError("Negative amounts are not supported in this sales-only demo.")
                except ValueError as exc:
                    invalid = True
                    log(filename, line, order_id, "Invalid values", field, raw.get(field, ""), "Row excluded", str(exc))
            for field in SCHEMA[:-1]:
                if str(row[field]) != raw.get(field, ""):
                    log(filename, line, order_id, "Cleanup actions", field, raw.get(field, ""),
                        f"Normalized to {row[field]}")
            if invalid:
                metrics["invalid_rows"] += 1
                log(filename, line, order_id, "Rows skipped", original=json.dumps(raw, ensure_ascii=False),
                    action="Row excluded", details="Failed required-value validation; original row retained here.")
                continue
            if row["quantity"] * row["unit_price"] != row["total_amount"]:
                log(filename, line, order_id, "Amount mismatch", "total_amount", raw["total_amount"],
                    "Kept supplied total", "Quantity × unit price differs from total; check discounts, tax or source data.")
            row["source"] = source
            if order_id in seen:
                previous, prev_file, prev_line = seen[order_id]
                conflict = any(previous[f] != row[f] for f in SCHEMA if f != "source")
                metrics["duplicates_removed"] += 1
                log(filename, line, order_id, "Duplicate records", "order_id", json.dumps(raw, ensure_ascii=False),
                    "Row excluded", f"{'CONFLICT: values differ. ' if conflict else ''}First valid row retained: {prev_file}, row {prev_line}.")
                continue
            seen[order_id] = (row.copy(), filename, line)
            cleaned.append(row)
    data = pd.DataFrame(cleaned, columns=SCHEMA)
    metrics["output_rows"] = len(data)
    revenue = sum((r["total_amount"] for r in cleaned), Decimal("0.00"))
    metrics["total_revenue"] = revenue
    metrics["average_order_value"] = (revenue / len(data)).quantize(Decimal("0.01")) if len(data) else Decimal("0.00")
    return ProcessingResult(data, pd.DataFrame(logs, columns=QUALITY_COLUMNS), metrics,
                            revenue_group(data, "source"), revenue_group(data, "category"), errors)
