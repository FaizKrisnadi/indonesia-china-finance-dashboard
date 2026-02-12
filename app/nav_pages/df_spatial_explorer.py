try:
    from app.nav_pages.common import render_locked_section_page
    from app.sections import render_spatial_section
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_locked_section_page
    from sections import render_spatial_section

render_locked_section_page(
    page_title="Development Finance - Spatial Explorer",
    locked_type="DF",
    page_key="spatial",
    renderer=render_spatial_section,
)
