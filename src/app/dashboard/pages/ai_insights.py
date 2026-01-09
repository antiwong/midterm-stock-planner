"""
AI Insights Page
================
AI-powered analysis and recommendations.
"""

import streamlit as st
import pandas as pd

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card, render_alert
from ..data import load_runs, load_run_scores, load_ai_commentary, load_ai_recommendations
from ..utils import format_percent, format_number, get_run_folder
from ..config import COLORS


def render_ai_insights():
    """Render the AI insights page."""
    render_page_header(
        "AI Insights",
        "Gemini-powered analysis and recommendations"
    )
    
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if not completed_runs:
        st.warning("No completed runs found")
        return
    
    # Run selector
    selected_run_id = st.selectbox(
        "Select Analysis Run",
        options=[r['run_id'] for r in completed_runs],
        format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}"
    )
    
    if not selected_run_id:
        return
    
    st.markdown("---")
    
    # Tabs for different insights
    tabs = st.tabs(["📄 Commentary", "💡 Recommendations", "🎯 Stock Analysis", "🔮 Generate New"])
    
    with tabs[0]:
        _render_commentary_tab(selected_run_id)
    
    with tabs[1]:
        _render_recommendations_tab(selected_run_id)
    
    with tabs[2]:
        _render_stock_analysis_tab(selected_run_id)
    
    with tabs[3]:
        _render_generate_tab(selected_run_id)


def _render_commentary_tab(run_id: str):
    """Render AI commentary tab."""
    render_section_header("AI Commentary", "📄")
    
    commentary = load_ai_commentary(run_id)
    
    if commentary:
        st.markdown(commentary)
        
        st.download_button(
            "📥 Download Commentary",
            commentary,
            file_name=f"ai_commentary_{run_id[:8]}.md",
            mime="text/markdown"
        )
    else:
        st.info("No AI commentary available for this run. Generate one using the 'Generate New' tab.")


def _render_recommendations_tab(run_id: str):
    """Render AI recommendations tab."""
    render_section_header("Portfolio Recommendations", "💡")
    
    recommendations = load_ai_recommendations(run_id)
    
    if not recommendations:
        st.info("No AI recommendations available for this run. Generate one using the 'Generate New' tab.")
        return
    
    # Display recommendations by profile
    profiles = recommendations.get('profiles', {})
    
    if not profiles:
        st.markdown(recommendations.get('summary', 'No summary available'))
        return
    
    profile_tabs = st.tabs([p.title() for p in profiles.keys()])
    
    for tab, (profile_name, profile_data) in zip(profile_tabs, profiles.items()):
        with tab:
            st.markdown(f"### {profile_name.title()} Portfolio")
            
            # Profile metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                expected_return = profile_data.get('expected_return')
                if expected_return:
                    st.metric("Expected Return", f"{expected_return}")
            
            with col2:
                risk_level = profile_data.get('risk_level')
                if risk_level:
                    st.metric("Risk Level", risk_level)
            
            with col3:
                time_horizon = profile_data.get('time_horizon')
                if time_horizon:
                    st.metric("Time Horizon", time_horizon)
            
            # Holdings
            holdings = profile_data.get('holdings', [])
            if holdings:
                st.markdown("**Suggested Holdings:**")
                for holding in holdings:
                    if isinstance(holding, dict):
                        ticker = holding.get('ticker', 'Unknown')
                        weight = holding.get('weight', 0)
                        rationale = holding.get('rationale', '')
                        st.write(f"- **{ticker}** ({weight*100:.1f}%): {rationale}")
                    else:
                        st.write(f"- {holding}")
            
            # Rationale
            rationale = profile_data.get('rationale', '')
            if rationale:
                with st.expander("View Rationale"):
                    st.markdown(rationale)


def _render_stock_analysis_tab(run_id: str):
    """Render individual stock AI analysis tab."""
    render_section_header("Stock Analysis", "🎯")
    
    scores = load_run_scores(run_id)
    
    if not scores:
        st.info("No stock data available")
        return
    
    scores_df = pd.DataFrame(scores)
    
    # Stock selector
    selected_ticker = st.selectbox(
        "Select Stock",
        options=sorted(scores_df['ticker'].unique())
    )
    
    if not selected_ticker:
        return
    
    stock_data = scores_df[scores_df['ticker'] == selected_ticker].iloc[0].to_dict()
    
    # Display stock info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Score", f"{stock_data.get('score', 0):.1f}")
    with col2:
        st.metric("Rank", f"#{stock_data.get('rank', 'N/A')}")
    with col3:
        st.metric("Sector", stock_data.get('sector', 'Unknown'))
    
    # Score breakdown
    st.markdown("**Score Breakdown:**")
    breakdown_cols = st.columns(4)
    
    with breakdown_cols[0]:
        tech = stock_data.get('tech_score', 0) or 0
        st.metric("Technical", f"{tech:.1f}")
    with breakdown_cols[1]:
        fund = stock_data.get('fund_score', 0) or 0
        st.metric("Fundamental", f"{fund:.1f}")
    with breakdown_cols[2]:
        sent = stock_data.get('sent_score', 0) or 0
        st.metric("Sentiment", f"{sent:.1f}")
    with breakdown_cols[3]:
        ret = stock_data.get('return_21d', 0) or 0
        st.metric("21d Return", f"{ret*100:+.1f}%")
    
    # Generate AI analysis button
    if st.button("🤖 Generate AI Analysis", key=f"ai_{selected_ticker}"):
        with st.spinner("Generating analysis..."):
            _generate_stock_analysis(selected_ticker, stock_data)


def _generate_stock_analysis(ticker: str, stock_data: dict):
    """Generate AI analysis for a stock."""
    try:
        from src.analytics.ai_insights import AIInsightsGenerator
        
        generator = AIInsightsGenerator()
        
        # Create prompt
        prompt = f"""
        Analyze this stock for a mid-term investment:
        
        Ticker: {ticker}
        Sector: {stock_data.get('sector', 'Unknown')}
        Overall Score: {stock_data.get('score', 0):.1f}/100
        Technical Score: {stock_data.get('tech_score', 0):.1f}
        Fundamental Score: {stock_data.get('fund_score', 0):.1f}
        Sentiment Score: {stock_data.get('sent_score', 0):.1f}
        21-day Return: {(stock_data.get('return_21d', 0) or 0)*100:+.1f}%
        Volatility: {(stock_data.get('volatility', 0) or 0)*100:.1f}%
        RSI: {stock_data.get('rsi', 50):.1f}
        
        Provide:
        1. Overall assessment (bullish/neutral/bearish)
        2. Key strengths
        3. Key risks
        4. Recommended action
        """
        
        analysis = generator._call_gemini(prompt)
        
        if analysis:
            st.markdown("### AI Analysis")
            st.markdown(analysis)
        else:
            st.warning("Could not generate analysis. Check API configuration.")
            
    except Exception as e:
        st.error(f"Error generating analysis: {e}")


def _render_generate_tab(run_id: str):
    """Render tab for generating new AI insights."""
    render_section_header("Generate New Insights", "🔮")
    
    st.info("Generate new AI-powered analysis and recommendations for this run.")
    
    # Options
    col1, col2 = st.columns(2)
    
    with col1:
        generate_commentary = st.checkbox("Generate Commentary", value=True)
        generate_recommendations = st.checkbox("Generate Recommendations", value=True)
    
    with col2:
        risk_profile = st.selectbox(
            "Risk Profile",
            ["Conservative", "Moderate", "Aggressive"]
        )
    
    # Generate button
    if st.button("🚀 Generate AI Insights", type="primary"):
        with st.spinner("Generating AI insights... This may take a minute."):
            _generate_new_insights(run_id, generate_commentary, generate_recommendations, risk_profile)


def _generate_new_insights(run_id: str, gen_commentary: bool, gen_recommendations: bool, risk_profile: str):
    """Generate new AI insights for a run."""
    try:
        scores = load_run_scores(run_id)
        
        if not scores:
            st.error("No stock data available for this run")
            return
        
        scores_df = pd.DataFrame(scores)
        
        from src.analytics.ai_insights import AIInsightsGenerator
        generator = AIInsightsGenerator()
        
        if gen_commentary:
            st.markdown("### Portfolio Commentary")
            
            # Generate summary
            summary = generator.generate_executive_summary(scores_df.to_dict('records'))
            if summary:
                st.markdown(summary)
            
            # Sector analysis
            sector_analysis = generator.generate_sector_analysis(scores_df.to_dict('records'))
            if sector_analysis:
                st.markdown("### Sector Analysis")
                st.markdown(sector_analysis)
        
        if gen_recommendations:
            st.markdown("### Investment Recommendations")
            
            recommendations = generator.generate_recommendations(
                scores_df.to_dict('records'),
                risk_profile=risk_profile.lower()
            )
            if recommendations:
                st.markdown(recommendations)
        
        st.success("AI insights generated successfully!")
        
    except Exception as e:
        st.error(f"Error generating insights: {e}")
