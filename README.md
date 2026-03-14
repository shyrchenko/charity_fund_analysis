# Charity Fund Analysis

Interactive toolkit for aggregating public donation reports from Ukrainian charity funds, storing them in a local DuckDB database, and exploring trends through a Streamlit dashboard. Parsers convert PDFs, APIs, or manually curated data into a unified schema so you can inspect monthly income, slice by fund, and manually exclude anomalies.

## Features
- Collects income reports from Prytula, Savelife, Sternenko, and UNITED24 (PDF + API sources).
- Normalises everything into `charity_reports.duckdb` with a simple schema and helper utilities in `db/`.
- Streamlit dashboard with fund/date filters, optional outlier exclusion, KPI tiles, and interactive Plotly bar charts.
- Jupyter notebooks for experimenting with forecasting / exploratory analysis on top of the same DuckDB file.

## Repository layout

```
├─ data_collection/        # Parsers for each fund (PDF parsing, HTTP APIs, manual tables)
├─ db/                     # DuckDB schema, ETL helpers, and population script
├─ visualization/app.py    # Streamlit app that queries DuckDB and renders analytics
├─ notebooks/              # Ad-hoc exploration notebooks and reference data
```

## Getting started

1. **Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. **Install dependencies**
   ```bash
   pip install -r reaquirements.txt
   ```
   (Add any extras you need for notebooks, e.g. `jupyter`.)

3. **Populate DuckDB** – if `charity_reports.duckdb` is missing or outdated:
   ```bash
   python -m db.fill_db
   ```
   This script pulls from the parsers in `data_collection/` and inserts into the `charity_reports` table defined in `db/utils.py`. The Savelife parser hits a public API with Cloudflare protection, so `curl_cffi` is used to mimic a browser session; you need an active internet connection for those sources.

## Running the analytics app

Launch Streamlit and open the served URL in your browser:

```bash
streamlit run visualization/app.py
```

### Dashboard controls
- **Select Funds** – multi-select built from the fund names stored in DuckDB.
- **Select Date Range** – Streamlit date slider backed by monthly timestamps.
- **Show Outliers Filter** – optional toggle that exposes a second multi-select where you can drop specific fund-month points (the selection is persisted in `st.session_state`).

Below the filters you will find two KPI tiles (total amount and median month income) followed by the monthly Plotly bar chart. All widgets react instantly to DuckDB queries filtered in-memory via pandas.

## Data collection modules
- `data_collection/prytula` and `data_collection/sternenko`: placeholder parsers returning manually entered monthly totals (replace with scrapers when available).
- `data_collection/united24`: downloads multiple PDF reports, parses the tables with `pdfplumber`, and normalises daily donations.
- `data_collection/savelife`: calls an authenticated JSON API using `curl_cffi.requests` to obtain daily income by source.

Use or extend these modules to bring new sources online, then rerun `python -m db.fill_db` to refresh the aggregate database.
