# Screenshot Evidence

All images must be actual captures of the running app or downloaded workbook. No mock screenshots.

- `01_upload.png`: running Streamlit app before upload.
- `02_processed_dashboard.png`: three files processed, showing 22 input rows, 15 clean orders and $4,545.00 revenue.
- `03_excel_summary.png`: capture the downloaded workbook's Summary sheet in a spreadsheet application, with both native charts.
- `04_data_quality.png`: running app's Data Quality tab with file/row references.
- `05_web_summary.png`: running app's source/category summary (additional evidence).

The browser captures are produced by `tests/browser_smoke.py`. The Excel screenshot requires
opening the actual browser-downloaded workbook in a spreadsheet application. If that file is absent,
capture it manually; do not substitute a browser summary or generated picture for Excel evidence.

Captured on 2026-09-11: all five primary images above are present. The Excel workbook was opened
in WPS Office on Windows. `06_excel_cleaned_data.png` and `07_excel_data_quality.png` provide
additional native spreadsheet evidence. Native captures are cropped to the worksheet region
to exclude account/avatar and unrelated application controls; worksheet pixels are unchanged.
