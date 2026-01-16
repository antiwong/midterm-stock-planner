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
from ..utils import get_project_root, get_version
from ..config import COLORS


def render_settings():
    """Render the settings page."""
    render_page_header(
        "Settings",
        "Configure dashboard and manage data"
    )
    
    tabs = st.tabs(["🔑 API Keys", "🗄️ Database", "📁 Files", "ℹ️ About"])
    
    with tabs[0]:
        _render_api_keys_tab()
    
    with tabs[1]:
        _render_database_tab()
    
    with tabs[2]:
        _render_files_tab()
    
    with tabs[3]:
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


def _render_about_tab():
    """Render about information tab."""
    render_section_header("About", "ℹ️")
    
    # Get version from README
    version = get_version()
    
    st.markdown(f"""
    ## Mid-term Stock Planner
    
    **Version:** {version}
    
    ML-powered stock analysis and portfolio optimization platform.
    
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
