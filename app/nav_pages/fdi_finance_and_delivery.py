try:
    from app.nav_pages.common import render_fdi_top_deals_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_fdi_top_deals_page

render_fdi_top_deals_page()
