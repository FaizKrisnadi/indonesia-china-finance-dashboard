from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd

logger = logging.getLogger(__name__)

AIDDATA_FILENAME = "AidDatasGlobalChineseDevelopmentFinanceDataset_v3.0.xlsx"
AIDDATA_SHEET = "GCDF_3.0"
AIDDATA_HEADER = 0

CGIT_TRACKER_FILENAME = "China-Global-Investment-Tracker-2024-Fall-public.xlsx"
CGIT_INDONESIA_FILENAME = "cgit_indonesia_investments_2006_2025.xlsx"
ENRICHMENT_FILENAME = "ChinaGlobalProjectDetails.xlsx"

PRIMARY_SOURCES: dict[str, str] = {
    AIDDATA_FILENAME: "DF",
    CGIT_TRACKER_FILENAME: "FDI",
    CGIT_INDONESIA_FILENAME: "FDI",
}

EXCLUDED_SOURCES = {
    "IMF DIP.csv",
    "bps_fdi_china_2015_2023.xlsx",
    "bps_fdi_country_2000_2024_combined.xlsx",
    "BI_FDI In Indonesia By Country Of Origin.xls",
    "Geographical Spead [Spreadsheet].xlsx",
    ENRICHMENT_FILENAME,
}

CANONICAL_FIELDS = [
    "project_id",
    "project_name",
    "finance_type",
    "sector",
    "province",
    "district",
    "latitude",
    "longitude",
    "status",
    "approval_date",
    "construction_start_date",
    "financial_close_date",
    "operation_date",
    "committed_usd",
    "disbursed_usd",
    "year",
]

DATE_FIELDS = [
    "approval_date",
    "construction_start_date",
    "financial_close_date",
    "operation_date",
]

NUMERIC_FIELDS = ["latitude", "longitude", "committed_usd", "disbursed_usd"]

STRING_FIELDS = [
    column for column in CANONICAL_FIELDS if column not in set(DATE_FIELDS + NUMERIC_FIELDS + ["year"])
]

XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

COUNTRY_HINTS = (
    "country",
    "recipient",
    "host",
)

PROVINCE_CANDIDATES = [
    "Available ADM1 Level",
    "Province",
    "State/Province",
    "Region",
    "Project Location",
    "Location",
    "ADM1",
]

DISTRICT_CANDIDATES = [
    "Available ADM2 Level",
    "District",
    "City",
    "Kabupaten",
    "Kota",
    "ADM2",
]

LATITUDE_CANDIDATES = [
    "Latitude",
    "latitude",
    "Lat",
    "lat",
    "Y",
    "y_coord",
]

LONGITUDE_CANDIDATES = [
    "Longitude",
    "longitude",
    "Lon",
    "lng",
    "Long",
    "X",
    "x_coord",
]


@dataclass(slots=True)
class ETLWarning:
    source_file: str
    warning_type: str
    message: str


@dataclass(slots=True)
class SourceLoadStat:
    source_file: str
    role: str
    parser_used: str
    rows_in_source: int
    rows_loaded: int
    rows_excluded: int
    rows_used_for_enrichment: int = 0
    province_missing_pct: float | None = None
    coordinate_missing_pct: float | None = None
    note: str = ""


@dataclass(slots=True)
class MappingAuditRow:
    source_file: str
    source_column: str
    canonical_column: str
    transform: str
    null_rate_pct: float


def discover_raw_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        return []

    files: list[Path] = []
    for pattern in ("*.csv", "*.xlsx", "*.xls"):
        files.extend(raw_dir.rglob(pattern))

    return sorted({path for path in files if path.is_file()})


def _normalize_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _strip_column_whitespace(frame: pd.DataFrame) -> pd.DataFrame:
    stripped = frame.copy()
    stripped.columns = _dedupe_columns(
        ["" if pd.isna(column) else str(column).strip() for column in stripped.columns]
    )
    return stripped


def _column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in frame.columns:
        raw = str(column).strip()
        normalized = _normalize_column_name(raw)
        if normalized and normalized not in lookup:
            lookup[normalized] = raw
    return lookup


def _find_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = _column_lookup(frame)
    for candidate in candidates:
        normalized = _normalize_column_name(candidate)
        if normalized in lookup:
            return lookup[normalized]

    for candidate in candidates:
        normalized = _normalize_column_name(candidate)
        if not normalized:
            continue
        for normalized_column, original in lookup.items():
            if normalized in normalized_column or normalized_column in normalized:
                return original
    return None


def _get_column(frame: pd.DataFrame, candidates: list[str]) -> pd.Series:
    match = _find_column(frame, candidates)
    if match is None:
        return pd.Series([pd.NA] * len(frame), index=frame.index)
    return frame[match]


def _to_numeric_clean(series: pd.Series, multiplier: float = 1.0) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce") * multiplier


def _coalesce_series(series_list: list[pd.Series], index: pd.Index) -> pd.Series:
    if not series_list:
        return pd.Series([pd.NA] * len(index), index=index)

    result = series_list[0].copy()
    for series in series_list[1:]:
        result = result.combine_first(series)
    return result


def parse_date_any(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().replace({"": pd.NA})
    parsed = pd.to_datetime(text, errors="coerce")
    numeric = pd.to_numeric(text, errors="coerce")
    parsed_excel_serial = pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
    return parsed.fillna(parsed_excel_serial)


def _excel_col_to_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if match is None:
        return 0

    value = 0
    for char in match.group(1):
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []

    root = ET.fromstring(archive.read(path))
    values: list[str] = []
    for item in root.findall("a:si", XLSX_NS):
        values.append("".join((node.text or "") for node in item.findall(".//a:t", XLSX_NS)))
    return values


def _xlsx_sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    rel_map = {
        rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
        for rel in rels_root.findall("pr:Relationship", XLSX_NS)
    }

    targets: dict[str, str] = {}
    for sheet in workbook_root.findall("a:sheets/a:sheet", XLSX_NS):
        name = sheet.attrib.get("name")
        rel_id = sheet.attrib.get(f"{{{XLSX_NS['r']}}}id", "")
        target = rel_map.get(rel_id, "")
        if not name or not target:
            continue

        normalized = target.replace("\\", "/")
        if normalized.startswith("/"):
            normalized = normalized.lstrip("/")
        if not normalized.startswith("xl/"):
            normalized = f"xl/{normalized}"

        targets[name] = normalized

    return targets


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join((node.text or "") for node in cell.findall("a:is/a:t", XLSX_NS))

    value_node = cell.find("a:v", XLSX_NS)
    if value_node is None or value_node.text is None:
        return pd.NA

    raw = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw

    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"

    return raw


def _xlsx_rows_for_sheet(
    archive: zipfile.ZipFile,
    sheet_target: str,
    shared_strings: list[str],
) -> list[list[Any]]:
    sheet_root = ET.fromstring(archive.read(sheet_target))
    sheet_data = sheet_root.find("a:sheetData", XLSX_NS)
    if sheet_data is None:
        return []

    sparse_rows: list[dict[int, Any]] = []
    max_col = 0

    for row in sheet_data.findall("a:row", XLSX_NS):
        values: dict[int, Any] = {}
        for cell in row.findall("a:c", XLSX_NS):
            index = _excel_col_to_index(cell.attrib.get("r", "A1"))
            values[index] = _xlsx_cell_value(cell, shared_strings)
            max_col = max(max_col, index)
        sparse_rows.append(values)

    dense_rows: list[list[Any]] = []
    width = max_col + 1
    for sparse in sparse_rows:
        dense_rows.append([sparse.get(index, pd.NA) for index in range(width)])

    return dense_rows


def _dedupe_columns(raw_columns: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    columns: list[str] = []

    for index, value in enumerate(raw_columns):
        name = "" if pd.isna(value) else str(value).strip()
        if not name:
            name = f"Unnamed: {index}"

        count = seen.get(name, 0)
        seen[name] = count + 1
        columns.append(name if count == 0 else f"{name}.{count}")

    return columns


def _frame_from_rows(rows: list[list[Any]], header_row: int) -> pd.DataFrame:
    if header_row >= len(rows):
        return pd.DataFrame()

    header = rows[header_row]
    columns = _dedupe_columns(header)
    values = rows[header_row + 1 :]

    frame = pd.DataFrame(values, columns=columns)
    frame = frame.replace({"": pd.NA})
    frame = frame.dropna(how="all").reset_index(drop=True)
    return _strip_column_whitespace(frame)


def _non_unnamed_column_count(columns: list[Any]) -> int:
    count = 0
    for column in columns:
        value = "" if pd.isna(column) else str(column).strip()
        if not value:
            continue
        if value.lower().startswith("unnamed"):
            continue
        count += 1
    return count


def _read_xlsx_sheet_header(path: Path, sheet_name: str, header_row: int) -> tuple[pd.DataFrame, str]:
    with zipfile.ZipFile(path) as archive:
        targets = _xlsx_sheet_targets(archive)
        target = targets.get(sheet_name)
        if target is None:
            raise ValueError(f"Sheet '{sheet_name}' not found in {path.name}.")

        shared = _xlsx_shared_strings(archive)
        rows = _xlsx_rows_for_sheet(archive, target, shared)
        frame = _frame_from_rows(rows, header_row)

    parser = f"xlsx_zip(sheet={sheet_name},header={header_row})"
    return frame, parser


def _scan_xlsx_for_best_parse(path: Path) -> tuple[pd.DataFrame, str]:
    best_frame: pd.DataFrame | None = None
    best_parser = ""
    best_score = -1
    best_rows = -1

    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        targets = _xlsx_sheet_targets(archive)

        for sheet_name, target in targets.items():
            try:
                rows = _xlsx_rows_for_sheet(archive, target, shared)
            except Exception:  # noqa: BLE001
                continue

            for header in range(0, 9):
                frame = _frame_from_rows(rows, header)
                score = _non_unnamed_column_count(frame.columns.tolist())
                row_count = len(frame)
                if score > best_score or (score == best_score and row_count > best_rows):
                    best_frame = frame
                    best_score = score
                    best_rows = row_count
                    best_parser = f"excel_fallback_scan(sheet={sheet_name},header={header},score={score})"

    if best_frame is None:
        raise ValueError(f"Failed to parse {path.name} using xlsx fallback scan.")

    return best_frame, best_parser


def _scan_excel_with_pandas(path: Path) -> tuple[pd.DataFrame, str]:
    best_frame: pd.DataFrame | None = None
    best_parser = ""
    best_score = -1
    best_rows = -1

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        for header in range(0, 9):
            try:
                frame = pd.read_excel(path, sheet_name=sheet_name, header=header)
            except Exception:  # noqa: BLE001
                continue

            score = _non_unnamed_column_count(frame.columns.tolist())
            row_count = len(frame)
            if score > best_score or (score == best_score and row_count > best_rows):
                best_frame = frame
                best_score = score
                best_rows = row_count
                best_parser = f"excel_fallback_scan(sheet={sheet_name},header={header},score={score})"

    if best_frame is None:
        raise ValueError(f"Failed to parse {path.name} using excel fallback scan.")

    return best_frame, best_parser


def read_raw_file(
    path: Path,
    warnings: list[ETLWarning],
    fixed_sheet: str | None = None,
    fixed_header: int | None = None,
) -> tuple[pd.DataFrame, str]:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _strip_column_whitespace(pd.read_csv(path)), "csv(header=0)"

    if suffix not in {".xlsx", ".xls"}:
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    if fixed_sheet is not None and fixed_header is not None:
        try:
            frame = pd.read_excel(path, sheet_name=fixed_sheet, header=fixed_header)
            parser = f"excel_fixed(sheet={fixed_sheet},header={fixed_header})"
            return _strip_column_whitespace(frame), parser
        except Exception as exc:  # noqa: BLE001
            if suffix == ".xlsx":
                frame, parser = _read_xlsx_sheet_header(path, fixed_sheet, fixed_header)
                warnings.append(
                    ETLWarning(
                        source_file=str(path),
                        warning_type="excel_default_failed",
                        message=(
                            "Fixed-sheet parser failed; fallback xlsx parser used. "
                            f"Error: {exc}"
                        ),
                    )
                )
                return _strip_column_whitespace(frame), parser
            raise

    try:
        frame = pd.read_excel(path, sheet_name=0, header=0)
        return _strip_column_whitespace(frame), "excel_default(sheet=0,header=0)"
    except Exception as exc:  # noqa: BLE001
        if suffix == ".xlsx":
            frame, parser = _scan_xlsx_for_best_parse(path)
        else:
            frame, parser = _scan_excel_with_pandas(path)

        warnings.append(
            ETLWarning(
                source_file=str(path),
                warning_type="excel_default_failed",
                message=(
                    "Default Excel parser failed; fallback scanner used. "
                    f"Error: {exc}"
                ),
            )
        )
        return _strip_column_whitespace(frame), parser


def _indonesia_mask(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series, list[str]]:
    lookup = _column_lookup(frame)
    candidate_columns = [
        original
        for normalized, original in lookup.items()
        if any(hint in normalized for hint in COUNTRY_HINTS)
    ]

    if not candidate_columns:
        return pd.Series([False] * len(frame), index=frame.index), pd.Series([pd.NA] * len(frame), index=frame.index), []

    mask = pd.Series([False] * len(frame), index=frame.index)
    country_series = pd.Series([pd.NA] * len(frame), index=frame.index)

    for column in candidate_columns:
        values = frame[column].astype("string").str.strip()
        normalized = _normalize_column_name(column)

        if "iso" in normalized:
            country_hit = values.str.upper().eq("IDN")
        else:
            lower = values.str.lower()
            country_hit = lower.eq("indonesia") | lower.str.contains(r"\bindonesia\b", regex=True) | values.str.upper().eq("IDN")

        mask = mask | country_hit.fillna(False)
        country_series = country_series.combine_first(values)

    return mask, country_series, candidate_columns


def _enforce_indonesia_filter(
    frame: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
) -> tuple[pd.DataFrame, pd.Series, int]:
    mask, country_series, country_columns = _indonesia_mask(frame)
    if not country_columns:
        warnings.append(
            ETLWarning(
                source_file=source_file,
                warning_type="missing_country_filter_columns",
                message="No country/recipient/host column found; all rows excluded by Indonesia-only rule.",
            )
        )

    filtered = frame.loc[mask].copy()
    filtered_country = country_series.loc[mask]
    excluded_rows = int((~mask).sum())

    return filtered, filtered_country, excluded_rows


def _parse_dates(series: pd.Series) -> pd.Series:
    return parse_date_any(series)


def _resolve_location_series(filtered: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "province": _get_column(filtered, PROVINCE_CANDIDATES),
        "district": _get_column(filtered, DISTRICT_CANDIDATES),
        "latitude": _to_numeric_clean(_get_column(filtered, LATITUDE_CANDIDATES)),
        "longitude": _to_numeric_clean(_get_column(filtered, LONGITUDE_CANDIDATES)),
    }


def _source_missingness(standardized: pd.DataFrame) -> tuple[float | None, float | None]:
    if standardized.empty:
        return None, None

    province_missing_pct = float((standardized["province"].isna().mean() * 100).round(2))
    coordinate_missing_pct = float(
        ((standardized["latitude"].isna() | standardized["longitude"].isna()).mean() * 100).round(2)
    )
    return province_missing_pct, coordinate_missing_pct


def _finalize_schema(
    standardized: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
) -> pd.DataFrame:
    for column in CANONICAL_FIELDS:
        if column not in standardized.columns:
            standardized[column] = pd.NA

    standardized = standardized.loc[:, CANONICAL_FIELDS].copy()

    for column in STRING_FIELDS:
        standardized[column] = standardized[column].astype("string").str.strip().replace({"": pd.NA})

    for column in DATE_FIELDS:
        standardized[column] = pd.to_datetime(standardized[column], errors="coerce")

    for column in NUMERIC_FIELDS:
        standardized[column] = pd.to_numeric(standardized[column], errors="coerce")

    standardized["year"] = pd.to_numeric(standardized["year"], errors="coerce").astype("Int64")

    invalid_finance = ~standardized["finance_type"].isin(["DF", "FDI"])
    if invalid_finance.any():
        warnings.append(
            ETLWarning(
                source_file=source_file,
                warning_type="invalid_finance_type",
                message="Rows with invalid finance_type were set to null before fallback handling.",
            )
        )
        standardized.loc[invalid_finance, "finance_type"] = pd.NA

    return standardized


def _generate_deterministic_ids(
    standardized: pd.DataFrame,
    source_file: str,
    country_series: pd.Series,
) -> pd.DataFrame:
    frame = standardized.copy()
    missing_id = frame["project_id"].isna() | frame["project_id"].astype("string").str.strip().eq("")
    if not missing_id.any():
        return frame

    names = frame["project_name"].astype("string").fillna("")
    years = frame["year"].astype("string").fillna("")
    countries = country_series.astype("string").fillna("")

    generated: list[str] = []
    for idx in frame.index:
        if not bool(missing_id.loc[idx]):
            generated.append(str(frame.loc[idx, "project_id"]))
            continue

        payload = f"{source_file}|{names.loc[idx]}|{years.loc[idx]}|{countries.loc[idx]}"
        hash_value = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
        generated.append(f"gen_{hash_value}")

    frame["project_id"] = pd.Series(generated, index=frame.index, dtype="string")
    return frame


def _add_mapping_audit(
    audits: list[MappingAuditRow],
    source_file: str,
    mappings: list[tuple[str, str, str]],
    standardized: pd.DataFrame,
) -> None:
    null_rates = (standardized.isna().mean() * 100).round(2).to_dict() if not standardized.empty else {}

    for source_column, canonical_column, transform in mappings:
        audits.append(
            MappingAuditRow(
                source_file=source_file,
                source_column=source_column,
                canonical_column=canonical_column,
                transform=transform,
                null_rate_pct=float(null_rates.get(canonical_column, 100.0)),
            )
        )


def _standardize_aiddata(
    frame: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
    audits: list[MappingAuditRow],
) -> tuple[pd.DataFrame, int, int]:
    rows_in = len(frame)
    filtered, country_series, rows_excluded_by_country = _enforce_indonesia_filter(frame, source_file, warnings)

    standardized = pd.DataFrame(index=filtered.index)
    standardized["project_id"] = _get_column(filtered, ["AidData Record ID"])
    standardized["project_name"] = _get_column(filtered, ["Title"])
    standardized["finance_type"] = "DF"
    standardized["sector"] = _get_column(filtered, ["Sector Name"])
    standardized["province"] = _get_column(filtered, ["Available ADM1 Level"])
    standardized["district"] = _get_column(filtered, ["Available ADM2 Level"])
    location_resolved = _resolve_location_series(filtered)
    standardized["latitude"] = _coalesce_series(
        [
            _to_numeric_clean(
                _get_column(filtered, ["Latitude", "Project Latitude", "Available Latitude", "Lat"])
            ),
            location_resolved["latitude"],
        ],
        index=filtered.index,
    )
    standardized["longitude"] = _coalesce_series(
        [
            _to_numeric_clean(
                _get_column(
                    filtered,
                    ["Longitude", "Project Longitude", "Available Longitude", "Lon", "Lng"],
                )
            ),
            location_resolved["longitude"],
        ],
        index=filtered.index,
    )
    standardized["status"] = _get_column(filtered, ["Status"])
    standardized["approval_date"] = _parse_dates(
        _get_column(
            filtered,
            [
                "Commitment Date",
                "Commitment Date (MM/DD/YYYY)",
                "Original Commitment Date",
                "Date of Commitment",
            ],
        )
    )

    actual_start = _parse_dates(
        _get_column(
            filtered,
            [
                "Actual Implementation Start Date",
                "Implementation Start Date",
                "Actual Construction Start Date",
                "Construction Start Date",
            ],
        )
    )
    planned_start = _parse_dates(
        _get_column(
            filtered,
            [
                "Planned Implementation Start Date",
                "Planned Construction Start Date",
                "Planned Start Date",
                "Expected Start Date",
            ],
        )
    )
    standardized["construction_start_date"] = actual_start.combine_first(planned_start)
    standardized["financial_close_date"] = _parse_dates(
        _get_column(filtered, ["Financial Close Date", "Loan Signing Date"])
    )
    actual_completion = _parse_dates(
        _get_column(
            filtered,
            [
                "Actual Completion Date",
                "Actual Project Completion Date",
            ],
        )
    )
    planned_completion = _parse_dates(
        _get_column(
            filtered,
            [
                "Planned Completion Date",
                "Expected Completion Date",
            ],
        )
    )
    standardized["operation_date"] = actual_completion.combine_first(planned_completion)

    committed = _coalesce_series(
        [
            _to_numeric_clean(_get_column(filtered, ["Adjusted Amount (Nominal USD)"])),
            _to_numeric_clean(_get_column(filtered, ["Amount (Nominal USD)"])),
        ],
        index=filtered.index,
    )
    standardized["committed_usd"] = committed
    standardized["disbursed_usd"] = _to_numeric_clean(
        _get_column(filtered, ["Disbursed Amount (Nominal USD)", "Disbursement Amount (Nominal USD)"])
    )
    standardized["year"] = _to_numeric_clean(_get_column(filtered, ["Commitment Year"]))

    standardized = _finalize_schema(standardized, source_file, warnings)
    standardized = _generate_deterministic_ids(standardized, source_file, country_series)

    mapping_rows = [
        ("AidData Record ID", "project_id", "direct"),
        ("Title", "project_name", "direct"),
        ("(constant)", "finance_type", "constant('DF')"),
        ("Sector Name", "sector", "direct"),
        ("Available ADM1 Level", "province", "direct"),
        ("Available ADM2 Level", "district", "direct"),
        ("Latitude | Project Latitude | Available Latitude | Lat", "latitude", "numeric"),
        (
            "Longitude | Project Longitude | Available Longitude | Lon | Lng",
            "longitude",
            "numeric",
        ),
        ("Status", "status", "direct"),
        ("Commitment Date (nearest match)", "approval_date", "parse_date_any"),
        (
            "Actual Implementation Start Date -> Planned Start Date",
            "construction_start_date",
            "parse_date_any_with_fallback",
        ),
        (
            "Financial Close Date | Loan Signing Date",
            "financial_close_date",
            "parse_date_any",
        ),
        (
            "Actual Completion Date -> Planned Completion Date",
            "operation_date",
            "parse_date_any_with_fallback",
        ),
        (
            "Adjusted Amount (Nominal USD) | Amount (Nominal USD)",
            "committed_usd",
            "coalesce_numeric(adjusted, amount)",
        ),
        (
            "Disbursed Amount (Nominal USD) | Disbursement Amount (Nominal USD)",
            "disbursed_usd",
            "coalesce_numeric",
        ),
        ("Commitment Year", "year", "numeric"),
        (
            "source_file + project_name + year + country",
            "project_id",
            "deterministic_hash_if_missing",
        ),
    ]
    _add_mapping_audit(audits, source_file, mapping_rows, standardized)

    rows_loaded = len(standardized)
    return standardized.reset_index(drop=True), rows_in, rows_excluded_by_country + max(rows_in - rows_loaded - rows_excluded_by_country, 0)


def _standardize_cgit_tracker(
    frame: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
    audits: list[MappingAuditRow],
) -> tuple[pd.DataFrame, int, int]:
    rows_in = len(frame)
    filtered, country_series, rows_excluded_by_country = _enforce_indonesia_filter(frame, source_file, warnings)
    location_resolved = _resolve_location_series(filtered)

    standardized = pd.DataFrame(index=filtered.index)
    standardized["project_id"] = pd.NA
    standardized["project_name"] = _coalesce_series(
        [
            _get_column(filtered, ["Transaction Party"]),
            _get_column(filtered, ["Investor/Contractor", "Investor", "Investor or Builder"]),
        ],
        index=filtered.index,
    )
    standardized["finance_type"] = "FDI"
    standardized["sector"] = _get_column(filtered, ["Sector"])
    standardized["province"] = location_resolved["province"]
    standardized["district"] = location_resolved["district"]
    standardized["latitude"] = location_resolved["latitude"]
    standardized["longitude"] = location_resolved["longitude"]
    standardized["status"] = pd.NA
    standardized["approval_date"] = pd.NA
    standardized["construction_start_date"] = pd.NA
    standardized["financial_close_date"] = pd.NA
    standardized["operation_date"] = pd.NA
    standardized["committed_usd"] = _to_numeric_clean(_get_column(filtered, ["Quantity in Millions"]), multiplier=1_000_000)
    standardized["disbursed_usd"] = pd.NA
    standardized["year"] = _to_numeric_clean(_get_column(filtered, ["Year"]))

    standardized = _finalize_schema(standardized, source_file, warnings)
    standardized = _generate_deterministic_ids(standardized, source_file, country_series)

    mapping_rows = [
        ("(generated)", "project_id", "deterministic_hash_if_missing"),
        (
            "Transaction Party | Investor/Contractor | Investor | Investor or Builder",
            "project_name",
            "coalesce_string",
        ),
        ("(constant)", "finance_type", "constant('FDI')"),
        ("Sector", "sector", "direct"),
        ("keyword location candidates", "province", "keyword_resolve"),
        ("keyword location candidates", "district", "keyword_resolve"),
        ("keyword location candidates", "latitude", "keyword_resolve_numeric"),
        ("keyword location candidates", "longitude", "keyword_resolve_numeric"),
        ("Quantity in Millions", "committed_usd", "numeric * 1_000_000"),
        ("Year", "year", "numeric"),
    ]
    _add_mapping_audit(audits, source_file, mapping_rows, standardized)

    rows_loaded = len(standardized)
    return standardized.reset_index(drop=True), rows_in, rows_excluded_by_country + max(rows_in - rows_loaded - rows_excluded_by_country, 0)


def _standardize_cgit_indonesia(
    frame: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
    audits: list[MappingAuditRow],
) -> tuple[pd.DataFrame, int, int]:
    rows_in = len(frame)
    filtered, country_series, rows_excluded_by_country = _enforce_indonesia_filter(frame, source_file, warnings)
    location_resolved = _resolve_location_series(filtered)

    standardized = pd.DataFrame(index=filtered.index)
    standardized["project_id"] = pd.NA
    standardized["project_name"] = _get_column(filtered, ["Investor or Builder", "Investor"])
    standardized["finance_type"] = "FDI"
    standardized["sector"] = _get_column(filtered, ["Sector"])
    standardized["province"] = location_resolved["province"]
    standardized["district"] = location_resolved["district"]
    standardized["latitude"] = location_resolved["latitude"]
    standardized["longitude"] = location_resolved["longitude"]
    standardized["status"] = _get_column(filtered, ["Status"])
    standardized["approval_date"] = pd.NA
    standardized["construction_start_date"] = pd.NA
    standardized["financial_close_date"] = pd.NA
    standardized["operation_date"] = pd.NA
    standardized["committed_usd"] = _coalesce_series(
        [
            _to_numeric_clean(_get_column(filtered, ["Amount_musd"]), multiplier=1_000_000),
            _to_numeric_clean(_get_column(filtered, ["Amount"])),
        ],
        index=filtered.index,
    )
    standardized["disbursed_usd"] = pd.NA
    standardized["year"] = _to_numeric_clean(_get_column(filtered, ["Year"]))

    standardized = _finalize_schema(standardized, source_file, warnings)
    standardized = _generate_deterministic_ids(standardized, source_file, country_series)

    mapping_rows = [
        ("(generated)", "project_id", "deterministic_hash_if_missing"),
        ("Investor or Builder | Investor", "project_name", "coalesce_string"),
        ("(constant)", "finance_type", "constant('FDI')"),
        ("Sector", "sector", "direct"),
        ("keyword location candidates", "province", "keyword_resolve"),
        ("keyword location candidates", "district", "keyword_resolve"),
        ("keyword location candidates", "latitude", "keyword_resolve_numeric"),
        ("keyword location candidates", "longitude", "keyword_resolve_numeric"),
        ("Status", "status", "direct_if_present"),
        ("Amount_musd | Amount", "committed_usd", "coalesce_numeric_with_scaling"),
        ("Year", "year", "numeric"),
    ]
    _add_mapping_audit(audits, source_file, mapping_rows, standardized)

    rows_loaded = len(standardized)
    return standardized.reset_index(drop=True), rows_in, rows_excluded_by_country + max(rows_in - rows_loaded - rows_excluded_by_country, 0)


def _optional_enrichment_frame(
    frame: pd.DataFrame,
    source_file: str,
    warnings: list[ETLWarning],
    audits: list[MappingAuditRow],
) -> tuple[pd.DataFrame, int, int]:
    rows_in = len(frame)
    filtered, country_series, rows_excluded_by_country = _enforce_indonesia_filter(frame, source_file, warnings)

    enrich = pd.DataFrame(index=filtered.index)
    enrich["project_id"] = _get_column(filtered, ["AidData Record ID", "project_id"])
    enrich["project_name"] = _get_column(filtered, ["Title", "Project Name", "project_name"])
    enrich["sector"] = _get_column(filtered, ["Sector Name", "Sector"])
    enrich["province"] = _get_column(filtered, ["Available ADM1 Level", "Province"])
    enrich["district"] = _get_column(filtered, ["Available ADM2 Level", "District"])
    enrich["latitude"] = _to_numeric_clean(_get_column(filtered, ["Latitude"]))
    enrich["longitude"] = _to_numeric_clean(_get_column(filtered, ["Longitude"]))
    enrich["status"] = _get_column(filtered, ["Status"])
    enrich["approval_date"] = _parse_dates(_get_column(filtered, ["Commitment Date"]))
    enrich["construction_start_date"] = _parse_dates(_get_column(filtered, ["Implementation Start Date"]))
    enrich["financial_close_date"] = _parse_dates(_get_column(filtered, ["Financial Close Date"]))
    enrich["operation_date"] = _parse_dates(_get_column(filtered, ["Actual Completion Date"]))
    enrich["committed_usd"] = _coalesce_series(
        [
            _to_numeric_clean(_get_column(filtered, ["Adjusted Amount (Nominal USD)"])),
            _to_numeric_clean(_get_column(filtered, ["Amount (Nominal USD)"])),
        ],
        index=filtered.index,
    )
    enrich["disbursed_usd"] = _to_numeric_clean(_get_column(filtered, ["Disbursed Amount (Nominal USD)"]))
    enrich["year"] = _to_numeric_clean(_get_column(filtered, ["Commitment Year", "Year"]))

    enrich = _finalize_schema(enrich.assign(finance_type="DF"), source_file, warnings)
    enrich = _generate_deterministic_ids(enrich, source_file, country_series)
    enrich = enrich.drop(columns=["finance_type"])  # enrichment never overrides finance type

    mapping_rows = [
        ("AidData Record ID", "project_id", "direct_or_hash"),
        ("Title | Project Name", "project_name", "coalesce_string"),
        ("Sector Name | Sector", "sector", "coalesce_string"),
        ("Available ADM1 Level | Province", "province", "coalesce_string"),
        ("Available ADM2 Level | District", "district", "coalesce_string"),
        ("Latitude", "latitude", "numeric"),
        ("Longitude", "longitude", "numeric"),
        ("Status", "status", "direct"),
        ("Commitment Date", "approval_date", "parse_mmddyyyy_or_excel_serial"),
        ("Implementation Start Date", "construction_start_date", "parse_mmddyyyy_or_excel_serial"),
        ("Financial Close Date", "financial_close_date", "parse_mmddyyyy_or_excel_serial"),
        ("Actual Completion Date", "operation_date", "parse_mmddyyyy_or_excel_serial"),
        (
            "Adjusted Amount (Nominal USD) | Amount (Nominal USD)",
            "committed_usd",
            "coalesce_numeric(adjusted, amount)",
        ),
        ("Disbursed Amount (Nominal USD)", "disbursed_usd", "numeric"),
        ("Commitment Year | Year", "year", "coalesce_numeric"),
    ]
    _add_mapping_audit(audits, source_file, mapping_rows, enrich.assign(finance_type="DF"))

    rows_loaded = len(enrich)
    return enrich.reset_index(drop=True), rows_in, rows_excluded_by_country + max(rows_in - rows_loaded - rows_excluded_by_country, 0)


def _normalize_name_for_key(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"[^a-z0-9 ]+", "", regex=True)
        .str.strip()
    )


def _apply_optional_enrichment(projects: pd.DataFrame, enrich: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if projects.empty or enrich.empty:
        return projects, 0

    enriched = projects.copy()
    fill_fields = [
        "sector",
        "province",
        "district",
        "latitude",
        "longitude",
        "status",
        "approval_date",
        "construction_start_date",
        "financial_close_date",
        "operation_date",
        "committed_usd",
        "disbursed_usd",
        "year",
    ]

    rows_touched = pd.Series([False] * len(enriched), index=enriched.index)

    enrich_by_id = enrich.dropna(subset=["project_id"]).drop_duplicates(subset=["project_id"], keep="first")
    if not enrich_by_id.empty:
        id_lookup = enrich_by_id.set_index("project_id")
        for idx, project_id in enriched["project_id"].items():
            if pd.isna(project_id) or project_id not in id_lookup.index:
                continue
            updates = 0
            for field in fill_fields:
                if pd.isna(enriched.at[idx, field]) and pd.notna(id_lookup.at[project_id, field]):
                    enriched.at[idx, field] = id_lookup.at[project_id, field]
                    updates += 1
            if updates > 0:
                rows_touched.at[idx] = True

    left_key = _normalize_name_for_key(enriched["project_name"]) + "|" + enriched["year"].astype("string")
    right_key = _normalize_name_for_key(enrich["project_name"]) + "|" + enrich["year"].astype("string")
    enrich_by_name_year = enrich.assign(_key=right_key).dropna(subset=["_key"]).drop_duplicates("_key", keep="first")
    key_lookup = enrich_by_name_year.set_index("_key") if not enrich_by_name_year.empty else pd.DataFrame()

    if not key_lookup.empty:
        for idx, key in left_key.items():
            if pd.isna(key) or key not in key_lookup.index:
                continue
            updates = 0
            for field in fill_fields:
                if pd.isna(enriched.at[idx, field]) and pd.notna(key_lookup.at[key, field]):
                    enriched.at[idx, field] = key_lookup.at[key, field]
                    updates += 1
            if updates > 0:
                rows_touched.at[idx] = True

    return enriched, int(rows_touched.sum())


def _build_quality_report(
    projects: pd.DataFrame,
    raw_files: list[Path],
    warnings: list[ETLWarning],
    source_loads: list[SourceLoadStat],
) -> dict[str, Any]:
    missing_pct = (
        {column: 100.0 for column in CANONICAL_FIELDS}
        if projects.empty
        else (projects.isna().mean() * 100).round(2).to_dict()
    )

    return {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "raw_file_count": len(raw_files),
        "row_count": int(len(projects)),
        "warning_count": len(warnings),
        "warnings": [asdict(item) for item in warnings],
        "source_loads": [asdict(item) for item in source_loads],
        "missing_pct": missing_pct,
    }


def _write_outputs(projects: pd.DataFrame, quality_report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "projects_canonical.csv"
    projects.to_csv(csv_path, index=False)

    quality_path = out_dir / "data_quality.json"
    quality_path.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")


def _write_methodology(
    raw_files: list[Path],
    source_loads: list[SourceLoadStat],
    audits: list[MappingAuditRow],
    output_path: Path = Path("docs/methodology.md"),
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Methodology",
        "",
        "## Source Inclusion Policy",
        "Project-level canonical dataset is built from primary sources only:",
        f"- `{AIDDATA_FILENAME}` (`finance_type = DF`)",
        f"- `{CGIT_TRACKER_FILENAME}` (`finance_type = FDI`)",
        f"- `{CGIT_INDONESIA_FILENAME}` (`finance_type = FDI`)",
        "",
        "Excluded from primary rows:",
    ]

    for source in sorted(EXCLUDED_SOURCES):
        lines.append(f"- `{source}`")

    lines.extend(
        [
            "",
            "Optional enrichment source (does not add primary rows):",
            f"- `{ENRICHMENT_FILENAME}`",
            "",
            "## Raw Files Discovered",
            f"- Count: {len(raw_files)}",
        ]
    )

    if raw_files:
        for path in raw_files:
            lines.append(f"- `{path}`")
    else:
        lines.append("- No files found.")

    lines.extend(
        [
            "",
            "## Source Load Audit",
            "| Source | Role | Parser | Rows In Source | Rows Loaded | Rows Excluded | Rows Used For Enrichment | Note |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )

    if source_loads:
        for row in source_loads:
            lines.append(
                f"| `{row.source_file}` | `{row.role}` | `{row.parser_used}` | {row.rows_in_source} | "
                f"{row.rows_loaded} | {row.rows_excluded} | {row.rows_used_for_enrichment} | {row.note or ''} |"
            )
    else:
        lines.append("| _n/a_ | _n/a_ | _n/a_ | 0 | 0 | 0 | 0 | no data |")

    lines.extend(
        [
            "",
            "## Mapping Audit (Source Column -> Canonical Column)",
            "| Source File | Source Column | Canonical Column | Transform | Null Rate (%) |",
            "|---|---|---|---|---:|",
        ]
    )

    if audits:
        for row in sorted(audits, key=lambda item: (item.source_file, item.canonical_column, item.source_column)):
            lines.append(
                f"| `{row.source_file}` | `{row.source_column}` | `{row.canonical_column}` | "
                f"`{row.transform}` | {row.null_rate_pct:.2f} |"
            )
    else:
        lines.append("| _n/a_ | _n/a_ | _n/a_ | _n/a_ | 100.00 |")

    lines.extend(
        [
            "",
            "## Rules",
            "- AidData is always parsed from sheet `GCDF_3.0` with header row `0`.",
            "- Indonesia-only filter is applied to each included source using available country/recipient/host fields.",
            "- Unknown values remain null (no-fabrication policy).",
            "- Deterministic IDs are generated only when source project ID is missing.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_etl(
    raw_dir: Path = Path("data/raw"),
    out_dir: Path = Path("data/processed"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    warnings: list[ETLWarning] = []
    source_loads: list[SourceLoadStat] = []
    audits: list[MappingAuditRow] = []

    raw_files = discover_raw_files(raw_dir)
    if not raw_files:
        warnings.append(
            ETLWarning(
                source_file=str(raw_dir),
                warning_type="no_raw_files",
                message="No files found in data/raw. ETL produced an empty project-level dataset.",
            )
        )

    primary_frames: list[pd.DataFrame] = []
    optional_enrichment: pd.DataFrame | None = None

    files_by_name = {path.name: path for path in raw_files}

    for source_name, finance_type in PRIMARY_SOURCES.items():
        path = files_by_name.get(source_name)
        if path is None:
            warnings.append(
                ETLWarning(
                    source_file=str(raw_dir / source_name),
                    warning_type="missing_primary_source",
                    message="Required primary source file is missing.",
                )
            )
            source_loads.append(
                SourceLoadStat(
                    source_file=str(raw_dir / source_name),
                    role="primary",
                    parser_used="missing",
                    rows_in_source=0,
                    rows_loaded=0,
                    rows_excluded=0,
                    note="required_primary_source_missing",
                )
            )
            continue

        try:
            if source_name == AIDDATA_FILENAME:
                frame, parser = read_raw_file(
                    path,
                    warnings,
                    fixed_sheet=AIDDATA_SHEET,
                    fixed_header=AIDDATA_HEADER,
                )
            else:
                frame, parser = read_raw_file(path, warnings)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ETLWarning(
                    source_file=str(path),
                    warning_type="read_error",
                    message=f"Failed to read source file: {exc}",
                )
            )
            source_loads.append(
                SourceLoadStat(
                    source_file=str(path),
                    role="primary",
                    parser_used="read_error",
                    rows_in_source=0,
                    rows_loaded=0,
                    rows_excluded=0,
                    note=str(exc),
                )
            )
            continue

        if source_name == AIDDATA_FILENAME:
            standardized, rows_in, rows_excluded = _standardize_aiddata(frame, str(path), warnings, audits)
        elif source_name == CGIT_TRACKER_FILENAME:
            standardized, rows_in, rows_excluded = _standardize_cgit_tracker(
                frame,
                str(path),
                warnings,
                audits,
            )
        elif source_name == CGIT_INDONESIA_FILENAME:
            standardized, rows_in, rows_excluded = _standardize_cgit_indonesia(
                frame,
                str(path),
                warnings,
                audits,
            )
        else:
            standardized = pd.DataFrame(columns=CANONICAL_FIELDS)
            rows_in = len(frame)
            rows_excluded = rows_in

        standardized["finance_type"] = finance_type
        standardized = _finalize_schema(standardized, str(path), warnings)

        primary_frames.append(standardized)
        rows_loaded = len(standardized)
        province_missing_pct, coordinate_missing_pct = _source_missingness(standardized)

        logger.info(
            "Loaded source file=%s rows=%s parser=%s role=primary",
            source_name,
            rows_loaded,
            parser,
        )

        source_loads.append(
            SourceLoadStat(
                source_file=str(path),
                role="primary",
                parser_used=parser,
                rows_in_source=rows_in,
                rows_loaded=rows_loaded,
                rows_excluded=max(rows_excluded, rows_in - rows_loaded),
                province_missing_pct=province_missing_pct,
                coordinate_missing_pct=coordinate_missing_pct,
            )
        )

    enrichment_path = files_by_name.get(ENRICHMENT_FILENAME)
    if enrichment_path is not None:
        try:
            enrich_raw, parser = read_raw_file(enrichment_path, warnings)
            enrichment, rows_in, rows_excluded = _optional_enrichment_frame(
                enrich_raw,
                str(enrichment_path),
                warnings,
                audits,
            )
            optional_enrichment = enrichment
            province_missing_pct, coordinate_missing_pct = _source_missingness(
                enrichment.assign(finance_type="DF")
            )
            source_loads.append(
                SourceLoadStat(
                    source_file=str(enrichment_path),
                    role="enrichment",
                    parser_used=parser,
                    rows_in_source=rows_in,
                    rows_loaded=0,
                    rows_excluded=max(rows_excluded, rows_in),
                    note="optional_enrichment_only",
                    province_missing_pct=province_missing_pct,
                    coordinate_missing_pct=coordinate_missing_pct,
                )
            )
            logger.info(
                "Loaded source file=%s rows=%s parser=%s role=enrichment",
                ENRICHMENT_FILENAME,
                len(enrichment),
                parser,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ETLWarning(
                    source_file=str(enrichment_path),
                    warning_type="enrichment_read_error",
                    message=f"Failed to read enrichment source: {exc}",
                )
            )
            source_loads.append(
                SourceLoadStat(
                    source_file=str(enrichment_path),
                    role="enrichment",
                    parser_used="read_error",
                    rows_in_source=0,
                    rows_loaded=0,
                    rows_excluded=0,
                    note=str(exc),
                )
            )

    for source_name in sorted(EXCLUDED_SOURCES - {ENRICHMENT_FILENAME}):
        path = files_by_name.get(source_name)
        if path is None:
            continue

        rows_in = 0
        parser = "excluded"
        note = "excluded_from_project_level"
        try:
            frame, parser = read_raw_file(path, warnings)
            rows_in = len(frame)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ETLWarning(
                    source_file=str(path),
                    warning_type="excluded_source_read_error",
                    message=(
                        "Source is excluded from canonical rows; row count could not be inspected. "
                        f"Error: {exc}"
                    ),
                )
            )
            note = f"excluded_from_project_level; row_count_unavailable ({exc})"

        source_loads.append(
            SourceLoadStat(
                source_file=str(path),
                role="excluded",
                parser_used=parser,
                rows_in_source=rows_in,
                rows_loaded=0,
                rows_excluded=rows_in,
                note=note,
            )
        )

    if primary_frames:
        projects = pd.concat(primary_frames, ignore_index=True)
    else:
        projects = pd.DataFrame(columns=CANONICAL_FIELDS)

    if optional_enrichment is not None and not projects.empty:
        projects, touched_rows = _apply_optional_enrichment(projects, optional_enrichment)
        for item in source_loads:
            if Path(item.source_file).name == ENRICHMENT_FILENAME and item.role == "enrichment":
                item.rows_used_for_enrichment = touched_rows
                break

    if not projects.empty:
        projects = _finalize_schema(projects, "canonical_dataset", warnings)
        missing_finance = projects["finance_type"].isna()
        if missing_finance.any():
            warnings.append(
                ETLWarning(
                    source_file="canonical_dataset",
                    warning_type="missing_finance_type",
                    message="Some rows had missing finance_type after source mapping and were dropped.",
                )
            )
            projects = projects.loc[~missing_finance].reset_index(drop=True)

        projects = projects.drop_duplicates(subset=["project_id", "finance_type"], keep="first")

    quality_report = _build_quality_report(projects, raw_files, warnings, source_loads)
    _write_outputs(projects, quality_report, out_dir)
    _write_methodology(raw_files, source_loads, audits)

    return projects, quality_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ETL for project-level canonical dataset")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    projects, quality_report = run_etl(raw_dir=args.raw_dir, out_dir=args.out_dir)
    logger.info(
        "ETL complete. rows=%s files=%s warnings=%s",
        len(projects),
        quality_report.get("raw_file_count", 0),
        quality_report.get("warning_count", 0),
    )


if __name__ == "__main__":
    main()
