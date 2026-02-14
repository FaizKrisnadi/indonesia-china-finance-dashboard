import streamlit as st

try:
    from app.theme import apply_global_styles
except ModuleNotFoundError:
    from theme import apply_global_styles

st.set_page_config(
    page_title="Indonesia-China Finance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_global_styles()

home_page = st.Page("nav_pages/home_page.py", title="Home", default=True)

df_pages = [
    st.Page("nav_pages/df_overview.py", title="Overview"),
    st.Page("nav_pages/df_spatial_explorer.py", title="Spatial Explorer"),
    st.Page("nav_pages/df_trends_and_sectors.py", title="Trends & Sectors"),
    st.Page("nav_pages/df_finance_and_delivery.py", title="Finance and Delivery"),
    st.Page("nav_pages/df_impact_and_friction.py", title="Impact and Friction"),
]

fdi_pages = [
    st.Page("nav_pages/fdi_overview.py", title="Overview"),
    st.Page("nav_pages/fdi_region_page.py", title="Regional distribution"),
    st.Page("nav_pages/fdi_spatial_explorer.py", title="Trends & Sectors"),
    st.Page("nav_pages/fdi_finance_and_delivery.py", title="Top Deals"),
    st.Page("nav_pages/fdi_impact_and_friction.py", title="Data Coverage"),
]

nav = st.navigation(
    {
        "": [home_page],
        "Development Finance": df_pages,
        "FDI": fdi_pages,
    },
    position="sidebar",
)
nav.run()
