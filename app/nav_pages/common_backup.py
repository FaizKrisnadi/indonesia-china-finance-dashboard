from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from app.sections import filter_by_locked_type
    from app.shared import (
        apply_global_filters,
        format_currency,
        format_pct,
        get_filter_options_from_projects,
        load_data_quality_cached,
        load_projects_cached,
        render_current_view_bar,
        render_data_quality_panel,
        render_global_sidebar_filters,
        render_trust_metadata_strip,
        set_filter_values,
    )
except ModuleNotFoundError:
    from sections import filter_by_locked_type
    from shared import (
        apply_global_filters,
        format_currency,
        format_pct,
        get_filter_options_from_projects,
        load_data_quality_cached,
        load_projects_cached,
        render_current_view_bar,
        render_data_quality_panel,
        render_global_sidebar_filters,
        render_trust_metadata_strip,
        set_filter_values,
    )

try:
    from src.metrics import (
        add_time_to_implementation_days,
        overall_realization_rate,
        sector_concentration_shares,
    )
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.metrics import (
        add_time_to_implementation_days,
        overall_realization_rate,
        sector_concentration_shares,
    )

SectionRenderer = Callable[[pd.DataFrame], None]


def _load_page_state(show_finance_type: bool) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, list[Any]]]:
    projects = load_projects_cached()
    quality_report = load_data_quality_cached()
    filters = render_global_sidebar_filters(projects, show_finance_type=show_finance_type)
    render_current_view_bar(projects)
    filtered = apply_global_filters(projects, filters)
    return projects, filtered, quality_report, filters


def render_home_page() -> None:
    st.title("Home")
    st.caption(
        "Portfolio-grade monitoring of project pipeline, realization, spatial exposure, and delivery risk."
    )

    projects, filtered, quality_report, filters = _load_page_state(show_finance_type=True)

    if projects.empty:
        st.warning(
            "No processed dataset detected. Add source files to `data/raw`, run `make etl`, "
            "then refresh the app."
        )
        render_data_quality_panel(projects, quality_report)
        return

    render_trust_metadata_strip("home", projects, filtered, quality_report)
    st.info("Detailed analysis is split into dedicated sidebar sections: Development Finance and FDI.")

    options = get_filter_options_from_projects(projects)
    if filtered.empty:
        st.info("No records match the current sidebar filters.")
        narrowed: list[str] = []
        for field, label in [
            ("year", "Year"),
            ("finance_type", "Finance Type"),
            ("sector", "Sector"),
            ("province", "Province"),
            ("status", "Status"),
            ("sponsor_type", "Sponsor Type"),
        ]:
            selected = filters.get(field, [])
            all_values = options.get(field, [])
            if selected and all_values and set(selected) != set(all_values):
                narrowed.append(f"{label}: {', '.join(str(item) for item in selected[:4])}")

        if narrowed:
            st.caption("Filters currently narrowing results:")
            for item in narrowed:
                st.markdown(f"- {item}")

        recovery_col1, recovery_col2, recovery_col3 = st.columns(3)
        if recovery_col1.button("Show all years", key="recover_years"):
            set_filter_values("year", options.get("year", []))
            st.rerun()
        if recovery_col2.button("Show all sectors", key="recover_sectors"):
            set_filter_values("sector", options.get("sector", []))
            st.rerun()
        if recovery_col3.button("Show both finance types", key="recover_types"):
            set_filter_values("finance_type", options.get("finance_type", []))
            st.rerun()

        render_data_quality_panel(projects, quality_report)
        return

    finance_series = filtered["finance_type"].astype("string").str.upper()
    df_projects_count = int(finance_series.eq("DF").sum())
    fdi_projects_count = int(finance_series.eq("FDI").sum())

    committed_total = pd.to_numeric(filtered["committed_usd"], errors="coerce").sum(min_count=1)
    disbursed_total = pd.to_numeric(filtered["disbursed_usd"], errors="coerce").sum(min_count=1)
    realization_rate = overall_realization_rate(filtered)
    implementation_days = add_time_to_implementation_days(filtered)["time_to_implementation_days"]
    median_implementation = pd.to_numeric(implementation_days, errors="coerce").median()

    card_1, card_2, card_3, card_4 = st.columns(4)
    card_1.metric("Projects", f"{len(filtered):,}")
    card_2.metric("Committed Capital", format_currency(committed_total))
    card_3.metric("Disbursed Capital", format_currency(disbursed_total))
    card_4.metric(
        "Median Time to Implementation",
        f"{median_implementation:,.0f} days" if pd.notna(median_implementation) else "N/A",
    )

    df_card, fdi_card = st.columns(2)
    df_card.metric("DF Projects", f"{df_projects_count:,}")
    fdi_card.metric("FDI Projects", f"{fdi_projects_count:,}")
    st.metric("Portfolio Realization Rate", format_pct(realization_rate))

    trend_year = filtered["year"]
    if trend_year.dropna().empty:
        trend_year = pd.to_datetime(filtered["approval_date"], errors="coerce").dt.year

    trend = pd.DataFrame(
        {
            "year": pd.to_numeric(trend_year, errors="coerce"),
            "committed_usd": pd.to_numeric(filtered["committed_usd"], errors="coerce"),
            "disbursed_usd": pd.to_numeric(filtered["disbursed_usd"], errors="coerce"),
        }
    ).dropna(subset=["year"])

    left_col, right_col = st.columns((2, 1))
    with left_col:
        st.subheader("Capital Trend")
        if trend.empty:
            st.info("Year field is unavailable for current records.")
        else:
            yearly = (
                trend.groupby("year", as_index=False)[["committed_usd", "disbursed_usd"]]
                .sum(min_count=1)
                .sort_values("year")
            )
            trend_long = yearly.melt(
                id_vars="year",
                value_vars=["committed_usd", "disbursed_usd"],
                var_name="metric",
                value_name="usd",
            )
            trend_fig = px.line(
                trend_long,
                x="year",
                y="usd",
                color="metric",
                markers=True,
                labels={"year": "Year", "usd": "USD", "metric": "Series"},
            )
            trend_fig.update_layout(legend_title_text="")
            st.plotly_chart(trend_fig, width="stretch")

    with right_col:
        st.subheader("Sector Concentration")
        concentration = sector_concentration_shares(filtered)
        if concentration.empty:
            st.info("Sector and committed values are missing.")
        else:
            concentration_fig = px.pie(
                concentration,
                names="sector",
                values="value",
                hole=0.45,
            )
            concentration_fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(concentration_fig, width="stretch")

    render_data_quality_panel(projects, quality_report)


def render_locked_section_page(
    *,
    page_title: str,
    locked_type: str,
    page_key: str,
    renderer: SectionRenderer,
) -> None:
    st.title(page_title)

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning(
            "No processed dataset detected. Add source files to `data/raw`, run `make etl`, "
            "then refresh the app."
        )
        render_data_quality_panel(projects, quality_report)
        return

    locked_frame = filter_by_locked_type(filtered, locked_type)
    st.caption(f"Active view: Finance Type = {locked_type} (locked)")
    render_trust_metadata_strip(page_key, projects, locked_frame, quality_report)
    renderer(locked_frame)
    render_data_quality_panel(projects, quality_report)


def _prepare_fdi_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    analysis = frame.copy()
    analysis["year_num"] = pd.to_numeric(analysis.get("year"), errors="coerce")
    analysis["committed_usd_num"] = pd.to_numeric(analysis.get("committed_usd"), errors="coerce")
    return analysis


def _render_locked_fdi_page_header(
    page_title: str,
    page_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    st.title(page_title)
    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning(
            "No processed dataset detected. Add source files to `data/raw`, run `make etl`, "
            "then refresh the app."
        )
        render_data_quality_panel(projects, quality_report)
        return projects, filtered.iloc[0:0], quality_report

    locked_frame = filter_by_locked_type(filtered, "FDI")
    st.caption("Active view: Finance Type = FDI (locked)")
    render_trust_metadata_strip(page_key, projects, locked_frame, quality_report)
    return projects, locked_frame, quality_report


def render_fdi_overview_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Overview",
        page_key="overview",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)
    year_values = analysis["year_num"].dropna().astype(int)
    active_year_range = "N/A"
    if not year_values.empty:
        active_year_range = f"{int(year_values.min())} - {int(year_values.max())}"

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("Projects", f"{len(analysis):,}")
    kpi_col2.metric(
        "Total Committed USD",
        format_currency(analysis["committed_usd_num"].sum(min_count=1)),
    )
    median_committed = analysis["committed_usd_num"].median()
    kpi_col3.metric(
        "Median Committed USD",
        format_currency(median_committed) if pd.notna(median_committed) else "N/A",
    )
    kpi_col4.metric("Active Year Range", active_year_range)

    st.subheader("Yearly Project Count")
    yearly_count = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)
        .size()
        .rename(columns={"size": "projects"})
        .sort_values("year_num")
    )
    if yearly_count.empty:
        st.info("Year values are unavailable for the selected FDI records.")
    else:
        yearly_count["year_num"] = yearly_count["year_num"].astype(int)
        yearly_count_fig = px.bar(
            yearly_count,
            x="year_num",
            y="projects",
            labels={"year_num": "Year", "projects": "Projects"},
        )
        st.plotly_chart(
            yearly_count_fig,
            width="stretch",
            key="fdi_overview_yearly_project_count",
        )

    st.subheader("Yearly Committed USD")
    yearly_committed = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)["committed_usd_num"]
        .sum(min_count=1)
        .sort_values("year_num")
    )
    yearly_committed = yearly_committed.dropna(subset=["committed_usd_num"])
    if yearly_committed.empty:
        st.info("Committed USD values are unavailable for yearly aggregation.")
    else:
        yearly_committed["year_num"] = yearly_committed["year_num"].astype(int)
        yearly_committed_fig = px.area(
            yearly_committed,
            x="year_num",
            y="committed_usd_num",
            labels={"year_num": "Year", "committed_usd_num": "Committed USD"},
        )
        st.plotly_chart(
            yearly_committed_fig,
            width="stretch",
            key="fdi_overview_yearly_committed_usd",
        )

    render_data_quality_panel(projects, quality_report)


def render_fdi_trends_and_sectors_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Trends & Sectors",
        page_key="overview",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)
    analysis["sector_clean"] = (
        analysis["sector"].astype("string").fillna("Unknown").str.strip().replace({"": "Unknown"})
    )

    top_sector_count = (
        analysis.groupby("sector_clean", dropna=False)
        .size()
        .reset_index(name="projects")
        .sort_values("projects", ascending=False)
        .head(15)
    )
    st.subheader("Top Sectors by Project Count")
    sector_count_fig = px.bar(
        top_sector_count.sort_values("projects"),
        x="projects",
        y="sector_clean",
        orientation="h",
        labels={"projects": "Projects", "sector_clean": "Sector"},
    )
    st.plotly_chart(
        sector_count_fig,
        width="stretch",
        key="fdi_trends_top_sector_project_count",
    )

    top_sector_committed = (
        analysis.groupby("sector_clean", dropna=False)["committed_usd_num"]
        .sum(min_count=1)
        .reset_index()
        .dropna(subset=["committed_usd_num"])
        .sort_values("committed_usd_num", ascending=False)
        .head(15)
    )
    st.subheader("Top Sectors by Committed USD")
    if top_sector_committed.empty:
        st.info("Committed USD values are unavailable for sector ranking.")
    else:
        sector_committed_fig = px.bar(
            top_sector_committed.sort_values("committed_usd_num"),
            x="committed_usd_num",
            y="sector_clean",
            orientation="h",
            labels={"committed_usd_num": "Committed USD", "sector_clean": "Sector"},
        )
        st.plotly_chart(
            sector_committed_fig,
            width="stretch",
            key="fdi_trends_top_sector_committed_usd",
        )

        sector_share_fig = px.pie(
            top_sector_committed,
            names="sector_clean",
            values="committed_usd_num",
            hole=0.45,
        )
        sector_share_fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(
            sector_share_fig,
            width="stretch",
            key="fdi_trends_sector_share",
        )

    status_non_null_pct = float(
        (
            analysis["status"].astype("string").str.strip().replace({"": pd.NA}).notna().mean()
            * 100
        ).round(1)
    )
    if status_non_null_pct >= 40:
        status_counts = (
            analysis["status"]
            .astype("string")
            .fillna("Unknown")
            .str.strip()
            .replace({"": "Unknown"})
            .value_counts(dropna=False)
            .rename_axis("status")
            .reset_index(name="projects")
        )
        status_fig = px.bar(
            status_counts.sort_values("projects"),
            x="projects",
            y="status",
            orientation="h",
            labels={"projects": "Projects", "status": "Status"},
        )
        st.plotly_chart(status_fig, width="stretch", key="fdi_trends_status_mix")
    else:
        st.info(
            f"Status coverage is {status_non_null_pct:.1f}%; status mix is hidden for this FDI view."
        )

    render_data_quality_panel(projects, quality_report)


def render_fdi_top_deals_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Top Deals",
        page_key="overview",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)
    committed_values = analysis["committed_usd_num"].dropna()
    st.subheader("Committed USD Distribution")
    if committed_values.empty:
        st.info("Committed USD values are unavailable for distribution analysis.")
    else:
        committed_hist = px.histogram(
            committed_values,
            nbins=30,
            labels={"value": "Committed USD"},
        )
        committed_hist.update_layout(xaxis_title="Committed USD", yaxis_title="Projects")
        st.plotly_chart(
            committed_hist,
            width="stretch",
            key="fdi_top_deals_committed_distribution",
        )

    table_columns = ["project_name", "year", "sector", "committed_usd"]
    if "source_file" in analysis.columns:
        table_columns.append("source_file")

    top_deals = analysis.loc[:, table_columns].copy()
    top_deals["committed_usd_num"] = analysis["committed_usd_num"]
    top_deals = top_deals.sort_values("committed_usd_num", ascending=False).head(20)
    top_deals = top_deals.drop(columns=["committed_usd_num"])
    top_deals["committed_usd"] = pd.to_numeric(top_deals["committed_usd"], errors="coerce").apply(
        format_currency
    )

    st.markdown("**Top 20 Deals**")
    st.dataframe(top_deals, width="stretch", hide_index=True)

    render_data_quality_panel(projects, quality_report)


def render_fdi_data_coverage_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Data Coverage",
        page_key="impact_friction",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    key_fields = [
        "project_id",
        "project_name",
        "year",
        "sector",
        "committed_usd",
        "province",
        "latitude",
        "longitude",
        "approval_date",
        "disbursed_usd",
        "status",
    ]

    rows: list[dict[str, Any]] = []
    total = len(locked_frame)
    for field in key_fields:
        if field in locked_frame.columns:
            series = locked_frame[field]
            if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
                non_null_mask = series.notna()
            else:
                non_null_mask = series.astype("string").str.strip().replace({"": pd.NA}).notna()
            non_null_count = int(non_null_mask.sum())
        else:
            non_null_count = 0
        missing_count = total - non_null_count
        non_null_pct = (non_null_count / total * 100) if total else 0.0
        missing_pct = 100 - non_null_pct
        rows.append(
            {
                "field": field,
                "non_null_pct": round(non_null_pct, 1),
                "missing_pct": round(missing_pct, 1),
                "non_null_count": non_null_count,
                "missing_count": missing_count,
            }
        )

    coverage = pd.DataFrame(rows).sort_values("missing_pct", ascending=False).reset_index(drop=True)
    st.dataframe(coverage, width="stretch", hide_index=True)
    st.caption(
        "FDI source coverage differs from DF; unavailable fields are hidden from analysis pages."
    )

    render_data_quality_panel(projects, quality_report)


def render_fdi_region_distribution_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Regional Distribution",
        page_key="spatial",
    )
    if projects.empty:
        return

    if locked_frame.empty:
        st.info(
            "No FDI project records match current filters. "
            "Regional CAPEX distribution is shown from the embedded regional dataset."
        )

    st.caption(
        "Chinese inbound FDI commitments by region (CAPEX, constant 2024 USD, billions). "
        "Source: fDi Markets (Financial Times)."
    )

    data = [
        {
            "region": "Java",
            "included_provinces": (
                "Banten, Central Java, East Java, DKI Jakarta, DI Yogyakarta, West Java"
            ),
            "china_capex_2024usd_b": 20.75,
            "all_source_capex_2024usd_b": 181.10,
        },
        {
            "region": "Kalimantan",
            "included_provinces": "Central, East, North, South, West Kalimantan",
            "china_capex_2024usd_b": 11.21,
            "all_source_capex_2024usd_b": 28.07,
        },
        {
            "region": "Maluku",
            "included_provinces": "Maluku, North Maluku",
            "china_capex_2024usd_b": 7.58,
            "all_source_capex_2024usd_b": 12.87,
        },
        {
            "region": "Nusa Tenggara",
            "included_provinces": "Bali, West Nusa Tenggara, East Nusa Tenggara",
            "china_capex_2024usd_b": 0.77,
            "all_source_capex_2024usd_b": 10.01,
        },
        {
            "region": "Papua",
            "included_provinces": "Central, Highland, Papua, South, Southwest, West Papua",
            "china_capex_2024usd_b": 0.60,
            "all_source_capex_2024usd_b": 2.62,
        },
        {
            "region": "Sulawesi",
            "included_provinces": "Central, Gorontalo, North, South, Southeast, West Sulawesi",
            "china_capex_2024usd_b": 13.24,
            "all_source_capex_2024usd_b": 36.01,
        },
        {
            "region": "Sumatra",
            "included_provinces": (
                "Aceh, Babel, Bengkulu, Jambi, Lampung, North Sumatra, Riau, "
                "Kepri, South Sumatra, West Sumatra"
            ),
            "china_capex_2024usd_b": 26.06,
            "all_source_capex_2024usd_b": 46.70,
        },
        {
            "region": "Not Specified",
            "included_provinces": "NA",
            "china_capex_2024usd_b": 13.92,
            "all_source_capex_2024usd_b": 95.41,
        },
    ]
    df = pd.DataFrame(data)

    total_china = df["china_capex_2024usd_b"].sum()
    not_spec = df.loc[df["region"] == "Not Specified", "china_capex_2024usd_b"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total China CAPEX (bn, 2024 USD)", f"{total_china:,.2f}")
    c2.metric("Location not specified (bn)", f"{not_spec:,.2f}")
    c3.metric("Share not specified", f"{(not_spec / total_china) * 100:,.1f}%")

    st.divider()

    include_unspecified = st.toggle(
        "Include 'Not Specified' in charts",
        value=True,
        key="fdi_region_include_unspecified",
    )

    plot_df = df.copy()
    if not include_unspecified:
        plot_df = plot_df[plot_df["region"] != "Not Specified"].copy()

    plot_df = plot_df.sort_values("china_capex_2024usd_b", ascending=False)

    fig = px.bar(
        plot_df,
        x="region",
        y="china_capex_2024usd_b",
        text=plot_df["china_capex_2024usd_b"].map(lambda x: f"{x:.2f}"),
        labels={"china_capex_2024usd_b": "China CAPEX (bn, constant 2024 USD)", "region": "Region"},
        title="Chinese FDI CAPEX by Region",
    )
    fig.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(fig, width="stretch", key="fdi_region_capex_by_region")

    fig2 = px.pie(
        plot_df,
        names="region",
        values="china_capex_2024usd_b",
        title="Share of Chinese FDI CAPEX by Region",
    )
    st.plotly_chart(fig2, width="stretch", key="fdi_region_capex_share")

    st.subheader("Underlying table")
    show_context = st.toggle(
        "Show all-source CAPEX column (context only)",
        value=False,
        key="fdi_region_show_context",
    )
    if not show_context:
        st.dataframe(
            df[["region", "included_provinces", "china_capex_2024usd_b"]],
            width="stretch",
        )
    else:
        df2 = df.copy()
        df2["china_share_of_all_sources"] = (
            df2["china_capex_2024usd_b"] / df2["all_source_capex_2024usd_b"]
        )
        st.dataframe(
            df2[
                [
                    "region",
                    "included_provinces",
                    "china_capex_2024usd_b",
                    "all_source_capex_2024usd_b",
                    "china_share_of_all_sources",
                ]
            ],
            width="stretch",
        )

    st.caption(
        "Notes: Regions are aggregates of provinces; several projects have no specified location. "
        "CAPEX is reported in billions of constant 2024 USD."
    )

    render_data_quality_panel(projects, quality_report)
