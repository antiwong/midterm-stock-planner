"""
Dashboard Configuration & Theming
=================================
Centralized configuration for page settings and custom CSS.
"""

import streamlit as st

from .utils import load_ui_settings

# Color palette
COLORS = {
    'primary': '#F4B8A5',      # Soft peach (AnuPpuccin-inspired)
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
        page_title="The Long Game",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/yourusername/midterm-stock-planner',
            'Report a bug': 'https://github.com/yourusername/midterm-stock-planner/issues',
            'About': '# The Long Game\nMid-term portfolio intelligence and analysis.'
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
    :root {{
        --primary-color: {primary_color};
        --secondary-color: {secondary_color};
        --accent-color: {accent_color};
        --card-radius: {card_radius}px;
        --font-scale: {font_scale};
    }}

    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global Styles */
    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: calc(16px * var(--font-scale));
        background-color: {bg_color};
        color: {text_color};
    }}

    .block-container {{
        padding-top: 0.75rem;
    }}
    
    /* Hide Streamlit top bar/decorator - multiple selectors */
    header[data-testid="stHeader"],
    div[data-testid="stHeader"],
    .stHeader,
    header {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
    }}
    
    /* Hide menu and footer */
    #MainMenu,
    #stMainMenu {{
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
    }}
    
    footer,
    footer[data-testid="stFooter"] {{
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
    }}
    
    /* Hide Streamlit decorator */
    .stDecoration,
    div[data-testid="stDecoration"] {{
        display: none !important;
        height: 0 !important;
    }}
    
    /* Hide top toolbar */
    div[data-testid="stToolbar"] {{
        display: none !important;
    }}
    
    /* Adjust top padding since header is hidden */
    .block-container {{
        padding-top: 0.5rem !important;
    }}
    
    /* Hide Streamlit's header but NOT our page-header */
    div[class*="stHeader"],
    div[class*="st-header"] {{
        display: none !important;
    }}
    
    /* Ensure our page-header is visible */
    .page-header {{
        display: flex !important;
        visibility: visible !important;
    }}
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg_start};
    }}
    
    [data-testid="stSidebar"] * {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] label {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio label {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio label span {{
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
    
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
        color: {sidebar_label_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] button {{
        color: {sidebar_text_color} !important;
        background-color: {sidebar_button_bg} !important;
        border: 1px solid {sidebar_button_border} !important;
    }}
    
    [data-testid="stSidebar"] button:hover {{
        background-color: rgba(30, 41, 59, 1) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
    }}
    
    /* Radio button specific styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label p {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label span {{
        color: {sidebar_text_color} !important;
    }}
    
    /* Fix for metric text */
    [data-testid="stSidebar"] [data-testid="metric-container"] {{
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="metric-container"] label {{
        color: {sidebar_label_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {sidebar_text_color} !important;
    }}
    
    /* Info box in sidebar */
    [data-testid="stSidebar"] [data-testid="stAlert"] {{
        background: rgba(255, 255, 255, 0.1) !important;
        color: {sidebar_text_color} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stAlert"] p {{
        color: {sidebar_text_color} !important;
    }}
    
    /* Main Header */
    .main-header {{
        font-size: 1.8rem;
        font-weight: 700;
        color: {text_color};
        margin-bottom: 0;
        letter-spacing: -0.025em;
        line-height: 1.2;
    }}
    
    .sub-header {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {text_color};
        margin: 1.5rem 0 1.5rem 0;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid var(--primary-color);
    }}
    
    /* Metric Cards */
    .metric-card {{
        background: {COLORS['primary'] if not dark_mode else card_bg};
        padding: 0.5rem 0.85rem;
        border-radius: var(--card-radius);
        color: {COLORS['dark'] if not dark_mode else text_color};
        box-shadow: 0 8px 20px rgba(43, 42, 47, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        min-height: 75px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }}
    
    .metric-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 16px 32px rgba(43, 42, 47, 0.12);
    }}
    
    .metric-card h3 {{
        font-size: 0.75rem;
        font-weight: 600;
        opacity: 0.9;
        margin: 0;
        margin-bottom: 0.15rem;
        padding: 0;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        line-height: 1.1;
    }}
    
    .metric-card .value {{
        font-size: 1.4rem;
        font-weight: 700;
        margin: 0;
        margin-bottom: 0.1rem;
        padding: 0;
        line-height: 1.1;
        word-break: break-word;
    }}
    
    .metric-card .delta {{
        font-size: 0.75rem;
        opacity: 0.9;
        line-height: 1.1;
        word-break: break-word;
        margin: 0;
        padding: 0;
        min-height: 1.1em;
    }}
    
    /* Hide empty delta but preserve space for consistent card height */
    .metric-card .delta.delta-empty {{
        visibility: hidden;
        min-height: 1.1em;
        height: 1.1em;
    }}
    
    /* Info Cards */
    .info-card {{
        background: {card_bg};
        padding: 0.65rem 0.85rem;
        border-radius: var(--card-radius);
        border: 1px solid {card_border};
        box-shadow: 0 4px 16px rgba(43, 42, 47, 0.05);
        transition: box-shadow 0.2s ease;
        line-height: 1.2;
        word-break: break-word;
        min-height: 85px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        color: {text_color};
    }}
    
    .info-card:hover {{
        box-shadow: 0 8px 20px rgba(43, 42, 47, 0.08);
    }}
    
    /* Stock Cards */
    .stock-card {{
        background: {card_bg};
        padding: 0.85rem 1rem;
        border-radius: var(--card-radius);
        border-left: 4px solid {COLORS['primary']};
        margin: 0.5rem 0;
        box-shadow: 0 4px 14px rgba(43, 42, 47, 0.06);
        transition: all 0.2s ease;
        line-height: 1.3;
    }}
    
    .stock-card:hover {{
        transform: translateX(4px);
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15);
    }}
    
    .stock-card.positive {{
        border-left-color: {COLORS['success']};
    }}
    
    .stock-card.negative {{
        border-left-color: {COLORS['danger']};
    }}
    
    .stock-card .ticker {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {text_color};
        line-height: 1.2;
    }}
    
    .stock-card .sector {{
        font-size: 0.7rem;
        color: {muted_color};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        line-height: 1.2;
    }}

    /* Buttons */
    .stButton > button, .stDownloadButton > button {{
        border-radius: var(--card-radius) !important;
        padding: 0.5rem 1rem !important;
        margin-top: 0.25rem !important;
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

    /* Button groups spacing */
    div[data-testid="column"] .stButton {{
        margin-top: 0.35rem !important;
    }}
    
    /* Reduce spacing between columns/cards */
    div[data-testid="column"] {{
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }}
    
    div[data-testid="column"]:first-child {{
        padding-left: 0 !important;
    }}
    
    div[data-testid="column"]:last-child {{
        padding-right: 0 !important;
    }}

    /* Page titles */
    .main-header {{
        letter-spacing: -0.02em;
        margin-top: 0.25rem;
        color: #0b0b0f;
    }}

    h1, h2, h3 {{
        letter-spacing: -0.015em;
    }}

    .page-header {{
        background: #ffffff;
        border: 1px solid {COLORS['card_border']};
        border-radius: var(--card-radius);
        padding: 0.4rem 0.9rem;
        box-shadow: 0 2px 8px rgba(43, 42, 47, 0.04);
        margin-bottom: 1rem;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 0.9rem !important;
        flex-direction: row !important;
    }}

    .page-subtitle {{
        color: #6e6e73;
        margin-top: -0.15rem;
    }}

    .page-title-wrap {{
        display: flex;
        flex-direction: column;
        gap: 0.05rem;
    }}

    .page-image {{
        max-width: 80px !important;
        width: 80px !important;
        height: 80px !important;
        flex-shrink: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        vertical-align: middle !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    .page-image img {{
        max-height: 80px !important;
        max-width: 80px !important;
        width: 80px !important;
        height: 80px !important;
        object-fit: contain !important;
        vertical-align: middle !important;
        margin: 0 !important;
        display: block !important;
    }}
    
    .page-title-wrap {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0.15rem !important;
        align-items: flex-start !important;
        justify-content: center !important;
    }}

    /* Tables */
    .stDataFrame {{
        border-radius: var(--card-radius) !important;
        overflow: hidden !important;
        border: 1px solid {COLORS['card_border']} !important;
    }}

    .stDataFrame thead th {{
        background: #f4f0f2 !important;
        color: {COLORS['dark']} !important;
        font-weight: 600 !important;
    }}

    .stDataFrame tbody td {{
        font-size: 0.9rem !important;
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }}

    /* Symbols formatting */
    .symbol-text, code, pre {{
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }}
    
    /* Status Badges */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }}
    
    .status-badge.completed {{
        background: rgba(16, 185, 129, 0.1);
        color: {COLORS['success']};
    }}
    
    .status-badge.running {{
        background: rgba(59, 130, 246, 0.1);
        color: {COLORS['info']};
    }}
    
    .status-badge.failed {{
        background: rgba(239, 68, 68, 0.1);
        color: {COLORS['danger']};
    }}
    
    .status-badge.pending {{
        background: rgba(245, 158, 11, 0.1);
        color: {COLORS['warning']};
    }}
    
    /* Progress Indicators */
    .progress-step {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        background: {COLORS['card_bg']};
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid {COLORS['card_border']};
    }}
    
    .progress-step.active {{
        border-color: {COLORS['primary']};
        background: rgba(99, 102, 241, 0.05);
    }}
    
    .progress-step.complete {{
        border-color: {COLORS['success']};
        background: rgba(16, 185, 129, 0.05);
    }}
    
    .progress-step .step-icon {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        background: {COLORS['muted']};
        color: white;
    }}
    
    .progress-step.active .step-icon {{
        background: {COLORS['primary']};
    }}
    
    .progress-step.complete .step-icon {{
        background: {COLORS['success']};
    }}
    
    /* Data Tables */
    .stDataFrame {{
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
    }}
    
    .stDataFrame th {{
        background: {COLORS['light']} !important;
        font-weight: 600 !important;
        color: {COLORS['dark']} !important;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }}
    
    /* Positive/Negative Values */
    .positive {{
        color: {COLORS['success']} !important;
        font-weight: 600;
    }}
    
    .negative {{
        color: {COLORS['danger']} !important;
        font-weight: 600;
    }}
    
    .neutral {{
        color: {COLORS['muted']};
    }}
    
    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s ease;
        border: none;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(10, 132, 255, 0.2);
    }}
    
    .stButton > button[kind="primary"] {{
        background: {COLORS['primary']};
    }}
    
    /* Sidebar buttons - darker background for visibility */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(30, 41, 59, 0.8) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: rgba(30, 41, 59, 1) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background: {COLORS['primary']} !important;
        color: white !important;
        border: 1px solid {COLORS['primary']} !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
        background: {COLORS['secondary']} !important;
        box-shadow: 0 4px 12px rgba(10, 132, 255, 0.25) !important;
    }}
    
    /* Expanders */
    .streamlit-expanderHeader {{
        font-weight: 600;
        color: {COLORS['dark']};
        background: {COLORS['light']};
        border-radius: 8px;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: #f1ecef;
        padding: 0.5rem;
        border-radius: 10px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1rem;
    }}
    
    .stTabs [aria-selected="true"] {{
        background: {COLORS['primary']} !important;
        color: {text_color if dark_mode else COLORS['dark']} !important;
    }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-weight: 700;
        color: {text_color};
    }}
    
    [data-testid="stMetricDelta"] svg {{
        display: none;
    }}
    
    /* Code blocks */
    .stCodeBlock {{
        font-family: 'JetBrains Mono', monospace;
        border-radius: 8px;
        background-color: {card_bg if dark_mode else '#f8f9fa'} !important;
        color: {text_color} !important;
        border: 1px solid {card_border} !important;
    }}
    
    /* Alerts */
    .stAlert {{
        border-radius: 10px;
        border-left-width: 4px;
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    /* Info boxes */
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="InfoIcon"]) {{
        background-color: {card_bg if dark_mode else '#e8f4f8'} !important;
    }}
    
    /* Success boxes */
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="CheckCircleIcon"]) {{
        background-color: {card_bg if dark_mode else '#d4edda'} !important;
    }}
    
    /* Warning boxes */
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="WarningIcon"]) {{
        background-color: {card_bg if dark_mode else '#fff3cd'} !important;
    }}
    
    /* Error boxes */
    div[data-testid="stAlert"]:has([data-baseweb="icon"] svg[data-testid="ErrorIcon"]) {{
        background-color: {card_bg if dark_mode else '#f8d7da'} !important;
    }}
    
    /* Input Widgets - Dark Mode Support */
    {"/* Dark mode input styling */" if dark_mode else "/* Light mode input styling */"}
    
    /* Text Input */
    .stTextInput > div > div > input {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}
    
    /* Text Area */
    .stTextArea > div > div > textarea {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    .stTextArea > div > div > textarea:focus {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}
    
    /* Number Input */
    .stNumberInput > div > div > input {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    .stNumberInput > div > div > input:focus {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}
    
    /* Selectbox */
    .stSelectbox > div > div {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    .stSelectbox > div > div:focus-within {{
        border-color: {primary_color} !important;
        box-shadow: 0 0 0 2px {primary_color}33 !important;
    }}
    
    /* Selectbox dropdown */
    .stSelectbox [data-baseweb="select"] {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    /* Multiselect */
    .stMultiSelect > div > div {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    /* Date Input */
    .stDateInput > div > div > input {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    /* Time Input */
    .stTimeInput > div > div > input {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    /* Slider */
    .stSlider > div > div > div {{
        background: {primary_color};
    }}
    
    /* Slider track and thumb */
    .stSlider > div > div > div[data-testid="stThumbValue"] {{
        color: {text_color} !important;
    }}
    
    /* Checkbox */
    .stCheckbox > label {{
        color: {text_color} !important;
    }}
    
    /* Radio buttons */
    .stRadio > label {{
        color: {text_color} !important;
    }}
    
    /* Toggle/Switch */
    .stToggle > label {{
        color: {text_color} !important;
    }}
    
    /* File Uploader */
    .stFileUploader > div {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        border-color: {card_border} !important;
        border-radius: 8px;
    }}
    
    /* All input labels */
    label {{
        color: {text_color} !important;
    }}
    
    /* Small input fields - ensure they're not colored */
    input[type="text"][size],
    input[type="number"][size],
    input[type="text"].small,
    input[type="number"].small {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
    }}
    
    /* All input elements - catch any we missed (except buttons and checkboxes) */
    input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]):not([type="file"]):not([type="range"]) {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
        border-color: {card_border} !important;
    }}
    
    /* BaseWeb input containers - more specific targeting */
    div[data-baseweb="input"] input,
    div[data-baseweb="input"] textarea,
    div[data-baseweb="input"] > div > input {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    /* Select dropdown options */
    ul[role="listbox"],
    li[role="option"],
    div[data-baseweb="popover"] {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    /* Dataframe/Table styling */
    .stDataFrame {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
    }}
    
    .stDataFrame table {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame th {{
        background-color: {card_bg if dark_mode else '#f8f9fa'} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame td {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame tr:hover {{
        background-color: {card_bg if dark_mode else '#f8f9fa'} !important;
    }}
    
    /* Expander content */
    .streamlit-expanderContent {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame table {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame th {{
        background-color: {card_bg if dark_mode else '#f8f9fa'} !important;
        color: {text_color} !important;
    }}
    
    .stDataFrame td {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {card_bg if dark_mode else '#ffffff'} !important;
        color: {text_color} !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        color: {text_color} !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        color: {primary_color} !important;
        border-bottom-color: {primary_color} !important;
    }}
    
    /* Markdown text */
    .stMarkdown {{
        color: {text_color} !important;
    }}
    
    .stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th {{
        color: {text_color} !important;
    }}
    
    /* Metric labels and values */
    [data-testid="stMetricLabel"] {{
        color: {muted_color} !important;
    }}
    
    [data-testid="stMetricValue"] {{
        color: {text_color} !important;
    }}
    
    [data-testid="stMetricDelta"] {{
        color: {text_color} !important;
    }}
    
    /* Divider */
    hr {{
        border: none;
        height: 1px;
        background: {card_border};
        margin: 1.25rem 0;
    }}
    
    /* Divider */
    hr {{
        border: none;
        height: 1px;
        background: {COLORS['card_border']};
        margin: 1.25rem 0;
    }}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {bg_color};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {muted_color};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {primary_color};
    }}
    
    /* Animation */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .animate-fade-in {{
        animation: fadeIn 0.3s ease-out;
    }}
    
    /* Dark mode specific styles */
    {"/* Dark mode active */" if dark_mode else ""}
    
    /* Responsive adjustments - Mobile */
    @media (max-width: 768px) {{
        .main-header {{
            font-size: 1.5rem;
        }}
        
        .sub-header {{
            font-size: 1.25rem;
            margin: 1rem 0;
        }}
        
        .metric-card {{
            padding: 0.5rem 0.65rem;
            min-height: 70px;
        }}
        
        .metric-card .value {{
            font-size: 1.2rem;
        }}
        
        .metric-card h3 {{
            font-size: 0.7rem;
        }}
        
        .info-card {{
            padding: 0.5rem 0.65rem;
            min-height: 70px;
        }}
        
        .stock-card {{
            padding: 0.65rem 0.85rem;
        }}
        
        .page-header {{
            padding: 0.3rem 0.6rem !important;
            flex-direction: column;
            align-items: flex-start !important;
        }}
        
        .page-image {{
            max-width: 60px !important;
            width: 60px !important;
            margin-bottom: 0.5rem;
        }}
        
        div[data-testid="column"] {{
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }}
        
        /* Touch-friendly buttons */
        .stButton > button {{
            min-height: 44px !important;
            padding: 0.6rem 1.2rem !important;
        }}
        
        /* Better spacing for mobile */
        .block-container {{
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}
    }}
    
    /* Tablet adjustments */
    @media (min-width: 769px) and (max-width: 1024px) {{
        .main-header {{
            font-size: 1.65rem;
        }}
        
        div[data-testid="column"] {{
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }}
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
