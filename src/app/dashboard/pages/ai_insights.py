"""
AI Insights Page
================
AI-powered analysis and recommendations.
"""

import streamlit as st
import pandas as pd

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card, render_alert
from ..components.tooltips import get_tooltip
from ..data import load_runs, load_run_scores, load_ai_commentary, load_ai_recommendations
from ..utils import format_percent, format_number, get_run_folder
from ..config import COLORS
from src.analytics.analysis_service import AnalysisService


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
        format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}",
        help=get_tooltip('select_run') or "Choose a completed run to view AI commentary and recommendations"
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
    
    # Try loading from database first
    from src.analytics.analysis_service import AnalysisService
    service = AnalysisService()
    db_insights = service.get_all_ai_insights(run_id)
    db_recommendations = [i for i in db_insights if i.insight_type == 'recommendations']
    
    # Also try loading from files
    file_recommendations = load_ai_recommendations(run_id)
    
    # Use database recommendations if available, otherwise use file
    recommendations = None
    if db_recommendations:
        # Get latest recommendation from database
        latest = max(db_recommendations, key=lambda x: x.created_at)
        # Try to parse as JSON, otherwise use as text
        try:
            import json
            recommendations = json.loads(latest.content) if latest.content else None
        except:
            # If not JSON, create a simple dict structure
            # Get risk profile from context if available
            context = latest.get_context() if hasattr(latest, 'get_context') else {}
            recommendations = {
                'summary': latest.content,
                'generated_at': latest.created_at.isoformat(),
                'risk_profile': context.get('risk_profile', 'moderate')
            }
    
    if not recommendations:
        recommendations = file_recommendations
    
    if not recommendations:
        st.info("No AI recommendations available for this run. Generate one using the options below.")
        
        # Quick generate button
        st.markdown("### Quick Generate Recommendations")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            risk_profile = st.selectbox(
                "Risk Profile",
                ["Conservative", "Moderate", "Aggressive"],
                key="recommendations_risk_profile",
                help=get_tooltip('risk_tolerance') or "Risk tolerance for recommendations"
            )
        
        with col2:
            if st.button("🚀 Generate Recommendations", type="primary", use_container_width=True,
                        help=get_tooltip('generate_recommendations')):
                from ..components.loading import loading_spinner
                from ..components.errors import ErrorHandler
                
                with loading_spinner("Generating recommendations... This may take 1-2 minutes.", show_progress=False):
                    try:
                        from src.analytics.ai_insights import AIInsightsGenerator
                        from ..data import load_run_scores
                        import pandas as pd
                        from datetime import datetime
                        import json
                        
                        # Load stock data
                        scores = load_run_scores(run_id)
                        if not scores:
                            st.error("No stock data available for this run")
                            return
                        
                        scores_df = pd.DataFrame(scores)
                        
                        # Generate recommendations
                        generator = AIInsightsGenerator(save_to_db=True)
                        
                        if not generator.is_available:
                            st.error("AI insights not available. Please check GEMINI_API_KEY configuration.")
                            return
                        
                        # Generate recommendations
                        recommendations_text = generator.generate_recommendations(
                            scores_df.to_dict('records'),
                            risk_profile=risk_profile.lower(),
                            run_id=run_id
                        )
                        
                        if recommendations_text:
                            # Save to database
                            service.save_ai_insight(
                                run_id=run_id,
                                insight_type='recommendations',
                                content=recommendations_text,
                                context={'risk_profile': risk_profile.lower()}
                            )
                            
                            # Also save to file for compatibility
                            run_folder = get_run_folder(run_id)
                            run_folder.mkdir(parents=True, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            recommendations_json = {
                                'run_id': run_id,
                                'risk_profile': risk_profile.lower(),
                                'generated_at': datetime.now().isoformat(),
                                'recommendations': recommendations_text,
                                'summary': recommendations_text
                            }
                            
                            json_file = run_folder / f"recommendations_{run_id[:8]}_{timestamp}.json"
                            with open(json_file, 'w') as f:
                                json.dump(recommendations_json, f, indent=2)
                            
                            st.success("✅ Recommendations generated successfully!")
                            st.rerun()
                        else:
                            st.warning("⚠️ No recommendations generated. Check API configuration.")
                            
                    except Exception as e:
                        ErrorHandler.render_error(
                            e,
                            error_type='ai_generation_error',
                            show_traceback=True,
                            custom_actions=[
                                "Check GEMINI_API_KEY is configured",
                                "Verify stock data is available",
                                "Try generating from 'Generate New' tab instead"
                            ]
                        )
        
        st.markdown("---")
        st.markdown("### Alternative Method")
        st.markdown("""
        **Generate from 'Generate New' Tab:**
        - Go to the **"🔮 Generate New"** tab above
        - Check **"Generate Recommendations"**
        - Select your **Risk Profile**
        - Click **"🚀 Generate AI Insights"**
        """)
        return
    
    # Display recommendations
    # Check if structured (with profiles) or plain text
    profiles = recommendations.get('profiles', {})
    
    if profiles:
        # Structured recommendations with multiple profiles
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
    else:
        # Plain text recommendations (from database or simple format)
        summary = recommendations.get('summary') or recommendations.get('recommendations')
        if summary:
            # Show metadata if available
            if 'risk_profile' in recommendations:
                st.info(f"**Risk Profile:** {recommendations['risk_profile'].title()}")
            if 'generated_at' in recommendations:
                st.caption(f"Generated: {recommendations['generated_at']}")
            st.markdown("---")
            st.markdown(summary)
        else:
            st.markdown(recommendations.get('recommendations', 'No recommendations available'))


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
    if st.button("🤖 Generate AI Analysis", key=f"ai_{selected_ticker}",
                help=get_tooltip('generate_insights')):
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
            ["Conservative", "Moderate", "Aggressive"],
            help=get_tooltip('risk_tolerance') or "Risk tolerance for AI analysis"
        )
    
    # Generate button
    if st.button("🚀 Generate AI Insights", type="primary",
                help=get_tooltip('generate_insights')):
        with st.spinner("Generating AI insights... This may take a minute."):
            _generate_new_insights(run_id, generate_commentary, generate_recommendations, risk_profile)


def _generate_new_insights(run_id: str, gen_commentary: bool, gen_recommendations: bool, risk_profile: str):
    """Generate new AI insights for a run and save them to files."""
    try:
        scores = load_run_scores(run_id)
        
        if not scores:
            st.error("No stock data available for this run")
            return
        
        scores_df = pd.DataFrame(scores)
        
        # Validate data quality before generating insights
        from src.analytics.data_validation import InsightsDataValidator
        from src.analytics.ai_insights import AIInsightsGenerator
        from datetime import datetime
        import json
        
        validator = InsightsDataValidator()
        is_valid, validation_report = validator.validate(scores_df)
        
        # Display validation results
        st.markdown("### Data Quality Validation")
        
        if validation_report['is_valid']:
            if validation_report['has_warnings']:
                st.warning(validation_report['summary'])
                with st.expander("View Validation Details", expanded=False):
                    st.markdown(validator.get_validation_message(validation_report))
            else:
                st.success(validation_report['summary'])
        else:
            st.error(validation_report['summary'])
            with st.expander("View Validation Errors", expanded=True):
                st.markdown(validator.get_validation_message(validation_report))
            
            # Ask user if they want to proceed despite errors
            if not st.checkbox("⚠️ Proceed with AI insights generation despite errors (not recommended)", value=False):
                st.stop()
        
        generator = AIInsightsGenerator(save_to_db=True)  # Enable database saving
        
        # Get run folder for saving files
        run_folder = get_run_folder(run_id)
        run_folder.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []
        
        if gen_commentary:
            st.markdown("### Portfolio Commentary")
            
            # Add validation context to data for AI
            scores_data = scores_df.to_dict('records')
            validation_context = None
            if validation_report['has_warnings'] or not validation_report['is_valid']:
                validation_context = {
                    'has_errors': not validation_report['is_valid'],
                    'warnings': validation_report['warnings'],
                    'errors': validation_report['errors']
                }
            
            # Generate summary
            summary = generator.generate_executive_summary(scores_data, validation_context=validation_context)
            sector_analysis = generator.generate_sector_analysis(scores_data, validation_context=validation_context)
            
            # Combine into full commentary
            commentary_parts = []
            if summary:
                commentary_parts.append(f"# Executive Summary\n\n{summary}\n")
                st.markdown(summary)
            
            if sector_analysis:
                commentary_parts.append(f"# Sector Analysis\n\n{sector_analysis}\n")
                st.markdown("### Sector Analysis")
                st.markdown(sector_analysis)
            
            # Save commentary to file
            if commentary_parts:
                commentary_text = "\n".join(commentary_parts)
                commentary_text += f"\n\n---\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
                
                commentary_file = run_folder / f"ai_commentary_{run_id[:8]}_{timestamp}.md"
                with open(commentary_file, 'w') as f:
                    f.write(commentary_text)
                saved_files.append(commentary_file.name)
                st.success(f"✅ Commentary saved to: `{commentary_file.name}`")
        
        if gen_recommendations:
            st.markdown("### Investment Recommendations")
            
            recommendations = generator.generate_recommendations(
                scores_df.to_dict('records'),
                risk_profile=risk_profile.lower(),
                run_id=run_id
            )
            
            if recommendations:
                st.markdown(recommendations)
                
                # Save recommendations to both JSON and Markdown
                # JSON format (structured)
                recommendations_json = {
                    'run_id': run_id,
                    'risk_profile': risk_profile.lower(),
                    'generated_at': datetime.now().isoformat(),
                    'recommendations': recommendations,
                    'summary': recommendations  # Store full text in summary field
                }
                
                json_file = run_folder / f"recommendations_{run_id[:8]}_{timestamp}.json"
                with open(json_file, 'w') as f:
                    json.dump(recommendations_json, f, indent=2)
                saved_files.append(json_file.name)
                
                # Markdown format (readable)
                md_file = run_folder / f"recommendations_{run_id[:8]}_{timestamp}.md"
                with open(md_file, 'w') as f:
                    f.write(f"# Investment Recommendations\n\n")
                    f.write(f"**Risk Profile:** {risk_profile}\n\n")
                    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(recommendations)
                    f.write(f"\n\n---\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
                saved_files.append(md_file.name)
                
                st.success(f"✅ Recommendations saved to: `{json_file.name}` and `{md_file.name}`")
        
        if saved_files:
            st.success(f"🎉 AI insights generated and saved successfully!")
            st.info(f"📁 Files saved in: `{run_folder.relative_to(run_folder.parent.parent.parent)}`")
            # Clear cache so new files are visible
            st.cache_data.clear()
        else:
            st.warning("⚠️ No insights were generated. Check API configuration.")
        
    except Exception as e:
        st.error(f"Error generating insights: {e}")
        import traceback
        st.code(traceback.format_exc())