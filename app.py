"""Small Streamlit UI; reusable business logic lives in src/."""
import hashlib
import logging
from time import perf_counter

import streamlit as st

from src.cleaner import process_files
from src.reporter import build_report

st.set_page_config(page_title="Spreadsheet Automation Demo", page_icon="📊", layout="wide")
st.caption("PYTHON AUTOMATION  /  SELF-INITIATED SAMPLE PROJECT")
st.title("Spreadsheet Automation Demo")
st.write("Upload messy CSV files and turn them into a clean Excel report automatically.")
st.caption("01 Upload  →  02 Clean & merge  →  03 Download your report")

with st.container(border=True):
    st.subheader("Start with your weekly exports")
    files = st.file_uploader("Multiple CSV Files", type=["csv"], accept_multiple_files=True,
                            help="Comma-delimited CSV UTF-8. Up to 10 files, 10 MB each and 20,000 combined rows.")
    st.caption("USD only · Slash dates use MM/DD/YYYY · One row per order · First valid order ID wins")
    process = st.button("Process Files", type="primary", disabled=not files)

# A changed upload invalidates the previous download and dashboard.
inputs = [(file.name, file.getvalue()) for file in files]
signature = tuple((name, hashlib.sha256(content).hexdigest()) for name, content in inputs)
if signature != st.session_state.get("input_signature"):
    st.session_state.pop("report_result", None)
    st.session_state.pop("report_bytes", None)
    st.session_state["input_signature"] = signature

if process:
    try:
        with st.spinner("Cleaning your files and building the Excel report…"):
            started = perf_counter()
            result = process_files(inputs)
            report = build_report(result)
            st.session_state.update(report_result=result, report_bytes=report,
                                    elapsed=perf_counter() - started)
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        logging.exception("Report processing failed")
        st.error("We could not finish this report. Try a smaller CSV batch or check the input format.")

if "report_result" in st.session_state:
    result = st.session_state.report_result
    m = result.metrics
    for error in result.errors:
        st.warning(error)
    if m["output_rows"]:
        st.success(f"Report ready · {m['processed_files']} files processed in {st.session_state.elapsed:.2f}s")
    else:
        st.warning("No valid orders were found. Download the report to review Data Quality and correct your files.")
    cols = st.columns(5)
    for col, label, value in zip(cols, ["Files", "Input Rows", "Clean Rows", "Duplicates Removed", "Total Revenue"],
                                [m["files"], m["input_rows"], m["output_rows"], m["duplicates_removed"], f"${m['total_revenue']:,.2f}"]):
        col.metric(label, value)
    st.caption(f"Invalid rows: {m['invalid_rows']}  ·  Missing values: {m['missing_values']}  ·  "
               f"Average order value: ${m['average_order_value']:,.2f}  ·  Failed files: {m['failed_files']}")
    st.download_button("Download Excel Report", st.session_state.report_bytes,
                       file_name="automated_sales_report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    preview, summary, quality = st.tabs(["Cleaned Data Preview", "Summary", "Data Quality"])
    with preview:
        st.dataframe(result.cleaned.head(200), hide_index=True, width="stretch")
        st.caption("Preview shows up to 200 clean orders. The Excel report contains all accepted rows.")
    with summary:
        left, right = st.columns(2)
        for col, title, group in [(left, "Revenue by Source", result.by_source),
                                  (right, "Revenue by Category", result.by_category)]:
            with col:
                st.subheader(title)
                st.dataframe(group, hide_index=True, width="stretch")
    with quality:
        st.write("Review skipped rows, conflicting duplicates, missing values and cleanup actions.")
        issues = ["All", *sorted(result.quality.issue.unique())] if not result.quality.empty else ["All"]
        issue = st.selectbox("Issue type", issues)
        view = result.quality if issue == "All" else result.quality[result.quality.issue == issue]
        st.dataframe(view.head(500), hide_index=True, width="stretch")
        st.caption("Input Rows excludes rejected files. Missing Values counts blank canonical cells before cleanup. "
                   "Quality entries are events; one row may have several. Preview capped at 500 events.")
else:
    st.info("To try the demo, upload the three fictional CSVs from the sample_data folder.")
    a, b, c = st.columns(3)
    a.markdown("**Consistent data**\n\nMap different column names and normalize dates, names and USD amounts.")
    b.markdown("**Clear audit trail**\n\nReview duplicates and invalid rows with source file and row references.")
    c.markdown("**Ready-to-use Excel**\n\nGet clean orders, sales summaries and native charts in one workbook.")

st.divider()
st.caption("Self-Initiated Sample Project · All included sample records are fictional. "
           "Local processing; no account or paid API required.")
