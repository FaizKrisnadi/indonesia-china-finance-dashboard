try:
    from app.nav_pages.common import render_home_page
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_home_page

render_home_page()
