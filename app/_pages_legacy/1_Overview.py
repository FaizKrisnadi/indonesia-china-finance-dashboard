from __future__ import annotations

import streamlit as st

from app.sections import render_overview_section
from app.shared import (
    apply_global_filters,
    load_data_quality_cached,
    load_projects_cached,
    render_data_quality_panel,
    render_global_sidebar_filters,
    render_trust_metadata_strip,
)

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("Overview")

projects = load_projects_cached()
quality_report = load_data_quality_cached()
filters = render_global_sidebar_filters(projects)
filtered = apply_global_filters(projects, filters)
render_trust_metadata_strip("overview", projects, filtered, quality_report)

render_overview_section(filtered)

render_data_quality_panel(projects, quality_report)
