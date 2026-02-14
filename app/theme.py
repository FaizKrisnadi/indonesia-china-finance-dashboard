from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

BASE_FONT = "'Lato', sans-serif"
PLOTLY_DARK_TEMPLATE_NAME = "dashboard_dark"
PLOTLY_LIGHT_TEMPLATE_NAME = "dashboard_light"

DARK_THEME_COLORS = {
    "bg": "#0f141d",
    "surface_1": "#161d29",
    "surface_2": "#1c2431",
    "surface_sticky": "rgba(22, 29, 41, 0.96)",
    "border": "#2d3a4d",
    "text": "#e6edf5",
    "muted": "#a8b4c6",
    "link": "#7eb4ff",
    "link_hover": "#a4cbff",
    "focus": "#9bc5ff",
    "grid": "rgba(182, 198, 220, 0.22)",
    "axis": "rgba(182, 198, 220, 0.38)",
    "geo_country_border": "rgba(138, 160, 189, 0.58)",
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
    "primary_button_text": "#08111f",
}

LIGHT_THEME_COLORS = {
    "bg": "#f7f9fc",
    "surface_1": "#ffffff",
    "surface_2": "#f1f5fb",
    "surface_sticky": "rgba(255, 255, 255, 0.95)",
    "border": "#d9e2f0",
    "text": "#1f2a3a",
    "muted": "#5f6f86",
    "link": "#1c83e1",
    "link_hover": "#146cba",
    "focus": "#3b82f6",
    "grid": "rgba(49, 67, 94, 0.15)",
    "axis": "rgba(49, 67, 94, 0.28)",
    "geo_country_border": "rgba(84, 102, 129, 0.42)",
    "insight_bg": "#eaf3ff",
    "insight_border": "#4f8fe6",
    "warning_bg": "#fff4e8",
    "warning_border": "#e7a65f",
    "success_bg": "#e9f8ee",
    "success_border": "#4caf7f",
    "neutral_bg": "#f3f6fb",
    "neutral_border": "#b8c6d9",
    "chart_primary": "#2e78da",
    "chart_secondary": "#dc8e3e",
    "chart_tertiary": "#2ea57a",
    "chart_quaternary": "#a05acb",
    "chart_quinary": "#2f9fa6",
    "chart_senary": "#d05f7f",
    "primary_button_text": "#ffffff",
}

# Backward-compatible export used by existing imports.
THEME_COLORS = DARK_THEME_COLORS

CHART_SEQUENCE = [
    DARK_THEME_COLORS["chart_primary"],
    DARK_THEME_COLORS["chart_secondary"],
    DARK_THEME_COLORS["chart_tertiary"],
    DARK_THEME_COLORS["chart_quaternary"],
]

QUALITATIVE_SEQUENCE = [
    DARK_THEME_COLORS["chart_primary"],
    DARK_THEME_COLORS["chart_secondary"],
    DARK_THEME_COLORS["chart_tertiary"],
    DARK_THEME_COLORS["chart_quaternary"],
    DARK_THEME_COLORS["chart_quinary"],
    DARK_THEME_COLORS["chart_senary"],
]

MAP_POINT_RGBA = [97, 167, 255, 185]


def _theme_type() -> str:
    try:
        theme_info = st.context.theme
        raw = str(theme_info.get("type", "")).strip().lower()
        if raw in {"light", "dark"}:
            return raw
    except Exception:  # noqa: BLE001
        pass
    return "light"


def is_dark_theme() -> bool:
    return _theme_type() == "dark"


def get_theme_colors() -> dict[str, str]:
    return DARK_THEME_COLORS if is_dark_theme() else LIGHT_THEME_COLORS


def _build_plotly_template(theme_colors: dict[str, str]) -> go.layout.Template:
    return go.layout.Template(
        layout={
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"family": BASE_FONT, "size": 12, "color": theme_colors["text"]},
            "colorway": QUALITATIVE_SEQUENCE,
            "legend": {
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": theme_colors["text"]},
            },
            "xaxis": {
                "gridcolor": theme_colors["grid"],
                "linecolor": theme_colors["axis"],
                "tickcolor": theme_colors["axis"],
                "zeroline": False,
            },
            "yaxis": {
                "gridcolor": theme_colors["grid"],
                "linecolor": theme_colors["axis"],
                "tickcolor": theme_colors["axis"],
                "zeroline": False,
            },
            "geo": {
                "bgcolor": "rgba(0,0,0,0)",
                "landcolor": theme_colors["surface_1"],
                "subunitcolor": theme_colors["geo_country_border"],
                "countrycolor": theme_colors["geo_country_border"],
                "coastlinecolor": theme_colors["geo_country_border"],
                "showland": True,
                "showlakes": False,
            },
            "polar": {
                "bgcolor": "rgba(0,0,0,0)",
                "radialaxis": {
                    "gridcolor": theme_colors["grid"],
                    "linecolor": theme_colors["axis"],
                },
                "angularaxis": {"gridcolor": theme_colors["grid"]},
            },
        }
    )


def _ensure_plotly_templates() -> None:
    if PLOTLY_DARK_TEMPLATE_NAME not in pio.templates:
        pio.templates[PLOTLY_DARK_TEMPLATE_NAME] = _build_plotly_template(DARK_THEME_COLORS)
    if PLOTLY_LIGHT_TEMPLATE_NAME not in pio.templates:
        pio.templates[PLOTLY_LIGHT_TEMPLATE_NAME] = _build_plotly_template(LIGHT_THEME_COLORS)


def _active_plotly_template_name() -> str:
    return PLOTLY_DARK_TEMPLATE_NAME if is_dark_theme() else PLOTLY_LIGHT_TEMPLATE_NAME


def _activate_plotly_default_template() -> None:
    template_name = _active_plotly_template_name()
    try:
        # On some deploy runtimes, this validation path can trigger early pandas imports.
        pio.templates.default = template_name
    except Exception:  # noqa: BLE001
        # Keep app startup resilient; per-figure layout still applies template styling.
        return


def apply_standard_chart_layout(fig: go.Figure, *, legend_horizontal: bool = False) -> None:
    _ensure_plotly_templates()
    active_colors = get_theme_colors()
    template_name = _active_plotly_template_name()
    _activate_plotly_default_template()

    try:
        fig.update_layout(
            template=template_name,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={"t": 40, "b": 40, "l": 40, "r": 40},
        )
    except Exception:  # noqa: BLE001
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": BASE_FONT, "size": 12, "color": active_colors["text"]},
            colorway=QUALITATIVE_SEQUENCE,
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

    fig.update_xaxes(showgrid=True, gridcolor=active_colors["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=active_colors["grid"], zeroline=False)


def _build_global_css() -> str:
    light = LIGHT_THEME_COLORS
    dark = DARK_THEME_COLORS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;500;700;900&display=swap');

:root {{
  --bg: {light["bg"]};
  --surface-1: {light["surface_1"]};
  --surface-2: {light["surface_2"]};
  --surface-sticky: {light["surface_sticky"]};
  --border: {light["border"]};
  --text: {light["text"]};
  --muted: {light["muted"]};
  --link: {light["link"]};
  --link-hover: {light["link_hover"]};
  --focus: {light["focus"]};
  --insight-bg: {light["insight_bg"]};
  --insight-border: {light["insight_border"]};
  --warning-bg: {light["warning_bg"]};
  --warning-border: {light["warning_border"]};
  --success-bg: {light["success_bg"]};
  --success-border: {light["success_border"]};
  --neutral-bg: {light["neutral_bg"]};
  --neutral-border: {light["neutral_border"]};
  --primary-btn-bg: {light["chart_primary"]};
  --primary-btn-text: {light["primary_button_text"]};
}}

@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: {dark["bg"]};
    --surface-1: {dark["surface_1"]};
    --surface-2: {dark["surface_2"]};
    --surface-sticky: {dark["surface_sticky"]};
    --border: {dark["border"]};
    --text: {dark["text"]};
    --muted: {dark["muted"]};
    --link: {dark["link"]};
    --link-hover: {dark["link_hover"]};
    --focus: {dark["focus"]};
    --insight-bg: {dark["insight_bg"]};
    --insight-border: {dark["insight_border"]};
    --warning-bg: {dark["warning_bg"]};
    --warning-border: {dark["warning_border"]};
    --success-bg: {dark["success_bg"]};
    --success-border: {dark["success_border"]};
    --neutral-bg: {dark["neutral_bg"]};
    --neutral-border: {dark["neutral_border"]};
    --primary-btn-bg: {dark["chart_primary"]};
    --primary-btn-text: {dark["primary_button_text"]};
  }}
}}

html[data-theme="dark"],
body[data-theme="dark"],
.stApp[data-theme="dark"],
[data-theme="dark"] {{
  --bg: {dark["bg"]};
  --surface-1: {dark["surface_1"]};
  --surface-2: {dark["surface_2"]};
  --surface-sticky: {dark["surface_sticky"]};
  --border: {dark["border"]};
  --text: {dark["text"]};
  --muted: {dark["muted"]};
  --link: {dark["link"]};
  --link-hover: {dark["link_hover"]};
  --focus: {dark["focus"]};
  --insight-bg: {dark["insight_bg"]};
  --insight-border: {dark["insight_border"]};
  --warning-bg: {dark["warning_bg"]};
  --warning-border: {dark["warning_border"]};
  --success-bg: {dark["success_bg"]};
  --success-border: {dark["success_border"]};
  --neutral-bg: {dark["neutral_bg"]};
  --neutral-border: {dark["neutral_border"]};
  --primary-btn-bg: {dark["chart_primary"]};
  --primary-btn-text: {dark["primary_button_text"]};
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
  color: var(--link-hover) !important;
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
  background: var(--primary-btn-bg);
  color: var(--primary-btn-text);
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
  background: var(--insight-bg);
  border-left: 4px solid var(--insight-border);
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
  background: var(--insight-bg);
  border-left-color: var(--insight-border);
}}

.theme-insight-warning {{
  background: var(--warning-bg);
  border-left-color: var(--warning-border);
}}

.theme-insight-positive {{
  background: var(--success-bg);
  border-left-color: var(--success-border);
}}

.theme-insight-neutral {{
  background: var(--neutral-bg);
  border-left-color: var(--neutral-border);
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
  background: var(--surface-sticky);
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

.js-plotly-plot .modebar {{
  display: none !important;
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
    _ensure_plotly_templates()
    _activate_plotly_default_template()

    if st.session_state.get("_dashboard_global_styles_injected", False):
        return

    css = _build_global_css()
    if hasattr(st, "html"):
        st.html(css)
    else:
        st.markdown(css, unsafe_allow_html=True)
    st.session_state["_dashboard_global_styles_injected"] = True
