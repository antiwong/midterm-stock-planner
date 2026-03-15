"""
Sidebar Component
=================
Navigation sidebar with process-flow phases and quick stats.
Uses HTML links with query-param navigation to avoid Streamlit button styling issues.
"""

import streamlit as st
from typing import Optional
import base64
from pathlib import Path
from urllib.parse import quote

from ..config import PAGES, MAIN_WORKFLOW, STANDALONE_TOOLS, ADVANCED_ANALYTICS, UTILITIES, COLORS, PROCESS_PHASES
from ..data import load_runs, get_available_run_folders
from ..utils import get_project_root, get_version
from .search import render_global_search
from .notifications import render_notification_bell, NotificationManager


def _nav_href(page_label: str) -> str:
    """Return a query-param URL for navigating to a page."""
    return f"?page={quote(page_label)}"


def _inject_sidebar_css():
    """Inject CSS for sidebar nav links and breadcrumbs."""
    st.markdown(f"""
<style>
    /* ---- Sidebar nav links (<a> tags, not st.button) ---- */
    a.nav-phase,
    a.nav-phase:link,
    a.nav-phase:visited {{
        display: flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.55rem 0.8rem;
        margin: 0.2rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s ease;
        text-decoration: none !important;
        color: rgba(255, 255, 255, 0.75) !important;
        font-family: 'Instrument Sans', sans-serif;
        font-size: 0.88rem;
        font-weight: 500;
        letter-spacing: -0.01em;
    }}
    a.nav-phase:hover {{
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.95) !important;
    }}
    a.nav-phase .phase-icon {{
        font-size: 1.05rem;
        flex-shrink: 0;
    }}

    /* Active phase */
    a.nav-phase.active,
    a.nav-phase.active:link,
    a.nav-phase.active:visited {{
        background: rgba(232, 115, 90, 0.18);
        border-left: 3px solid {COLORS['primary']};
        border-radius: 0 6px 6px 0;
        color: white !important;
        font-weight: 600;
    }}

    /* Child page links */
    a.nav-child,
    a.nav-child:link,
    a.nav-child:visited {{
        display: block;
        padding: 0.35rem 0.8rem 0.35rem 2.4rem;
        margin: 0.05rem 0;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.2s ease;
        text-decoration: none !important;
        font-size: 0.82rem;
        color: rgba(255, 255, 255, 0.55) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        margin-left: 1rem;
    }}
    a.nav-child:hover {{
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.85) !important;
        border-left-color: rgba(255, 255, 255, 0.2);
    }}
    a.nav-child.active,
    a.nav-child.active:link,
    a.nav-child.active:visited {{
        color: {COLORS['primary']} !important;
        font-weight: 600;
        border-left: 2px solid {COLORS['primary']};
        background: rgba(232, 115, 90, 0.08);
    }}

    /* Back-to-hub link */
    a.nav-back,
    a.nav-back:link,
    a.nav-back:visited {{
        display: block;
        padding: 0.3rem 0.8rem 0.3rem 2.4rem;
        margin: 0.05rem 0 0.15rem 1rem;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.4) !important;
        cursor: pointer;
        text-decoration: none !important;
        transition: color 0.2s ease;
    }}
    a.nav-back:hover {{
        color: rgba(255, 255, 255, 0.7) !important;
    }}

    /* Separator */
    .nav-separator {{
        height: 1px;
        background: rgba(255, 255, 255, 0.08);
        margin: 0.75rem 0.5rem;
    }}

    /* Footer link (docs) */
    a.nav-footer-link,
    a.nav-footer-link:link,
    a.nav-footer-link:visited {{
        display: block;
        padding: 0.4rem 0.8rem;
        margin: 0.2rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s ease;
        text-decoration: none !important;
        font-size: 0.82rem;
        color: rgba(255, 255, 255, 0.55) !important;
    }}
    a.nav-footer-link:hover {{
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.85) !important;
    }}

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

    # Navigation state — query params are the source of truth
    qp = st.query_params.get("page", "Overview")
    if 'selected_nav_item' not in st.session_state or st.session_state.selected_nav_item != qp:
        st.session_state.selected_nav_item = qp

    current = st.session_state.selected_nav_item

    # Build the entire nav as one HTML block per phase
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

        active_cls = " active" if is_active_phase else ""

        # Phase link (<a href>)
        html = f"""
        <a class="nav-phase{active_cls}" href="{_nav_href(page)}">
            <span class="phase-icon">{icon}</span>
            {label}
        </a>
        """

        # Children (only if active phase)
        if is_active_phase and children:
            # Back to hub link (if on a child page)
            if current != page:
                html += f"""
                <a class="nav-back" href="{_nav_href(page)}">← {label} Hub</a>
                """

            for child_label, child_id, child_desc in children:
                is_child_active = (current == child_label)
                child_cls = " active" if is_child_active else ""
                html += f"""
                <a class="nav-child{child_cls}" href="{_nav_href(child_label)}">{child_label}</a>
                """

            html += '<div style="height: 0.3rem;"></div>'

        st.sidebar.markdown(html, unsafe_allow_html=True)

    # Separator
    st.sidebar.markdown('<div class="nav-separator"></div>', unsafe_allow_html=True)

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
    st.sidebar.markdown(f"""
    <a class="nav-footer-link" href="{_nav_href('Documentation')}">📖  Documentation</a>
    """, unsafe_allow_html=True)

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
            phase_page = phase["page"]
            st.markdown(f"""
            <div class="breadcrumb">
                <a class="bc-phase" href="{_nav_href(phase_page)}" style="text-decoration:none;">{phase_label}</a>
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
