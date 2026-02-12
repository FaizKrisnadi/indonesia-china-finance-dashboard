from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.etl import CANONICAL_FIELDS, DATE_FIELDS, NUMERIC_FIELDS

try:
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None


def _empty_projects() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_FIELDS)


def coerce_projects_schema(frame: pd.DataFrame) -> pd.DataFrame:
    projects = frame.copy()

    for column in CANONICAL_FIELDS:
        if column not in projects.columns:
            projects[column] = pd.NA

    projects = projects.loc[:, CANONICAL_FIELDS]

    for column in DATE_FIELDS:
        projects[column] = pd.to_datetime(projects[column], errors="coerce")

    for column in NUMERIC_FIELDS:
        projects[column] = pd.to_numeric(projects[column], errors="coerce")

    projects["year"] = pd.to_numeric(projects["year"], errors="coerce").astype("Int64")

    categorical_columns = [
        column
        for column in CANONICAL_FIELDS
        if column not in set(DATE_FIELDS + NUMERIC_FIELDS + ["year"])
    ]
    for column in categorical_columns:
        projects[column] = projects[column].astype("string").str.strip().replace({"": pd.NA})

    return projects


def load_projects(processed_dir: Path = Path("data/processed")) -> pd.DataFrame:
    db_path = processed_dir / "projects.duckdb"
    parquet_path = processed_dir / "projects_canonical.parquet"
    csv_path = processed_dir / "projects_canonical.csv"

    if db_path.exists() and duckdb is not None:
        try:
            connection = duckdb.connect(str(db_path), read_only=True)
            try:
                projects = connection.execute("SELECT * FROM projects").df()
            finally:
                connection.close()
            return coerce_projects_schema(projects)
        except Exception:  # noqa: BLE001
            pass

    if parquet_path.exists():
        try:
            projects = pd.read_parquet(parquet_path)
            return coerce_projects_schema(projects)
        except Exception:  # noqa: BLE001
            pass

    if csv_path.exists():
        try:
            projects = pd.read_csv(csv_path)
            return coerce_projects_schema(projects)
        except Exception:  # noqa: BLE001
            pass

    return _empty_projects()


def load_data_quality(processed_dir: Path = Path("data/processed")) -> dict[str, Any]:
    quality_path = processed_dir / "data_quality.json"

    if quality_path.exists():
        try:
            return json.loads(quality_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "raw_file_count": 0,
                "row_count": 0,
                "warning_count": 1,
                "warnings": [
                    {
                        "source_file": str(quality_path),
                        "warning_type": "invalid_quality_json",
                        "message": "Could not parse data_quality.json.",
                    }
                ],
                "missing_pct": {column: 100.0 for column in CANONICAL_FIELDS},
            }

    projects = load_projects(processed_dir)
    missing_pct = {column: 100.0 for column in CANONICAL_FIELDS}
    if not projects.empty:
        missing_pct = (projects.isna().mean() * 100).round(2).to_dict()

    return {
        "raw_file_count": 0,
        "row_count": int(len(projects)),
        "warning_count": 1,
        "warnings": [
            {
                "source_file": str(quality_path),
                "warning_type": "quality_file_missing",
                "message": "No data_quality.json found. Run ETL to generate quality diagnostics.",
            }
        ],
        "missing_pct": missing_pct,
    }


def get_filter_options(projects: pd.DataFrame) -> dict[str, list[Any]]:
    options: dict[str, list[Any]] = {
        "year": [],
        "finance_type": [],
        "sector": [],
        "province": [],
        "status": [],
        "sponsor_type": [],
    }

    if projects.empty:
        return options

    year_values = (
        projects["year"].dropna().astype(int).sort_values().unique().tolist()
        if "year" in projects.columns
        else []
    )
    options["year"] = year_values

    for field in ["finance_type", "sector", "province", "status", "sponsor_type"]:
        if field in projects.columns:
            options[field] = sorted(projects[field].dropna().astype(str).unique().tolist())

    return options


def apply_filters(projects: pd.DataFrame, filters: dict[str, list[Any]]) -> pd.DataFrame:
    if projects.empty:
        return projects

    filtered = projects.copy()

    field_map = {
        "year": "year",
        "finance_type": "finance_type",
        "sector": "sector",
        "province": "province",
        "status": "status",
        "sponsor_type": "sponsor_type",
    }

    for filter_name, column in field_map.items():
        selected_values = filters.get(filter_name, [])
        if selected_values:
            filtered = filtered[filtered[column].isin(selected_values)]

    return filtered
