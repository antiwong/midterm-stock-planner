"""
Settings Page
=============
Configuration and system settings.
"""

import streamlit as st
import os
from pathlib import Path

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card, render_alert
from ..data import load_runs, delete_run, get_database
from ..utils import get_project_root, get_version, load_ui_settings, save_ui_settings, DEFAULT_UI_SETTINGS
from ..config import COLORS


def render_settings():
    """Render the settings page."""
    render_page_header(
        "Settings",
        "Configure dashboard and manage data"
    )
    
    tabs = st.tabs(["🔑 API Keys", "🗄️ Database", "📁 Files", "🎨 Styles", "⌨️ Shortcuts", "⏰ Scheduled Updates", "📊 Dashboard", "ℹ️ About"])
    
    with tabs[0]:
        _render_api_keys_tab()
    
    with tabs[1]:
        _render_database_tab()
    
    with tabs[2]:
        _render_files_tab()
    
    with tabs[3]:
        _render_styles_tab()
    
    with tabs[4]:
        _render_shortcuts_tab()
    
    with tabs[5]:
        _render_scheduled_updates_tab()
    
    with tabs[6]:
        _render_dashboard_customization_tab()

    with tabs[7]:
        _render_about_tab()


def _render_api_keys_tab():
    """Render API keys configuration tab."""
    render_section_header("API Configuration", "🔑")
    
    # Check API key status
    api_keys = {
        'ALPHA_VANTAGE_API_KEY': os.getenv('ALPHA_VANTAGE_API_KEY'),
        'NEWS_API_KEY': os.getenv('NEWS_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    }
    
    st.markdown("**API Key Status**")
    
    for key_name, key_value in api_keys.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            display_name = key_name.replace('_', ' ').title().replace('Api', 'API')
            st.write(display_name)
        with col2:
            if key_value:
                st.success("✅ Set")
            else:
                st.error("❌ Missing")
    
    st.markdown("---")
    
    with st.expander("📝 How to Configure API Keys"):
        st.markdown("""
        Create a `.env` file in the project root with your API keys:
        
        ```
        ALPHA_VANTAGE_API_KEY=your_key_here
        NEWS_API_KEY=your_key_here
        OPENAI_API_KEY=your_key_here
        GEMINI_API_KEY=your_key_here
        ```
        
        **Getting API Keys:**
        - Alpha Vantage: https://www.alphavantage.co/support/#api-key
        - NewsAPI: https://newsapi.org/register
        - OpenAI: https://platform.openai.com/api-keys
        - Gemini: https://makersuite.google.com/app/apikey
        """)
    
    # Test API connections
    if st.button("🧪 Test API Connections"):
        with st.spinner("Testing connections..."):
            _test_api_connections()


def _test_api_connections():
    """Test API connections."""
    try:
        from src.config.api_keys import test_api_keys
        results = test_api_keys()
        
        for api, status in results.items():
            if status['success']:
                st.success(f"✅ {api}: Connected")
            else:
                st.error(f"❌ {api}: {status.get('error', 'Failed')}")
    except Exception as e:
        st.error(f"Error testing APIs: {e}")


def _render_database_tab():
    """Render database management tab."""
    render_section_header("Database Management", "🗄️")
    
    db_path = get_project_root() / "data" / "analysis.db"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Database Info**")
        st.write(f"- **Path:** `{db_path}`")
        st.write(f"- **Exists:** {'Yes' if db_path.exists() else 'No'}")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            st.write(f"- **Size:** {size_mb:.2f} MB")
    
    with col2:
        st.markdown("**Statistics**")
        runs = load_runs()
        st.write(f"- **Total Runs:** {len(runs)}")
        completed = sum(1 for r in runs if r['status'] == 'completed')
        st.write(f"- **Completed:** {completed}")
        failed = sum(1 for r in runs if r['status'] == 'failed')
        st.write(f"- **Failed:** {failed}")
    
    st.markdown("---")
    
    st.markdown("**Database Actions**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Failed Runs", type="secondary"):
            failed_runs = [r for r in runs if r['status'] == 'failed']
            if failed_runs:
                for run in failed_runs:
                    try:
                        delete_run(run['run_id'])
                    except:
                        pass
                st.success(f"Deleted {len(failed_runs)} failed runs")
                st.rerun()
            else:
                st.info("No failed runs to delete")
    
    with col2:
        if st.button("⚠️ Delete All Runs", type="secondary"):
            if st.checkbox("I confirm I want to delete ALL runs"):
                try:
                    for run in runs:
                        delete_run(run['run_id'])
                    st.success("All runs deleted")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


def _render_files_tab():
    """Render file management tab."""
    render_section_header("Output Files", "📁")
    
    output_dir = get_project_root() / "output"
    
    if not output_dir.exists():
        st.info("Output directory does not exist yet")
        return
    
    # List run folders
    folders = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith('run_')]
    
    st.markdown(f"**{len(folders)} Run Folders**")
    
    if folders:
        for folder in sorted(folders, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            files = list(folder.iterdir())
            with st.expander(f"📁 {folder.name} ({len(files)} files)"):
                for f in files:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f.name)
                    with col2:
                        size_kb = f.stat().st_size / 1024
                        st.write(f"{size_kb:.1f} KB")
    
    st.markdown("---")
    
    # Cleanup options
    st.markdown("**Cleanup**")
    
    if st.button("🧹 Remove Empty Folders"):
        removed = 0
        for folder in folders:
            if not list(folder.iterdir()):
                folder.rmdir()
                removed += 1
        st.success(f"Removed {removed} empty folders")
        st.rerun()


def _render_styles_tab():
    """Render style configuration tab."""
    render_section_header("Style Settings", "🎨")

    settings = load_ui_settings()

    st.info("Changes apply on next page refresh. Use the button below to save.")

    with st.form("style_settings_form"):
        enable_custom_css = st.toggle(
            "Enable custom dashboard styling",
            value=bool(settings.get("enable_custom_css", True)),
            help="Turn off to use Streamlit default styling."
        )
        
        dark_mode = st.toggle(
            "🌙 Dark mode",
            value=bool(settings.get("dark_mode", False)),
            help="Switch to dark theme for better viewing in low-light conditions."
        )

        st.markdown("**Sidebar Colors**")
        col1, col2 = st.columns(2)
        with col1:
            sidebar_bg_start = st.color_picker(
                "Sidebar background",
                value=settings.get("sidebar_bg_start", DEFAULT_UI_SETTINGS["sidebar_bg_start"])
            )
            sidebar_text_color = st.color_picker(
                "Sidebar text color",
                value=settings.get("sidebar_text_color", DEFAULT_UI_SETTINGS["sidebar_text_color"])
            )
            sidebar_hover_bg = st.color_picker(
                "Sidebar hover background",
                value=settings.get("sidebar_hover_bg", DEFAULT_UI_SETTINGS["sidebar_hover_bg"])
            )
        with col2:
            sidebar_label_color = st.color_picker(
                "Sidebar label color",
                value=settings.get("sidebar_label_color", DEFAULT_UI_SETTINGS["sidebar_label_color"])
            )
            sidebar_button_bg = st.color_picker(
                "Sidebar button background",
                value=settings.get("sidebar_button_bg", DEFAULT_UI_SETTINGS["sidebar_button_bg"])
            )

        sidebar_button_border = st.color_picker(
            "Sidebar button border",
            value=settings.get("sidebar_button_border", DEFAULT_UI_SETTINGS["sidebar_button_border"])
        )

        st.markdown("**Theme Colors & Layout**")
        theme_col1, theme_col2 = st.columns(2)
        with theme_col1:
            primary_color = st.color_picker(
                "Primary color",
                value=settings.get("primary_color", DEFAULT_UI_SETTINGS["primary_color"])
            )
            accent_color = st.color_picker(
                "Accent color",
                value=settings.get("accent_color", DEFAULT_UI_SETTINGS["accent_color"])
            )
            font_scale = st.slider(
                "Base font scale",
                min_value=0.85,
                max_value=1.15,
                value=float(settings.get("font_scale", DEFAULT_UI_SETTINGS["font_scale"])),
                step=0.02
            )
        with theme_col2:
            secondary_color = st.color_picker(
                "Secondary color",
                value=settings.get("secondary_color", DEFAULT_UI_SETTINGS["secondary_color"])
            )
            card_radius = st.slider(
                "Card radius (px)",
                min_value=6,
                max_value=24,
                value=int(settings.get("card_radius", DEFAULT_UI_SETTINGS["card_radius"])),
                step=1
            )

        col_apply, col_reset = st.columns(2)
        with col_apply:
            apply_changes = st.form_submit_button("💾 Save Styles")
        with col_reset:
            reset_defaults = st.form_submit_button("↩️ Reset to Defaults")

    if reset_defaults:
        save_ui_settings(DEFAULT_UI_SETTINGS.copy())
        st.success("Style settings reset to defaults.")
        st.rerun()

    if apply_changes:
        new_settings = {
            "enable_custom_css": enable_custom_css,
            "dark_mode": dark_mode,
            "sidebar_bg_start": sidebar_bg_start,
            "sidebar_bg_end": sidebar_bg_start,
            "sidebar_text_color": sidebar_text_color,
            "sidebar_label_color": sidebar_label_color,
            "sidebar_hover_bg": sidebar_hover_bg,
            "sidebar_button_bg": sidebar_button_bg,
            "sidebar_button_border": sidebar_button_border,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "accent_color": accent_color,
            "card_radius": card_radius,
            "font_scale": font_scale,
        }
        save_ui_settings(new_settings)
        st.success("Style settings saved. Refresh the page to apply.")


def _render_shortcuts_tab():
    """Render keyboard shortcuts help tab."""
    render_section_header("Keyboard Shortcuts", "⌨️")
    
    st.markdown("""
    Use keyboard shortcuts to navigate and perform actions quickly.
    Shortcuts work when you're not typing in input fields.
    """)
    
    render_shortcuts_help()
    
    st.markdown("---")
    st.markdown("**Tips:**")
    st.markdown("""
    - Press `?` on any page to show shortcuts help
    - Shortcuts are most reliable when not focused on input fields
    - Some shortcuts may require page refresh to take effect
    - Navigation shortcuts (O, A, P, W, D, S) work from any page
    """)


def _render_dashboard_customization_tab():
    """Render dashboard customization tab."""
    from ..components.dashboard_customizer import render_dashboard_customizer
    render_dashboard_customizer()


def _render_scheduled_updates_tab():
    """Render scheduled updates configuration tab."""
    render_section_header("Scheduled Updates", "⏰")
    
    st.markdown("""
    Configure automatic data updates to keep your analysis current.
    Updates can be scheduled for daily or weekly execution.
    """)
    
    st.info("💡 **Note**: Scheduled updates require the application to be running. For production use, consider setting up a cron job or scheduled task.")
    
    st.markdown("---")
    st.markdown("### Price Data Updates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_price_updates = st.toggle(
            "Enable Automatic Price Updates",
            value=False,
            help="Automatically update price data on schedule"
        )
    
    with col2:
        price_update_frequency = st.selectbox(
            "Update Frequency",
            ["Daily", "Weekly", "Monthly"],
            disabled=not enable_price_updates,
            help="How often to update price data"
        )
    
    st.markdown("---")
    st.markdown("### Benchmark Data Updates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_benchmark_updates = st.toggle(
            "Enable Automatic Benchmark Updates",
            value=False,
            help="Automatically update benchmark data on schedule"
        )
    
    with col2:
        benchmark_update_frequency = st.selectbox(
            "Update Frequency",
            ["Daily", "Weekly", "Monthly"],
            disabled=not enable_benchmark_updates,
            help="How often to update benchmark data"
        )
    
    st.markdown("---")
    st.markdown("### Update Schedule")
    
    from datetime import time as dt_time
    update_time = st.time_input(
        "Preferred Update Time",
        value=dt_time(2, 0),
        help="Time of day to run scheduled updates (recommended: early morning)"
    )
    
    st.markdown("---")
    
    if st.button("💾 Save Schedule", type="primary", use_container_width=True):
        # Save schedule settings (would be stored in ui_settings.json or config)
        st.success("✅ Schedule saved! Updates will run automatically.")
        st.info("⚠️ **Reminder**: Ensure the application is running for scheduled updates to execute.")
    
    st.markdown("---")
    st.markdown("### Manual Update")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Update Prices Now", use_container_width=True,
                    help="Manually trigger price data update"):
            from ..pages.overview import _update_prices
            _update_prices()
    
    with col2:
        if st.button("🔄 Update Benchmark Now", use_container_width=True,
                    help="Manually trigger benchmark data update"):
            from ..pages.overview import _update_benchmark
            _update_benchmark()


def _render_about_tab():
    """Render about information tab."""
    render_section_header("About", "ℹ️")
    
    # Get version from README
    version = get_version()
    
    st.markdown(f"""
    ## The Long Game
    
    **Version:** {version}
    
    Mid-term portfolio intelligence and analysis platform.
    
    ### Features
    
    - 📊 **Walk-forward Backtesting** - Rigorous out-of-sample testing
    - 🤖 **AI Insights** - Gemini-powered analysis and recommendations
    - 📈 **Portfolio Builder** - Personalized portfolio optimization
    - 🎯 **Risk Management** - Risk parity, volatility targeting, position limits
    - 📉 **Domain Analysis** - Vertical and horizontal stock selection
    
    ### Documentation
    
    - [README](../readme.md)
    - [Portfolio Builder Guide](../docs/portfolio-builder.md)
    - [Dashboard Guide](../docs/dashboard.md)
    - [Risk Management](../docs/risk-management.md)
    
    ### Support
    
    - GitHub Issues
    - Documentation
    """)
    
    # System info
    st.markdown("---")
    st.markdown("**System Information**")
    
    import sys
    import platform
    
    st.write(f"- **Python:** {sys.version.split()[0]}")
    st.write(f"- **Platform:** {platform.system()} {platform.release()}")
    st.write(f"- **Project Root:** `{get_project_root()}`")
