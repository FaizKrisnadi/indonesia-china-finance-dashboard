try:
    from app.nav_pages.common import render_fdi_data_coverage_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_fdi_data_coverage_page

render_fdi_data_coverage_page()
