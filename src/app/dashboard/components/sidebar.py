"""
Sidebar Component
=================
Navigation sidebar with process-flow phases and quick stats.
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


def _inject_sidebar_css():
    """Inject CSS for sidebar visual hierarchy."""
    st.markdown(f"""
<style>
    /* Breadcrumb on main content */
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
        cursor: pointer;
    }}
    .breadcrumb .bc-phase:hover {{
        text-decoration: underline;
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

    st.sidebar.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    # Navigation state — query params are the source of truth (survive reload/hot-reload)
    qp = st.query_params.get("page", "Overview")
    if 'selected_nav_item' not in st.session_state or st.session_state.selected_nav_item != qp:
        st.session_state.selected_nav_item = qp

    current = st.session_state.selected_nav_item

    # Render phase buttons
    for phase in PROCESS_PHASES:
        phase_id = phase["id"]
        icon = phase["icon"]
        label = phase["label"]
        page = phase["page"]
        children = phase.get("children", [])

        # Check if current page is in this phase
        is_active_phase = (current == page)
        if children:
            child_labels = [c[0] for c in children]
            is_active_phase = is_active_phase or current in child_labels

        # Active phase gets a styled indicator
        if is_active_phase:
            st.sidebar.markdown(f"""
            <div style="
                background: rgba(232, 115, 90, 0.15);
                border-left: 3px solid {COLORS['primary']};
                border-radius: 0 6px 6px 0;
                padding: 0.45rem 0.7rem;
                margin: 0.15rem 0;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            ">
                <span style="font-size: 1.1rem;">{icon}</span>
                <span style="font-size: 0.85rem; font-weight: 600; color: white; font-family: 'Instrument Sans', sans-serif;">{label}</span>
            </div>
            """, unsafe_allow_html=True)
            # Still need a button for hub page navigation (hidden-ish, but functional)
            if current != page and children:
                if st.sidebar.button(
                    f"  ← Back to {label} Hub",
                    key=f"phase_{phase_id}",
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state.selected_nav_item = page
                    st.query_params["page"] = page
                    st.rerun()
        else:
            # Inactive phase — standard button
            btn_label = f"{icon}  {label}"
            if st.sidebar.button(
                btn_label,
                key=f"phase_{phase_id}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state.selected_nav_item = page
                st.query_params["page"] = page
                st.rerun()

        # Show children if this phase is active
        if is_active_phase and children:
            for child_label, child_id, child_desc in children:
                is_child_active = (current == child_label)
                if is_child_active:
                    # Active child — styled indicator
                    st.sidebar.markdown(f"""
                    <div style="
                        margin-left: 0.9rem;
                        border-left: 2px solid {COLORS['primary']};
                        padding: 0.3rem 0 0.3rem 0.75rem;
                        margin-bottom: 0.1rem;
                    ">
                        <span style="font-size: 0.82rem; color: {COLORS['primary']}; font-weight: 600;">
                            {child_label}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Inactive child — small button
                    if st.sidebar.button(
                        f"    {child_label}",
                        key=f"nav_{child_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.selected_nav_item = child_label
                        st.query_params["page"] = child_label
                        st.rerun()

            # Small spacer after children
            st.sidebar.markdown('<div style="height: 0.3rem;"></div>', unsafe_allow_html=True)

    st.sidebar.markdown("---")

    # Compact quick stats
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
    if st.sidebar.button("📖  Documentation", key="nav_docs", use_container_width=True, type="secondary"):
        st.session_state.selected_nav_item = "Documentation"
        st.query_params["page"] = "Documentation"
        st.rerun()

    # Version
    version = get_version()
    st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 0.5rem 0; margin-top: 0.5rem;">
        <span style="font-size: 0.65rem; color: rgba(255,255,255,0.3);">v{version}</span>
    </div>
    """, unsafe_allow_html=True)

    return st.session_state.selected_nav_item


def render_breadcrumb(current_page: str):
    """Render a breadcrumb showing Phase > Page for child pages.

    Call this at the top of child pages (before render_page_header) to show
    navigation context. Clicking the phase name navigates to the hub page.
    """
    # Find which phase this page belongs to
    for phase in PROCESS_PHASES:
        children = phase.get("children", [])
        child_labels = [c[0] for c in children]
        if current_page in child_labels:
            phase_label = phase["label"]
            phase_page = phase["page"]
            st.markdown(f"""
            <div class="breadcrumb">
                <span class="bc-phase" onclick="
                    const url = new URL(window.location);
                    url.searchParams.set('page', '{phase_page}');
                    window.location = url;
                ">{phase_label}</span>
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
    """Render a page header with optional refresh button.

    Args:
        title: Page title
        subtitle: Optional subtitle
        show_refresh: Whether to show refresh button
    """
    header_image = _get_header_image(title)

    # Build header HTML
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
    """Render a section header.

    Args:
        title: Section title
        icon: Optional emoji icon
    """
    icon_html = f"{icon} " if icon else ""
    st.markdown(f'<h2 class="sub-header">{icon_html}{title}</h2>', unsafe_allow_html=True)
