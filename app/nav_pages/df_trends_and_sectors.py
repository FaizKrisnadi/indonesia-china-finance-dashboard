try:
    from app.nav_pages.common import render_df_trends_and_sectors_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_df_trends_and_sectors_page

render_df_trends_and_sectors_page()
