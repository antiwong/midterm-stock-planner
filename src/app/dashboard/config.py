"""
Dashboard Configuration & Theming
=================================
Centralized configuration for page settings and custom CSS.
"""

import streamlit as st

from .utils import load_ui_settings

# Color palette
COLORS = {
    'primary': '#E8735A',      # Warm coral (vibrant AnuPuccin accent)
    'secondary': '#E9C7B8',    # Muted clay
    'accent': '#CFE6DA',       # Soft mint
    'success': '#BFE6CF',      # Pastel green
    'warning': '#F6D2AE',      # Pastel orange
    'danger': '#F4C3C3',       # Pastel red
    'info': '#C7D7F2',         # Pastel blue
    'dark': '#2b2a2f',         # Charcoal ink
    'light': '#f6f2f3',        # Soft paper
    'muted': '#7a6f73',        # Warm gray
    'card_bg': '#ffffff',
    'card_border': '#ece3e7',
}

# Chart color schemes
CHART_COLORS = {
    'sequential': ['#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff'],
    'categorical': ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
    'diverging': ['#ef4444', '#f87171', '#fca5a5', '#e2e8f0', '#a5b4fc', '#818cf8', '#6366f1'],
    'heatmap': 'RdYlGn',
}


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="QuantaAlpha",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': '# QuantaAlpha\nMid-term portfolio intelligence and analysis.'
        }
    )


def inject_custom_css():
    """Inject custom CSS for improved styling."""
    ui_settings = load_ui_settings()
    if not ui_settings.get("enable_custom_css", True):
        return

    dark_mode = ui_settings.get("dark_mode", False)
    sidebar_bg_start = ui_settings.get("sidebar_bg_start", COLORS["dark"])
    sidebar_bg_end = ui_settings.get("sidebar_bg_end", "#0f172a")
    sidebar_text_color = ui_settings.get("sidebar_text_color", COLORS["light"])
    sidebar_label_color = ui_settings.get("sidebar_label_color", "#e2e8f0")
    sidebar_hover_bg = ui_settings.get("sidebar_hover_bg", "rgba(99, 102, 241, 0.2)")
    sidebar_button_bg = ui_settings.get("sidebar_button_bg", "rgba(30, 41, 59, 0.8)")
    sidebar_button_border = ui_settings.get("sidebar_button_border", "rgba(255, 255, 255, 0.2)")
    primary_color = ui_settings.get("primary_color", COLORS["primary"])
    secondary_color = ui_settings.get("secondary_color", COLORS["secondary"])
    accent_color = ui_settings.get("accent_color", COLORS["accent"])
    card_radius = ui_settings.get("card_radius", 12)
    font_scale = ui_settings.get("font_scale", 1.0)
    
    # Dark mode color overrides
    if dark_mode:
        bg_color = "#1a1a1f"
        text_color = "#f5f5f7"
        card_bg = "#2a2a2f"
        card_border = "#3a3a3f"
        muted_color = "#9a9a9f"
    else:
        bg_color = COLORS['light']
        text_color = COLORS['dark']
        card_bg = COLORS['card_bg']
        card_border = COLORS['card_border']
        muted_color = COLORS['muted']

    st.markdown(f"""
<style>
    /* =========================================================
       1. CSS Variables & Fonts
       ========================================================= */
    :root {{
        --primary-color: {primary_color};
        --secondary-color: {secondary_color};
        --accent-color: {accent_color};
        --card-radius: {card_radius}px;
        --font-scale: {font_scale};
    }}

    @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

    /* =========================================================
       2. Global / Reset
       ========================================================= */
    .stApp {{
        font-family: 'Source Sans 3', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: calc(16px * var(--font-scale));
        background-color: {bg_color};
        color: {text_color};
    }}

    .block-container {{
        padding-top: 1rem !important;
    }}

    h1, h2, h3 {{
        letter-spacing: -0.015em;
    }}

    hr {{
        border: none;
        height: 1px;
        background: {card_border};
        margin: 1.25rem 0;
    }}

    /* =========================================================
       3. Hide Streamlit Chrome (header, footer, toolbar, nav)
       ========================================================= */
    header[data-testid="stHeader"],
    div[data-testid="stHeader"],
    .stHeader,
    header,
    div[class*="stHeader"],
    div[class*="st-header"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
    }}

    #MainMenu, #stMainMenu {{
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
    }}

    footer, footer[data-testid="stFooter"] {{
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
    }}

    .stDecoration, div[data-testid="stDecoration"],
    div[data-testid="stToolbar"] {{
        display: none !important;
        height: 0 !important;
    }}

    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    section[data-testid="stSidebar"] nav,
    section[data-testid="stSidebar"] ul[data-testid="stSidebarNavItems"] {{
        display: none !important;
        height: 0 !important;
        overflow: hidden !important;
    }}

    /* =========================================================
       4. Sidebar
       ========================================================= */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {sidebar_bg_start} 0%, {sidebar_bg_end} 100%);
    }}

    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio label span,
    [data-testid="stSidebar"] [data-testid="stRadio"],
    [data-testid="stSidebar"] [data-testid="stRadio"] > div,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [role="radiogroup"] label,
    [data-testid="stSidebar"] [role="radiogroup"] label p,
    [data-testid="stSidebar"] [role="radiogroup"] label span {{
        color: {sidebar_text_color} !important;
    }}

    [data-testid="stSidebar"] .stRadio > div {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 0.5rem;
    }}

    [data-testid="stSidebar"] .stRadio > div > label:hover {{
        background: {sidebar_hover_bg};
        border-radius: 6px;
    }}

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stNumberInput label {{
        color: {COLORS['light']} !important;
    }}

    [data-testid="stSidebar"] [data-testid="stMetricLabel"],
    [data-testid="stSidebar"] [data-testid="metric-container"] label {{
        color: {sidebar_label_color} !important;
    }}

    [data-testid="stSidebar"] [data-testid="stMetricValue"],
    [data-testid="stSidebar"] [data-testid="metric-container"],
    [data-testid="stSidebar"] [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {sidebar_text_color} !important;
    }}

    /* Sidebar buttons — aggressive overrides for all Streamlit button variants */
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] .stButton button,
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] [data-testid*="BaseButton"],
    [data-testid="stSidebar"] [class*="BaseButton"],
    [data-testid="stSidebar"] [class*="stButton"] button {{
        color: white !important;
        background-color: #1e293b !important;
        background: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        font-weight: 500 !important;
    }}

    [data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] .stButton button:hover,
    [data-testid="stSidebar"] [data-testid*="BaseButton"]:hover,
    [data-testid="stSidebar"] [class*="BaseButton"]:hover {{
        background-color: #334155 !important;
        background: #334155 !important;
        border-color: rgba(232, 115, 90, 0.5) !important;
        color: white !important;
    }}

    /* Ensure ALL text inside sidebar buttons is white */
    [data-testid="stSidebar"] button *,
    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span,
    [data-testid="stSidebar"] button div,
    [data-testid="stSidebar"] .stButton button *,
    [data-testid="stSidebar"] [data-testid*="BaseButton"] *,
    [data-testid="stSidebar"] [class*="BaseButton"] * {{
        color: white !important;
    }}

    /* Primary variant */
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] button[kind="primary"] {{
        background: {COLORS['primary']} !important;
        background-color: {COLORS['primary']} !important;
        border: 1px solid {COLORS['primary']} !important;
    }}

    [data-testid="stSidebar"] [data-testid="stAlert"],
    [data-testid="stSidebar"] [data-testid="stAlert"] p {{
        background: rgba(255, 255, 255, 0.1) !important;
        color: {sidebar_text_color} !important;
    }}

    /* =========================================================
       5. Page Header
       ========================================================= */
    .page-header {{
        background: {card_bg if dark_mode else '#ffffff'};
        border: 1px solid {card_border};
        border-radius: var(--card-radius);
        padding: 0.6rem 1.1rem;
        box-shadow: 0 2px 8px rgba(43, 42, 47, 0.04);
        margin-bottom: 1.5rem;
        display: flex !important;
        visibility: visible !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 0.9rem !important;
        flex-direction: row !important;
    }}

    .page-subtitle {{
        color: {muted_color};
        margin-top: -0.15rem;
    }}

    .page-title-wrap {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0.15rem !important;
        align-items: flex-start !important;
        justify-content: center !important;
    }}

    .page-image {{
        max-width: 80px !important;
        width: 80px !important;
        height: 80px !important;
        flex-shrink: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    .page-image img {{
        max-height: 80px !important;
        max-width: 80px !important;
        width: 80px !important;
        height: 80px !important;
        object-fit: contain !important;
        margin: 0 !important;
        display: block !important;
    }}

    /* =========================================================
       6. Typography
       ========================================================= */
    .main-header {{
        font-family: 'Instrument Sans', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: {text_color};
        margin-bottom: 0;
        letter-spacing: -0.025em;
        line-height: 1.2;
    }}

    .sub-header {{
        font-family: 'Instrument Sans', sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: {text_color};
        margin: 2rem 0 1.75rem 0;
        padding-bottom: 0.6rem;
        border-bottom: 2px solid var(--primary-color);
    }}

    .symbol-text, code, pre {{
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }}

    /* =========================================================
       7. Cards (Metric, Info, Stock)
       ========================================================= */
    .metric-card {{
        background: {COLORS['primary'] if not dark_mode else card_bg};
        padding: 0.85rem 1.1rem;
        border-radius: var(--card-radius);
        color: {COLORS['dark'] if not dark_mode else text_color};
        box-shadow: 0 8px 20px rgba(43, 42, 47, 0.08);
        transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.3s ease;
        min-height: 85px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        margin-bottom: 0.5rem;
    }}

    .metric-card:hover {{
        transform: scale(1.02);
        box-shadow: 0 16px 32px rgba(43, 42, 47, 0.14);
    }}

    .metric-card h3 {{
        font-size: 0.7rem; font-weight: 500; opacity: 0.7;
        margin: 0 0 0.3rem; padding: 0;
        text-transform: uppercase; letter-spacing: 0.06em; line-height: 1.1;
    }}

    .metric-card .value {{
        font-size: 1.65rem; font-weight: 700;
        font-family: 'Instrument Sans', sans-serif;
        margin: 0 0 0.15rem; padding: 0; line-height: 1.15; word-break: break-word;
    }}

    .metric-card .delta {{
        font-size: 0.72rem; opacity: 0.75; line-height: 1.1;
        word-break: break-word; margin: 0; padding: 0; min-height: 1.1em;
    }}

    .metric-card .delta.delta-empty {{
        visibility: hidden; min-height: 1.1em; height: 1.1em;
    }}

    .info-card {{
        background: {card_bg};
        padding: 0.85rem 1.1rem;
        border-radius: var(--card-radius);
        border: 1px solid {card_border};
        box-shadow: 0 4px 16px rgba(43, 42, 47, 0.05);
        transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.3s ease;
        line-height: 1.2; word-break: break-word; min-height: 90px;
        display: flex; flex-direction: column; justify-content: center;
        color: {text_color}; margin-bottom: 0.5rem;
    }}

    .info-card:hover {{
        transform: scale(1.015);
        box-shadow: 0 8px 24px rgba(43, 42, 47, 0.1);
    }}

    .stock-card {{
        background: {card_bg};
        padding: 1rem 1.15rem;
        border-radius: var(--card-radius);
        border-left: 4px solid {COLORS['primary']};
        margin: 0.65rem 0;
        box-shadow: 0 4px 14px rgba(43, 42, 47, 0.06);
        transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.3s ease;
        line-height: 1.3;
    }}

    .stock-card:hover {{
        transform: scale(1.01);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.15);
    }}

    .stock-card.positive {{ border-left-color: {COLORS['success']}; }}
    .stock-card.negative {{ border-left-color: {COLORS['danger']}; }}
    .stock-card .ticker {{ font-size: 1.05rem; font-weight: 700; color: {text_color}; line-height: 1.2; }}
    .stock-card .sector {{ font-size: 0.7rem; color: {muted_color}; text-transform: uppercase; letter-spacing: 0.04em; line-height: 1.2; }}

    /* =========================================================
       8. Status Badges & Progress
       ========================================================= */
    .status-badge {{
        display: inline-flex; align-items: center;
        padding: 0.25rem 0.75rem; border-radius: 9999px;
        font-size: 0.75rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.025em;
    }}
    .status-badge.completed {{ background: rgba(16, 185, 129, 0.1); color: {COLORS['success']}; }}
    .status-badge.running   {{ background: rgba(59, 130, 246, 0.1); color: {COLORS['info']}; }}
    .status-badge.failed    {{ background: rgba(239, 68, 68, 0.1); color: {COLORS['danger']}; }}
    .status-badge.pending   {{ background: rgba(245, 158, 11, 0.1); color: {COLORS['warning']}; }}

    .progress-step {{
        display: flex; align-items: center; gap: 0.75rem; padding: 1rem;
        background: {COLORS['card_bg']}; border-radius: 10px;
        margin: 0.5rem 0; border: 1px solid {COLORS['card_border']};
    }}
    .progress-step.active  {{ border-color: {COLORS['primary']}; background: rgba(99, 102, 241, 0.05); }}
    .progress-step.complete {{ border-color: {COLORS['success']}; background: rgba(16, 185, 129, 0.05); }}
    .progress-step .step-icon {{
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; background: {COLORS['muted']}; color: white;
    }}
    .progress-step.active .step-icon  {{ background: {COLORS['primary']}; }}
    .progress-step.complete .step-icon {{ background: {COLORS['success']}; }}

    .positive {{ color: {COLORS['success']} !important; font-weight: 600; }}
    .negative {{ color: {COLORS['danger']} !important; font-weight: 600; }}
    .neutral  {{ color: {COLORS['muted']}; }}

    /* =========================================================
       9. Buttons
       ========================================================= */
    .stButton > button, .stDownloadButton > button {{
        border-radius: var(--card-radius) !important;
        padding: 0.5rem 1rem !important;
        margin-top: 0.25rem !important;
        font-weight: 600;
        transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.25s ease;
    }}

    .stButton > button:hover {{
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(10, 132, 255, 0.2);
    }}

    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
        background: var(--primary-color) !important;
        border-color: var(--primary-color) !important;
    }}
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
        background: var(--secondary-color) !important;
        border-color: var(--secondary-color) !important;
    }}
    .stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {{
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
    }}
    .stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover {{
        background: rgba(99, 102, 241, 0.08) !important;
    }}

    div[data-testid="column"] .stButton {{
        margin-top: 0.35rem !important;
    }}

    /* =========================================================
       10. Layout & Spacing
       ========================================================= */
    div[data-testid="column"] {{
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }}
    div[data-testid="column"]:first-child {{ padding-left: 0 !important; }}
    div[data-testid="column"]:last-child  {{ padding-right: 0 !important; }}

    /* =========================================================
       11. Data Tables
       ========================================================= */
    .stDataFrame {{
        border-radius: var(--card-radius) !important;
        overflow: hidden !important;
        border: 1px solid {card_border} !important;
        background-color: {card_bg} !important;
        font-family: 'Source Sans 3', sans-serif;
        font-size: 0.875rem;
    }}

    .stDataFrame table {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
    }}

    .stDataFrame th {{
        background-color: {COLORS['light'] if not dark_mode else card_bg} !important;
        color: {text_color} !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }}

    .stDataFrame td {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-size: 0.9rem !important;
    }}

    .stDataFrame tr:hover {{
        background-color: {COLORS['light'] if not dark_mode else card_bg} !important;
    }}

    /* =========================================================
       12. Expanders & Tabs
       ========================================================= */
    .streamlit-expanderHeader {{
        font-weight: 600;
        color: {text_color};
        background: {card_bg if dark_mode else COLORS['light']};
        border-radius: 8px;
    }}

    .streamlit-expanderContent {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: {card_bg if dark_mode else '#f1ecef'};
        padding: 0.5rem;
        border-radius: 10px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1rem;
        color: {text_color} !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: {COLORS['primary']} !important;
        color: {COLORS['dark'] if not dark_mode else text_color} !important;
    }}

    /* =========================================================
       13. Metrics
       ========================================================= */
    [data-testid="stMetricValue"] {{ font-weight: 700; color: {text_color}; }}
    [data-testid="stMetricLabel"] {{ color: {muted_color} !important; }}
    [data-testid="stMetricDelta"]     {{ color: {text_color} !important; }}
    [data-testid="stMetricDelta"] svg {{ display: none; }}

    /* =========================================================
       14. Code Blocks & Alerts
       ========================================================= */
    .stCodeBlock {{
        font-family: 'JetBrains Mono', monospace;
        border-radius: 8px;
        background-color: {card_bg if dark_mode else '#f8f9fa'} !important;
        color: {text_color} !important;
        border: 1px solid {card_border} !important;
    }}

    .stAlert {{
        border-radius: 10px;
        border-left-width: 4px;
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}

    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="InfoIcon"])         {{ background-color: {card_bg if dark_mode else '#e8f4f8'} !important; }}
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="CheckCircleIcon"])   {{ background-color: {card_bg if dark_mode else '#d4edda'} !important; }}
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="WarningIcon"])       {{ background-color: {card_bg if dark_mode else '#fff3cd'} !important; }}
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="ErrorIcon"])         {{ background-color: {card_bg if dark_mode else '#f8d7da'} !important; }}

    /* =========================================================
       15. Form Inputs (text, number, select, date, etc.)
       ========================================================= */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}

    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}

    .stSelectbox > div > div:focus-within {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}

    .stSelectbox [data-baseweb="select"] {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}

    .stSlider > div > div > div {{ background: {primary_color}; }}
    .stSlider > div > div > div[data-testid="stThumbValue"] {{ color: {text_color} !important; }}

    .stCheckbox > label,
    .stRadio > label,
    .stToggle > label,
    label {{
        color: {text_color} !important;
    }}

    .stFileUploader > div {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}

    /* Catch-all for remaining inputs */
    input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]):not([type="file"]):not([type="range"]) {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="input"] textarea {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}

    ul[role="listbox"],
    li[role="option"],
    div[data-baseweb="popover"] {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}

    /* =========================================================
       16. Markdown text
       ========================================================= */
    .stMarkdown,
    .stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th {{
        color: {text_color} !important;
    }}

    /* =========================================================
       17. Scrollbar & Animations
       ========================================================= */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: {bg_color}; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb {{ background: {muted_color}; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {primary_color}; }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .animate-fade-in {{ animation: fadeIn 0.3s ease-out; }}

    /* =========================================================
       18. Responsive
       ========================================================= */
    @media (max-width: 768px) {{
        .main-header {{ font-size: 1.5rem; }}
        .sub-header  {{ font-size: 1.25rem; margin: 1rem 0; }}
        .metric-card {{ padding: 0.5rem 0.65rem; min-height: 70px; }}
        .metric-card .value {{ font-size: 1.2rem; }}
        .metric-card h3 {{ font-size: 0.7rem; }}
        .info-card {{ padding: 0.5rem 0.65rem; min-height: 70px; }}
        .stock-card {{ padding: 0.65rem 0.85rem; }}
        .page-header {{ padding: 0.3rem 0.6rem !important; flex-direction: column; align-items: flex-start !important; }}
        .page-image {{ max-width: 60px !important; width: 60px !important; margin-bottom: 0.5rem; }}
        div[data-testid="column"] {{ padding-left: 0.25rem !important; padding-right: 0.25rem !important; }}
        .stButton > button {{ min-height: 44px !important; padding: 0.6rem 1.2rem !important; }}
        .block-container {{ padding-left: 0.5rem !important; padding-right: 0.5rem !important; }}
    }}

    @media (min-width: 769px) and (max-width: 1024px) {{
        .main-header {{ font-size: 1.65rem; }}
        div[data-testid="column"] {{ padding-left: 0.4rem !important; padding-right: 0.4rem !important; }}
    }}
</style>
""", unsafe_allow_html=True)


# Navigation pages - organized by workflow groups
# Main workflow (sequential)
MAIN_WORKFLOW = [
    ("Overview", "overview"),
    ("Run Analysis", "run_analysis"),
    ("Portfolio Builder", "portfolio_builder"),
    ("Reports", "reports"),
    ("Portfolio Analysis", "portfolio_analysis"),
    ("Comprehensive Analysis", "comprehensive_analysis"),
    ("Purchase Triggers", "purchase_triggers"),
    ("Analysis Runs", "analysis_runs"),
    ("AI Insights", "ai_insights"),
]

# Standalone tools
STANDALONE_TOOLS = [
    ("Watchlist Manager", "watchlist_manager"),
    ("Stock Explorer", "stock_explorer"),
    ("Trigger Backtester", "trigger_backtester"),
    ("Strategy Optimizer", "strategy_optimizer"),
    ("Regression Testing", "regression_testing"),
    ("Compare Runs", "compare_runs"),
    ("Advanced Comparison", "advanced_comparison"),
]

# Advanced Analytics
ADVANCED_ANALYTICS = [
    ("Event Analysis", "event_analysis"),
    ("Tax Optimization", "tax_optimization"),
    ("Monte Carlo", "monte_carlo"),
    ("Turnover Analysis", "turnover_analysis"),
    ("Earnings Calendar", "earnings_calendar"),
    ("Real-Time Monitoring", "realtime_monitoring"),
    ("Recommendation Tracking", "recommendation_tracking"),
]

# Utilities
UTILITIES = [
    ("Performance Monitoring", "performance_monitoring"),
    ("Alert Management", "alert_management"),
    ("Report Templates", "report_templates"),
    ("Fundamentals Status", "fundamentals_status"),
    ("Data Quality", "data_quality"),
    ("Documentation", "documentation"),
    ("Settings", "settings"),
]

# Combined list for backward compatibility
PAGES = MAIN_WORKFLOW + STANDALONE_TOOLS + ADVANCED_ANALYTICS + UTILITIES

# Process-flow navigation phases
# Each phase groups related pages and has a hub page
PROCESS_PHASES = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "icon": "📊",
        "description": "Portfolio overview and key metrics",
        "page": "Overview",  # Direct page, no hub needed
    },
    {
        "id": "setup",
        "label": "Setup",
        "icon": "⚙️",
        "description": "Configure watchlists, data sources, and settings",
        "page": "Setup Hub",
        "children": [
            ("Watchlist Manager", "watchlist_manager", "Define stock universes and watchlists"),
            ("Data Quality", "data_quality", "Validate data completeness and accuracy"),
            ("Fundamentals Status", "fundamentals_status", "Check fundamental data coverage"),
            ("Settings", "settings", "Configure system preferences"),
        ],
    },
    {
        "id": "analyze",
        "label": "Analyze",
        "icon": "🔬",
        "description": "Run analyses, backtest strategies, and test features",
        "page": "Analyze Hub",
        "children": [
            ("Run Analysis", "run_analysis", "Execute walk-forward backtests on watchlists"),
            ("Regression Testing", "regression_testing", "Test features one-by-one for marginal contribution"),
            ("Strategy Optimizer", "strategy_optimizer", "Optimize MACD/RSI parameters via Bayesian search"),
            ("Trigger Backtester", "trigger_backtester", "Backtest buy/sell trigger signals"),
            ("Stock Explorer", "stock_explorer", "Browse individual stock scores and features"),
            ("AI Insights", "ai_insights", "AI-generated commentary on analysis results"),
        ],
    },
    {
        "id": "build",
        "label": "Build",
        "icon": "🏗️",
        "description": "Construct and optimize portfolios",
        "page": "Build Hub",
        "children": [
            ("Portfolio Builder", "portfolio_builder", "Build risk-optimized portfolios from scored stocks"),
            ("Purchase Triggers", "purchase_triggers", "Generate actionable buy/sell signals"),
            ("Tax Optimization", "tax_optimization", "Tax-loss harvesting and wash sale analysis"),
        ],
    },
    {
        "id": "monitor",
        "label": "Monitor",
        "icon": "📡",
        "description": "Track portfolio performance and market signals",
        "page": "Monitor Hub",
        "children": [
            ("Real-Time Monitoring", "realtime_monitoring", "Live portfolio and market tracking"),
            ("Recommendation Tracking", "recommendation_tracking", "Track recommendation accuracy over time"),
            ("Alert Management", "alert_management", "Configure price and event alerts"),
            ("Earnings Calendar", "earnings_calendar", "Upcoming earnings dates and estimates"),
            ("Notifications", "notifications", "View notification history"),
        ],
    },
    {
        "id": "review",
        "label": "Review",
        "icon": "📋",
        "description": "Compare results, generate reports, and deep-dive analytics",
        "page": "Review Hub",
        "children": [
            ("Portfolio Analysis", "portfolio_analysis", "Analyze portfolio composition and risk"),
            ("Comprehensive Analysis", "comprehensive_analysis", "Full-spectrum analysis suite"),
            ("Compare Runs", "compare_runs", "Compare analysis runs side-by-side"),
            ("Advanced Comparison", "advanced_comparison", "Statistical comparison of run results"),
            ("Reports", "reports", "Generate PDF and markdown reports"),
            ("Report Templates", "report_templates", "Manage report templates"),
            ("Analysis Runs", "analysis_runs", "Browse run history and results"),
            ("Event Analysis", "event_analysis", "Analyze market event impacts"),
            ("Monte Carlo", "monte_carlo", "Monte Carlo portfolio simulations"),
            ("Turnover Analysis", "turnover_analysis", "Portfolio turnover and rebalancing costs"),
            ("Performance Monitoring", "performance_monitoring", "System performance metrics"),
        ],
    },
]
