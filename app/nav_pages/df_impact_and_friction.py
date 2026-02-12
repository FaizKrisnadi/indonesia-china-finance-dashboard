try:
    from app.nav_pages.common import render_locked_section_page
    from app.sections import render_impact_and_friction_section
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_locked_section_page
    from sections import render_impact_and_friction_section

render_locked_section_page(
    page_title="Development Finance - Impact and Friction",
    locked_type="DF",
    page_key="impact_friction",
    renderer=render_impact_and_friction_section,
)
