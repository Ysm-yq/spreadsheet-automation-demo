"""Explicit mappings and conservative format parsers (USD, US slash dates)."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

SCHEMA = ["order_id", "order_date", "customer_name", "customer_email", "product",
          "category", "quantity", "unit_price", "total_amount", "source"]
ALIASES = {
    "order_id": ["Order ID", "transaction_id", "ID"],
    "order_date": ["Date", "created_at", "OrderDate"],
    "customer_name": ["Customer", "Client"],
    "customer_email": ["Email", "EmailAddress"],
    "product": ["Product", "item", "ItemName"],
    "category": ["Category", "type", "ProductCategory"],
    "quantity": ["Qty", "quantity", "Units"],
    "unit_price": ["Price", "unit_price", "PriceEach"],
    "total_amount": ["Total", "amount", "Revenue"],
}
REQUIRED = {"order_id", "order_date", "quantity", "unit_price", "total_amount"}


def column_key(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value.strip()).casefold()


LOOKUP = {column_key(alias): field for field, aliases in ALIASES.items()
          for alias in [field, *aliases]}


def map_columns(headers: list[str]) -> dict[str, int]:
    mapping = {}
    for index, header in enumerate(headers):
        field = LOOKUP.get(column_key(header))
        if field:
            if field in mapping:
                raise ValueError(f"More than one column matches '{field}'. Keep one matching column and try again.")
            mapping[field] = index
    missing = sorted(REQUIRED - mapping.keys())
    if missing:
        raise ValueError("This file is missing recognizable required columns: " + ", ".join(missing) +
                         ". Please check the column names and try again.")
    return mapping


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_date(value: str):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(value.strip(), fmt).date()
            if parsed.year < 1900:
                break
            return parsed
        except ValueError:
            continue
    raise ValueError("Use YYYY-MM-DD, MM/DD/YYYY, or Aug 03, 2026 (year 1900 or later).")


def normalize_money(value: str) -> Decimal:
    text = value.strip()
    if not re.fullmatch(r"-?\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?", text):
        raise ValueError("Use a USD number such as $1,299.00; up to two decimal places.")
    try:
        amount = Decimal(text.replace("$", "").replace(",", ""))
        if abs(amount) > Decimal("1000000000"):
            raise ValueError("Amount exceeds the demo limit of 1 billion USD per value.")
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError("Amount is not a valid USD number.") from exc


def normalize_quantity(value: str) -> int:
    if not re.fullmatch(r"\d+(?:\.0+)?", value.strip()):
        raise ValueError("Quantity must be a positive whole number.")
    quantity = int(Decimal(value.strip()))
    if not 1 <= quantity <= 1_000_000:
        raise ValueError("Quantity must be between 1 and 1,000,000.")
    return quantity
