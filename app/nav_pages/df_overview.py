try:
    from app.nav_pages.common import render_locked_section_page
    from app.sections import render_overview_section
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_locked_section_page
    from sections import render_overview_section

render_locked_section_page(
    page_title="Development Finance - Overview",
    locked_type="DF",
    page_key="overview",
    renderer=render_overview_section,
)
