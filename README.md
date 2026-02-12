# Indonesia-China Finance Dashboard

Portfolio-grade Streamlit dashboard for Chinese FDI and development finance projects in Indonesia.

## Stack
- Python 3.11
- Streamlit (multi-page)
- DuckDB + pandas
- Plotly + PyDeck
- pytest
- ruff + pre-commit

## Project Layout
- `app/Home.py`
- `app/pages/1_Overview.py`
- `app/pages/2_Spatial_Explorer.py`
- `app/pages/3_Finance_and_Delivery.py`
- `app/pages/4_Impact_and_Friction.py`
- `src/etl.py`
- `src/model.py`
- `src/metrics.py`
- `tests/test_metrics.py`
- `docs/data_dictionary.md`
- `docs/methodology.md`

## Quickstart
```bash
make setup
make etl
make run
```

## Testing
```bash
make test
```

## Linting
```bash
make lint
```

## Data Workflow
1. Put raw source files in `data/raw` (`.csv`, `.xlsx`, `.xls`, `.json`, `.parquet`).
2. Run `make etl`.
3. ETL writes:
   - `data/processed/projects_canonical.parquet`
   - `data/processed/projects_canonical.csv` (fallback when parquet engine is unavailable)
   - `data/processed/projects.duckdb` (table: `projects`)
   - `data/processed/data_quality.json`

## Canonical Fields
ETL standardizes all sources into:
`project_id, project_name, finance_type, sector, province, district, latitude, longitude, sponsor_type, status, approval_date, financial_close_date, construction_start_date, operation_date, committed_usd, disbursed_usd, year`

## Dashboard Features
- Global filters on every page: year, finance type, sector, province, status, sponsor type
- Overview KPIs + trend charts
- Spatial clustered map + project drilldown
- Finance & Delivery funnel + cohorts + delay diagnostics
- Impact & Friction comparison of high vs low exposure regions
- Data quality panel with ETL warnings and missingness diagnostics

## Notes
- ETL never fabricates unavailable source fields; missing values remain null and are surfaced in warnings.
- Full mapping assumptions and metric definitions are documented in `docs/methodology.md`.
