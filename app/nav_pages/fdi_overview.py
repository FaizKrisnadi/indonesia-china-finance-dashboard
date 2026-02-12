try:
    from app.nav_pages.common import render_fdi_overview_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_fdi_overview_page

render_fdi_overview_page()
