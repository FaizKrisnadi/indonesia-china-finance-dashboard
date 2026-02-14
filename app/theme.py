from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

BASE_FONT = "'Lato', sans-serif"
PLOTLY_TEMPLATE_NAME = "dashboard_dark"

THEME_COLORS = {
    "bg": "#0f141d",
    "surface_1": "#161d29",
    "surface_2": "#1c2431",
    "border": "#2d3a4d",
    "text": "#e6edf5",
    "muted": "#a8b4c6",
    "link": "#7eb4ff",
    "focus": "#9bc5ff",
    "grid": "rgba(182, 198, 220, 0.22)",
    "axis": "rgba(182, 198, 220, 0.38)",
    "geo_country_border": "rgba(189, 203, 223, 0.5)",
    "insight_bg": "#1b2636",
    "insight_border": "#5d9eff",
    "warning_bg": "#332416",
    "warning_border": "#efb16f",
    "success_bg": "#163026",
    "success_border": "#56c49a",
    "neutral_bg": "#1a2331",
    "neutral_border": "#7888a1",
    "chart_primary": "#61a7ff",
    "chart_secondary": "#f2b168",
    "chart_tertiary": "#65c89f",
    "chart_quaternary": "#d191f0",
    "chart_quinary": "#87d4d8",
    "chart_senary": "#f29cb1",
}

CHART_SEQUENCE = [
    THEME_COLORS["chart_primary"],
    THEME_COLORS["chart_secondary"],
    THEME_COLORS["chart_tertiary"],
    THEME_COLORS["chart_quaternary"],
]

QUALITATIVE_SEQUENCE = [
    THEME_COLORS["chart_primary"],
    THEME_COLORS["chart_secondary"],
    THEME_COLORS["chart_tertiary"],
    THEME_COLORS["chart_quaternary"],
    THEME_COLORS["chart_quinary"],
    THEME_COLORS["chart_senary"],
]

MAP_POINT_RGBA = [97, 167, 255, 185]


def _build_plotly_template() -> go.layout.Template:
    return go.layout.Template(
        layout={
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"family": BASE_FONT, "size": 12, "color": THEME_COLORS["text"]},
            "colorway": QUALITATIVE_SEQUENCE,
            "legend": {
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": THEME_COLORS["text"]},
            },
            "xaxis": {
                "gridcolor": THEME_COLORS["grid"],
                "linecolor": THEME_COLORS["axis"],
                "tickcolor": THEME_COLORS["axis"],
                "zeroline": False,
            },
            "yaxis": {
                "gridcolor": THEME_COLORS["grid"],
                "linecolor": THEME_COLORS["axis"],
                "tickcolor": THEME_COLORS["axis"],
                "zeroline": False,
            },
            "geo": {
                "bgcolor": "rgba(0,0,0,0)",
                "landcolor": THEME_COLORS["surface_1"],
                "subunitcolor": THEME_COLORS["geo_country_border"],
                "countrycolor": THEME_COLORS["geo_country_border"],
                "coastlinecolor": THEME_COLORS["geo_country_border"],
                "showland": True,
                "showlakes": False,
            },
            "polar": {
                "bgcolor": "rgba(0,0,0,0)",
                "radialaxis": {
                    "gridcolor": THEME_COLORS["grid"],
                    "linecolor": THEME_COLORS["axis"],
                },
                "angularaxis": {"gridcolor": THEME_COLORS["grid"]},
            },
        }
    )


def _ensure_plotly_theme() -> None:
    if PLOTLY_TEMPLATE_NAME not in pio.templates:
        pio.templates[PLOTLY_TEMPLATE_NAME] = _build_plotly_template()
    pio.templates.default = PLOTLY_TEMPLATE_NAME


def apply_standard_chart_layout(fig: go.Figure, *, legend_horizontal: bool = False) -> None:
    _ensure_plotly_theme()
    fig.update_layout(
        template=PLOTLY_TEMPLATE_NAME,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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

    fig.update_xaxes(showgrid=True, gridcolor=THEME_COLORS["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=THEME_COLORS["grid"], zeroline=False)


def _build_global_css() -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;500;700;900&display=swap');

:root {{
  --bg: {THEME_COLORS["bg"]};
  --surface-1: {THEME_COLORS["surface_1"]};
  --surface-2: {THEME_COLORS["surface_2"]};
  --border: {THEME_COLORS["border"]};
  --text: {THEME_COLORS["text"]};
  --muted: {THEME_COLORS["muted"]};
  --link: {THEME_COLORS["link"]};
  --focus: {THEME_COLORS["focus"]};
}}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {{
  background: var(--bg);
  color: var(--text);
}}

html, body, .stApp, [data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="stHeader"], [data-testid="stToolbar"], .stMarkdown, .stText, .stMetric, .stCaption, .stAlert, .stButton button, .stDownloadButton button, .stTextInput input, .stSelectbox, .stMultiSelect, .stSlider, .stNumberInput input, .stDateInput input, textarea, input, label, select, option, div[data-baseweb], .js-plotly-plot .plotly text {{
  font-family: {BASE_FONT} !important;
}}

[data-testid="stSidebar"] {{
  background: var(--surface-1);
  border-right: 1px solid var(--border);
}}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
  background: var(--surface-1);
}}

[data-testid="stSidebar"] * {{
  color: var(--text);
}}

[data-testid="stSidebar"] hr {{
  border-color: var(--border);
}}

[data-testid="stAppViewBlockContainer"], .block-container {{
  max-width: 1200px;
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  padding-left: 1.4rem;
  padding-right: 1.4rem;
}}

.stMarkdown h1 {{
  color: var(--text);
  font-size: 2.3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 0.55rem;
  overflow-wrap: anywhere;
}}

.stMarkdown h2 {{
  color: var(--text);
  font-size: 1.7rem;
  font-weight: 650;
  margin-top: 1.45rem;
  margin-bottom: 0.7rem;
  overflow-wrap: anywhere;
}}

.stMarkdown h3 {{
  color: var(--text);
  font-size: 1.2rem;
  font-weight: 620;
  margin-top: 1.1rem;
  margin-bottom: 0.55rem;
  overflow-wrap: anywhere;
}}

p, li, span, .stCaption {{
  color: var(--text);
}}

a {{
  color: var(--link) !important;
}}

a:hover {{
  color: #a4cbff !important;
}}

[data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stAlertContainer"] > div, [data-testid="stDataFrame"], [data-testid="stDataEditor"], div[data-baseweb="select"], [data-testid="stHorizontalBlock"] > div [data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
}}

[data-testid="stMetric"] {{
  padding: 0.9rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}}

[data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {{
  color: var(--muted);
}}

[data-testid="stMetricValue"] {{
  color: var(--text);
}}

[data-testid="stTabs"] [role="tablist"] {{
  gap: 0.35rem;
}}

[data-testid="stTabs"] [role="tab"] {{
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
  color: var(--muted);
  padding-top: 0.45rem;
  padding-bottom: 0.45rem;
}}

[data-testid="stTabs"] [aria-selected="true"] {{
  color: var(--text);
  border-bottom-color: var(--surface-2);
  background: var(--surface-2);
}}

[data-testid="stExpander"] details summary {{
  color: var(--text);
}}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
[data-baseweb="textarea"] {{
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
}}

[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stDateInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {{
  color: var(--muted) !important;
}}

[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button,
[data-testid="baseButton-secondary"] {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 10px;
  min-height: 2.6rem;
}}

[data-testid="stButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover {{
  border-color: var(--focus);
  color: var(--text);
}}

[data-testid="baseButton-primary"] {{
  background: {THEME_COLORS["chart_primary"]};
  color: #08111f;
  border-color: transparent;
}}

*:focus-visible,
[data-testid="stButton"] > button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[data-baseweb="select"] *:focus-visible {{
  outline: 2px solid var(--focus) !important;
  outline-offset: 1px;
  box-shadow: none !important;
}}

[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {{
  overflow: hidden;
}}

[data-testid="stDataFrame"] > div,
[data-testid="stDataEditor"] > div {{
  overflow-x: auto !important;
  border-radius: 11px;
}}

[data-testid="stDataFrame"] table,
[data-testid="stDataEditor"] table {{
  color: var(--text) !important;
}}

[data-testid="stDataFrame"] th,
[data-testid="stDataEditor"] th {{
  background: var(--surface-2) !important;
  color: var(--text) !important;
}}

[data-testid="stDataFrame"] td,
[data-testid="stDataEditor"] td {{
  background: var(--surface-1) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
}}

[data-testid="stDataFrame"] [role="gridcell"] {{
  color: var(--text) !important;
}}

.theme-breadcrumb {{
  color: var(--muted);
  font-weight: 500;
  margin-bottom: 0.1rem;
}}

.theme-question-box {{
  background: {THEME_COLORS["insight_bg"]};
  border-left: 4px solid {THEME_COLORS["insight_border"]};
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 10px;
  color: var(--text);
  margin: 0.8rem 0;
  padding: 0.95rem 1rem;
}}

.theme-insight-box {{
  border-left: 4px solid transparent;
  border-radius: 10px;
  margin: 1rem 0;
  padding: 0.9rem 1rem;
  border: 1px solid var(--border);
  color: var(--text);
}}

.theme-insight-key {{
  background: {THEME_COLORS["insight_bg"]};
  border-left-color: {THEME_COLORS["insight_border"]};
}}

.theme-insight-warning {{
  background: {THEME_COLORS["warning_bg"]};
  border-left-color: {THEME_COLORS["warning_border"]};
}}

.theme-insight-positive {{
  background: {THEME_COLORS["success_bg"]};
  border-left-color: {THEME_COLORS["success_border"]};
}}

.theme-insight-neutral {{
  background: {THEME_COLORS["neutral_bg"]};
  border-left-color: {THEME_COLORS["neutral_border"]};
}}

.theme-nav-card {{
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  min-height: 120px;
  padding: 0.9rem;
}}

.theme-nav-card__title {{
  color: var(--text);
  font-weight: 640;
}}

.theme-nav-card__body {{
  color: var(--muted);
  margin-top: 0.35rem;
}}

.theme-footer-credit {{
  color: var(--muted);
  font-size: 0.9rem;
  text-align: center;
}}

.theme-home-card {{
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
}}

.theme-home-card h4 {{
  margin: 0;
  color: var(--text);
}}

.theme-home-card p {{
  color: var(--muted);
  margin: 0.52rem 0 0.2rem 0;
}}

.trust-strip {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.3rem 0 0.6rem 0;
}}

.trust-pill {{
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.22rem 0.65rem;
  background: var(--surface-2);
  font-size: 0.82rem;
  color: var(--text);
}}

.current-view-sticky {{
  position: sticky;
  top: 0.25rem;
  z-index: 999;
  background: rgba(22, 29, 41, 0.96);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  margin-bottom: 0.7rem;
  backdrop-filter: blur(3px);
}}

.current-view-pill {{
  display: inline-block;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  margin-right: 0.3rem;
  margin-bottom: 0.3rem;
  font-size: 0.82rem;
  background: var(--surface-2);
  color: var(--text);
}}

.js-plotly-plot .plotly .main-svg {{
  background: transparent !important;
}}

@media (max-width: 640px) {{
  [data-testid="stAppViewBlockContainer"], .block-container {{
    padding-left: 0.72rem;
    padding-right: 0.72rem;
    padding-top: 1rem;
    padding-bottom: 1.3rem;
  }}

  .stMarkdown h1 {{
    font-size: 1.66rem;
    line-height: 1.25;
  }}

  .stMarkdown h2 {{
    font-size: 1.35rem;
    line-height: 1.3;
  }}

  .stMarkdown h3 {{
    font-size: 1.06rem;
    line-height: 1.3;
  }}

  [data-testid="stMetric"] {{
    padding: 0.72rem;
  }}

  [data-testid="stButton"] > button,
  [data-testid="stDownloadButton"] > button {{
    min-height: 2.75rem;
    padding: 0.55rem 0.8rem;
    width: 100%;
  }}

  [data-testid="stHorizontalBlock"] {{
    gap: 0.65rem !important;
  }}

  .theme-nav-card,
  .theme-home-card {{
    min-height: auto;
  }}

  [data-testid="stDataFrame"] table,
  [data-testid="stDataEditor"] table {{
    font-size: 0.86rem;
  }}
}}
</style>
"""


def apply_global_styles() -> None:
    if st.session_state.get("_dashboard_global_styles_injected", False):
        return

    _ensure_plotly_theme()
    css = _build_global_css()
    if hasattr(st, "html"):
        st.html(css)
    else:
        st.markdown(css, unsafe_allow_html=True)
    st.session_state["_dashboard_global_styles_injected"] = True
