# Methodology

## Source Inclusion Policy
Project-level canonical dataset is built from primary sources only:
- `AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` (`finance_type = DF`)
- `China-Global-Investment-Tracker-2024-Fall-public.xlsx` (`finance_type = FDI`)
- `cgit_indonesia_investments_2006_2025.xlsx` (`finance_type = FDI`)

Excluded from primary rows:
- `BI_FDI In Indonesia By Country Of Origin.xls`
- `ChinaGlobalProjectDetails.xlsx`
- `Geographical Spead [Spreadsheet].xlsx`
- `IMF DIP.csv`
- `bps_fdi_china_2015_2023.xlsx`
- `bps_fdi_country_2000_2024_combined.xlsx`

Optional enrichment source (does not add primary rows):
- `ChinaGlobalProjectDetails.xlsx`

## Raw Files Discovered
- Count: 9
- `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx`
- `data/raw/BI_FDI In Indonesia By Country Of Origin.xls`
- `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx`
- `data/raw/ChinaGlobalProjectDetails.xlsx`
- `data/raw/Geographical Spead [Spreadsheet].xlsx`
- `data/raw/IMF DIP.csv`
- `data/raw/bps_fdi_china_2015_2023.xlsx`
- `data/raw/bps_fdi_country_2000_2024_combined.xlsx`
- `data/raw/cgit_indonesia_investments_2006_2025.xlsx`

## Source Load Audit
| Source | Role | Parser | Rows In Source | Rows Loaded | Rows Excluded | Rows Used For Enrichment | Note |
|---|---|---|---:|---:|---:|---:|---|
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `primary` | `excel_fixed(sheet=GCDF_3.0,header=0)` | 20985 | 437 | 20548 | 0 |  |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `primary` | `excel_default(sheet=0,header=0)` | 2329 | 0 | 2329 | 0 |  |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `primary` | `excel_default(sheet=0,header=0)` | 94 | 94 | 0 | 0 |  |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `enrichment` | `excel_default(sheet=0,header=0)` | 400 | 0 | 400 | 0 | optional_enrichment_only |
| `data/raw/BI_FDI In Indonesia By Country Of Origin.xls` | `excluded` | `excel_default(sheet=0,header=0)` | 78 | 0 | 78 | 0 | excluded_from_project_level |
| `data/raw/Geographical Spead [Spreadsheet].xlsx` | `excluded` | `excel_default(sheet=0,header=0)` | 38 | 0 | 38 | 0 | excluded_from_project_level |
| `data/raw/IMF DIP.csv` | `excluded` | `csv(header=0)` | 2 | 0 | 2 | 0 | excluded_from_project_level |
| `data/raw/bps_fdi_china_2015_2023.xlsx` | `excluded` | `excel_default(sheet=0,header=0)` | 9 | 0 | 9 | 0 | excluded_from_project_level |
| `data/raw/bps_fdi_country_2000_2024_combined.xlsx` | `excluded` | `excel_default(sheet=0,header=0)` | 825 | 0 | 825 | 0 | excluded_from_project_level |

## Mapping Audit (Source Column -> Canonical Column)
| Source File | Source Column | Canonical Column | Transform | Null Rate (%) |
|---|---|---|---|---:|
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Commitment Date (nearest match)` | `approval_date` | `parse_date_any` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Adjusted Amount (Nominal USD) | Amount (Nominal USD)` | `committed_usd` | `coalesce_numeric(adjusted, amount)` | 16.25 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Actual Implementation Start Date -> Planned Start Date` | `construction_start_date` | `parse_date_any_with_fallback` | 55.15 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Disbursed Amount (Nominal USD) | Disbursement Amount (Nominal USD)` | `disbursed_usd` | `coalesce_numeric` | 16.25 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Available ADM2 Level` | `district` | `direct` | 100.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `(constant)` | `finance_type` | `constant('DF')` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Financial Close Date | Loan Signing Date` | `financial_close_date` | `parse_date_any` | 100.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Latitude | Project Latitude | Available Latitude | Lat` | `latitude` | `numeric` | 100.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Longitude | Project Longitude | Available Longitude | Lon | Lng` | `longitude` | `numeric` | 100.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Actual Completion Date -> Planned Completion Date` | `operation_date` | `parse_date_any_with_fallback` | 49.66 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `AidData Record ID` | `project_id` | `direct` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `source_file + project_name + year + country` | `project_id` | `deterministic_hash_if_missing` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Title` | `project_name` | `direct` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Available ADM1 Level` | `province` | `direct` | 100.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Sector Name` | `sector` | `direct` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Status` | `status` | `direct` | 0.00 |
| `data/raw/AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx` | `Commitment Year` | `year` | `numeric` | 0.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `Quantity in Millions` | `committed_usd` | `numeric * 1_000_000` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `keyword location candidates` | `district` | `keyword_resolve` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `(constant)` | `finance_type` | `constant('FDI')` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `keyword location candidates` | `latitude` | `keyword_resolve_numeric` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `keyword location candidates` | `longitude` | `keyword_resolve_numeric` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `(generated)` | `project_id` | `deterministic_hash_if_missing` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `Transaction Party | Investor/Contractor | Investor | Investor or Builder` | `project_name` | `coalesce_string` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `keyword location candidates` | `province` | `keyword_resolve` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `Sector` | `sector` | `direct` | 100.00 |
| `data/raw/China-Global-Investment-Tracker-2024-Fall-public.xlsx` | `Year` | `year` | `numeric` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Commitment Date` | `approval_date` | `parse_mmddyyyy_or_excel_serial` | 0.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Adjusted Amount (Nominal USD) | Amount (Nominal USD)` | `committed_usd` | `coalesce_numeric(adjusted, amount)` | 15.25 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Implementation Start Date` | `construction_start_date` | `parse_mmddyyyy_or_excel_serial` | 97.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Disbursed Amount (Nominal USD)` | `disbursed_usd` | `numeric` | 15.25 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Available ADM2 Level | District` | `district` | `coalesce_string` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Financial Close Date` | `financial_close_date` | `parse_mmddyyyy_or_excel_serial` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Latitude` | `latitude` | `numeric` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Longitude` | `longitude` | `numeric` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Actual Completion Date` | `operation_date` | `parse_mmddyyyy_or_excel_serial` | 49.75 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `AidData Record ID` | `project_id` | `direct_or_hash` | 0.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Title | Project Name` | `project_name` | `coalesce_string` | 0.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Available ADM1 Level | Province` | `province` | `coalesce_string` | 100.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Sector Name | Sector` | `sector` | `coalesce_string` | 0.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Status` | `status` | `direct` | 0.00 |
| `data/raw/ChinaGlobalProjectDetails.xlsx` | `Commitment Year | Year` | `year` | `coalesce_numeric` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `Amount_musd | Amount` | `committed_usd` | `coalesce_numeric_with_scaling` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `keyword location candidates` | `district` | `keyword_resolve` | 100.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `(constant)` | `finance_type` | `constant('FDI')` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `keyword location candidates` | `latitude` | `keyword_resolve_numeric` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `keyword location candidates` | `longitude` | `keyword_resolve_numeric` | 100.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `(generated)` | `project_id` | `deterministic_hash_if_missing` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `Investor or Builder | Investor` | `project_name` | `coalesce_string` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `keyword location candidates` | `province` | `keyword_resolve` | 100.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `Sector` | `sector` | `direct` | 0.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `Status` | `status` | `direct_if_present` | 100.00 |
| `data/raw/cgit_indonesia_investments_2006_2025.xlsx` | `Year` | `year` | `numeric` | 0.00 |

## Rules
- AidData is always parsed from sheet `GCDF_3.0` with header row `0`.
- Indonesia-only filter is applied to each included source using available country/recipient/host fields.
- Unknown values remain null (no-fabrication policy).
- Deterministic IDs are generated only when source project ID is missing.
