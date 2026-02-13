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


# ==========================================
# STORYTELLING UI COMPONENTS
# ==========================================

def render_page_header(
    title: str,
    research_question: str | None = None,
    context: str | None = None,
    show_breadcrumb: bool = True
) -> None:
    """
    Render a narrative-driven page header with research context.
    
    Args:
        title: Page title
        research_question: The key question this page answers (optional)
        context: Why this analysis matters (optional)
        show_breadcrumb: Show navigation breadcrumb
    """
    if show_breadcrumb:
        # Extract section from title (e.g., "FDI - Overview" → "FDI")
        parts = title.split(" - ")
        if len(parts) == 2:
            section, page = parts
            st.markdown(f"<small style='color: #666;'>📊 {section} / **{page}**</small>", unsafe_allow_html=True)
        
    st.title(title)
    
    if research_question:
        st.markdown(f"""
        <div style='background-color: #f0f7ff; padding: 1rem; border-left: 4px solid #1f77b4; margin: 1rem 0;'>
            <strong>🔍 Research Question:</strong> {research_question}
        </div>
        """, unsafe_allow_html=True)
    
    if context:
        st.caption(context)


def render_insight_box(insight: str, insight_type: str = "key") -> None:
    """
    Highlight a key finding or insight.
    
    Args:
        insight: The finding to highlight
        insight_type: 'key' (blue), 'warning' (yellow), 'positive' (green), or 'neutral' (gray)
    """
    colors = {
        "key": ("#e3f2fd", "#1976d2", "💡"),
        "warning": ("#fff3e0", "#f57c00", "⚠️"),
        "positive": ("#e8f5e9", "#388e3c", "✓"),
        "neutral": ("#f5f5f5", "#616161", "→")
    }
    bg_color, border_color, icon = colors.get(insight_type, colors["neutral"])
    
    st.markdown(f"""
    <div style='background-color: {bg_color}; padding: 1rem; border-left: 4px solid {border_color}; margin: 1rem 0;'>
        <strong>{icon} Key Finding:</strong> {insight}
    </div>
    """, unsafe_allow_html=True)


def render_metric_with_context(
    label: str,
    value: str,
    delta: str | None = None,
    interpretation: str | None = None,
    help_text: str | None = None
) -> None:
    """
    Render a metric with contextual explanation.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Change indicator (optional)
        interpretation: What this number means (optional)
        help_text: Tooltip explanation (optional)
    """
    st.metric(label, value, delta=delta, help=help_text)
    if interpretation:
        st.caption(f"_{interpretation}_")


def render_chart_with_insight(
    fig: go.Figure,
    title: str,
    insight: str | None = None,
    methodology: str | None = None
) -> None:
    """
    Render a chart with interpretive context.
    
    Args:
        fig: Plotly figure
        title: Chart title
        insight: What to notice in this chart
        methodology: How this was calculated (optional)
    """
    st.subheader(title)
    
    if insight:
        st.markdown(f"**What to notice:** {insight}")
    
    st.plotly_chart(fig, use_container_width=True)
    
    if methodology:
        with st.expander("📊 Methodology"):
            st.caption(methodology)


def render_section_divider(title: str | None = None) -> None:
    """Render a visual section divider."""
    if title:
        st.markdown(f"### {title}")
    st.divider()


def render_navigation_suggestions(suggestions: list[dict[str, str]]) -> None:
    """
    Suggest related pages to explore.
    
    Args:
        suggestions: List of dicts with 'page' and 'reason' keys
    """
    st.markdown("---")
    st.markdown("**📖 Continue exploring:**")
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            st.markdown(f"**{suggestion['page']}**")
            st.caption(suggestion['reason'])


# ==========================================
# DATA LOADING
# ==========================================

def _load_page_state(show_finance_type: bool) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, list[Any]]]:
    projects = load_projects_cached()
    quality_report = load_data_quality_cached()
    filters = render_global_sidebar_filters(projects, show_finance_type=show_finance_type)
    render_current_view_bar(projects)
    filtered = apply_global_filters(projects, filters)
    return projects, filtered, quality_report, filters


# ==========================================
# HOME PAGE - REDESIGNED
# ==========================================

def render_home_page() -> None:
    """Narrative-driven home page with executive summary."""
    
    render_page_header(
        title="Indonesia–China Finance Dashboard",
        research_question="How is Chinese capital flowing into Indonesia, and what patterns emerge in development finance versus foreign direct investment?",
        context="Portfolio-grade monitoring of China-linked project pipelines, spatial exposure, and delivery dynamics.",
        show_breadcrumb=False
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

    # Calculate metrics
    finance_series = filtered["finance_type"].astype("string").str.upper()
    df_projects_count = int(finance_series.eq("DF").sum())
    fdi_projects_count = int(finance_series.eq("FDI").sum())

    committed_total = pd.to_numeric(filtered["committed_usd"], errors="coerce").sum(min_count=1)
    disbursed_total = pd.to_numeric(filtered["disbursed_usd"], errors="coerce").sum(min_count=1)
    realization_rate = overall_realization_rate(filtered)
    implementation_days = add_time_to_implementation_days(filtered)["time_to_implementation_days"]
    median_implementation = pd.to_numeric(implementation_days, errors="coerce").median()

    # EXECUTIVE SUMMARY SECTION
    st.markdown("## 📋 Executive Summary")
    
    # Generate dynamic insight based on data
    total_projects = len(filtered)
    df_share = (df_projects_count / total_projects * 100) if total_projects > 0 else 0
    fdi_share = (fdi_projects_count / total_projects * 100) if total_projects > 0 else 0
    
    if realization_rate and realization_rate < 0.5:
        realization_insight = "warning"
        realization_text = f"Portfolio realization rate is {format_pct(realization_rate)}, indicating significant implementation gaps between commitments and actual disbursements."
    elif realization_rate and realization_rate >= 0.75:
        realization_insight = "positive"
        realization_text = f"Strong portfolio performance with {format_pct(realization_rate)} realization rate, showing effective conversion of commitments to disbursements."
    else:
        realization_insight = "neutral"
        realization_text = f"Portfolio realization rate stands at {format_pct(realization_rate)}, reflecting moderate implementation progress."
    
    render_insight_box(realization_text, insight_type=realization_insight)

    # PRIMARY METRICS - Focused on the most important numbers
    st.markdown("### Portfolio Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_metric_with_context(
            label="Total Projects Tracked",
            value=f"{total_projects:,}",
            interpretation=f"{df_share:.0f}% Development Finance, {fdi_share:.0f}% FDI"
        )
    
    with col2:
        render_metric_with_context(
            label="Committed Capital",
            value=format_currency(committed_total),
            interpretation="Total pledged across all projects",
            help_text="Aggregated committed amounts in constant 2024 USD"
        )
    
    with col3:
        render_metric_with_context(
            label="Portfolio Realization",
            value=format_pct(realization_rate),
            interpretation="Share of commitments actually disbursed",
            help_text="Disbursed / Committed ratio"
        )

    # SECONDARY METRICS - Important but less prominent
    with st.expander("📊 Additional Portfolio Metrics", expanded=False):
        sec_col1, sec_col2, sec_col3 = st.columns(3)
        sec_col1.metric("Disbursed Capital", format_currency(disbursed_total))
        sec_col2.metric(
            "Median Time to Implementation",
            f"{median_implementation:,.0f} days" if pd.notna(median_implementation) else "N/A"
        )
        sec_col3.metric("DF vs FDI Split", f"{df_projects_count:,} / {fdi_projects_count:,}")

    render_section_divider("Key Patterns")

    # TREND ANALYSIS - With narrative
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
            
            # Calculate insight
            if len(yearly) >= 2:
                recent_committed = yearly.iloc[-1]["committed_usd"]
                prev_committed = yearly.iloc[-2]["committed_usd"]
                change_pct = ((recent_committed - prev_committed) / prev_committed * 100) if prev_committed else 0
                
                if abs(change_pct) > 20:
                    trend_insight = f"Notable {abs(change_pct):.0f}% {'increase' if change_pct > 0 else 'decrease'} in commitments from {int(yearly.iloc[-2]['year'])} to {int(yearly.iloc[-1]['year'])}"
                else:
                    trend_insight = "Commitment flows show relative stability in recent years"
            else:
                trend_insight = "Track how Chinese capital commitments and disbursements evolve over time"
            
            trend_fig = px.line(
                trend_long,
                x="year",
                y="usd",
                color="metric",
                markers=True,
                labels={"year": "Year", "usd": "USD (Constant 2024)", "metric": "Type"},
            )
            trend_fig.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                legend_title_text=""
            )
            
            render_chart_with_insight(
                fig=trend_fig,
                title="Capital Flow Trends",
                insight=trend_insight,
                methodology="Annual aggregation of committed and disbursed amounts across all projects in the current filter scope"
            )

    with right_col:
        concentration = sector_concentration_shares(filtered)
        if concentration.empty:
            st.info("Sector and committed values are missing.")
        else:
            # Calculate Herfindahl index for concentration insight
            shares_squared = (concentration["value"] / concentration["value"].sum()) ** 2
            hhi = shares_squared.sum()
            
            if hhi > 0.25:
                conc_insight = "High sector concentration - capital is heavily focused in a few sectors"
            elif hhi > 0.15:
                conc_insight = "Moderate diversification across sectors"
            else:
                conc_insight = "Well-diversified across multiple sectors"
            
            concentration_fig = px.pie(
                concentration,
                names="sector",
                values="value",
                hole=0.45,
            )
            concentration_fig.update_traces(textposition="inside", textinfo="percent+label")
            
            render_chart_with_insight(
                fig=concentration_fig,
                title="Sector Distribution",
                insight=conc_insight
            )

    # NAVIGATION GUIDANCE
    render_navigation_suggestions([
        {
            "page": "Development Finance",
            "reason": "Explore concessional loans, grants, and official development assistance patterns"
        },
        {
            "page": "FDI Overview",
            "reason": "Analyze commercial investment commitments and sectoral trends"
        }
    ])

    render_data_quality_panel(projects, quality_report)


# ==========================================
# LOCKED SECTION PAGES (DF)
# ==========================================

def render_locked_section_page(
    *,
    page_title: str,
    locked_type: str,
    page_key: str,
    renderer: SectionRenderer,
) -> None:
    """Render DF pages with improved narrative structure."""
    
    # Extract research question based on page
    research_questions = {
        "overview": "What is the scale and composition of Chinese development finance to Indonesia?",
        "spatial": "Where is Chinese development finance concentrated geographically?",
        "finance_delivery": "How are commitments structured, and what is the delivery timeline?",
        "impact_friction": "What implementation challenges and impacts are observed?"
    }
    
    render_page_header(
        title=page_title,
        research_question=research_questions.get(page_key),
        context=f"Analysis filtered to {locked_type} projects only"
    )

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)
    if projects.empty:
        st.warning(
            "No processed dataset detected. Add source files to `data/raw`, run `make etl`, "
            "then refresh the app."
        )
        render_data_quality_panel(projects, quality_report)
        return

    render_trust_metadata_strip(page_key, projects, filtered, quality_report)

    locked_frame = filter_by_locked_type(filtered, locked_type)

    if locked_frame.empty:
        st.info(f"No {locked_type} records match the current sidebar filters.")
        render_data_quality_panel(projects, quality_report)
        return

    renderer(locked_frame)
    render_data_quality_panel(projects, quality_report)


# ==========================================
# FDI PAGES - REDESIGNED
# ==========================================

def _render_locked_fdi_page_header(
    *, page_title: str, page_key: str
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Helper for FDI page headers with narrative context."""
    
    research_questions = {
        "overview": "What is the scale, sectoral composition, and temporal pattern of Chinese FDI commitments to Indonesia?",
        "spatial": "How is Chinese FDI distributed across Indonesian regions?",
        "trends": "What sectoral trends and investment patterns emerge over time?",
        "top_deals": "Which are the largest Chinese FDI commitments, and what sectors do they target?",
        "impact_friction": "How complete is our FDI data coverage, and where are the gaps?"
    }
    
    render_page_header(
        title=page_title,
        research_question=research_questions.get(page_key),
        context="Analysis of Chinese commercial FDI commitments (CAPEX, constant 2024 USD)"
    )

    projects, filtered, quality_report, _ = _load_page_state(show_finance_type=False)

    if projects.empty:
        st.warning(
            "No processed dataset detected. Add source files to `data/raw`, run `make etl`, "
            "then refresh the app."
        )
        render_data_quality_panel(projects, quality_report)
        return projects, pd.DataFrame(), quality_report

    render_trust_metadata_strip(page_key, projects, filtered, quality_report)

    locked_frame = filter_by_locked_type(filtered, "FDI")

    return projects, locked_frame, quality_report


def render_fdi_overview_page() -> None:
    """Redesigned FDI overview with narrative flow."""
    
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

    # Calculate key metrics
    total_projects = len(locked_frame)
    committed_total = pd.to_numeric(locked_frame["committed_usd"], errors="coerce").sum(min_count=1)
    
    # Sector analysis
    sector_committed = (
        locked_frame.groupby("sector", as_index=False)["committed_usd"]
        .apply(lambda x: pd.to_numeric(x, errors="coerce").sum(min_count=1))
    )
    top_sector = sector_committed.loc[sector_committed["committed_usd"].idxmax()] if not sector_committed.empty else None

    # EXECUTIVE SUMMARY
    if top_sector is not None and pd.notna(top_sector["committed_usd"]):
        top_sector_share = (top_sector["committed_usd"] / committed_total * 100) if committed_total else 0
        insight_text = f"Chinese FDI portfolio of {format_currency(committed_total)} across {total_projects:,} projects shows concentration in {top_sector['sector']} ({top_sector_share:.0f}% of total CAPEX)"
        render_insight_box(insight_text, insight_type="key")

    # PRIMARY METRICS
    st.markdown("### Portfolio Snapshot")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_metric_with_context(
            label="Total FDI Projects",
            value=f"{total_projects:,}",
            interpretation="Distinct Chinese investment commitments tracked"
        )
    
    with col2:
        render_metric_with_context(
            label="Total CAPEX Committed",
            value=format_currency(committed_total),
            interpretation="Capital expenditure in constant 2024 USD",
            help_text="Source: fDi Markets (Financial Times)"
        )
    
    with col3:
        if top_sector is not None:
            render_metric_with_context(
                label="Leading Sector",
                value=str(top_sector["sector"]),
                interpretation=f"{format_currency(top_sector['committed_usd'])} committed"
            )

    render_section_divider("Sectoral Breakdown")

    # Sector analysis with insights
    if not sector_committed.empty:
        sector_committed = sector_committed.sort_values("committed_usd", ascending=False).head(10)
        
        fig = px.bar(
            sector_committed,
            x="sector",
            y="committed_usd",
            labels={"committed_usd": "CAPEX (USD)", "sector": "Sector"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        
        # Generate sector insight
        if len(sector_committed) >= 3:
            top3_share = (sector_committed.head(3)["committed_usd"].sum() / committed_total * 100) if committed_total else 0
            sector_insight = f"Top 3 sectors account for {top3_share:.0f}% of total Chinese FDI CAPEX"
        else:
            sector_insight = "Sectoral distribution of Chinese commercial investment commitments"
        
        render_chart_with_insight(
            fig=fig,
            title="Top Sectors by CAPEX",
            insight=sector_insight
        )

    # Navigation suggestions
    render_navigation_suggestions([
        {
            "page": "Regional Distribution",
            "reason": "See geographic patterns across Indonesian islands"
        },
        {
            "page": "Trends & Sectors",
            "reason": "Explore temporal evolution and sectoral dynamics"
        },
        {
            "page": "Top Deals",
            "reason": "Review the 20 largest individual projects"
        }
    ])

    render_data_quality_panel(projects, quality_report)


def render_fdi_trends_and_sectors_page() -> None:
    """Placeholder - keeping original logic for now."""
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Trends & Sectors",
        page_key="trends",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    st.info("Detailed temporal and sectoral analysis - to be implemented with narrative components")
    render_data_quality_panel(projects, quality_report)


def render_fdi_top_deals_page() -> None:
    """Redesigned top deals page with context."""
    
    projects, locked_frame, quality_report = _render_locked_fdi_page_header(
        page_title="FDI - Top Deals",
        page_key="top_deals",
    )
    if projects.empty:
        return
    if locked_frame.empty:
        st.info("No FDI records match the current filters.")
        render_data_quality_panel(projects, quality_report)
        return

    analysis = locked_frame.copy()
    analysis["committed_usd_num"] = pd.to_numeric(analysis["committed_usd"], errors="coerce")
    
    top_deals = analysis[
        ["project_name", "sector", "province", "year", "committed_usd", "status"]
    ].copy()
    top_deals["committed_usd_num"] = analysis["committed_usd_num"]
    top_deals = top_deals.sort_values("committed_usd_num", ascending=False).head(20)
    
    # Calculate insights
    total_top20 = top_deals["committed_usd_num"].sum()
    total_all = analysis["committed_usd_num"].sum()
    top20_share = (total_top20 / total_all * 100) if total_all else 0
    
    render_insight_box(
        f"The 20 largest deals represent {format_currency(total_top20)}, accounting for {top20_share:.0f}% of total FDI CAPEX",
        insight_type="key"
    )
    
    top_deals = top_deals.drop(columns=["committed_usd_num"])
    top_deals["committed_usd"] = pd.to_numeric(top_deals["committed_usd"], errors="coerce").apply(
        format_currency
    )

    st.markdown("### Top 20 Projects by Committed CAPEX")
    st.dataframe(top_deals, use_container_width=True, hide_index=True)

    with st.expander("💡 How to interpret this table"):
        st.markdown("""
        - **CAPEX size** indicates project scale and strategic importance
        - **Sector** shows investment priorities
        - **Province** reveals geographic targeting
        - **Status** indicates implementation stage
        """)

    render_data_quality_panel(projects, quality_report)


def render_fdi_data_coverage_page() -> None:
    """Redesigned data coverage page with clearer context."""
    
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

    st.markdown("""
    **Understanding data quality:** FDI data comes from commercial sources (fDi Markets) with different 
    field availability than development finance datasets. This page shows completion rates for key analytical fields.
    """)

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
    
    # Generate insight
    low_coverage_fields = coverage[coverage["non_null_pct"] < 50]["field"].tolist()
    
    if low_coverage_fields:
        render_insight_box(
            f"Data gaps exist in: {', '.join(low_coverage_fields[:3])}. These limitations affect spatial and temporal analyses.",
            insight_type="warning"
        )

    st.markdown("### Field Completion Rates")
    st.dataframe(coverage, use_container_width=True, hide_index=True)
    
    st.caption(
        "**Note:** FDI source coverage differs from development finance datasets. "
        "Fields with low completion are excluded from relevant analysis pages."
    )

    render_data_quality_panel(projects, quality_report)


def render_fdi_region_distribution_page() -> None:
    """Redesigned regional distribution with narrative flow."""
    
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

    # Data
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
    
    # Generate regional insight
    df_specified = df[df["region"] != "Not Specified"].copy()
    top_region = df_specified.loc[df_specified["china_capex_2024usd_b"].idxmax()]
    top_region_share = (top_region["china_capex_2024usd_b"] / (total_china - not_spec) * 100)
    
    render_insight_box(
        f"{top_region['region']} leads with ${top_region['china_capex_2024usd_b']:.1f}B ({top_region_share:.0f}% of specified locations), "
        f"while {(not_spec/total_china)*100:.0f}% of CAPEX lacks geographic specificity",
        insight_type="key"
    )

    # Metrics
    st.markdown("### Regional Portfolio Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total China CAPEX", f"${total_china:,.2f}B", help="Constant 2024 USD, billions")
    c2.metric("Location Not Specified", f"${not_spec:,.2f}B")
    c3.metric("Share Not Specified", f"{(not_spec / total_china) * 100:,.1f}%")

    st.divider()

    include_unspecified = st.toggle(
        "Include 'Not Specified' in charts",
        value=False,  # Changed default to False for cleaner initial view
        key="fdi_region_include_unspecified",
        help="Toggle to show/hide projects without specified locations"
    )

    plot_df = df.copy()
    if not include_unspecified:
        plot_df = plot_df[plot_df["region"] != "Not Specified"].copy()

    plot_df = plot_df.sort_values("china_capex_2024usd_b", ascending=False)

    # Bar chart with insights
    fig = px.bar(
        plot_df,
        x="region",
        y="china_capex_2024usd_b",
        text=plot_df["china_capex_2024usd_b"].map(lambda x: f"${x:.1f}B"),
        labels={"china_capex_2024usd_b": "China CAPEX (Billions, 2024 USD)", "region": "Region"},
    )
    fig.update_layout(
        xaxis_tickangle=-20,
        showlegend=False
    )
    fig.update_traces(textposition="outside")
    
    render_chart_with_insight(
        fig=fig,
        title="Chinese FDI by Region",
        insight=f"{'Sumatra and Java together account for nearly 50% of Chinese FDI' if not include_unspecified else 'Geographic distribution shows concentration in major economic centers'}",
        methodology="Regional aggregates based on provincial location data from fDi Markets. CAPEX in constant 2024 USD."
    )

    # Pie chart
    fig2 = px.pie(
        plot_df,
        names="region",
        values="china_capex_2024usd_b",
    )
    fig2.update_traces(textposition="inside", textinfo="percent+label")
    
    render_chart_with_insight(
        fig=fig2,
        title="Regional Share of Chinese FDI",
        insight="Proportional view highlights relative investment concentration across Indonesian archipelago"
    )

    # Detailed table
    render_section_divider("Detailed Regional Breakdown")
    
    show_context = st.toggle(
        "Compare with all-source FDI",
        value=False,
        key="fdi_region_show_context",
        help="View Chinese FDI in context of total foreign investment to each region"
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
            "China's Share"
        ]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.caption(
        "**Data notes:** Regions aggregate provincial data. 'Not Specified' includes projects "
        "without clear geographic assignment. All values in constant 2024 USD billions."
    )

    # Navigation
    render_navigation_suggestions([
        {
            "page": "Trends & Sectors",
            "reason": "Analyze how regional patterns evolved over time"
        },
        {
            "page": "Top Deals",
            "reason": "See which major projects drive these regional totals"
        }
    ])

    render_data_quality_panel(projects, quality_report)
