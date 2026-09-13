"""Read bounded, comma-delimited UTF-8 CSV files without guessing schemas."""
import csv
import io
import json
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20_000
MAX_FILES = 10


def read_csv_file(filename: str, content: bytes) -> tuple[list[str], list[tuple[int, list[str]]]]:
    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Please upload a CSV file (.csv). Excel workbooks are not supported as input.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("This file is too large. Please keep each CSV under 10 MB.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("This file is not UTF-8 text. Export it as CSV UTF-8 and try again.") from exc
    if not decoded.strip():
        raise ValueError("This file is empty. Add a header and at least one data row.")
    # Reject controls incompatible with Excel XML; tabs/newlines are allowed.
    if any(ord(char) < 32 and char not in "\t\r\n" for char in decoded):
        raise ValueError("This file contains unsupported control characters. Export a fresh CSV UTF-8 copy.")
    try:
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        headers = next(reader)
        if not headers or not all(h.strip() for h in headers):
            raise ValueError("Every CSV column needs a non-empty header.")
        if len(json.dumps(headers, ensure_ascii=False)) > 5000:
            raise ValueError("CSV headers are too long. Shorten the column names.")
        records = []
        for row in reader:
            records.append((reader.line_num, row))
            if len(records) > MAX_ROWS:
                raise ValueError("This file exceeds 20,000 rows. Split it into smaller files.")
            if any(len(cell) > 10_000 for cell in row):
                raise ValueError("A cell exceeds 10,000 characters. Shorten it before uploading.")
            if len(json.dumps(row, ensure_ascii=False)) > 20_000:
                raise ValueError("A row is too long for the Excel audit trail. Shorten its text fields.")
        if not records:
            raise ValueError("This file only has a header. Add at least one data row.")
        return headers, records
    except (csv.Error, StopIteration) as exc:
        raise ValueError("We could not read this CSV. Check commas and quoted values, then export it again.") from exc
