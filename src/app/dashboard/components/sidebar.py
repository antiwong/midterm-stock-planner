"""
Sidebar Component
=================
Navigation sidebar with process-flow phases and quick stats.
Uses st.radio for navigation — already styled for dark sidebar in config.py CSS.
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
    """Inject CSS for sidebar nav and breadcrumbs."""
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

    # Build phase options with icons
    phase_options = []
    phase_page_map = {}  # display label -> page value
    for phase in PROCESS_PHASES:
        display = f"{phase['icon']}  {phase['label']}"
        phase_options.append(display)
        phase_page_map[display] = phase["page"]

    # Find current phase index
    current_phase_idx = 0
    for i, phase in enumerate(PROCESS_PHASES):
        if current == phase["page"]:
            current_phase_idx = i
            break
        children = phase.get("children", [])
        if children and current in [c[0] for c in children]:
            current_phase_idx = i
            break

    # Phase radio
    selected_phase_display = st.sidebar.radio(
        "Navigation",
        phase_options,
        index=current_phase_idx,
        key="nav_phase_radio",
        label_visibility="collapsed",
    )

    selected_phase_page = phase_page_map[selected_phase_display]
    active_phase = PROCESS_PHASES[phase_options.index(selected_phase_display)]

    # If phase changed (user clicked a different phase), navigate to its hub
    if selected_phase_page != active_phase["page"]:
        pass  # shouldn't happen
    children = active_phase.get("children", [])

    # Determine the target page
    target_page = selected_phase_page

    # If this phase has children, show child radio
    if children:
        child_options = [f"  {active_phase['label']} Hub"]  # Hub as first option
        child_page_map = {child_options[0]: active_phase["page"]}
        for child_label, child_id, child_desc in children:
            child_options.append(f"  {child_label}")
            child_page_map[f"  {child_label}"] = child_label

        # Find current child index
        child_idx = 0
        for i, opt in enumerate(child_options):
            if child_page_map[opt] == current:
                child_idx = i
                break

        selected_child_display = st.sidebar.radio(
            f"{active_phase['label']} pages",
            child_options,
            index=child_idx,
            key=f"nav_child_radio_{active_phase['id']}",
            label_visibility="collapsed",
        )

        target_page = child_page_map[selected_child_display]

    # Update navigation state
    if target_page != current:
        st.query_params["page"] = target_page
        st.session_state.selected_nav_item = target_page
        st.rerun()

    st.sidebar.divider()

    # Quick stats
    runs = load_runs()
    if runs:
        completed = sum(1 for r in runs if r['status'] == 'completed')
        st.sidebar.metric("Completed Runs", f"{completed}/{len(runs)}")

    # Version
    version = get_version()
    st.sidebar.caption(f"v{version}")

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
