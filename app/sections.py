from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

try:
    from app.shared import format_currency, format_pct
except ModuleNotFoundError:
    from shared import format_currency, format_pct

try:
    from src.metrics import (
        add_realization_rate,
        add_time_to_implementation_days,
        approval_cohorts,
        compute_status_risk_index,
        delay_distribution,
        lifecycle_funnel,
        overall_realization_rate,
        province_year_exposure,
        status_mix,
        summarize_exposure_vs_friction,
    )
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.metrics import (
        add_realization_rate,
        add_time_to_implementation_days,
        approval_cohorts,
        compute_status_risk_index,
        delay_distribution,
        lifecycle_funnel,
        overall_realization_rate,
        province_year_exposure,
        status_mix,
        summarize_exposure_vs_friction,
    )


def render_overview_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    kpi_frame = add_time_to_implementation_days(add_realization_rate(filtered))
    committed_total = pd.to_numeric(kpi_frame["committed_usd"], errors="coerce").sum(min_count=1)
    disbursed_total = pd.to_numeric(kpi_frame["disbursed_usd"], errors="coerce").sum(min_count=1)
    portfolio_realization = overall_realization_rate(kpi_frame)
    avg_project_realization = pd.to_numeric(kpi_frame["realization_rate"], errors="coerce").mean()
    median_implementation = pd.to_numeric(
        kpi_frame["time_to_implementation_days"], errors="coerce"
    ).median()
    portfolio_risk_index = compute_status_risk_index(kpi_frame)

    cards = st.columns(5)
    cards[0].metric("Projects", f"{len(kpi_frame):,}")
    cards[1].metric("Committed", format_currency(committed_total))
    cards[2].metric("Disbursed", format_currency(disbursed_total))
    cards[3].metric("Portfolio Realization", format_pct(portfolio_realization))
    cards[4].metric(
        "Status Risk Index",
        f"{portfolio_risk_index:,.1f}" if portfolio_risk_index is not None else "N/A",
    )

    median_implementation_label = (
        f"{median_implementation:,.0f} days" if pd.notna(median_implementation) else "N/A"
    )
    st.caption(
        "Average project realization: "
        f"{format_pct(avg_project_realization)} | "
        f"Median implementation time: {median_implementation_label}"
    )

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
        st.subheader("Committed vs Disbursed Trend")
        if trend.empty:
            st.info("Trend view unavailable because year values are missing.")
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
            fig = px.area(
                trend_long,
                x="year",
                y="usd",
                color="metric",
                labels={"year": "Year", "usd": "USD", "metric": "Series"},
            )
            fig.update_layout(legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.subheader("Status Mix")
        status_frame = status_mix(filtered)
        if status_frame.empty:
            st.info("Status values are missing.")
        else:
            status_fig = px.bar(
                status_frame,
                x="projects",
                y="status",
                orientation="h",
                labels={"projects": "Projects", "status": "Status"},
            )
            status_fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(status_fig, use_container_width=True)

    province_table = (
        filtered.groupby("province", as_index=False)
        .agg(
            projects=("project_id", "size"),
            committed_usd=("committed_usd", "sum"),
            disbursed_usd=("disbursed_usd", "sum"),
        )
        .sort_values("disbursed_usd", ascending=False)
    )
    if not province_table.empty:
        st.subheader("Top Provinces by Disbursed Capital")
        province_table["committed_usd"] = province_table["committed_usd"].apply(format_currency)
        province_table["disbursed_usd"] = province_table["disbursed_usd"].apply(format_currency)
        st.dataframe(province_table.head(10), use_container_width=True, hide_index=True)


def render_spatial_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    analysis_frame = filtered.copy()
    analysis_frame["latitude"] = pd.to_numeric(analysis_frame["latitude"], errors="coerce")
    analysis_frame["longitude"] = pd.to_numeric(analysis_frame["longitude"], errors="coerce")
    analysis_frame["disbursed_usd"] = pd.to_numeric(analysis_frame["disbursed_usd"], errors="coerce")
    analysis_frame["committed_usd"] = pd.to_numeric(analysis_frame["committed_usd"], errors="coerce")

    approval_date = pd.to_datetime(analysis_frame["approval_date"], errors="coerce")
    year_fallback = pd.to_datetime(
        pd.to_numeric(analysis_frame["year"], errors="coerce").astype("Int64").astype("string")
        + "-01-01",
        errors="coerce",
    )
    analysis_frame["plotting_date"] = approval_date.fillna(year_fallback)

    coordinate_mask = analysis_frame["latitude"].notna() & analysis_frame["longitude"].notna()
    province_mask = (
        analysis_frame["province"].astype("string").str.strip().replace({"": pd.NA}).notna()
    )

    coordinate_coverage_pct = float(coordinate_mask.mean() * 100)
    province_coverage_pct = float(province_mask.mean() * 100)

    coverage_col1, coverage_col2 = st.columns(2)
    coverage_col1.metric("Coordinate Coverage", f"{coordinate_coverage_pct:,.1f}%")
    coverage_col2.metric("Province Coverage", f"{province_coverage_pct:,.1f}%")

    map_frame = analysis_frame.loc[coordinate_mask].copy()

    def _render_fallback_views(frame: pd.DataFrame) -> None:
        fallback_left, fallback_right = st.columns(2)
        with fallback_left:
            sector_counts = (
                frame["sector"]
                .astype("string")
                .fillna("Unknown")
                .value_counts(dropna=False)
                .rename_axis("sector")
                .reset_index(name="projects")
            )
            sector_fig = px.bar(
                sector_counts,
                x="projects",
                y="sector",
                orientation="h",
                labels={"projects": "Projects", "sector": "Sector"},
            )
            sector_fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(sector_fig, use_container_width=True)

        with fallback_right:
            status_counts = (
                frame["status"]
                .astype("string")
                .fillna("Unknown")
                .value_counts(dropna=False)
                .rename_axis("status")
                .reset_index(name="projects")
            )
            status_fig = px.bar(
                status_counts,
                x="projects",
                y="status",
                orientation="h",
                labels={"projects": "Projects", "status": "Status"},
            )
            status_fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(status_fig, use_container_width=True)

        top_projects = frame[["project_name", "finance_type", "year", "committed_usd", "status"]].copy()
        top_projects["project_name"] = top_projects["project_name"].fillna("Unnamed Project")
        top_projects["status"] = top_projects["status"].fillna("Unknown")
        top_projects = top_projects.sort_values("committed_usd", ascending=False).head(20)
        top_projects["committed_usd"] = top_projects["committed_usd"].apply(format_currency)

        st.markdown("**Top 20 Projects**")
        st.dataframe(top_projects, use_container_width=True, hide_index=True)

    if coordinate_coverage_pct == 0:
        st.info("No project coordinates available in current sources.")
        st.subheader("Fallback Views")
        _render_fallback_views(analysis_frame)
        return

    st.subheader("Project Point Map")
    view_state = pdk.ViewState(
        latitude=float(map_frame["latitude"].mean()),
        longitude=float(map_frame["longitude"].mean()),
        zoom=4.3,
        pitch=32,
    )
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_frame,
        get_position="[longitude, latitude]",
        get_radius=5000,
        radius_min_pixels=3,
        get_fill_color=[25, 118, 210, 170],
        pickable=True,
    )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=view_state,
        layers=[point_layer],
        tooltip={
            "html": (
                "<b>{project_name}</b><br/>"
                "Finance Type: {finance_type}<br/>"
                "Province: {province}<br/>"
                "Status: {status}"
            )
        },
    )
    st.pydeck_chart(deck, use_container_width=True)

    left_col, right_col = st.columns((1, 1))
    with left_col:
        st.subheader("Province-Year Exposure")
        exposure = province_year_exposure(analysis_frame)
        if exposure.empty:
            st.info("Exposure cannot be computed because province/year data is missing.")
        else:
            exposure_fig = px.bar(
                exposure,
                x="year",
                y="province_year_exposure",
                color="province",
                labels={
                    "year": "Year",
                    "province_year_exposure": "Active Disbursed USD",
                    "province": "Province",
                },
            )
            st.plotly_chart(exposure_fig, use_container_width=True)

        st.subheader("Project Timeline")
        timeline = analysis_frame.dropna(subset=["plotting_date"]).copy()
        if timeline.empty:
            st.info("No approval dates or year fallback available for timeline chart.")
        else:
            timeline["period"] = timeline["plotting_date"].dt.to_period("Y").dt.to_timestamp()
            timeline_counts = (
                timeline.groupby("period", as_index=False)
                .size()
                .rename(columns={"size": "projects"})
                .sort_values("period")
            )
            timeline_fig = px.line(
                timeline_counts,
                x="period",
                y="projects",
                markers=True,
                labels={"period": "Plotting Date", "projects": "Projects"},
            )
            st.plotly_chart(timeline_fig, use_container_width=True)

    with right_col:
        st.subheader("Project Drilldown")
        if analysis_frame["project_name"].dropna().empty:
            st.info("Project names are missing in the filtered data.")
        else:
            drilldown_label = (
                analysis_frame["project_name"].fillna("Unnamed Project")
                + " ("
                + analysis_frame["province"].fillna("Unknown Province")
                + ")"
            )
            selectable = analysis_frame.assign(_label=drilldown_label)
            selected_label = st.selectbox("Select a project", selectable["_label"].tolist())
            project_row = selectable[selectable["_label"] == selected_label].iloc[0]

            details = pd.DataFrame(
                {
                    "field": [
                        "Project ID",
                        "Project Name",
                        "Finance Type",
                        "Sector",
                        "Province",
                        "District",
                        "Status",
                        "Committed USD",
                        "Disbursed USD",
                        "Approval Date",
                        "Operation Date",
                    ],
                    "value": [
                        project_row.get("project_id"),
                        project_row.get("project_name"),
                        project_row.get("finance_type"),
                        project_row.get("sector"),
                        project_row.get("province"),
                        project_row.get("district"),
                        project_row.get("status"),
                        format_currency(project_row.get("committed_usd")),
                        format_currency(project_row.get("disbursed_usd")),
                        project_row.get("approval_date"),
                        project_row.get("operation_date"),
                    ],
                }
            )
            st.dataframe(details, use_container_width=True, hide_index=True)

    if coordinate_coverage_pct < 40:
        st.subheader("Fallback Views (Low Coordinate Coverage)")
        st.info("Coordinate coverage is below 40%, so non-spatial fallback visuals are shown.")
        _render_fallback_views(analysis_frame)


def render_finance_and_delivery_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    st.subheader("Lifecycle Funnel")
    funnel = lifecycle_funnel(filtered)
    funnel_fig = px.funnel(
        funnel,
        x="projects",
        y="stage",
        labels={"projects": "Project Count", "stage": "Lifecycle Stage"},
    )
    st.plotly_chart(funnel_fig, use_container_width=True)

    st.subheader("Approval Cohorts")
    cohorts = approval_cohorts(filtered)
    if cohorts.empty:
        st.info("Cohort analysis unavailable because approval dates are missing.")
    else:
        cohort_left, cohort_right = st.columns((1, 1))
        with cohort_left:
            projects_fig = px.bar(
                cohorts,
                x="approval_year",
                y="projects",
                labels={"approval_year": "Approval Year", "projects": "Projects"},
            )
            st.plotly_chart(projects_fig, use_container_width=True)

        with cohort_right:
            realization_fig = px.line(
                cohorts,
                x="approval_year",
                y="avg_realization_rate",
                markers=True,
                labels={
                    "approval_year": "Approval Year",
                    "avg_realization_rate": "Avg. Realization Rate",
                },
            )
            st.plotly_chart(realization_fig, use_container_width=True)

        display_cohorts = cohorts.copy()
        display_cohorts["committed_usd"] = display_cohorts["committed_usd"].apply(format_currency)
        display_cohorts["disbursed_usd"] = display_cohorts["disbursed_usd"].apply(format_currency)
        display_cohorts["avg_realization_rate"] = display_cohorts["avg_realization_rate"].apply(
            format_pct
        )
        st.dataframe(display_cohorts, use_container_width=True, hide_index=True)

    st.subheader("Delay Distribution")
    delays = delay_distribution(filtered)
    if delays.empty:
        st.info("Delay metrics cannot be computed without approval and operation dates.")
    else:
        delay_fig = px.histogram(
            delays,
            nbins=30,
            labels={"value": "Days from Approval to Operation"},
        )
        delay_fig.update_layout(xaxis_title="Days", yaxis_title="Projects")
        st.plotly_chart(delay_fig, use_container_width=True)

        enriched = add_time_to_implementation_days(add_realization_rate(filtered))
        delayed_projects = enriched[
            ["project_name", "province", "status", "time_to_implementation_days", "realization_rate"]
        ].copy()
        delayed_projects["time_to_implementation_days"] = pd.to_numeric(
            delayed_projects["time_to_implementation_days"], errors="coerce"
        )
        delayed_projects["realization_rate"] = delayed_projects["realization_rate"].apply(format_pct)
        delayed_projects = delayed_projects.sort_values(
            "time_to_implementation_days", ascending=False
        ).head(20)
        st.markdown("**Top 20 Longest Implementation Durations**")
        st.dataframe(delayed_projects, use_container_width=True, hide_index=True)


def render_impact_and_friction_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    comparison = summarize_exposure_vs_friction(filtered)
    if comparison.empty:
        st.info("Exposure comparison is unavailable because key fields are missing.")
        return

    st.subheader("Province Exposure vs Friction")
    scatter = px.scatter(
        comparison,
        x="total_exposure",
        y="status_risk_index",
        color="exposure_band",
        hover_name="province",
        size="total_exposure",
        labels={
            "total_exposure": "Total Active Disbursed USD",
            "status_risk_index": "Status Risk Index",
            "exposure_band": "Exposure Band",
        },
    )
    st.plotly_chart(scatter, use_container_width=True)

    band_summary = (
        comparison.groupby("exposure_band", as_index=False)
        .agg(
            provinces=("province", "count"),
            avg_exposure=("total_exposure", "mean"),
            avg_risk_index=("status_risk_index", "mean"),
            avg_realization_rate=("avg_realization_rate", "mean"),
        )
        .sort_values("avg_exposure", ascending=False)
    )

    left_col, right_col = st.columns((1, 1))
    with left_col:
        st.subheader("High vs Low Exposure Comparison")
        compare_chart_data = band_summary.melt(
            id_vars="exposure_band",
            value_vars=["avg_risk_index", "avg_realization_rate"],
            var_name="metric",
            value_name="value",
        )
        comparison_fig = px.bar(
            compare_chart_data,
            x="exposure_band",
            y="value",
            color="metric",
            barmode="group",
            labels={"value": "Value", "exposure_band": "Exposure Band", "metric": "Metric"},
        )
        st.plotly_chart(comparison_fig, use_container_width=True)

    with right_col:
        st.subheader("Province Ranking")
        ranking_fig = px.bar(
            comparison.sort_values("status_risk_index", ascending=False).head(15),
            x="status_risk_index",
            y="province",
            color="exposure_band",
            orientation="h",
            labels={"status_risk_index": "Status Risk Index", "province": "Province"},
        )
        ranking_fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(ranking_fig, use_container_width=True)

    band_summary_display = band_summary.copy()
    band_summary_display["avg_realization_rate"] = band_summary_display["avg_realization_rate"].apply(
        format_pct
    )
    st.dataframe(band_summary_display, use_container_width=True, hide_index=True)


def filter_by_locked_type(frame: pd.DataFrame, locked_type: str) -> pd.DataFrame:
    if frame.empty or "finance_type" not in frame.columns:
        return frame.iloc[0:0]
    finance = frame["finance_type"].astype("string").str.upper()
    return frame[finance.eq(locked_type.upper())].copy()
