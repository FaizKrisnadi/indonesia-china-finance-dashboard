from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

try:
    from app.shared import format_currency, format_pct, load_projects_cached
    from app.theme import (
        MAP_POINT_RGBA,
        QUALITATIVE_SEQUENCE,
        get_plotly_chart_config,
        get_theme_colors,
    )
except ModuleNotFoundError:
    from shared import format_currency, format_pct, load_projects_cached
    from theme import (
        MAP_POINT_RGBA,
        QUALITATIVE_SEQUENCE,
        get_plotly_chart_config,
        get_theme_colors,
    )

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


DF_REPORT_PROJECTS = [
    {"region": "Sumatra", "province_name": "Aceh", "project_value_2024_usd_b": 0.23, "project_count": 12, "per_capita_2024_usd": 42.20},
    {"region": "Nusa Tenggara", "province_name": "Bali", "project_value_2024_usd_b": 0.60, "project_count": 7, "per_capita_2024_usd": 135.07},
    {"region": "Sumatra", "province_name": "Bangka Belitung Islands", "project_value_2024_usd_b": 0.00, "project_count": 0, "per_capita_2024_usd": 0.00},
    {"region": "Java", "province_name": "Banten", "project_value_2024_usd_b": 4.28, "project_count": 22, "per_capita_2024_usd": 344.05},
    {"region": "Sumatra", "province_name": "Bengkulu", "project_value_2024_usd_b": 0.36, "project_count": 3, "per_capita_2024_usd": 168.86},
    {"region": "Java", "province_name": "Central Java", "project_value_2024_usd_b": 5.56, "project_count": 12, "per_capita_2024_usd": 146.75},
    {"region": "Kalimantan", "province_name": "Central Kalimantan", "project_value_2024_usd_b": 0.03, "project_count": 1, "per_capita_2024_usd": 11.01},
    {"region": "Papua", "province_name": "Central Papua", "project_value_2024_usd_b": 0.00, "project_count": 2, "per_capita_2024_usd": None},
    {"region": "Sulawesi", "province_name": "Central Sulawesi", "project_value_2024_usd_b": 5.76, "project_count": 15, "per_capita_2024_usd": 1844.92},
    {"region": "Java", "province_name": "East Java", "project_value_2024_usd_b": 3.42, "project_count": 22, "per_capita_2024_usd": 81.90},
    {"region": "Kalimantan", "province_name": "East Kalimantan", "project_value_2024_usd_b": 0.27, "project_count": 5, "per_capita_2024_usd": 66.51},
    {"region": "Nusa Tenggara", "province_name": "East Nusa Tenggara", "project_value_2024_usd_b": 0.02, "project_count": 2, "per_capita_2024_usd": 4.28},
    {"region": "Sulawesi", "province_name": "Gorontalo", "project_value_2024_usd_b": 0.00, "project_count": 1, "per_capita_2024_usd": 1.30},
    {"region": "Papua", "province_name": "Highland Papua", "project_value_2024_usd_b": 0.00, "project_count": 0, "per_capita_2024_usd": None},
    {"region": "Java", "province_name": "Jakarta Special Capital Region", "project_value_2024_usd_b": 3.53, "project_count": 21, "per_capita_2024_usd": 330.54},
    {"region": "Sumatra", "province_name": "Jambi", "project_value_2024_usd_b": 0.00, "project_count": 1, "per_capita_2024_usd": 0.43},
    {"region": "Sumatra", "province_name": "Lampung", "project_value_2024_usd_b": 0.03, "project_count": 2, "per_capita_2024_usd": 3.24},
    {"region": "Maluku Islands", "province_name": "Maluku", "project_value_2024_usd_b": 0.02, "project_count": 1, "per_capita_2024_usd": 12.38},
    {"region": "Kalimantan", "province_name": "North Kalimantan", "project_value_2024_usd_b": 0.02, "project_count": 1, "per_capita_2024_usd": 21.32},
    {"region": "Maluku Islands", "province_name": "North Maluku", "project_value_2024_usd_b": 0.71, "project_count": 6, "per_capita_2024_usd": 523.21},
    {"region": "Sulawesi", "province_name": "North Sulawesi", "project_value_2024_usd_b": 0.42, "project_count": 6, "per_capita_2024_usd": 155.90},
    {"region": "Sumatra", "province_name": "North Sumatra", "project_value_2024_usd_b": 3.17, "project_count": 25, "per_capita_2024_usd": 203.56},
    {"region": "Papua", "province_name": "Papua", "project_value_2024_usd_b": 0.02, "project_count": 2, "per_capita_2024_usd": 5.31},
    {"region": "Sumatra", "province_name": "Riau", "project_value_2024_usd_b": 0.30, "project_count": 2, "per_capita_2024_usd": 44.36},
    {"region": "Sumatra", "province_name": "Riau Islands", "project_value_2024_usd_b": 0.26, "project_count": 1, "per_capita_2024_usd": 117.18},
    {"region": "Kalimantan", "province_name": "South Kalimantan", "project_value_2024_usd_b": 0.41, "project_count": 4, "per_capita_2024_usd": 94.78},
    {"region": "Papua", "province_name": "South Papua", "project_value_2024_usd_b": 0.00, "project_count": 0, "per_capita_2024_usd": None},
    {"region": "Sulawesi", "province_name": "South Sulawesi", "project_value_2024_usd_b": 0.58, "project_count": 5, "per_capita_2024_usd": 61.32},
    {"region": "Sumatra", "province_name": "South Sumatra", "project_value_2024_usd_b": 7.04, "project_count": 9, "per_capita_2024_usd": 797.14},
    {"region": "Sulawesi", "province_name": "Southeast Sulawesi", "project_value_2024_usd_b": 1.46, "project_count": 2, "per_capita_2024_usd": 521.81},
    {"region": "Papua", "province_name": "Southwest Papua", "project_value_2024_usd_b": 0.00, "project_count": 0, "per_capita_2024_usd": None},
    {"region": "Java", "province_name": "Special Region of Yogyakarta", "project_value_2024_usd_b": 0.01, "project_count": 5, "per_capita_2024_usd": 2.68},
    {"region": "Java", "province_name": "West Java", "project_value_2024_usd_b": 6.58, "project_count": 24, "per_capita_2024_usd": 130.79},
    {"region": "Kalimantan", "province_name": "West Kalimantan", "project_value_2024_usd_b": 0.53, "project_count": 6, "per_capita_2024_usd": 93.18},
    {"region": "Nusa Tenggara", "province_name": "West Nusa Tenggara", "project_value_2024_usd_b": 0.06, "project_count": 3, "per_capita_2024_usd": 11.28},
    {"region": "Papua", "province_name": "West Papua", "project_value_2024_usd_b": 3.69, "project_count": 5, "per_capita_2024_usd": 3063.52},
    {"region": "Sulawesi", "province_name": "West Sulawesi", "project_value_2024_usd_b": 0.00, "project_count": 0, "per_capita_2024_usd": 0.00},
    {"region": "Sumatra", "province_name": "West Sumatra", "project_value_2024_usd_b": 0.23, "project_count": 2, "per_capita_2024_usd": 39.97},
]

DF_PROVINCE_COORD_FALLBACK = {
    "Aceh": (5.55, 95.32),
    "Bali": (-8.65, 115.22),
    "Bangka Belitung Islands": (-2.13, 106.11),
    "Banten": (-6.12, 106.15),
    "Bengkulu": (-3.79, 102.26),
    "Central Java": (-6.99, 110.42),
    "Central Kalimantan": (-2.21, 113.92),
    "Central Papua": (-3.40, 135.50),
    "Central Sulawesi": (-0.89, 119.87),
    "East Java": (-7.25, 112.75),
    "East Kalimantan": (-0.50, 117.15),
    "East Nusa Tenggara": (-10.17, 123.61),
    "Gorontalo": (0.54, 123.06),
    "Highland Papua": (-4.10, 138.90),
    "Jakarta Special Capital Region": (-6.20, 106.82),
    "Jambi": (-1.61, 103.61),
    "Lampung": (-5.43, 105.26),
    "Maluku": (-3.69, 128.18),
    "North Kalimantan": (2.84, 117.37),
    "North Maluku": (0.78, 127.38),
    "North Sulawesi": (1.47, 124.84),
    "North Sumatra": (3.59, 98.67),
    "Papua": (-2.54, 140.71),
    "Riau": (0.53, 101.45),
    "Riau Islands": (0.92, 104.45),
    "South Kalimantan": (-3.31, 114.59),
    "South Papua": (-8.50, 140.40),
    "South Sulawesi": (-5.14, 119.41),
    "South Sumatra": (-2.99, 104.76),
    "Southeast Sulawesi": (-3.99, 122.52),
    "Southwest Papua": (-0.86, 131.25),
    "Special Region of Yogyakarta": (-7.80, 110.37),
    "West Java": (-6.91, 107.61),
    "West Kalimantan": (-0.03, 109.34),
    "West Nusa Tenggara": (-8.58, 116.10),
    "West Papua": (-0.86, 134.08),
    "West Sulawesi": (-2.67, 118.89),
    "West Sumatra": (-0.95, 100.35),
}

DF_REGION_COORD_FALLBACK = {
    "Sumatra": (-0.6, 101.2),
    "Java": (-7.3, 110.2),
    "Kalimantan": (0.3, 114.8),
    "Sulawesi": (-1.3, 121.1),
    "Papua": (-3.9, 136.5),
    "Maluku Islands": (-3.2, 129.1),
    "Nusa Tenggara": (-8.7, 117.8),
}

DF_COORD_ALIAS = {
    "jakarta special capital region": "dki jakarta",
    "special region of yogyakarta": "di yogyakarta",
    "bangka belitung islands": "bangka belitung",
}


def _normalize_text(value: str) -> str:
    return str(value).strip().lower()


def _build_province_coordinate_lookup() -> dict[str, tuple[float, float]]:
    projects = load_projects_cached()
    if projects.empty:
        return {}
    frame = projects.copy()
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame = frame.dropna(subset=["latitude", "longitude"])
    if frame.empty:
        return {}

    frame["province_clean"] = (
        frame["province"].astype("string").str.strip().str.lower().replace({"": pd.NA})
    )
    frame = frame.dropna(subset=["province_clean"])
    centroids = (
        frame.groupby("province_clean", as_index=False)[["latitude", "longitude"]]
        .mean()
        .rename(columns={"latitude": "lat", "longitude": "lon"})
    )
    return {
        row["province_clean"]: (float(row["lat"]), float(row["lon"]))
        for _, row in centroids.iterrows()
    }


def _build_df_report_map_frame() -> pd.DataFrame:
    frame = pd.DataFrame(DF_REPORT_PROJECTS).copy()
    lookup = _build_province_coordinate_lookup()

    lat_values: list[float | None] = []
    lon_values: list[float | None] = []
    for _, row in frame.iterrows():
        province_name = str(row["province_name"])
        normalized = _normalize_text(province_name)
        lookup_key = DF_COORD_ALIAS.get(normalized, normalized)
        coords = lookup.get(lookup_key)
        if coords is None:
            coords = DF_PROVINCE_COORD_FALLBACK.get(province_name)
        if coords is None:
            coords = DF_REGION_COORD_FALLBACK.get(str(row["region"]))

        lat_values.append(coords[0] if coords else None)
        lon_values.append(coords[1] if coords else None)

    frame["lat"] = lat_values
    frame["lon"] = lon_values
    return frame


def _plotly_chart(fig) -> None:
    fig.update_layout(dragmode=False)
    st.plotly_chart(fig, width="stretch", config=get_plotly_chart_config())


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
        _plotly_chart(fig)

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
        _plotly_chart(status_fig)

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
        st.dataframe(province_table.head(10), width="stretch", hide_index=True)


def render_spatial_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    st.subheader("Chinese-funded Development Projects by Province (2000-2023)")

    report_frame = _build_df_report_map_frame()
    show_zero_value = st.toggle(
        "Include provinces with zero reported project value",
        value=True,
        key="df_spatial_include_zero_value",
    )

    map_frame_report = report_frame.copy()
    if not show_zero_value:
        map_frame_report = map_frame_report[map_frame_report["project_value_2024_usd_b"] > 0].copy()
    map_frame_report = map_frame_report.dropna(subset=["lat", "lon"])

    if map_frame_report.empty:
        st.info("No report rows are available for mapping.")
    else:
        map_fig = px.scatter_geo(
            map_frame_report,
            lat="lat",
            lon="lon",
            size="project_value_2024_usd_b",
            color="region",
            hover_name="province_name",
            hover_data={
                "project_value_2024_usd_b": ":.2f",
                "project_count": True,
                "per_capita_2024_usd": ":,.2f",
                "lat": False,
                "lon": False,
            },
            labels={
                "project_value_2024_usd_b": "Project value ($B)",
                "project_count": "Project count",
                "per_capita_2024_usd": "Per-capita USD (2024)",
            },
            color_discrete_sequence=QUALITATIVE_SEQUENCE,
            projection="natural earth",
        )
        map_fig.update_geos(
            fitbounds="locations",
            visible=False,
            showcountries=True,
            countrycolor=get_theme_colors()["geo_country_border"],
            lataxis_range=[-12, 8],
            lonaxis_range=[94, 142],
        )
        map_fig.update_layout(
            margin={"t": 30, "b": 120, "l": 20, "r": 20},
            height=560,
            legend={
                "orientation": "h",
                "x": 0.0,
                "xanchor": "left",
                "y": -0.12,
                "yanchor": "top",
                "title": {"text": "Region"},
            },
        )
        _plotly_chart(map_fig)

    region_summary = (
        report_frame.groupby("region", as_index=False)
        .agg(
            project_value_2024_usd_b=("project_value_2024_usd_b", "sum"),
            project_count=("project_count", "sum"),
        )
        .sort_values("project_value_2024_usd_b", ascending=False)
    )
    region_display = region_summary.rename(
        columns={
            "region": "Region",
            "project_value_2024_usd_b": "Project Value ($B, 2024 USD)",
            "project_count": "Project Count",
        }
    )

    province_display = report_frame.rename(
        columns={
            "region": "Region",
            "province_name": "Province",
            "project_value_2024_usd_b": "Project Value ($B, 2024 USD)",
            "project_count": "Project Count",
            "per_capita_2024_usd": "Per Capita (USD, 2024)",
        }
    )
    province_display["Per Capita (USD, 2024)"] = province_display["Per Capita (USD, 2024)"].apply(
        lambda value: "Missing population data"
        if pd.isna(value)
        else f"{float(value):,.2f}"
    )

    st.markdown("**Regional Breakdown (Report Table)**")
    st.dataframe(region_display, width="stretch", hide_index=True)
    st.markdown("**Province Breakdown (Report Table)**")
    st.dataframe(province_display, width="stretch", hide_index=True)

    st.divider()

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
            _plotly_chart(sector_fig)

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
            _plotly_chart(status_fig)

        top_projects = frame[["project_name", "finance_type", "year", "committed_usd", "status"]].copy()
        top_projects["project_name"] = top_projects["project_name"].fillna("Unnamed Project")
        top_projects["status"] = top_projects["status"].fillna("Unknown")
        top_projects = top_projects.sort_values("committed_usd", ascending=False).head(20)
        top_projects["committed_usd"] = top_projects["committed_usd"].apply(format_currency)

        st.markdown("**Top 20 Projects**")
        st.dataframe(top_projects, width="stretch", hide_index=True)

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
        get_fill_color=MAP_POINT_RGBA,
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
    st.pydeck_chart(deck, width="stretch")

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
            _plotly_chart(exposure_fig)

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
            _plotly_chart(timeline_fig)

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
            st.dataframe(details, width="stretch", hide_index=True)

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
    _plotly_chart(funnel_fig)

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
            _plotly_chart(projects_fig)

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
            _plotly_chart(realization_fig)

        display_cohorts = cohorts.copy()
        display_cohorts["committed_usd"] = display_cohorts["committed_usd"].apply(format_currency)
        display_cohorts["disbursed_usd"] = display_cohorts["disbursed_usd"].apply(format_currency)
        display_cohorts["avg_realization_rate"] = display_cohorts["avg_realization_rate"].apply(
            format_pct
        )
        st.dataframe(display_cohorts, width="stretch", hide_index=True)

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
        delay_fig.update_layout(
            xaxis_title="Days",
            yaxis_title="Projects",
            showlegend=False,
        )
        _plotly_chart(delay_fig)

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
        st.dataframe(delayed_projects, width="stretch", hide_index=True)


def render_impact_and_friction_section(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    comparison = summarize_exposure_vs_friction(filtered)
    if comparison.empty:
        st.info("Exposure comparison is unavailable because key fields are missing.")
        return

    st.markdown("### Report Context")
    st.caption(
        "Neutral context adapted from: AidData et al. (June 2025), "
        "'Balancing Risk and Reward: Who benefits from China's investments in Indonesia?'"
    )
    st.markdown(
        "- The report describes average project delivery time from commitment to completion at about 2.5 years."
    )
    st.markdown(
        "- It highlights that energy and transport projects tend to face longer delays and greater environmental/social risk exposure."
    )
    st.markdown(
        "- It notes that a substantial share of the development finance portfolio used implementers with elevated ESG risk exposure or prior sanctions."
    )
    st.markdown(
        "- It reports mixed outcome patterns across provinces, including higher productivity in areas with more Chinese FDI exposure and lower unemployment where development finance exposure is higher."
    )
    st.divider()

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
    _plotly_chart(scatter)

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
        _plotly_chart(comparison_fig)

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
        _plotly_chart(ranking_fig)

    band_summary_display = band_summary.copy()
    band_summary_display["avg_realization_rate"] = band_summary_display["avg_realization_rate"].apply(
        format_pct
    )
    st.dataframe(band_summary_display, width="stretch", hide_index=True)


def filter_by_locked_type(frame: pd.DataFrame, locked_type: str) -> pd.DataFrame:
    if frame.empty or "finance_type" not in frame.columns:
        return frame.iloc[0:0]
    finance = frame["finance_type"].astype("string").str.upper()
    return frame[finance.eq(locked_type.upper())].copy()
