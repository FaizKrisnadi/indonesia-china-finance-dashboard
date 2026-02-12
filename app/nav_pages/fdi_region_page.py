try:
    from app.nav_pages.common import render_fdi_region_distribution_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_fdi_region_distribution_page

render_fdi_region_distribution_page()
