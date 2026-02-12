# Data Dictionary

## Canonical Project Table

| Field | Type | Description |
|---|---|---|
| `project_id` | string | Source project identifier. |
| `project_name` | string | Project name/title. |
| `finance_type` | string | Finance class (for example `fdi`, `development_finance`, `blended`). |
| `sector` | string | Project sector classification. |
| `province` | string | Indonesian province where the project is located. |
| `district` | string | District/city/municipality. |
| `latitude` | float | Latitude coordinate in decimal degrees. |
| `longitude` | float | Longitude coordinate in decimal degrees. |
| `sponsor_type` | string | Sponsor/owner type (`state_owned`, `private`, `mixed`, etc.). |
| `status` | string | Delivery status (`approved`, `construction`, `operational`, `delayed`, `stalled`, `cancelled`, etc.). |
| `approval_date` | datetime | Date of project approval/sanction. |
| `financial_close_date` | datetime | Date of financial close or loan signing. |
| `construction_start_date` | datetime | Construction start/groundbreaking date. |
| `operation_date` | datetime | Commercial operation/commissioning date. |
| `committed_usd` | float | Total committed capital in USD. |
| `disbursed_usd` | float | Total disbursed capital in USD. |
| `year` | integer | Reporting or approval year if provided by source. |

## Quality Output (`data/processed/data_quality.json`)

| Key | Type | Description |
|---|---|---|
| `generated_at_utc` | string | ETL execution timestamp (UTC ISO-8601). |
| `raw_file_count` | integer | Number of files discovered in `data/raw`. |
| `row_count` | integer | Number of output rows in canonical dataset. |
| `warning_count` | integer | Number of ETL warnings recorded. |
| `warnings` | list[object] | Warning records with source file, type, and message. |
| `missing_pct` | object | Percent missing by canonical field. |
