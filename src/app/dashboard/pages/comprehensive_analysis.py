"""
Comprehensive Analysis Page
============================
Display all analysis results: attribution, benchmark, factor exposure, AI insights.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
import zipfile
from datetime import datetime
from pathlib import Path

from ..components.sidebar import render_page_header
from ..components.enhanced_charts import create_attribution_waterfall, create_factor_exposure_heatmap
from ..components.tooltips import get_tooltip
from ..data import load_runs, get_run_folder
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService
from src.analytics.data_loader import load_run_data_for_analysis
from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner


def render_comprehensive_analysis():
    """Render comprehensive analysis page."""
    render_page_header("Comprehensive Analysis", "Deep dive into portfolio performance")
    
    # Get runs
    runs = load_runs()
    if not runs:
        st.warning("No analysis runs found. Run an analysis first.")
        return
    
    # Run selector
    run_options = {f"{r['name'] or r['run_id'][:16]} ({r['run_id'][:8]})": r['run_id'] 
                   for r in runs}
    selected_run_label = st.selectbox(
        "Select Run",
        options=list(run_options.keys()),
        key="comp_analysis_run",
        help=get_tooltip('run_select') or "Select the run to analyze across all advanced modules"
    )
    selected_run_id = run_options[selected_run_label]
    selected_run = next(r for r in runs if r['run_id'] == selected_run_id)
    
    # Initialize service
    service = AnalysisService()
    
    # Check if analysis exists
    analysis_results = service.get_all_analysis_results(selected_run_id)
    analysis_types = {r.analysis_type for r in analysis_results}
    
    # Run analysis button
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Run All Analyses", type="primary", use_container_width=True, 
                    help=get_tooltip('run_all_analyses')):
            from ..components.loading import loading_spinner
            from ..components.errors import ErrorHandler
            
            with loading_spinner("Running comprehensive analysis...", show_progress=False):
                try:
                    # Load data
                    run_dir = get_run_folder(selected_run_id, selected_run.get('watchlist'))
                    data = load_run_data_for_analysis(selected_run_id, run_dir)
                    
                    if data['error']:
                        ErrorHandler.render_error(
                            Exception(data['error']),
                            error_type='data_loading_error',
                            show_traceback=False,
                            custom_actions=[
                                "Verify the run folder exists",
                                "Check if required data files are present",
                                "Try selecting a different run",
                                "Re-run the analysis to generate missing data"
                            ]
                        )
                    else:
                        # Run analysis
                        runner = ComprehensiveAnalysisRunner()
                        results = runner.run_all_analysis(
                            run_id=selected_run_id,
                            portfolio_data=data['portfolio_data'] or {},
                            stock_data=data['stock_data'],
                            save_ai_insights=True
                        )
                        st.success("✅ Analysis complete!")
                        st.rerun()
                except Exception as e:
                    ErrorHandler.render_error(
                        e,
                        error_type='analysis_error',
                        show_traceback=True,
                        custom_actions=[
                            "Check the technical details below",
                            "Verify all required data is available",
                            "Review configuration settings",
                            "Try running individual analysis modules"
                        ]
                    )
    
    with col2:
        export_format = st.selectbox(
            "Export Format",
            ["PDF", "Excel", "CSV", "JSON"],
            key="export_format",
            help="Choose output format for export files"
        )
        if st.button("📥 Export Results", use_container_width=True):
            try:
                from ..export import export_to_pdf, export_to_excel, export_to_csv, export_to_json
                
                # Collect all analysis results
                all_results = {}
                for analysis_type in ['attribution', 'benchmark_comparison', 'factor_exposure', 'rebalancing', 'style']:
                    result = service.get_analysis_result(selected_run_id, analysis_type)
                    if result:
                        all_results[analysis_type] = {
                            'results': result.get_results() if hasattr(result, 'get_results') else result.results_json,
                            'summary': result.get_summary() if hasattr(result, 'get_summary') else result.summary_json
                        }
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_filename = f"analysis_{selected_run_id[:16]}_{timestamp}"
                
                if export_format == "PDF":
                    pdf_bytes = export_to_pdf(all_results, selected_run)
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"{base_filename}.pdf",
                        mime="application/pdf"
                    )
                elif export_format == "Excel":
                    excel_bytes = export_to_excel(all_results, selected_run)
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_bytes,
                        file_name=f"{base_filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                elif export_format == "CSV":
                    # Export each analysis type as separate CSV
                    csv_files = {}
                    for analysis_type, data in all_results.items():
                        if 'results' in data and isinstance(data['results'], dict):
                            df = pd.json_normalize(data['results'])
                            csv_bytes = export_to_csv(df)
                            csv_files[f"{analysis_type}.csv"] = csv_bytes
                    
                    if csv_files:
                        # Create a zip file with all CSVs
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for filename, csv_data in csv_files.items():
                                zip_file.writestr(filename, csv_data)
                        zip_buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download CSV (ZIP)",
                            data=zip_buffer.read(),
                            file_name=f"{base_filename}.zip",
                            mime="application/zip"
                        )
                elif export_format == "JSON":
                    json_bytes = export_to_json(all_results)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_bytes,
                        file_name=f"{base_filename}.json",
                        mime="application/json"
                    )
            except ImportError as e:
                st.error(f"Export requires additional packages: {e}")
            except Exception as e:
                st.error(f"Export failed: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Display analysis results
    tabs = st.tabs([
        "📈 Performance Attribution",
        "📊 Benchmark Comparison", 
        "🔍 Factor Exposure",
        "⚖️ Rebalancing",
        "🎨 Style Analysis",
        "🤖 AI Insights",
        "💡 Recommendations"
    ])
    
    # Performance Attribution Tab
    with tabs[0]:
        _render_attribution_tab(service, selected_run_id, analysis_types)
    
    # Benchmark Comparison Tab
    with tabs[1]:
        _render_benchmark_tab(service, selected_run_id, analysis_types)
    
    # Factor Exposure Tab
    with tabs[2]:
        _render_factor_tab(service, selected_run_id, analysis_types)
    
    # Rebalancing Tab
    with tabs[3]:
        _render_rebalancing_tab(service, selected_run_id, analysis_types)
    
    # Style Analysis Tab
    with tabs[4]:
        _render_style_tab(service, selected_run_id, analysis_types)
    
    # AI Insights Tab
    with tabs[5]:
        _render_ai_insights_tab(service, selected_run_id)
    
    # Recommendations Tab
    with tabs[6]:
        _render_recommendations_tab(service, selected_run_id)


def _render_attribution_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render performance attribution tab."""
    if 'attribution' not in analysis_types:
        st.info("Performance attribution not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'attribution')
    if not result:
        st.warning("Attribution data not found.")
        return
    
    attribution = result.get_results()
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Return", format_percent(attribution.get('total_return', 0)))
    with col2:
        st.metric("Factor", format_percent(attribution['attributions'].get('factor', 0)))
    with col3:
        st.metric("Sector", format_percent(attribution['attributions'].get('sector', 0)))
    with col4:
        st.metric("Stock Selection", format_percent(attribution['attributions'].get('stock_selection', 0)))
    with col5:
        st.metric("Timing", format_percent(attribution['attributions'].get('timing', 0)))
    
    # Attribution waterfall chart
    st.markdown("### Attribution Waterfall Chart")
    waterfall_data = {
        'factor_attribution': attribution['attributions'].get('factor', 0),
        'sector_attribution': attribution['attributions'].get('sector', 0),
        'stock_selection_attribution': attribution['attributions'].get('stock_selection', 0),
        'timing_attribution': attribution['attributions'].get('timing', 0),
        'total_return': attribution.get('total_return', 0)
    }
    fig = create_attribution_waterfall(waterfall_data, "Performance Attribution Waterfall")
    st.plotly_chart(fig, use_container_width=True)
    
    # Also show bar chart for comparison
    st.markdown("### Attribution Breakdown (Bar Chart)")
    attributions = attribution['attributions']
    fig = go.Figure(data=[
        go.Bar(
            x=list(attributions.keys()),
            y=[attributions.get(k, 0) * 100 for k in attributions.keys()],
            marker_color=['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'],
            text=[f"{attributions.get(k, 0)*100:.2f}%" for k in attributions.keys()],
            textposition='outside'
        )
    ])
    fig.update_layout(
        title="Performance Attribution Breakdown",
        xaxis_title="Attribution Component",
        yaxis_title="Return Contribution (%)",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed breakdown
    if 'breakdown' in attribution:
        st.subheader("Detailed Breakdown")
        breakdown = attribution['breakdown']
        
        # Factor breakdown
        if 'factor' in breakdown and breakdown['factor']:
            factor_data = breakdown['factor']
            # Handle different structures: dict with 'by_factor' or direct dict
            if isinstance(factor_data, dict):
                if 'by_factor' in factor_data:
                    factor_items = factor_data['by_factor']
                else:
                    # Direct dict of factors
                    factor_items = factor_data
                
                if factor_items and isinstance(factor_items, dict):
                    st.write("**Factor Attribution:**")
                    factor_df = pd.DataFrame(list(factor_items.items()), 
                                           columns=['Factor', 'Contribution'])
                    st.dataframe(factor_df, use_container_width=True)
        
        # Sector breakdown
        if 'sector' in breakdown and breakdown['sector']:
            sector_data = breakdown['sector']
            # Handle different structures: dict with 'by_sector' or direct dict
            if isinstance(sector_data, dict):
                if 'by_sector' in sector_data:
                    sector_items = sector_data['by_sector']
                else:
                    # Direct dict of sectors
                    sector_items = sector_data
                
                if sector_items and isinstance(sector_items, dict):
                    st.write("**Sector Attribution:**")
                    sector_df = pd.DataFrame(list(sector_items.items()),
                                           columns=['Sector', 'Contribution'])
                    st.dataframe(sector_df, use_container_width=True)
        
        # Stock selection breakdown
        if 'stock_selection' in breakdown and breakdown['stock_selection']:
            stock_data = breakdown['stock_selection']
            # Handle different structures
            if isinstance(stock_data, dict):
                if 'by_sector' in stock_data:
                    stock_items = stock_data['by_sector']
                elif 'by_stock' in stock_data:
                    stock_items = stock_data['by_stock']
                else:
                    stock_items = stock_data
                
                if stock_items and isinstance(stock_items, dict):
                    st.write("**Stock Selection Attribution:**")
                    stock_df = pd.DataFrame(list(stock_items.items()),
                                          columns=['Stock/Sector', 'Contribution'])
                    st.dataframe(stock_df, use_container_width=True)


def _render_benchmark_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render benchmark comparison tab."""
    if 'benchmark_comparison' not in analysis_types:
        st.info("Benchmark comparison not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'benchmark_comparison')
    if not result:
        st.warning("Benchmark comparison data not found.")
        return
    
    comparisons = result.get_results()
    
    # Display comparisons for each benchmark
    for benchmark_symbol, comparison in comparisons.items():
        if 'error' in comparison:
            st.warning(f"Error comparing to {benchmark_symbol}: {comparison['error']}")
            continue
        
        st.subheader(f"vs {comparison.get('benchmark_name', benchmark_symbol)}")
        
        portfolio_metrics = comparison['portfolio_metrics']
        benchmark_metrics = comparison['benchmark_metrics']
        relative_metrics = comparison['relative_metrics']
        
        # Metrics comparison
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Portfolio**")
            st.metric("Return", format_percent(portfolio_metrics.get('return', 0)))
            st.metric("Sharpe", f"{portfolio_metrics.get('sharpe', 0):.2f}")
            st.metric("Max DD", format_percent(portfolio_metrics.get('max_drawdown', 0)))
        
        with col2:
            st.write("**Benchmark**")
            st.metric("Return", format_percent(benchmark_metrics.get('return', 0)))
            st.metric("Sharpe", f"{benchmark_metrics.get('sharpe', 0):.2f}")
            st.metric("Max DD", format_percent(benchmark_metrics.get('max_drawdown', 0)))
        
        with col3:
            st.write("**Relative**")
            alpha = relative_metrics.get('alpha', 0)
            beta = relative_metrics.get('beta', 1)
            st.metric("Alpha", format_percent(alpha), 
                     delta=f"{alpha*100:.2f}%" if alpha else None)
            st.metric("Beta", f"{beta:.2f}")
            st.metric("Info Ratio", f"{relative_metrics.get('information_ratio', 0):.2f}")
        
        st.markdown("---")


def _render_factor_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render factor exposure tab."""
    if 'factor_exposure' not in analysis_types:
        st.info("Factor exposure analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'factor_exposure')
    if not result:
        st.warning("Factor exposure data not found.")
        return
    
    factor_data = result.get_results()
    factor_exposures = factor_data.get('factor_exposures', [])
    
    if not factor_exposures:
        st.info("No factor exposures calculated.")
        return
    
    # Factor exposure heatmap
    st.markdown("### Factor Exposure Heatmap")
    exposures_dict = {}
    for factor in factor_exposures:
        exposures_dict[factor['factor_name']] = {
            'exposure': factor.get('exposure', 0),
            'contribution_to_return': factor.get('contribution_to_return', 0),
            'contribution_to_risk': factor.get('contribution_to_risk', 0)
        }
    
    fig = create_factor_exposure_heatmap(exposures_dict, "Factor Exposure Analysis")
    st.plotly_chart(fig, use_container_width=True)
    
    # Also show bar chart
    st.markdown("### Factor Exposures (Bar Chart)")
    factors_df = pd.DataFrame(factor_exposures)
    fig = go.Figure(data=[
        go.Bar(
            x=factors_df['factor_name'],
            y=factors_df['exposure'],
            marker_color=factors_df['exposure'].apply(
                lambda x: '#10b981' if x > 0 else '#ef4444'
            ),
            text=[f"{x:.3f}" for x in factors_df['exposure']],
            textposition='outside'
        )
    ])
    fig.update_layout(
        title="Factor Exposures",
        xaxis_title="Factor",
        yaxis_title="Exposure",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
    
    # Factor details table
    st.subheader("Factor Details")
    display_df = factors_df[['factor_name', 'factor_type', 'exposure', 
                             'contribution_to_return', 'contribution_to_risk']].copy()
    display_df.columns = ['Factor', 'Type', 'Exposure', 'Return Contribution', 'Risk Contribution']
    st.dataframe(display_df, use_container_width=True)


def _render_ai_insights_tab(service: AnalysisService, run_id: str):
    """Render AI insights tab."""
    insights = service.get_all_ai_insights(run_id)
    
    # Always show generate button at the top
    st.markdown("### Generate AI Insights")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        risk_profile = st.selectbox(
            "Risk Profile",
            ["Conservative", "Moderate", "Aggressive"],
            key="ai_insights_risk_profile"
        )
    
    with col2:
        gen_commentary = st.checkbox("Generate Commentary", value=True, key="comp_ai_gen_commentary")
    
    with col3:
        gen_recommendations = st.checkbox("Generate Recommendations", value=True, key="comp_ai_gen_recommendations")
    
    if st.button("🚀 Generate AI Insights", type="primary", use_container_width=True, key="comp_ai_generate_button"):
                from ..components.loading import loading_spinner
                from ..components.errors import ErrorHandler
                
                with loading_spinner("Generating AI insights... This may take 1-2 minutes.", show_progress=False):
                    try:
                        from src.analytics.ai_insights import AIInsightsGenerator
                        from ..data import load_run_scores
                        import pandas as pd
                        
                        # Load stock data
                        scores = load_run_scores(run_id)
                        if not scores:
                            st.error("No stock data available for this run")
                            return
                        
                        scores_df = pd.DataFrame(scores)
                        
                        # Generate insights
                        generator = AIInsightsGenerator(save_to_db=True)
                        
                        if not generator.is_available:
                            st.error("AI insights not available. Please check GEMINI_API_KEY configuration.")
                            return
                        
                        # Generate commentary
                        summary = generator.generate_executive_summary(scores_df.to_dict('records'))
                        sector_analysis = generator.generate_sector_analysis(scores_df.to_dict('records'))
                        
                        # Save to database
                        if summary:
                            service.save_ai_insight(
                                run_id=run_id,
                                insight_type='commentary',
                                content=summary,
                                context={'section': 'executive_summary'}
                            )
                        
                        if sector_analysis:
                            service.save_ai_insight(
                                run_id=run_id,
                                insight_type='commentary',
                                content=sector_analysis,
                                context={'section': 'sector_analysis'}
                            )
                        
                        # Generate recommendations
                        recommendations = generator.generate_recommendations(
                            scores_df.to_dict('records'),
                            risk_profile=risk_profile.lower(),
                            run_id=run_id
                        )
                        
                        if recommendations:
                            service.save_ai_insight(
                                run_id=run_id,
                                insight_type='recommendations',
                                content=recommendations,
                                context={'risk_profile': risk_profile.lower()}
                            )
                        
                        st.success("✅ AI insights generated successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        ErrorHandler.render_error(
                            e,
                            error_type='ai_generation_error',
                            show_traceback=True,
                            custom_actions=[
                                "Check GEMINI_API_KEY is configured",
                                "Verify stock data is available",
                                "Try generating from AI Insights page instead"
                            ]
                        )
    
    st.markdown("---")
    
    # Display existing insights if available
    if not insights:
        st.info("No AI insights found yet. Use the button above to generate insights.")
        return
    
    # Group by type
    insight_types = {}
    for insight in insights:
        itype = insight.insight_type
        if itype not in insight_types:
            insight_types[itype] = []
        insight_types[itype].append(insight)
    
    # Display each type
    for insight_type, insight_list in insight_types.items():
        # Get latest
        latest = max(insight_list, key=lambda x: x.created_at)
        
        st.subheader(insight_type.replace('_', ' ').title())
        st.markdown(f"*Generated: {latest.created_at.strftime('%Y-%m-%d %H:%M')}*")
        st.markdown("---")
        st.markdown(latest.content)
        st.markdown("---")


def _render_rebalancing_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render rebalancing analysis tab."""
    if 'rebalancing' not in analysis_types:
        st.info("Rebalancing analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'rebalancing')
    if not result:
        st.warning("Rebalancing data not found.")
        return
    
    rebalancing = result.get_results()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Drift", format_percent(rebalancing.get('current_drift', 0)))
    with col2:
        st.metric("Avg Turnover", format_percent(rebalancing.get('avg_turnover', 0)))
    with col3:
        st.metric("Total Cost", format_percent(rebalancing.get('total_transaction_cost', 0)))
    with col4:
        st.metric("Rebalance Events", rebalancing.get('rebalance_events', 0))
    
    # Recommendation
    recommendation = rebalancing.get('recommendation', '')
    if 'Rebalance now' in recommendation:
        st.warning(recommendation)
    else:
        st.info(recommendation)
    
    # Optimal frequency
    if 'optimal_frequency' in rebalancing:
        opt_freq = rebalancing['optimal_frequency']
        st.subheader("Optimal Rebalancing Frequency")
        st.write(f"**Recommended:** {opt_freq.get('recommended', 'unknown').title()}")
        
        if 'frequencies' in opt_freq:
            freq_df = pd.DataFrame(opt_freq['frequencies']).T
            st.dataframe(freq_df, use_container_width=True)


def _render_style_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render style analysis tab."""
    if 'style' not in analysis_types:
        st.info("Style analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'style')
    if not result:
        st.warning("Style analysis data not found.")
        return
    
    style = result.get_results()
    
    if 'error' in style:
        st.error(f"Error: {style['error']}")
        return
    
    # Overall style
    gv_class = style.get('growth_value', {}).get('classification', 'Unknown')
    size_class = style.get('size', {}).get('classification', 'Unknown')
    overall = f"{gv_class} {size_class}"
    st.metric("Overall Style", overall)
    
    # Growth vs Value
    if 'growth_value' in style and style['growth_value']:
        gv = style['growth_value']
        st.subheader("Growth vs Value")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Classification:** {gv.get('classification', 'unknown').title()}")
        with col2:
            if 'portfolio_pe' in gv:
                st.write(f"**Portfolio PE:** {gv['portfolio_pe']:.2f}")
                if 'weighted_avg_pe' in gv:
                    st.write(f"**Weighted Avg PE:** {gv['weighted_avg_pe']:.2f}")
    
    # Size
    if 'size' in style and style['size']:
        size = style['size']
        st.subheader("Size Classification")
        st.write(f"**Classification:** {size.get('classification', 'unknown')}")
        if 'portfolio_market_cap_billions' in size:
            st.write(f"**Portfolio Market Cap:** ${size['portfolio_market_cap_billions']:.2f}B")


def _render_recommendations_tab(service: AnalysisService, run_id: str):
    """Render recommendations tab."""
    recommendations = service.get_recommendations(run_id=run_id)
    
    if not recommendations:
        st.info("No recommendations found for this run.")
        return
    
    # Group by action
    by_action = {}
    for rec in recommendations:
        action = rec.action
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(rec)
    
    for action, recs in by_action.items():
        st.subheader(f"{action} Recommendations ({len(recs)})")
        
        recs_df = pd.DataFrame([{
            'Ticker': r.ticker,
            'Date': r.recommendation_date.strftime('%Y-%m-%d') if r.recommendation_date else '',
            'Reason': r.reason or '',
            'Confidence': f"{r.confidence*100:.0f}%" if r.confidence else '',
            'Target': f"${r.target_price:.2f}" if r.target_price else '',
            'Return': format_percent(r.actual_return) if r.actual_return else ''
        } for r in recs])
        
        st.dataframe(recs_df, use_container_width=True)
        st.markdown("---")
