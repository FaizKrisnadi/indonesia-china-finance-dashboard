from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

COLORS = {
    "insight_blue": "#E3F2FD",
    "insight_border": "#2196F3",
    "warning_bg": "#FFF3E0",
    "warning_border": "#FF9800",
    "success_bg": "#E8F5E9",
    "success_border": "#4CAF50",
    "chart_primary": "#2196F3",
    "chart_secondary": "#FF9800",
    "chart_tertiary": "#4CAF50",
    "chart_quaternary": "#9C27B0",
    "text_dark": "#212121",
    "text_medium": "#616161",
    "text_light": "#9E9E9E",
    "bg_light": "#FAFAFA",
    "bg_white": "#FFFFFF",
}

CHART_SEQUENCE = [
    COLORS["chart_primary"],
    COLORS["chart_secondary"],
    COLORS["chart_tertiary"],
    COLORS["chart_quaternary"],
]

BASE_FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

FDI_REGION_COORDS = {
    "Sumatra": (-0.5, 101.0),
    "Java": (-7.2, 110.4),
    "Kalimantan": (0.3, 114.8),
    "Sulawesi": (-1.4, 121.0),
    "Papua": (-3.8, 136.6),
    "Maluku": (-3.3, 129.0),
    "Nusa Tenggara": (-8.7, 117.8),
}


def _inject_global_styles() -> None:
    if st.session_state.get("_dashboard_common_styles_injected"):
        return

    st.markdown(
        """
        <style>
            .stMarkdown h1 {
                font-size: 2.4rem;
                font-weight: 700;
                color: #212121;
                margin-bottom: 0.5rem;
                letter-spacing: -0.02em;
            }
            .stMarkdown h2 {
                font-size: 1.9rem;
                font-weight: 600;
                color: #424242;
                margin-top: 1.75rem;
                margin-bottom: 0.75rem;
            }
            .stMarkdown h3 {
                font-size: 1.35rem;
                font-weight: 600;
                color: #616161;
                margin-top: 1.2rem;
                margin-bottom: 0.6rem;
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                max-width: 1200px;
            }
            [data-testid="stMetric"] {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                padding: 0.85rem;
            }
            [data-testid="stMetricLabel"] {
                color: #616161;
                font-weight: 500;
            }
            [data-testid="stMetricValue"] {
                color: #212121;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_dashboard_common_styles_injected"] = True


def _apply_standard_chart_layout(fig: go.Figure, *, legend_horizontal: bool = False) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": BASE_FONT, "size": 12, "color": COLORS["text_dark"]},
        margin={"t": 40, "b": 40, "l": 40, "r": 40},
    )

    if legend_horizontal:
        fig.update_layout(
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            }
        )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", zeroline=False)


def render_page_header(
    title: str,
    research_question: str | None = None,
    context: str | None = None,
    show_breadcrumb: bool = True,
) -> None:
    if show_breadcrumb:
        parts = title.split(" - ")
        if len(parts) == 2:
            section, page = parts
            st.markdown(
                (
                    "<small style='color: #616161; font-weight: 500;'>"
                    f"{section} / <strong>{page}</strong>"
                    "</small>"
                ),
                unsafe_allow_html=True,
            )

    st.title(title)

    if research_question:
        st.markdown(
            (
                "<div style='background-color: #E3F2FD; padding: 1rem; border-left: "
                "4px solid #2196F3; border-radius: 6px; margin: 0.8rem 0 0.8rem 0;'>"
                f"<strong>Research Question:</strong> {research_question}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    if context:
        st.caption(context)


def render_insight_box(insight: str, insight_type: str = "key") -> None:
    colors = {
        "key": (COLORS["insight_blue"], COLORS["insight_border"], "Insight"),
        "warning": (COLORS["warning_bg"], COLORS["warning_border"], "Watchout"),
        "positive": (COLORS["success_bg"], COLORS["success_border"], "Signal"),
        "neutral": ("#F5F5F5", COLORS["text_light"], "Context"),
    }
    bg_color, border_color, label = colors.get(insight_type, colors["neutral"])

    st.markdown(
        (
            f"<div style='background-color: {bg_color}; padding: 1rem; border-left: "
            f"4px solid {border_color}; border-radius: 6px; margin: 1rem 0;'>"
            f"<strong>{label}:</strong> {insight}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_metric_with_context(
    label: str,
    value: str,
    delta: str | None = None,
    interpretation: str | None = None,
    help_text: str | None = None,
) -> None:
    st.metric(label, value, delta=delta, help=help_text)
    if interpretation:
        st.caption(interpretation)


def render_chart_with_insight(
    fig: go.Figure,
    title: str,
    insight: str | None = None,
    methodology: str | None = None,
    *,
    legend_horizontal: bool = False,
) -> None:
    _apply_standard_chart_layout(fig, legend_horizontal=legend_horizontal)
    st.subheader(title)

    if insight:
        st.markdown(f"**What to notice:** {insight}")

    st.plotly_chart(fig, use_container_width=True)

    if methodology:
        with st.expander("Methodology", expanded=False):
            st.caption(methodology)


def render_section_divider(title: str | None = None) -> None:
    if title:
        st.markdown(f"### {title}")
    st.divider()


def render_navigation_suggestions(suggestions: list[dict[str, str]]) -> None:
    if not suggestions:
        return

    st.markdown("**Continue exploring:**")
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            st.markdown(
                (
                    "<div style='background:#FAFAFA; border:1px solid #E0E0E0; border-radius:10px;"
                    "padding:0.9rem; min-height:120px;'>"
                    f"<div style='font-weight:600; color:#212121;'>{suggestion['page']}</div>"
                    f"<div style='color:#616161; margin-top:0.35rem;'>{suggestion['reason']}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


def render_footer_credit(*, compact: bool = False) -> None:
    padding = "1rem 0" if compact else "2rem 0"
    st.markdown(
        (
            "<div style='text-align:center; padding:"
            f"{padding}; color:#616161; font-size:0.9rem;'>"
            "Designed and maintained by "
            "<a href='https://faizkrisnadi.com' target='_blank' "
            "style='color:#2196F3; text-decoration:none; font-weight:600;'>"
            "Faiz Krisnadi"
            "</a>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_metadata_expander(
    page_key: str,
    projects: pd.DataFrame,
    filtered: pd.DataFrame,
    quality_report: dict[str, Any],
    *,
    label: str = "🔧 Data Quality & Metadata",
) -> None:
    with st.expander(label, expanded=False):
        render_trust_metadata_strip(page_key, projects, filtered, quality_report)
        render_data_quality_panel(projects, quality_report)


def _load_page_state(
    show_finance_type: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, list[Any]]]:
    projects = load_projects_cached()
    quality_report = load_data_quality_cached()
    filters = render_global_sidebar_filters(projects, show_finance_type=show_finance_type)
    filtered = apply_global_filters(projects, filters)
    return projects, filtered, quality_report, filters


def _prepare_fdi_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    analysis = frame.copy()
    analysis["year_num"] = pd.to_numeric(analysis.get("year"), errors="coerce")
    analysis["committed_usd_num"] = pd.to_numeric(analysis.get("committed_usd"), errors="coerce")
    analysis["disbursed_usd_num"] = pd.to_numeric(analysis.get("disbursed_usd"), errors="coerce")
    analysis["sector_clean"] = (
        analysis["sector"].astype("string").fillna("Unknown").str.strip().replace({"": "Unknown"})
    )
    return analysis


def render_home_page() -> None:
    _inject_global_styles()

    st.title("Indonesia-China Finance Dashboard")
    st.markdown(
        """
        Built by **[Faiz Krisnadi](https://faizkrisnadi.com)**, this dashboard tracks China-origin
        Development Finance (DF) and Foreign Direct Investment (FDI) inflows into Indonesia, from
        commitment to delivery, with spatial exposure and implementation risk in one view.
        """
    )

    projects, filtered, quality_report, filters = _load_page_state(show_finance_type=True)

    if projects.empty:
        st.warning("No data available. Please check data sources.")
        _render_metadata_expander(
            "home",
            projects,
            filtered,
            quality_report,
            label="🔧 Technical Details",
        )
        return

    options = get_filter_options_from_projects(projects)
    if filtered.empty:
        st.info("No records match current filters. Try adjusting sidebar filters.")

        recovery_col1, recovery_col2, recovery_col3 = st.columns(3)
        if recovery_col1.button("Show all years", key="home_recover_years"):
            set_filter_values("year", options.get("year", []))
            st.rerun()
        if recovery_col2.button("Show all sectors", key="home_recover_sectors"):
            set_filter_values("sector", options.get("sector", []))
            st.rerun()
        if recovery_col3.button("Show both finance types", key="home_recover_types"):
            set_filter_values("finance_type", options.get("finance_type", []))
            st.rerun()

        _render_metadata_expander(
            "home",
            projects,
            filtered,
            quality_report,
            label="🔧 Technical Details",
        )
        return

    finance_series = filtered["finance_type"].astype("string").str.upper()
    total_projects = len(filtered)
    df_count = int(finance_series.eq("DF").sum())
    fdi_count = int(finance_series.eq("FDI").sum())
    committed_total = pd.to_numeric(filtered["committed_usd"], errors="coerce").sum(min_count=1)
    disbursed_total = pd.to_numeric(filtered["disbursed_usd"], errors="coerce").sum(min_count=1)
    realization_rate = overall_realization_rate(filtered)

    implementation_days = add_time_to_implementation_days(filtered)["time_to_implementation_days"]
    median_implementation = pd.to_numeric(implementation_days, errors="coerce").median()

    concentration = sector_concentration_shares(filtered)

    with st.expander("ℹ️ About this dashboard", expanded=False):
        st.markdown(
            """
            This platform converts fragmented records into decision-ready monitoring of Chinese
            capital inflows. It helps users see:

            - Where China-backed projects are concentrated
            - How much capital is committed versus disbursed
            - How quickly implementation moves
            - Where delivery frictions may emerge

            **Interpretation note:** Home metrics are portfolio-level summaries of China-linked
            inflows. They support monitoring and comparison, not causal inference.
            """
        )

    st.divider()
    st.markdown("## Portfolio at a Glance")

    insights: list[str] = []
    df_pct = (df_count / total_projects * 100) if total_projects > 0 else 0
    fdi_pct = (fdi_count / total_projects * 100) if total_projects > 0 else 0
    insights.append(
        f"**{total_projects:,} projects tracked**: {df_pct:.0f}% Development Finance, "
        f"{fdi_pct:.0f}% Foreign Direct Investment"
    )

    if pd.notna(committed_total) and committed_total > 0:
        insights.append(f"**{format_currency(committed_total)} committed** across all China-linked projects")

    if realization_rate:
        if realization_rate < 0.5:
            insights.append(
                f"**{format_pct(realization_rate)} realization rate**: significant gap between "
                "commitments and disbursements"
            )
        elif realization_rate >= 0.75:
            insights.append(
                f"**{format_pct(realization_rate)} realization rate**: strong conversion from "
                "commitments to disbursements"
            )
        else:
            insights.append(
                f"**{format_pct(realization_rate)} realization rate**: moderate implementation progress"
            )

    if not concentration.empty:
        top_sector = concentration.iloc[0]
        total_value = concentration["value"].sum(min_count=1)
        top_sector_pct = (top_sector["value"] / total_value * 100) if total_value else 0
        if top_sector_pct > 30:
            insights.append(f"**{top_sector['sector']} leads** with {top_sector_pct:.0f}% of portfolio value")

    for insight in insights:
        st.markdown(f"- {insight}")

    st.divider()
    st.markdown("### Key Metrics")
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Projects", f"{total_projects:,}", help="China-linked projects in Indonesia")
    col2.metric(
        "Committed Capital",
        format_currency(committed_total),
        help="Total pledged amounts (constant 2024 USD)",
    )
    col3.metric(
        "Realization Rate",
        format_pct(realization_rate),
        help="Disbursed divided by committed",
    )

    with st.expander("Additional Portfolio Metrics", expanded=False):
        sec_col1, sec_col2, sec_col3 = st.columns(3)
        sec_col1.metric("Disbursed Capital", format_currency(disbursed_total))
        sec_col2.metric(
            "Median Time to Implementation",
            f"{median_implementation:,.0f} days" if pd.notna(median_implementation) else "N/A",
        )
        sec_col3.metric("DF / FDI Project Split", f"{df_count:,} / {fdi_count:,}")

    st.divider()
    st.markdown("### Portfolio Trends")

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

    if trend.empty:
        st.info("Year values are unavailable for trend visualization.")
    else:
        yearly = (
            trend.groupby("year", as_index=False)[["committed_usd", "disbursed_usd"]]
            .sum(min_count=1)
            .sort_values("year")
        )
        trend_long = yearly.melt(
            id_vars="year",
            value_vars=["committed_usd", "disbursed_usd"],
            var_name="series",
            value_name="usd",
        )
        trend_long["series"] = trend_long["series"].map(
            {"committed_usd": "Committed", "disbursed_usd": "Disbursed"}
        )

        trend_fig = px.line(
            trend_long,
            x="year",
            y="usd",
            color="series",
            markers=True,
            labels={"year": "Year", "usd": "Amount (USD)", "series": ""},
            color_discrete_map={
                "Committed": COLORS["chart_primary"],
                "Disbursed": COLORS["chart_secondary"],
            },
        )

        trend_insight = "Track how commitments and disbursements move over time."
        if len(yearly) >= 2:
            prev_value = yearly.iloc[-2]["committed_usd"]
            curr_value = yearly.iloc[-1]["committed_usd"]
            if pd.notna(prev_value) and prev_value not in (0,):
                change_pct = (curr_value - prev_value) / prev_value * 100
                trend_insight = (
                    f"Committed capital changed by {change_pct:+.0f}% from "
                    f"{int(yearly.iloc[-2]['year'])} to {int(yearly.iloc[-1]['year'])}."
                )

        render_chart_with_insight(
            trend_fig,
            title="Capital Flow Trend",
            insight=trend_insight,
            methodology="Annual totals of committed and disbursed values within current filters.",
            legend_horizontal=True,
        )

    if concentration.empty:
        st.info("Sector values are unavailable for this filter selection.")
    else:
        pie_fig = px.pie(
            concentration,
            names="sector",
            values="value",
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        pie_fig.update_traces(textposition="inside", textinfo="percent")

        render_chart_with_insight(
            pie_fig,
            title="Sector Concentration",
            insight="Highlights which sectors capture the largest share of portfolio value.",
        )

    st.divider()
    st.markdown("### Explore by Type")

    nav_col1, nav_col2 = st.columns(2)

    with nav_col1:
        st.markdown(
            """
            <div style='background:#F8FAFD; border:1px solid #DCE8F9; border-radius:12px; padding:1rem;'>
                <h4 style='margin:0; color:#1f4e79;'>Development Finance</h4>
                <p style='margin:0.55rem 0 0.2rem 0; color:#455A64;'>
                    Explore concessional loans, grants, and official development assistance.
                </p>
                <p style='margin:0; color:#546E7A;'><strong>See:</strong> spatial patterns, delivery timelines, and implementation risks.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with nav_col2:
        st.markdown(
            """
            <div style='background:#FFF8F3; border:1px solid #F6DFC7; border-radius:12px; padding:1rem;'>
                <h4 style='margin:0; color:#8c4a0b;'>Foreign Direct Investment</h4>
                <p style='margin:0.55rem 0 0.2rem 0; color:#5D4037;'>
                    Analyze commercial FDI commitments from Chinese companies.
                </p>
                <p style='margin:0; color:#6D4C41;'><strong>See:</strong> regional distribution, top deals, and sector trends.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    render_footer_credit(compact=False)

    _render_metadata_expander(
        "home",
        projects,
        filtered,
        quality_report,
        label="🔧 Technical Details",
    )


def render_locked_section_page(
    *,
    page_title: str,
    locked_type: str,
    page_key: str,
    renderer: SectionRenderer,
) -> None:
    _inject_global_styles()

    research_questions = {
        "overview": "What is the scale, performance, and provincial footprint of Chinese development finance in Indonesia?",
        "spatial": "Where are development finance projects located, and how complete is the location data?",
        "finance_delivery": "How quickly do projects move from approval to delivery, and where are delays concentrated?",
        "impact_friction": "How does provincial exposure to Chinese development finance relate to implementation friction?",
    }

    contexts = {
        "overview": "Portfolio summary view of Development Finance projects only.",
        "spatial": "Map and geographic exposure analysis for Development Finance projects only.",
        "finance_delivery": "Lifecycle, cohort, and delay analysis for Development Finance projects only.",
        "impact_friction": "Risk and exposure benchmarking for Development Finance projects only.",
    }

    render_page_header(
        title=page_title,
        research_question=research_questions.get(page_key),
        context=contexts.get(page_key),
    )

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning("No processed dataset detected. Add source files to `data/raw`, then run `make etl`.")
        _render_metadata_expander(page_key, projects, filtered, quality_report)
        return

    locked_frame = filter_by_locked_type(filtered, locked_type)
    if locked_frame.empty:
        st.info(f"No {locked_type} records match the current sidebar filters.")
        _render_metadata_expander(page_key, projects, locked_frame, quality_report)
        return

    intro_insights = {
        "overview": "This page summarizes the size, disbursement progress, and risk profile of the Development Finance portfolio.",
        "spatial": "Use this page to identify concentration hotspots and where missing coordinates may limit map interpretation.",
        "finance_delivery": "Focus here to see lifecycle bottlenecks, cohort performance, and implementation delays.",
        "impact_friction": "This view helps compare high-exposure provinces against delivery risk indicators.",
    }
    render_insight_box(intro_insights.get(page_key, "Development Finance portfolio view."), "neutral")

    renderer(locked_frame)

    nav_map = {
        "overview": [
            {
                "page": "Development Finance / Spatial Explorer",
                "reason": "See where projects are concentrated geographically.",
            },
            {
                "page": "Development Finance / Trends & Sectors",
                "reason": "Track DF movement over time and sector concentration.",
            },
            {
                "page": "Development Finance / Finance and Delivery",
                "reason": "Track lifecycle stages and approval cohorts.",
            },
        ],
        "spatial": [
            {
                "page": "Development Finance / Overview",
                "reason": "Return to portfolio totals and performance metrics.",
            },
            {
                "page": "Development Finance / Impact and Friction",
                "reason": "Compare exposure with risk outcomes.",
            },
            {
                "page": "Development Finance / Trends & Sectors",
                "reason": "View DF trends and sector mix in a dedicated page.",
            },
        ],
        "finance_delivery": [
            {
                "page": "Development Finance / Overview",
                "reason": "Re-check portfolio-wide baseline indicators.",
            },
            {
                "page": "Development Finance / Impact and Friction",
                "reason": "Link delivery pace to implementation risk.",
            },
        ],
        "impact_friction": [
            {
                "page": "Development Finance / Spatial Explorer",
                "reason": "Map the locations behind high-friction provinces.",
            },
            {
                "page": "Development Finance / Finance and Delivery",
                "reason": "Inspect lifecycle bottlenecks behind risk signals.",
            },
        ],
    }
    render_navigation_suggestions(nav_map.get(page_key, []))
    render_footer_credit(compact=True)
    _render_metadata_expander(page_key, projects, locked_frame, quality_report)


def _render_locked_df_page_header(
    *,
    page_title: str,
    page_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    _inject_global_styles()

    research_questions = {
        "trends": "How have Chinese development finance commitments evolved over time, and which sectors are most prominent?",
    }

    render_page_header(
        title=page_title,
        research_question=research_questions.get(page_key),
        context="All values shown in this section are filtered to Development Finance (DF).",
    )

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning("No processed dataset detected. Add source files to `data/raw`, then run `make etl`.")
        return projects, pd.DataFrame(), quality_report

    locked_frame = filter_by_locked_type(filtered, "DF")
    return projects, locked_frame, quality_report


def render_df_trends_and_sectors_page() -> None:
    projects, locked_frame, quality_report = _render_locked_df_page_header(
        page_title="Development Finance - Trends and Sectors",
        page_key="trends",
    )
    if projects.empty:
        _render_metadata_expander("trends_df", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info("No DF records match the current sidebar filters.")
        _render_metadata_expander("trends_df", projects, locked_frame, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)

    yearly = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)[["committed_usd_num", "disbursed_usd_num"]]
        .sum(min_count=1)
        .sort_values("year_num")
    )
    yearly_count = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)
        .size()
        .rename(columns={"size": "projects"})
        .sort_values("year_num")
    )

    top_sector_committed = (
        analysis.groupby("sector_clean", as_index=False)["committed_usd_num"]
        .sum(min_count=1)
        .dropna(subset=["committed_usd_num"])
        .sort_values("committed_usd_num", ascending=False)
        .head(15)
    )

    top_sector_count = (
        analysis.groupby("sector_clean", dropna=False)
        .size()
        .reset_index(name="projects")
        .sort_values("projects", ascending=False)
        .head(15)
    )

    if not top_sector_committed.empty and len(top_sector_committed) >= 3:
        total_committed = top_sector_committed["committed_usd_num"].sum(min_count=1)
        top3_share = (
            top_sector_committed.head(3)["committed_usd_num"].sum(min_count=1) / total_committed * 100
            if total_committed
            else 0
        )
        trend_note = f"Top three sectors account for {top3_share:.0f}% of DF commitments in this view."
    else:
        trend_note = "Use this page to compare DF sector concentration with year-by-year movement."
    render_insight_box(trend_note, "key")

    render_section_divider("Temporal Trends")
    time_left, time_right = st.columns([2, 1])
    with time_left:
        if yearly.empty:
            st.info("Year values are unavailable for temporal trend charts.")
        else:
            yearly_melted = yearly.melt(
                id_vars="year_num",
                value_vars=["committed_usd_num", "disbursed_usd_num"],
                var_name="series",
                value_name="usd",
            )
            yearly_melted["series"] = yearly_melted["series"].map(
                {
                    "committed_usd_num": "Committed",
                    "disbursed_usd_num": "Disbursed",
                }
            )
            time_fig = px.line(
                yearly_melted,
                x="year_num",
                y="usd",
                color="series",
                markers=True,
                labels={"year_num": "Year", "usd": "USD", "series": ""},
                color_discrete_map={
                    "Committed": COLORS["chart_primary"],
                    "Disbursed": COLORS["chart_secondary"],
                },
            )
            render_chart_with_insight(
                time_fig,
                title="Committed vs Disbursed Over Time",
                insight="Tracks how DF commitments and disbursements shift over time.",
                legend_horizontal=True,
            )

    with time_right:
        if yearly_count.empty:
            st.info("No year data available for project-count trend.")
        else:
            yearly_count["year_num"] = yearly_count["year_num"].astype(int)
            volume_fig = px.bar(
                yearly_count,
                x="year_num",
                y="projects",
                labels={"year_num": "Year", "projects": "Projects"},
                color_discrete_sequence=[COLORS["chart_tertiary"]],
            )
            render_chart_with_insight(
                volume_fig,
                title="Project Volume by Year",
                insight="Shows annual project entry volume in DF data.",
            )

    render_section_divider("Sector Dynamics")
    sector_left, sector_right = st.columns([1, 1])
    with sector_left:
        sector_count_fig = px.bar(
            top_sector_count.sort_values("projects"),
            x="projects",
            y="sector_clean",
            orientation="h",
            labels={"projects": "Projects", "sector_clean": "Sector"},
            color_discrete_sequence=[COLORS["chart_primary"]],
        )
        render_chart_with_insight(
            sector_count_fig,
            title="Top Sectors by Project Count",
            insight="Highlights sectors with the highest project volume.",
        )

    with sector_right:
        if top_sector_committed.empty:
            st.info("Committed values are unavailable for sector ranking.")
        else:
            sector_committed_fig = px.bar(
                top_sector_committed.sort_values("committed_usd_num"),
                x="committed_usd_num",
                y="sector_clean",
                orientation="h",
                labels={"committed_usd_num": "Committed USD", "sector_clean": "Sector"},
                color_discrete_sequence=[COLORS["chart_secondary"]],
            )
            render_chart_with_insight(
                sector_committed_fig,
                title="Top Sectors by Committed Value",
                insight="Compares DF sectors by commitment size.",
            )

    if not top_sector_committed.empty:
        share_fig = px.pie(
            top_sector_committed,
            names="sector_clean",
            values="committed_usd_num",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        share_fig.update_traces(textposition="inside", textinfo="percent+label")
        render_chart_with_insight(
            share_fig,
            title="Sector Share of DF Commitments",
            insight="Shows relative concentration across DF sectors.",
        )

    render_navigation_suggestions(
        [
            {
                "page": "Development Finance / Overview",
                "reason": "Return to portfolio baseline metrics.",
            },
            {
                "page": "Development Finance / Spatial Explorer",
                "reason": "See geographic concentration and regional breakdown.",
            },
            {
                "page": "Development Finance / Finance and Delivery",
                "reason": "Connect trend signals with delivery timelines.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("trends_df", projects, locked_frame, quality_report)


def _render_locked_fdi_page_header(
    *,
    page_title: str,
    page_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    _inject_global_styles()

    research_questions = {
        "overview": "How large is the Chinese FDI portfolio, how has it changed over time, and which sectors dominate?",
        "spatial": "How is Chinese FDI CAPEX distributed across Indonesian regions, and how much lacks location detail?",
        "trends": "Which sectors attract most Chinese FDI, and how have commitments shifted over time?",
        "top_deals": "Which individual Chinese FDI deals are largest, and how concentrated are commitments among them?",
        "impact_friction": "How complete is the FDI dataset across key analytical fields, and where are the largest gaps?",
    }

    render_page_header(
        title=page_title,
        research_question=research_questions.get(page_key),
        context="All values shown in this section are filtered to Foreign Direct Investment (FDI).",
    )

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning("No processed dataset detected. Add source files to `data/raw`, then run `make etl`.")
        return projects, pd.DataFrame(), quality_report

    locked_frame = filter_by_locked_type(filtered, "FDI")
    return projects, locked_frame, quality_report


def render_fdi_overview_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Overview",
        page_key="overview",
    )
    if projects.empty:
        _render_metadata_expander("overview", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info("No FDI records match the current sidebar filters.")
        _render_metadata_expander("overview", projects, locked_frame, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)
    total_projects = len(analysis)
    committed_total = analysis["committed_usd_num"].sum(min_count=1)
    median_committed = analysis["committed_usd_num"].median()

    sector_summary = (
        analysis.groupby("sector_clean", as_index=False)["committed_usd_num"]
        .sum(min_count=1)
        .dropna(subset=["committed_usd_num"])
        .sort_values("committed_usd_num", ascending=False)
    )

    if not sector_summary.empty:
        top_sector = sector_summary.iloc[0]
        top_share = (top_sector["committed_usd_num"] / committed_total * 100) if committed_total else 0
        render_insight_box(
            (
                f"{total_projects:,} FDI projects are tracked with {format_currency(committed_total)} in"
                f" commitments; {top_sector['sector_clean']} is the largest sector at {top_share:.0f}%"
                " of observed CAPEX."
            ),
            "key",
        )

    year_values = analysis["year_num"].dropna().astype(int)
    year_range = "N/A"
    if not year_values.empty:
        year_range = f"{int(year_values.min())} - {int(year_values.max())}"

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        render_metric_with_context(
            label="Total FDI Projects",
            value=f"{total_projects:,}",
            interpretation="Distinct FDI entries under current filters.",
        )
    with metric_col2:
        render_metric_with_context(
            label="Committed CAPEX",
            value=format_currency(committed_total),
            interpretation="Total committed value (constant 2024 USD).",
        )
    with metric_col3:
        render_metric_with_context(
            label="Median Deal Size",
            value=format_currency(median_committed) if pd.notna(median_committed) else "N/A",
            interpretation="Middle value among project-level commitments.",
        )
    with metric_col4:
        render_metric_with_context(
            label="Active Year Range",
            value=year_range,
            interpretation="Earliest to latest year represented.",
        )

    render_section_divider("Time Pattern")

    yearly_count = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)
        .size()
        .rename(columns={"size": "projects"})
        .sort_values("year_num")
    )
    yearly_committed = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)["committed_usd_num"]
        .sum(min_count=1)
        .dropna(subset=["committed_usd_num"])
        .sort_values("year_num")
    )

    if yearly_count.empty:
        st.info("Year values are unavailable for FDI project counts.")
    else:
        yearly_count["year_num"] = yearly_count["year_num"].astype(int)
        count_fig = px.bar(
            yearly_count,
            x="year_num",
            y="projects",
            labels={"year_num": "Year", "projects": "Projects"},
            color_discrete_sequence=[COLORS["chart_primary"]],
        )
        render_chart_with_insight(
            count_fig,
            title="Yearly Project Count",
            insight="Shows when Chinese FDI project entries are most concentrated.",
        )

    if yearly_committed.empty:
        st.info("Committed CAPEX values are unavailable for yearly trend analysis.")
    else:
        yearly_committed["year_num"] = yearly_committed["year_num"].astype(int)
        committed_fig = px.area(
            yearly_committed,
            x="year_num",
            y="committed_usd_num",
            labels={"year_num": "Year", "committed_usd_num": "Committed USD"},
            color_discrete_sequence=[COLORS["chart_secondary"]],
        )
        render_chart_with_insight(
            committed_fig,
            title="Yearly Committed CAPEX",
            insight="Highlights surges or slowdowns in annual commitment volume.",
        )

    render_section_divider("Sector Composition")

    if sector_summary.empty:
        st.info("Sector labels or committed values are unavailable.")
    else:
        top_sector_chart = sector_summary.head(10)
        sector_fig = px.bar(
            top_sector_chart,
            x="sector_clean",
            y="committed_usd_num",
            labels={"sector_clean": "Sector", "committed_usd_num": "Committed USD"},
            color="sector_clean",
            color_discrete_sequence=CHART_SEQUENCE,
        )
        sector_fig.update_layout(showlegend=False)
        sector_fig.update_xaxes(tickangle=-35)

        render_chart_with_insight(
            sector_fig,
            title="Top 10 Sectors by CAPEX",
            insight="Compares sectoral concentration in Chinese FDI commitments.",
        )

    render_navigation_suggestions(
        [
            {
                "page": "FDI / Regional Distribution",
                "reason": "See where capital is geographically concentrated.",
            },
            {
                "page": "FDI / Trends and Sectors",
                "reason": "Inspect year-by-year and sector-by-sector changes.",
            },
            {
                "page": "FDI / Top Deals",
                "reason": "Review the largest individual commitments.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("overview", projects, locked_frame, quality_report)


def render_fdi_trends_and_sectors_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Trends and Sectors",
        page_key="trends",
    )
    if projects.empty:
        _render_metadata_expander("trends", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info("No FDI records match the current sidebar filters.")
        _render_metadata_expander("trends", projects, locked_frame, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)

    yearly = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)[["committed_usd_num", "disbursed_usd_num"]]
        .sum(min_count=1)
        .sort_values("year_num")
    )
    yearly_count = (
        analysis.dropna(subset=["year_num"])
        .groupby("year_num", as_index=False)
        .size()
        .rename(columns={"size": "projects"})
        .sort_values("year_num")
    )

    top_sector_committed = (
        analysis.groupby("sector_clean", as_index=False)["committed_usd_num"]
        .sum(min_count=1)
        .dropna(subset=["committed_usd_num"])
        .sort_values("committed_usd_num", ascending=False)
        .head(15)
    )

    top_sector_count = (
        analysis.groupby("sector_clean", dropna=False)
        .size()
        .reset_index(name="projects")
        .sort_values("projects", ascending=False)
        .head(15)
    )

    if not top_sector_committed.empty and len(top_sector_committed) >= 3:
        total_committed = top_sector_committed["committed_usd_num"].sum(min_count=1)
        top3_share = (
            top_sector_committed.head(3)["committed_usd_num"].sum(min_count=1) / total_committed * 100
            if total_committed
            else 0
        )
        trend_note = f"Top three sectors represent {top3_share:.0f}% of committed CAPEX in this view."
    else:
        trend_note = "Use this page to compare sector concentration with year-by-year movement."

    render_insight_box(trend_note, "key")

    render_section_divider("Temporal Trends")

    time_left, time_right = st.columns([2, 1])
    with time_left:
        if yearly.empty:
            st.info("Year values are unavailable for temporal trend charts.")
        else:
            yearly_melted = yearly.melt(
                id_vars="year_num",
                value_vars=["committed_usd_num", "disbursed_usd_num"],
                var_name="series",
                value_name="usd",
            )
            yearly_melted["series"] = yearly_melted["series"].map(
                {
                    "committed_usd_num": "Committed",
                    "disbursed_usd_num": "Disbursed",
                }
            )
            time_fig = px.line(
                yearly_melted,
                x="year_num",
                y="usd",
                color="series",
                markers=True,
                labels={"year_num": "Year", "usd": "USD", "series": ""},
                color_discrete_map={
                    "Committed": COLORS["chart_primary"],
                    "Disbursed": COLORS["chart_secondary"],
                },
            )
            render_chart_with_insight(
                time_fig,
                title="Committed vs Disbursed Over Time",
                insight="Compares pledge volume against realized flows by year.",
                legend_horizontal=True,
            )

    with time_right:
        if yearly_count.empty:
            st.info("No year data available for project-count trend.")
        else:
            yearly_count["year_num"] = yearly_count["year_num"].astype(int)
            volume_fig = px.bar(
                yearly_count,
                x="year_num",
                y="projects",
                labels={"year_num": "Year", "projects": "Projects"},
                color_discrete_sequence=[COLORS["chart_tertiary"]],
            )
            render_chart_with_insight(
                volume_fig,
                title="Project Volume by Year",
                insight="Tracks when new FDI entries are most active.",
            )

    render_section_divider("Sector Dynamics")

    sector_left, sector_right = st.columns([1, 1])
    with sector_left:
        sector_count_fig = px.bar(
            top_sector_count.sort_values("projects"),
            x="projects",
            y="sector_clean",
            orientation="h",
            labels={"projects": "Projects", "sector_clean": "Sector"},
            color_discrete_sequence=[COLORS["chart_primary"]],
        )
        render_chart_with_insight(
            sector_count_fig,
            title="Top Sectors by Project Count",
            insight="Shows which sectors host the largest number of Chinese FDI projects.",
        )

    with sector_right:
        if top_sector_committed.empty:
            st.info("Committed CAPEX values are unavailable for sector ranking.")
        else:
            sector_committed_fig = px.bar(
                top_sector_committed.sort_values("committed_usd_num"),
                x="committed_usd_num",
                y="sector_clean",
                orientation="h",
                labels={"committed_usd_num": "Committed USD", "sector_clean": "Sector"},
                color_discrete_sequence=[COLORS["chart_secondary"]],
            )
            render_chart_with_insight(
                sector_committed_fig,
                title="Top Sectors by Committed CAPEX",
                insight="Captures capital intensity even when project counts are lower.",
            )

    if not top_sector_committed.empty:
        share_fig = px.pie(
            top_sector_committed,
            names="sector_clean",
            values="committed_usd_num",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        share_fig.update_traces(textposition="inside", textinfo="percent+label")
        render_chart_with_insight(
            share_fig,
            title="Sector Share of Committed CAPEX",
            insight="Makes concentration and diversification patterns easy to compare.",
        )

    status_non_null_pct = float(
        (
            analysis["status"].astype("string").str.strip().replace({"": pd.NA}).notna().mean() * 100
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
            color_discrete_sequence=[COLORS["chart_quaternary"]],
        )
        render_chart_with_insight(
            status_fig,
            title="Status Mix",
            insight="Useful for tracking pipeline health and execution risk.",
        )
    else:
        st.info(
            f"Status coverage is {status_non_null_pct:.1f}%; status mix is hidden for this view."
        )

    render_navigation_suggestions(
        [
            {
                "page": "FDI / Overview",
                "reason": "Return to high-level portfolio summary.",
            },
            {
                "page": "FDI / Regional Distribution",
                "reason": "Connect sector shifts with geographic concentration.",
            },
            {
                "page": "FDI / Top Deals",
                "reason": "Inspect project-level concentration driving trends.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("trends", projects, locked_frame, quality_report)


def render_fdi_top_deals_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Top Deals",
        page_key="top_deals",
    )
    if projects.empty:
        _render_metadata_expander("top_deals", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        _render_metadata_expander("top_deals", projects, locked_frame, quality_report)
        return

    analysis = _prepare_fdi_analysis(locked_frame)
    committed_values = analysis["committed_usd_num"].dropna()

    if committed_values.empty:
        st.info("Committed CAPEX values are unavailable for deal distribution analysis.")
    else:
        distribution_fig = px.histogram(
            committed_values,
            nbins=30,
            labels={"value": "Committed CAPEX (USD)"},
            color_discrete_sequence=[COLORS["chart_primary"]],
        )
        distribution_fig.update_layout(xaxis_title="Committed CAPEX", yaxis_title="Projects")
        render_chart_with_insight(
            distribution_fig,
            title="Committed CAPEX Distribution",
            insight="Shows whether capital is spread across many deals or concentrated in a few large ones.",
        )

    table_columns = ["project_name", "year", "sector", "province", "status", "committed_usd"]
    if "source_file" in analysis.columns:
        table_columns.append("source_file")

    top_deals = analysis.loc[:, table_columns].copy()
    top_deals["committed_usd_num"] = analysis["committed_usd_num"]
    top_deals = top_deals.sort_values("committed_usd_num", ascending=False).head(20)

    total_top20 = top_deals["committed_usd_num"].sum(min_count=1)
    total_all = analysis["committed_usd_num"].sum(min_count=1)
    top20_share = (total_top20 / total_all * 100) if total_all else 0

    render_insight_box(
        (
            f"Top 20 deals account for {format_currency(total_top20)} "
            f"({top20_share:.0f}% of visible committed CAPEX)."
        ),
        "key",
    )

    top_deals = top_deals.drop(columns=["committed_usd_num"])
    top_deals["committed_usd"] = pd.to_numeric(top_deals["committed_usd"], errors="coerce").apply(
        format_currency
    )

    st.markdown("### Top 20 Projects by Committed CAPEX")
    st.dataframe(top_deals, use_container_width=True, hide_index=True)

    with st.expander("How to read this table", expanded=False):
        st.markdown(
            """
            - **Committed CAPEX** shows project scale.
            - **Sector** indicates investment priority.
            - **Province** shows location targeting.
            - **Status** gives implementation stage context.
            """
        )

    render_navigation_suggestions(
        [
            {
                "page": "FDI / Trends and Sectors",
                "reason": "See whether these large deals drive sector-level shifts.",
            },
            {
                "page": "FDI / Regional Distribution",
                "reason": "Track where the largest commitments are concentrated.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("top_deals", projects, locked_frame, quality_report)


def render_fdi_data_coverage_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Data Coverage",
        page_key="impact_friction",
    )
    if projects.empty:
        _render_metadata_expander("impact_friction", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        _render_metadata_expander("impact_friction", projects, locked_frame, quality_report)
        return

    st.markdown(
        """
        This page shows field completion levels for FDI records. It helps you identify where
        data quality supports strong analysis and where interpretation needs caution.
        """
    )

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
        rows.append(
            {
                "field": field,
                "non_null_pct": round(non_null_pct, 1),
                "missing_pct": round(100 - non_null_pct, 1),
                "non_null_count": non_null_count,
                "missing_count": missing_count,
            }
        )

    coverage = pd.DataFrame(rows).sort_values("missing_pct", ascending=False).reset_index(drop=True)

    low_coverage_fields = coverage[coverage["non_null_pct"] < 50]["field"].tolist()
    if low_coverage_fields:
        render_insight_box(
            (
                "Largest data gaps are in "
                f"{', '.join(low_coverage_fields[:3])}. Use extra caution when interpreting related visuals."
            ),
            "warning",
        )
    else:
        render_insight_box(
            "Most core fields have strong coverage in the current filter scope.",
            "positive",
        )

    completion_fig = px.bar(
        coverage.sort_values("non_null_pct", ascending=True),
        x="non_null_pct",
        y="field",
        orientation="h",
        labels={"non_null_pct": "Completion (%)", "field": "Field"},
        color_discrete_sequence=[COLORS["chart_primary"]],
    )
    render_chart_with_insight(
        completion_fig,
        title="Field Completion Rates",
        insight="Fields near 100% are more reliable for comparison across projects.",
    )

    st.markdown("### Underlying Coverage Table")
    st.dataframe(coverage, use_container_width=True, hide_index=True)

    render_navigation_suggestions(
        [
            {
                "page": "FDI / Overview",
                "reason": "Return to portfolio findings with data quality context in mind.",
            },
            {
                "page": "FDI / Regional Distribution",
                "reason": "See how location completeness may affect geographic interpretation.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("impact_friction", projects, locked_frame, quality_report)


def render_fdi_region_distribution_page() -> None:
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Regional Distribution",
        page_key="spatial",
    )
    if projects.empty:
        _render_metadata_expander("spatial", projects, locked_frame, quality_report)
        return

    if locked_frame.empty:
        st.info(
            "No FDI records match current filters. Regional distribution below uses the embedded dataset."
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

    total_china = df["china_capex_2024usd_b"].sum(min_count=1)
    not_spec = df.loc[df["region"] == "Not Specified", "china_capex_2024usd_b"].sum(min_count=1)

    specified_df = df[df["region"] != "Not Specified"].copy()
    top_region = specified_df.loc[specified_df["china_capex_2024usd_b"].idxmax()]
    specified_total = specified_df["china_capex_2024usd_b"].sum(min_count=1)
    top_region_share = (top_region["china_capex_2024usd_b"] / specified_total * 100) if specified_total else 0
    not_spec_share = (not_spec / total_china * 100) if total_china else 0

    render_insight_box(
        (
            f"{top_region['region']} leads with ${top_region['china_capex_2024usd_b']:.1f}B "
            f"({top_region_share:.0f}% of specified locations), while {not_spec_share:.0f}% "
            "of CAPEX is not geographically specified."
        ),
        "key",
    )

    st.markdown("### Regional Portfolio Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total China CAPEX", f"${total_china:,.2f}B", help="Constant 2024 USD, billions")
    c2.metric("Location Not Specified", f"${not_spec:,.2f}B")
    c3.metric("Share Not Specified", f"{not_spec_share:,.1f}%")

    st.divider()

    include_unspecified = st.toggle(
        "Include 'Not Specified' in charts",
        value=False,
        key="fdi_region_include_unspecified",
    )

    plot_df = df.copy()
    if not include_unspecified:
        plot_df = plot_df[plot_df["region"] != "Not Specified"].copy()
    plot_df = plot_df.sort_values("china_capex_2024usd_b", ascending=False)

    bar_fig = px.bar(
        plot_df,
        x="region",
        y="china_capex_2024usd_b",
        text=plot_df["china_capex_2024usd_b"].map(lambda value: f"${value:.1f}B"),
        labels={"china_capex_2024usd_b": "China CAPEX (Billion USD)", "region": "Region"},
        color="region",
        color_discrete_sequence=CHART_SEQUENCE,
    )
    bar_fig.update_layout(showlegend=False)
    bar_fig.update_xaxes(tickangle=-20)
    bar_fig.update_traces(textposition="outside")

    render_chart_with_insight(
        bar_fig,
        title="Chinese FDI CAPEX by Region",
        insight="Compare absolute commitment size across Indonesian regional groupings.",
    )

    map_df = plot_df.copy()
    map_df["lat"] = map_df["region"].map(lambda value: FDI_REGION_COORDS.get(value, (None, None))[0])
    map_df["lon"] = map_df["region"].map(lambda value: FDI_REGION_COORDS.get(value, (None, None))[1])
    map_df = map_df.dropna(subset=["lat", "lon"])

    if map_df.empty:
        st.info("Map coordinates are unavailable for selected regions.")
    else:
        regional_map = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            size="china_capex_2024usd_b",
            color="region",
            hover_name="region",
            hover_data={
                "china_capex_2024usd_b": ":.2f",
                "all_source_capex_2024usd_b": ":.2f",
                "lat": False,
                "lon": False,
            },
            labels={
                "china_capex_2024usd_b": "China CAPEX ($B)",
                "all_source_capex_2024usd_b": "All-source CAPEX ($B)",
            },
            color_discrete_sequence=CHART_SEQUENCE,
            projection="natural earth",
        )
        regional_map.update_geos(
            fitbounds="locations",
            visible=False,
            showcountries=True,
            countrycolor="rgba(0,0,0,0.25)",
            lataxis_range=[-12, 8],
            lonaxis_range=[94, 142],
        )
        render_chart_with_insight(
            regional_map,
            title="Interactive Map: Chinese FDI by Region",
            insight="Bubble size reflects China CAPEX by region (constant 2024 USD, billions).",
        )

    render_section_divider("Underlying Regional Table")

    show_context = st.toggle(
        "Compare with all-source FDI",
        value=False,
        key="fdi_region_show_context",
    )

    if not show_context:
        display_df = df[["region", "included_provinces", "china_capex_2024usd_b"]].copy()
        display_df.columns = ["Region", "Provinces", "China CAPEX ($B, 2024 USD)"]
    else:
        df2 = df.copy()
        df2["china_share_of_all_sources"] = (
            df2["china_capex_2024usd_b"] / df2["all_source_capex_2024usd_b"]
        )
        display_df = df2[
            [
                "region",
                "included_provinces",
                "china_capex_2024usd_b",
                "all_source_capex_2024usd_b",
                "china_share_of_all_sources",
            ]
        ].copy()
        display_df.columns = [
            "Region",
            "Provinces",
            "China CAPEX ($B)",
            "All Sources CAPEX ($B)",
            "China Share",
        ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    render_navigation_suggestions(
        [
            {
                "page": "FDI / Trends and Sectors",
                "reason": "Connect regional concentration with year-by-year sector changes.",
            },
            {
                "page": "FDI / Top Deals",
                "reason": "See which major projects drive regional totals.",
            },
        ]
    )

    render_footer_credit(compact=True)
    _render_metadata_expander("spatial", projects, locked_frame, quality_report)
