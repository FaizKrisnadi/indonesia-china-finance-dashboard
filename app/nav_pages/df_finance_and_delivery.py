try:
    from app.nav_pages.common import render_locked_section_page
    from app.sections import render_finance_and_delivery_section
except (ModuleNotFoundError, ImportError):
    from nav_pages.common import render_locked_section_page
    from sections import render_finance_and_delivery_section

render_locked_section_page(
    page_title="Development Finance - Finance and Delivery",
    locked_type="DF",
    page_key="finance_delivery",
    renderer=render_finance_and_delivery_section,
)
