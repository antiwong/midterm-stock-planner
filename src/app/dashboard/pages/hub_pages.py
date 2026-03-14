"""
Hub Pages — Process-flow landing pages
=======================================
Each hub describes the available analyses in a phase and links to detail pages.
"""

import streamlit as st
from ..components.sidebar import render_page_header
from ..config import PROCESS_PHASES, COLORS


def _navigate_to(page_label: str):
    """Navigate to a page."""
    st.session_state.selected_nav_item = page_label
    st.query_params["page"] = page_label
    st.rerun()


def _render_hub(phase_id: str):
    """Render a generic hub page for a process phase."""
    phase = next((p for p in PROCESS_PHASES if p["id"] == phase_id), None)
    if not phase:
        st.error(f"Phase '{phase_id}' not found.")
        return

    render_page_header(phase["label"], phase["description"])

    children = phase.get("children", [])
    if not children:
        st.info("No sub-pages in this phase.")
        return

    # Render cards in a 2-column grid
    cols_per_row = 2
    for i in range(0, len(children), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(children):
                break
            label, identifier, description = children[idx]
            with col:
                st.markdown(f"""
                <div style="
                    background: {COLORS['card_bg']};
                    border: 1px solid {COLORS['card_border']};
                    border-radius: 12px;
                    padding: 1.5rem;
                    margin-bottom: 1rem;
                    min-height: 120px;
                    transition: border-color 0.2s ease, box-shadow 0.2s ease;
                    cursor: pointer;
                ">
                    <div style="font-size: 1.05rem; font-weight: 600; color: {COLORS['dark']}; font-family: 'DM Sans', sans-serif; margin-bottom: 0.5rem;">
                        {label}
                    </div>
                    <div style="font-size: 0.85rem; color: {COLORS['muted']}; line-height: 1.5;">
                        {description}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Open {label}", key=f"hub_open_{identifier}", use_container_width=True):
                    _navigate_to(label)


def render_setup_hub():
    """Render the Setup phase hub page."""
    _render_hub("setup")


def render_analyze_hub():
    """Render the Analyze phase hub page."""
    _render_hub("analyze")


def render_build_hub():
    """Render the Build phase hub page."""
    _render_hub("build")


def render_monitor_hub():
    """Render the Monitor phase hub page."""
    _render_hub("monitor")


def render_review_hub():
    """Render the Review phase hub page."""
    _render_hub("review")
