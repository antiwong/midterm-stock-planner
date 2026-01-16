"""
Dashboard Configuration & Theming
=================================
Centralized configuration for page settings and custom CSS.
"""

import streamlit as st

# Color palette
COLORS = {
    'primary': '#6366f1',      # Indigo
    'secondary': '#8b5cf6',    # Purple
    'accent': '#06b6d4',       # Cyan
    'success': '#10b981',      # Emerald
    'warning': '#f59e0b',      # Amber
    'danger': '#ef4444',       # Red
    'info': '#3b82f6',         # Blue
    'dark': '#1e293b',         # Slate-800
    'light': '#f8fafc',        # Slate-50
    'muted': '#64748b',        # Slate-500
    'card_bg': '#ffffff',
    'card_border': '#e2e8f0',
    'gradient_start': '#6366f1',
    'gradient_end': '#8b5cf6',
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
        page_title="Stock Analysis Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/yourusername/midterm-stock-planner',
            'Report a bug': 'https://github.com/yourusername/midterm-stock-planner/issues',
            'About': '# Mid-term Stock Planner\nML-powered stock analysis and portfolio optimization.'
        }
    )


def inject_custom_css():
    """Inject custom CSS for improved styling."""
    st.markdown(f"""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global Styles */
    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['dark']} 0%, #0f172a 100%);
    }}
    
    [data-testid="stSidebar"] * {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] label {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio label {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio label span {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio > div {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 0.5rem;
    }}
    
    [data-testid="stSidebar"] .stRadio > div > label:hover {{
        background: rgba(99, 102, 241, 0.2);
        border-radius: 6px;
    }}
    
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stNumberInput label {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
        color: rgba(255, 255, 255, 0.7) !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {{
        color: {COLORS['light']} !important;
    }}
    
    [data-testid="stSidebar"] button {{
        color: {COLORS['light']} !important;
        background-color: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }}
    
    [data-testid="stSidebar"] button:hover {{
        background-color: rgba(30, 41, 59, 1) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
    }}
    
    /* Radio button specific styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label p {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [role="radiogroup"] label span {{
        color: white !important;
    }}
    
    /* Fix for metric text */
    [data-testid="stSidebar"] [data-testid="metric-container"] {{
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="metric-container"] label {{
        color: rgba(255, 255, 255, 0.7) !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: white !important;
    }}
    
    /* Info box in sidebar */
    [data-testid="stSidebar"] [data-testid="stAlert"] {{
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stAlert"] p {{
        color: white !important;
    }}
    
    /* Main Header */
    .main-header {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        letter-spacing: -0.025em;
    }}
    
    .sub-header {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {COLORS['dark']};
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {COLORS['primary']};
    }}
    
    /* Metric Cards */
    .metric-card {{
        background: linear-gradient(135deg, {COLORS['gradient_start']} 0%, {COLORS['gradient_end']} 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        box-shadow: 0 10px 40px rgba(99, 102, 241, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .metric-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 20px 50px rgba(99, 102, 241, 0.4);
    }}
    
    .metric-card h3 {{
        font-size: 0.875rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    .metric-card .value {{
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }}
    
    .metric-card .delta {{
        font-size: 0.875rem;
        opacity: 0.85;
    }}
    
    /* Info Cards */
    .info-card {{
        background: {COLORS['card_bg']};
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid {COLORS['card_border']};
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: box-shadow 0.2s ease;
    }}
    
    .info-card:hover {{
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }}
    
    /* Stock Cards */
    .stock-card {{
        background: {COLORS['card_bg']};
        padding: 1.25rem;
        border-radius: 12px;
        border-left: 4px solid {COLORS['primary']};
        margin: 0.75rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
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
        font-size: 1.25rem;
        font-weight: 700;
        color: {COLORS['dark']};
    }}
    
    .stock-card .sector {{
        font-size: 0.75rem;
        color: {COLORS['muted']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
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
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }}
    
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
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
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
        color: white !important;
        border: 1px solid {COLORS['primary']} !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #818cf8 0%, #a78bfa 100%) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;
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
        background: {COLORS['light']};
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
        color: white !important;
    }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-weight: 700;
        color: {COLORS['dark']};
    }}
    
    [data-testid="stMetricDelta"] svg {{
        display: none;
    }}
    
    /* Code blocks */
    .stCodeBlock {{
        font-family: 'JetBrains Mono', monospace;
        border-radius: 8px;
    }}
    
    /* Alerts */
    .stAlert {{
        border-radius: 10px;
        border-left-width: 4px;
    }}
    
    /* Selectbox */
    .stSelectbox > div > div {{
        border-radius: 8px;
    }}
    
    /* Number Input */
    .stNumberInput > div > div > input {{
        border-radius: 8px;
    }}
    
    /* Slider */
    .stSlider > div > div > div {{
        background: {COLORS['primary']};
    }}
    
    /* Divider */
    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, {COLORS['card_border']}, transparent);
        margin: 2rem 0;
    }}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {COLORS['light']};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {COLORS['muted']};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['primary']};
    }}
    
    /* Animation */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .animate-fade-in {{
        animation: fadeIn 0.3s ease-out;
    }}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .main-header {{
            font-size: 1.75rem;
        }}
        
        .metric-card {{
            padding: 1rem;
        }}
        
        .metric-card .value {{
            font-size: 1.5rem;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# Navigation pages - organized by workflow groups
# Main workflow (sequential)
MAIN_WORKFLOW = [
    ("🏠 Overview", "overview"),
    ("🎮 Run Analysis", "run_analysis"),
    ("🎯 Portfolio Builder", "portfolio_builder"),
    ("📄 Reports", "reports"),
    ("💼 Portfolio Analysis", "portfolio_analysis"),
    ("📊 Comprehensive Analysis", "comprehensive_analysis"),
    ("🔍 Purchase Triggers", "purchase_triggers"),
    ("📊 Analysis Runs", "analysis_runs"),
    ("🤖 AI Insights", "ai_insights"),
]

# Standalone tools
STANDALONE_TOOLS = [
    ("📋 Watchlist Manager", "watchlist_manager"),
    ("🔎 Stock Explorer", "stock_explorer"),
    ("📈 Compare Runs", "compare_runs"),
    ("🔀 Advanced Comparison", "advanced_comparison"),
]

# Advanced Analytics
ADVANCED_ANALYTICS = [
    ("📅 Event Analysis", "event_analysis"),
    ("💰 Tax Optimization", "tax_optimization"),
    ("🎲 Monte Carlo", "monte_carlo"),
    ("🔄 Turnover Analysis", "turnover_analysis"),
    ("📅 Earnings Calendar", "earnings_calendar"),
    ("⚡ Real-Time Monitoring", "realtime_monitoring"),
    ("📊 Recommendation Tracking", "recommendation_tracking"),
]

# Utilities
UTILITIES = [
    ("🚨 Alert Management", "alert_management"),
    ("📄 Report Templates", "report_templates"),
    ("📚 Documentation", "documentation"),
    ("⚙️ Settings", "settings"),
]

# Combined list for backward compatibility
PAGES = MAIN_WORKFLOW + STANDALONE_TOOLS + ADVANCED_ANALYTICS + UTILITIES
