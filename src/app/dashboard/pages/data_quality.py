"""
Data Quality Dashboard
======================
Display data quality metrics and provide actionable guidance.
"""

import streamlit as st
from pathlib import Path

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card, render_alert
from ..components.metrics import render_metric_card
from ..utils import get_project_root
from ..utils.data_validation import DataQualityChecker
from ..config import COLORS


def render_data_quality():
    """Render the data quality dashboard."""
    render_page_header(
        "Data Quality",
        "Monitor data completeness, freshness, and quality"
    )
    
    project_root = get_project_root()
    checker = DataQualityChecker(project_root)
    
    # Overall quality summary
    overall = checker.get_overall_quality()
    
    st.markdown("---")
    
    # Overall score
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score = overall['overall_score']
        if score >= 0.8:
            delta_color = "normal"
            status = "✅ Good"
        elif score >= 0.5:
            delta_color = "off"
            status = "⚠️ Fair"
        else:
            delta_color = "inverse"
            status = "❌ Poor"
        
        st.metric("Overall Quality", f"{score*100:.0f}%", delta=status, delta_color=delta_color)
    
    with col2:
        st.metric("Total Issues", overall['total_issues'], delta_color="inverse" if overall['total_issues'] > 0 else "normal")
    
    with col3:
        price_status = overall['price_data']['status']
        st.metric("Price Data", price_status.upper(), delta_color="normal" if price_status == 'ok' else "off")
    
    with col4:
        fundamentals_status = overall['fundamentals_data']['status']
        st.metric("Fundamentals", fundamentals_status.upper(), delta_color="normal" if fundamentals_status == 'ok' else "off")
    
    st.markdown("---")
    
    # Detailed breakdown
    tabs = st.tabs(["📊 Price Data", "📈 Benchmark Data", "💼 Fundamentals", "🔧 Recommendations"])
    
    with tabs[0]:
        _render_price_data_quality(overall['price_data'])
    
    with tabs[1]:
        _render_benchmark_data_quality(overall['benchmark_data'])
    
    with tabs[2]:
        _render_fundamentals_quality(overall['fundamentals_data'])
    
    with tabs[3]:
        _render_recommendations(overall)


def _render_price_data_quality(quality: dict):
    """Render price data quality details."""
    render_section_header("Price Data Quality", "📊")
    
    col1, col2 = st.columns(2)
    
    with col1:
        completeness = quality.get('completeness', 0.0)
        st.metric("Completeness", f"{completeness*100:.1f}%")
    
    with col2:
        freshness = quality.get('freshness_days')
        if freshness is not None:
            st.metric("Data Age", f"{freshness} days")
        else:
            st.metric("Data Age", "Unknown")
    
    if quality['status'] == 'ok':
        st.success("✅ Price data is in good condition")
    elif quality['status'] == 'warning':
        st.warning("⚠️ Price data has some issues")
    elif quality['status'] == 'missing':
        st.error("❌ Price data is missing")
    else:
        st.error("❌ Price data has errors")
    
    if quality.get('issues'):
        st.markdown("### Issues")
        for issue in quality['issues']:
            st.markdown(f"- {issue}")
    
    if quality.get('suggestions'):
        st.markdown("### Suggestions")
        for suggestion in quality['suggestions']:
            st.markdown(f"- {suggestion}")


def _render_benchmark_data_quality(quality: dict):
    """Render benchmark data quality details."""
    render_section_header("Benchmark Data Quality", "📈")
    
    col1, col2 = st.columns(2)
    
    with col1:
        completeness = quality.get('completeness', 0.0)
        st.metric("Completeness", f"{completeness*100:.1f}%")
    
    with col2:
        freshness = quality.get('freshness_days')
        if freshness is not None:
            st.metric("Data Age", f"{freshness} days")
        else:
            st.metric("Data Age", "Unknown")
    
    if quality['status'] == 'ok':
        st.success("✅ Benchmark data is in good condition")
    elif quality['status'] == 'warning':
        st.warning("⚠️ Benchmark data has some issues")
    elif quality['status'] == 'missing':
        st.error("❌ Benchmark data is missing")
    else:
        st.error("❌ Benchmark data has errors")
    
    if quality.get('issues'):
        st.markdown("### Issues")
        for issue in quality['issues']:
            st.markdown(f"- {issue}")
    
    if quality.get('suggestions'):
        st.markdown("### Suggestions")
        for suggestion in quality['suggestions']:
            st.markdown(f"- {suggestion}")


def _render_fundamentals_quality(quality: dict):
    """Render fundamentals data quality details."""
    render_section_header("Fundamentals Data Quality", "💼")
    
    col1, col2 = st.columns(2)
    
    with col1:
        completeness = quality.get('completeness', 0.0)
        st.metric("Completeness", f"{completeness*100:.1f}%")
    
    with col2:
        ticker_count = quality.get('ticker_count', 0)
        st.metric("Stocks with Data", ticker_count)
    
    if quality['status'] == 'ok':
        st.success("✅ Fundamentals data is in good condition")
    elif quality['status'] == 'warning':
        st.warning("⚠️ Fundamentals data has some issues")
    elif quality['status'] == 'missing':
        st.error("❌ Fundamentals data is missing")
    else:
        st.error("❌ Fundamentals data has errors")
    
    if quality.get('issues'):
        st.markdown("### Issues")
        for issue in quality['issues']:
            st.markdown(f"- {issue}")
    
    if quality.get('suggestions'):
        st.markdown("### Suggestions")
        for suggestion in quality['suggestions']:
            st.markdown(f"- {suggestion}")


def _render_recommendations(overall: dict):
    """Render actionable recommendations."""
    render_section_header("Recommendations", "🔧")
    
    if overall['total_issues'] == 0:
        st.success("🎉 All data is in good condition! No action needed.")
        return
    
    st.info("💡 **Action Items:** Fix the following issues to improve data quality:")
    
    suggestions = overall.get('suggestions', [])
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"{i}. {suggestion}")
    
    st.markdown("---")
    
    # Quick action buttons
    st.markdown("### Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Update Prices", use_container_width=True,
                    help="Download latest price data"):
            st.session_state['page'] = 'Overview'
            st.session_state['action'] = 'update_prices'
            st.rerun()
    
    with col2:
        if st.button("🔄 Update Benchmark", use_container_width=True,
                    help="Download latest benchmark data"):
            st.session_state['page'] = 'Overview'
            st.session_state['action'] = 'update_benchmark'
            st.rerun()
    
    with col3:
        if st.button("📥 Download Fundamentals", use_container_width=True,
                    help="Download fundamentals data"):
            st.info("💡 Use the Fundamentals Status page to download fundamentals")
