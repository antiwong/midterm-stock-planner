"""
Sidebar Component
=================
Navigation sidebar with process-flow phases and quick stats.
Uses native st.button with on_click callbacks for reliable navigation.
"""

import streamlit as st
from typing import Optional
import base64
from pathlib import Path

from ..config import PAGES, MAIN_WORKFLOW, STANDALONE_TOOLS, ADVANCED_ANALYTICS, UTILITIES, COLORS, PROCESS_PHASES
from ..data import load_runs, get_available_run_folders
from ..utils import get_project_root, get_version
from .search import render_global_search
from .notifications import render_notification_bell, NotificationManager


def _navigate_to(page: str):
    """Callback to navigate to a page via query params."""
    st.query_params["page"] = page
    st.session_state.selected_nav_item = page


def _inject_sidebar_css():
    """Inject minimal CSS for sidebar nav and breadcrumbs."""
    st.markdown(f"""
<style>
    /* ---- Breadcrumb on main content ---- */
    .breadcrumb {{
        font-size: 0.78rem;
        color: {COLORS['muted']};
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }}
    .breadcrumb .bc-phase {{
        color: {COLORS['primary']};
        font-weight: 600;
    }}
    .breadcrumb .bc-sep {{
        color: {COLORS['card_border']};
    }}
    .breadcrumb .bc-page {{
        color: {COLORS['dark']};
        font-weight: 500;
    }}
</style>
""", unsafe_allow_html=True)


def render_sidebar() -> str:
    """Render process-flow sidebar navigation and return selected page."""
    _inject_sidebar_css()

    # Logo/Title
    logo_path = get_project_root() / "assets" / "long-game-logo.svg"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
    else:
        st.sidebar.markdown("""
        <div style="text-align: center; padding: 1.25rem 0 0.75rem;">
            <div style="font-size: 1.6rem; font-weight: 700; color: white; font-family: 'Instrument Sans', sans-serif; letter-spacing: -0.03em;">
                QuantaAlpha
            </div>
            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.45); letter-spacing: 0.15em; text-transform: uppercase; margin-top: 0.2rem;">
                Portfolio Intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Navigation state — query params are the source of truth
    qp = st.query_params.get("page", "Overview")
    if 'selected_nav_item' not in st.session_state or st.session_state.selected_nav_item != qp:
        st.session_state.selected_nav_item = qp

    current = st.session_state.selected_nav_item

    # Render navigation phases
    for phase in PROCESS_PHASES:
        icon = phase["icon"]
        label = phase["label"]
        page = phase["page"]
        children = phase.get("children", [])

        # Check if current page is in this phase
        is_active_phase = (current == page)
        if children:
            child_labels = [c[0] for c in children]
            is_active_phase = is_active_phase or current in child_labels

        # Phase button
        phase_label = f"{icon}  {label}"
        if is_active_phase:
            phase_label = f"{icon}  **{label}**"

        st.sidebar.button(
            phase_label,
            key=f"nav_phase_{phase['id']}",
            on_click=_navigate_to,
            args=(page,),
            use_container_width=True,
        )

        # Children (only if active phase)
        if is_active_phase and children:
            for child_label, child_id, child_desc in children:
                is_child_active = (current == child_label)
                display = f"    → **{child_label}**" if is_child_active else f"    → {child_label}"
                st.sidebar.button(
                    display,
                    key=f"nav_child_{child_id}",
                    on_click=_navigate_to,
                    args=(child_label,),
                    use_container_width=True,
                )

    st.sidebar.divider()

    # Quick stats
    runs = load_runs()
    if runs:
        completed = sum(1 for r in runs if r['status'] == 'completed')
        st.sidebar.markdown(f"""
        <div style="padding: 0.5rem 0.75rem; background: rgba(255,255,255,0.04); border-radius: 8px; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.7rem; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.1em;">Runs</span>
                <span style="font-size: 0.85rem; color: white; font-weight: 600;">{completed}/{len(runs)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Documentation link
    st.sidebar.button(
        "📖  Documentation",
        key="nav_docs",
        on_click=_navigate_to,
        args=("Documentation",),
        use_container_width=True,
    )

    # Version
    version = get_version()
    st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 0.5rem 0; margin-top: 0.5rem;">
        <span style="font-size: 0.65rem; color: rgba(255,255,255,0.3);">v{version}</span>
    </div>
    """, unsafe_allow_html=True)

    return st.session_state.selected_nav_item


def render_breadcrumb(current_page: str):
    """Render a breadcrumb showing Phase > Page for child pages."""
    for phase in PROCESS_PHASES:
        children = phase.get("children", [])
        child_labels = [c[0] for c in children]
        if current_page in child_labels:
            phase_label = phase["label"]
            st.markdown(f"""
            <div class="breadcrumb">
                <span class="bc-phase">{phase_label}</span>
                <span class="bc-sep">›</span>
                <span class="bc-page">{current_page}</span>
            </div>
            """, unsafe_allow_html=True)
            return


def _get_header_image(title: str) -> Optional[str]:
    """Get a header image path based on title."""
    title_lower = title.lower()
    mapping = {
        "overview": "header-analytics.svg",
        "the long game": "header-analytics.svg",
        "run analysis": "header-analytics.svg",
        "analysis runs": "header-analytics.svg",
        "comprehensive analysis": "header-analytics.svg",
        "portfolio analysis": "header-portfolio.svg",
        "portfolio builder": "header-portfolio.svg",
        "reports": "header-report.svg",
        "report templates": "header-report.svg",
        "watchlist": "header-watchlist.svg",
        "stock explorer": "header-data.svg",
        "ai insights": "header-ai.svg",
        "compare runs": "header-analytics.svg",
        "advanced comparison": "header-analytics.svg",
        "event analysis": "header-calendar.svg",
        "tax optimization": "header-analytics.svg",
        "monte carlo": "header-analytics.svg",
        "turnover analysis": "header-analytics.svg",
        "earnings calendar": "header-calendar.svg",
        "real-time monitoring": "header-analytics.svg",
        "recommendation tracking": "header-analytics.svg",
        "alert management": "header-analytics.svg",
        "fundamentals status": "header-data.svg",
        "documentation": "header-report.svg",
        "settings": "header-settings.svg",
        "setup": "header-settings.svg",
        "analyze": "header-analytics.svg",
        "build": "header-portfolio.svg",
        "monitor": "header-analytics.svg",
        "review": "header-report.svg",
    }

    for key, filename in mapping.items():
        if key in title_lower:
            image_path = get_project_root() / "assets" / filename
            if image_path.exists():
                return str(image_path)
    return None


def _encode_image(image_path: str) -> str:
    """Encode image to base64 for inline HTML."""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        return ""


def render_page_header(title: str, subtitle: Optional[str] = None, show_refresh: bool = True):
    """Render a page header with optional refresh button."""
    header_image = _get_header_image(title)

    image_html = ""
    if header_image:
        try:
            encoded = _encode_image(header_image)
            if encoded:
                image_html = f'<div class="page-image"><img src="data:image/svg+xml;base64,{encoded}" alt="header" /></div>'
        except Exception:
            pass

    title_html = f'<div class="page-title-wrap"><h1 class="main-header">{title}</h1>'
    if subtitle:
        title_html += f'<p class="page-subtitle">{subtitle}</p>'
    title_html += '</div>'

    st.markdown(
        f'<div class="page-header">{image_html}{title_html}</div>',
        unsafe_allow_html=True
    )


def render_section_header(title: str, icon: str = ""):
    """Render a section header."""
    icon_html = f"{icon} " if icon else ""
    st.markdown(f'<h2 class="sub-header">{icon_html}{title}</h2>', unsafe_allow_html=True)
