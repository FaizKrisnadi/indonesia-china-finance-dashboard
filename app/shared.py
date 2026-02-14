from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from app.theme import apply_global_styles, get_theme_colors
except ModuleNotFoundError:
    from theme import apply_global_styles, get_theme_colors

try:
    from src.model import CANONICAL_FIELDS, coerce_projects_schema, load_data_quality
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.model import CANONICAL_FIELDS, coerce_projects_schema, load_data_quality

try:
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None


def _empty_projects() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_FIELDS)


def load_projects_with_source(
    processed_dir: Path = Path("data/processed"),
) -> tuple[pd.DataFrame, str]:
    csv_path = processed_dir / "projects_canonical.csv"
    parquet_path = processed_dir / "projects_canonical.parquet"
    db_path = processed_dir / "projects.duckdb"

    if csv_path.exists():
        try:
            projects = pd.read_csv(csv_path)
            return coerce_projects_schema(projects), "csv"
        except Exception:  # noqa: BLE001
            pass

    if parquet_path.exists():
        try:
            projects = pd.read_parquet(parquet_path)
            return coerce_projects_schema(projects), "parquet"
        except Exception:  # noqa: BLE001
            pass

    if db_path.exists() and duckdb is not None:
        try:
            connection = duckdb.connect(str(db_path), read_only=True)
            try:
                projects = connection.execute("SELECT * FROM projects").df()
            finally:
                connection.close()
            return coerce_projects_schema(projects), "duckdb"
        except Exception:  # noqa: BLE001
            pass

    return _empty_projects(), "empty"


def load_projects(processed_dir: Path = Path("data/processed")) -> pd.DataFrame:
    projects, _ = load_projects_with_source(processed_dir)
    return projects


@st.cache_data(show_spinner=False)
def load_projects_with_source_cached() -> tuple[pd.DataFrame, str]:
    return load_projects_with_source()


def get_loaded_source_label() -> str:
    _, source = load_projects_with_source_cached()
    return source


@st.cache_data(show_spinner=False)
def load_projects_cached() -> pd.DataFrame:
    projects, _ = load_projects_with_source_cached()
    return projects


@st.cache_data(show_spinner=False)
def load_data_quality_cached() -> dict[str, Any]:
    return load_data_quality()


def format_currency(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    amount = float(value)
    magnitude = abs(amount)
    if magnitude >= 1_000_000_000:
        return f"${amount / 1_000_000_000:,.2f}B"
    if magnitude >= 1_000_000:
        return f"${amount / 1_000_000:,.2f}M"
    if magnitude >= 1_000:
        return f"${amount / 1_000:,.1f}K"
    return f"${amount:,.0f}"


def format_pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:,.1f}%"


def _sorted_string_options(series: pd.Series) -> list[str]:
    values = (
        series.astype("string").str.strip().replace({"": pd.NA}).dropna().astype(str).unique().tolist()
    )
    return sorted(values)


def _build_filter_options(projects: pd.DataFrame) -> dict[str, list[Any]]:
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

    if "year" in projects.columns:
        years = pd.to_numeric(projects["year"], errors="coerce").dropna()
        options["year"] = sorted(years.astype(int).unique().tolist())

    if "finance_type" in projects.columns:
        finance_values = _sorted_string_options(projects["finance_type"].str.upper())
        finance_values = [value for value in finance_values if value in {"DF", "FDI"}] + [
            value for value in finance_values if value not in {"DF", "FDI"}
        ]
        if len(projects) > 0 and not finance_values:
            finance_values = ["DF", "FDI"]
        options["finance_type"] = finance_values

    for field in ["sector", "province", "status", "sponsor_type"]:
        if field in projects.columns:
            options[field] = _sorted_string_options(projects[field])

    return options


def get_filter_options_from_projects(projects: pd.DataFrame) -> dict[str, list[Any]]:
    return _build_filter_options(projects)


def _as_int_list(values: list[Any]) -> list[int]:
    output: list[int] = []
    for value in values:
        try:
            output.append(int(value))
        except (TypeError, ValueError):
            continue
    return output


def _init_filter_state(options: dict[str, list[Any]]) -> None:
    for field, field_options in options.items():
        key = f"global_filter_{field}"
        if key not in st.session_state:
            st.session_state[key] = list(field_options)
            continue

        current = st.session_state[key]
        valid = [value for value in current if value in field_options]
        st.session_state[key] = valid if valid else list(field_options)


def _reset_filter_state(options: dict[str, list[Any]]) -> None:
    for field, field_options in options.items():
        st.session_state[f"global_filter_{field}"] = list(field_options)


def _queue_filter_updates(updates: dict[str, list[Any]]) -> None:
    pending = st.session_state.get("_pending_filter_updates", {})
    pending.update({key: list(value) for key, value in updates.items()})
    st.session_state["_pending_filter_updates"] = pending


def _apply_queued_filter_updates(options: dict[str, list[Any]]) -> None:
    pending = st.session_state.pop("_pending_filter_updates", {})
    if not pending:
        return

    for field, values in pending.items():
        key = f"global_filter_{field}"
        field_options = options.get(field, [])
        valid = [value for value in values if value in field_options]
        st.session_state[key] = valid if valid else list(field_options)


def _get_query_values(key: str) -> list[str]:
    params = st.query_params
    if hasattr(params, "get_all"):
        values = params.get_all(key)
        return [str(value) for value in values]

    value = params.get(key, None)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _apply_query_param_overrides_once(
    options: dict[str, list[Any]],
    include_finance_type: bool = True,
) -> None:
    if st.session_state.get("_query_filters_initialized", False):
        return

    field_map = {
        "year": "year",
        "sector": "sector",
        "province": "province",
    }
    if include_finance_type:
        field_map["finance_type"] = "finance_type"
    for query_key, field in field_map.items():
        raw_values = _get_query_values(query_key)
        if not raw_values:
            continue

        valid_options = options.get(field, [])
        if field == "year":
            parsed_values: list[int] = []
            for value in raw_values:
                try:
                    parsed_values.append(int(value))
                except (TypeError, ValueError):
                    continue
            valid_values = [value for value in parsed_values if value in valid_options]
        elif field == "finance_type":
            parsed_values = [value.upper() for value in raw_values]
            valid_values = [value for value in parsed_values if value in valid_options]
        else:
            valid_values = [value for value in raw_values if value in valid_options]

        st.session_state[f"global_filter_{field}"] = (
            list(valid_values) if valid_values else list(valid_options)
        )

    st.session_state["_query_filters_initialized"] = True


def init_view_mode_from_query() -> None:
    if "home_view_mode" in st.session_state:
        return

    raw_values = _get_query_values("view_mode")
    if not raw_values:
        return

    query_value = raw_values[0]
    valid_modes = {"Single view", "Compare DF vs FDI"}
    if query_value in valid_modes:
        st.session_state["home_view_mode"] = query_value


def _sync_filters_to_query_params(filters: dict[str, list[Any]], options: dict[str, list[Any]]) -> str:
    params: dict[str, list[str] | str] = {}

    def _set_if_present(key: str, values: list[Any]) -> None:
        if values:
            params[key] = [str(value) for value in values]

    selected_years = _as_int_list(filters.get("year", []))
    if selected_years and set(selected_years) != set(_as_int_list(options.get("year", []))):
        params["year"] = [str(value) for value in selected_years]

    selected_finance = [str(value).upper() for value in filters.get("finance_type", [])]
    all_finance = [str(value).upper() for value in options.get("finance_type", [])]
    if selected_finance and set(selected_finance) != set(all_finance):
        params["finance_type"] = selected_finance

    selected_sector = [str(value) for value in filters.get("sector", [])]
    if selected_sector and set(selected_sector) != set(str(value) for value in options.get("sector", [])):
        params["sector"] = selected_sector

    selected_province = [str(value) for value in filters.get("province", [])]
    if selected_province and set(selected_province) != set(
        str(value) for value in options.get("province", [])
    ):
        params["province"] = selected_province

    if "home_view_mode" in st.session_state:
        params["view_mode"] = st.session_state["home_view_mode"]
    else:
        query_view_mode = _get_query_values("view_mode")
        if query_view_mode:
            params["view_mode"] = query_view_mode[0]

    st.query_params.clear()
    for key, value in params.items():
        st.query_params[key] = value

    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if isinstance(value, list):
            pairs.extend((key, item) for item in value)
        else:
            pairs.append((key, value))
    query_string = urlencode(pairs, doseq=True)
    return f"?{query_string}" if query_string else "?"


def _render_copy_shareable_link_control(share_query: str) -> None:
    serialized_query = json.dumps(share_query)
    theme_colors = get_theme_colors()
    status_color = theme_colors["muted"]
    input_border = theme_colors["border"]
    input_bg = theme_colors["surface_2"]
    input_text = theme_colors["text"]
    st.sidebar.button("Copy shareable link", key="copy_shareable_link")
    if st.session_state.get("copy_shareable_link", False):
        components.html(
            f"""
            <script>
            (function () {{
              let shareUrl = "";
              try {{
                shareUrl = window.parent.location.origin + window.parent.location.pathname + {serialized_query};
              }} catch (error) {{
                shareUrl = {serialized_query};
              }}

              const status = document.getElementById("share-status");
              const urlInput = document.getElementById("share-url");
              urlInput.value = shareUrl;

              if (navigator.clipboard && shareUrl) {{
                navigator.clipboard.writeText(shareUrl)
                  .then(() => {{
                    status.textContent = "Link copied to clipboard.";
                  }})
                  .catch(() => {{
                    status.textContent = "Auto-copy unavailable. Copy URL below.";
                  }});
              }} else {{
                status.textContent = "Auto-copy unavailable. Copy URL below.";
              }}
            }})();
            </script>
            <div style="font-family: 'Lato', sans-serif; font-size: 0.8rem; color: {status_color}; margin-bottom: 0.3rem;" id="share-status">
              Preparing shareable URL...
            </div>
            <input
              id="share-url"
              readonly
              onclick="this.select();"
              style="width: 100%; font-size: 0.78rem; padding: 0.25rem 0.35rem; border: 1px solid {input_border}; border-radius: 4px; background: {input_bg}; color: {input_text};"
            />
            """,
            height=72,
        )


def render_trust_metadata_strip(
    page_key: str,
    projects: pd.DataFrame,
    filtered: pd.DataFrame,
    quality_report: dict[str, Any],
) -> None:
    return


def set_filter_to_all(projects: pd.DataFrame, field: str) -> None:
    options = _build_filter_options(projects)
    _queue_filter_updates({field: options.get(field, [])})


def set_filter_values(field: str, values: list[Any]) -> None:
    _queue_filter_updates({field: values})


def reset_all_filters(projects: pd.DataFrame) -> None:
    options = _build_filter_options(projects)
    _queue_filter_updates({field: values for field, values in options.items()})


def render_current_view_bar(projects: pd.DataFrame) -> None:
    options = _build_filter_options(projects)

    filter_meta = [
        ("year", "Year"),
        ("finance_type", "Type"),
        ("sector", "Sector"),
        ("province", "Province"),
    ]

    active_entries: list[tuple[str, str, str]] = []
    for field, label in filter_meta:
        all_values = options.get(field, [])
        selected = st.session_state.get(f"global_filter_{field}", list(all_values))
        if not all_values or not selected:
            continue
        if set(selected) == set(all_values):
            continue

        if field == "year":
            display = f"{min(selected)}-{max(selected)}" if len(selected) > 1 else str(selected[0])
        else:
            display = ", ".join(str(item) for item in selected[:2])
            if len(selected) > 2:
                display = f"{display} +{len(selected) - 2}"
        active_entries.append((field, label, display))

    with st.container():
        st.markdown('<div class="current-view-sticky">', unsafe_allow_html=True)
        st.markdown("**Current View**")
        if active_entries:
            pills = "".join(
                f'<span class="current-view-pill">{label}: {value}</span>'
                for _, label, value in active_entries
            )
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("All key filters are currently set to full scope.")

        button_cols = st.columns(max(1, len(active_entries) + 1))
        for index, (field, label, _) in enumerate(active_entries):
            if button_cols[index].button(f"Clear {label}", key=f"clear_pill_{field}"):
                set_filter_to_all(projects, field)
                st.rerun()
        if button_cols[-1].button("Reset all filters", key="reset_all_pills"):
            reset_all_filters(projects)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_global_sidebar_filters(
    projects: pd.DataFrame,
    *,
    show_finance_type: bool = True,
) -> dict[str, list[Any]]:
    apply_global_styles()

    options = _build_filter_options(projects)
    _init_filter_state(options)
    _apply_query_param_overrides_once(options, include_finance_type=show_finance_type)
    _apply_queued_filter_updates(options)

    st.sidebar.header("Global Filters")
    if st.sidebar.button("Reset all filters"):
        _reset_filter_state(options)
        st.rerun()

    years = st.sidebar.multiselect(
        "Year",
        options["year"],
        key="global_filter_year",
    )
    if show_finance_type:
        finance_types = st.sidebar.multiselect(
            "Finance Type",
            options["finance_type"],
            key="global_filter_finance_type",
        )
    else:
        finance_types = list(options["finance_type"])
        st.session_state["global_filter_finance_type"] = list(options["finance_type"])
    sectors = st.sidebar.multiselect(
        "Sector",
        options["sector"],
        key="global_filter_sector",
    )
    statuses = st.sidebar.multiselect(
        "Status",
        options["status"],
        key="global_filter_status",
    )
    provinces = list(options["province"])
    sponsor_types = list(options["sponsor_type"])
    st.session_state["global_filter_province"] = list(options["province"])
    st.session_state["global_filter_sponsor_type"] = list(options["sponsor_type"])

    filters = {
        "year": years,
        "finance_type": finance_types,
        "sector": sectors,
        "province": provinces,
        "status": statuses,
        "sponsor_type": sponsor_types,
    }
    _sync_filters_to_query_params(filters, options)

    return filters


def apply_global_filters(projects: pd.DataFrame, filters: dict[str, list[Any]]) -> pd.DataFrame:
    if projects.empty:
        return projects

    filtered = projects.copy()
    options = _build_filter_options(projects)

    if "year" in filtered.columns:
        filtered_year = pd.to_numeric(filtered["year"], errors="coerce").astype("Int64")
        selected_years = _as_int_list(filters.get("year", []))
        all_years = _as_int_list(options["year"])
        if selected_years and set(selected_years) != set(all_years):
            filtered = filtered[filtered_year.isin(selected_years)]

    if "finance_type" in filtered.columns:
        selected_finance = [str(value).upper() for value in filters.get("finance_type", [])]
        all_finance = [str(value).upper() for value in options["finance_type"]]
        if selected_finance and set(selected_finance) != set(all_finance):
            finance_series = filtered["finance_type"].astype("string").str.upper()
            filtered = filtered[finance_series.isin(selected_finance)]

    if "sector" in filtered.columns:
        selected_sector = [str(value) for value in filters.get("sector", [])]
        all_sector = [str(value) for value in options["sector"]]
        if selected_sector and set(selected_sector) != set(all_sector):
            filtered = filtered[filtered["sector"].isin(selected_sector)]

    for field in ["province", "status", "sponsor_type"]:
        if field in filtered.columns:
            selected = [str(value) for value in filters.get(field, [])]
            all_values = [str(value) for value in options[field]]
            if selected and set(selected) != set(all_values):
                filtered = filtered[filtered[field].isin(selected)]

    return filtered


def render_data_quality_panel(projects: pd.DataFrame, quality_report: dict[str, Any]) -> None:
    return
