"""
Purchase Triggers Page
======================
Display purchase triggers and selection logic for stocks.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import yaml
from datetime import datetime
from typing import Optional, Dict, List

from ..components.sidebar import render_page_header, render_section_header
from ..data import load_runs
from ..config import COLORS, CHART_COLORS
from src.analysis.domain_analysis import DomainAnalyzer, AnalysisConfig
from src.analytics.models import get_db, Run, StockScore
import time
import subprocess


def format_score(value: float, max_val: float = 100.0) -> str:
    """Format score with color coding."""
    if pd.isna(value):
        return "N/A"
    
    pct = value / max_val
    if pct >= 0.8:
        return f"{value:.1f}"
    elif pct >= 0.6:
        return f"{value:.1f}"
    elif pct >= 0.4:
        return f"{value:.1f}"
    else:
        return f"{value:.1f}"


def get_score_color(value: float, max_val: float = 100.0) -> str:
    """Get color for score."""
    if pd.isna(value):
        return COLORS['muted']
    
    pct = value / max_val
    if pct >= 0.8:
        return COLORS['success']
    elif pct >= 0.6:
        return CHART_COLORS['warning']
    elif pct >= 0.4:
        return COLORS['warning']
    else:
        return COLORS['danger']


def check_filters(row: pd.Series, config: AnalysisConfig) -> Dict[str, bool]:
    """Check if stock passes all filters."""
    filters = {}
    
    if 'roe' in row.index and config.min_roe is not None:
        filters['roe'] = pd.isna(row['roe']) or row['roe'] >= config.min_roe
    else:
        filters['roe'] = True
    
    if 'net_margin' in row.index and config.min_net_margin is not None:
        filters['net_margin'] = pd.isna(row['net_margin']) or row['net_margin'] >= config.min_net_margin
    else:
        filters['net_margin'] = True
    
    if 'debt_to_equity' in row.index and config.max_debt_to_equity is not None:
        filters['debt_to_equity'] = pd.isna(row['debt_to_equity']) or row['debt_to_equity'] <= config.max_debt_to_equity
    else:
        filters['debt_to_equity'] = True
    
    if 'market_cap' in row.index and config.min_market_cap is not None:
        filters['market_cap'] = pd.isna(row['market_cap']) or row['market_cap'] >= config.min_market_cap
    else:
        filters['market_cap'] = True
    
    if 'avg_volume' in row.index and config.min_avg_volume is not None:
        filters['avg_volume'] = pd.isna(row['avg_volume']) or row['avg_volume'] >= config.min_avg_volume
    else:
        filters['avg_volume'] = True
    
    return filters


def load_fundamentals() -> pd.DataFrame:
    """Load fundamentals data."""
    fundamentals_path = Path("data/fundamentals.csv")
    if not fundamentals_path.exists():
        return pd.DataFrame()
    return pd.read_csv(fundamentals_path)


def render_purchase_triggers():
    """Render the purchase triggers page."""
    render_page_header("Purchase Triggers", "Understand why stocks were selected or excluded")
    
    # Help/Guide expander
    with st.expander("📖 How to Read Purchase Triggers - Quick Guide", expanded=False):
        st.markdown("""
        ### Understanding Purchase Triggers
        
        Purchase triggers determine which stocks are selected for portfolios through a multi-step process:
        
        **1. Hard Filters** (Must Pass)
        - Stocks must meet minimum requirements (ROE, margins, debt levels)
        - Check Filter Status section to see pass/fail counts
        
        **2. Domain Score Calculation**
        - Composite score: `(50% × Model) + (30% × Value) + (20% × Quality)`
        - Model Score: ML prediction of 3-month excess return
        - Value Score: PE/PB ranking (cheaper = higher score)
        - Quality Score: ROE/margins ranking (more profitable = higher score)
        
        **3. Selection Process**
        - Vertical: Top K stocks per sector (default: 5)
        - Horizontal: Top N overall (default: 10)
        - Constraints: Max position (15%), Max sector (35%)
        
        ### Reading the Sections
        
        - **⚙️ Configuration**: Shows weights and filter settings
        - **🔍 Filter Status**: How many stocks passed/failed
        - **📊 Sector Rankings**: Top candidates within each sector with score breakdowns
        - **🏆 Overall Top Stocks**: Best stocks across all sectors with scatter plot
        - **🎯 Portfolio Estimate**: Final portfolio composition with weight distribution
        - **🤖 AI Commentary**: AI-generated insights and recommendations
        
        ### Score Color Coding
        
        - 🟢 **Green**: Score ≥ 80 (excellent)
        - 🟡 **Yellow**: Score 60-79 (good)
        - 🟠 **Orange**: Score 40-59 (fair)
        - 🔴 **Red**: Score < 40 (poor)
        
        ### Quick Analysis Tips
        
        1. **Check filter pass rate**: 30-70% is ideal (not too strict, not too lenient)
        2. **Review top stocks**: Look for balanced scores (all components high)
        3. **Check sector balance**: Ensure diversification across sectors
        4. **Use AI commentary**: Get objective analysis and recommendations
        
        **📚 For detailed documentation, see:** `docs/purchase-triggers.md`
        """)
    
    # Load runs
    runs = load_runs()
    if not runs:
        st.warning("No runs found. Please run an analysis first.")
        return
    
    # Run selection
    run_options = {f"{r.get('name', r['run_id'][:16])} ({r['run_id'][:8]})": r['run_id'] for r in runs}
    selected_run_label = st.selectbox(
        "Select Run",
        options=list(run_options.keys()),
        index=0,
        key="purchase_triggers_run_select"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Show run metadata
    selected_run = next((r for r in runs if r['run_id'] == selected_run_id), None)
    if selected_run:
        col1, col2, col3 = st.columns(3)
        with col1:
            if selected_run.get('created_at'):
                created = selected_run['created_at']
                if isinstance(created, str):
                    st.caption(f"📅 Run Created: {created}")
                else:
                    st.caption(f"📅 Run Created: {created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)}")
        with col2:
            st.caption(f"🆔 Run ID: {selected_run_id[:16]}")
        with col3:
            st.caption(f"📊 Status: {selected_run.get('status', 'N/A')}")
    
    # Load config
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
    else:
        config_dict = {}
    
    analysis_config = AnalysisConfig.from_dict(config_dict.get('analysis', {}))
    
    # Load run data
    with st.spinner("Loading run data..."):
        db = get_db("data/analysis.db")
        session = db.get_session()
        
        try:
            run = session.query(Run).filter_by(run_id=selected_run_id).first()
            if not run:
                st.error(f"Run not found: {selected_run_id}")
                return
            
            scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
            scores_data = [s.to_dict() for s in scores]
            scores_df = pd.DataFrame(scores_data)
            
            # Load fundamentals
            fundamentals_df = load_fundamentals()
            if not fundamentals_df.empty and 'ticker' in fundamentals_df.columns:
                # Handle time-series data: get latest values per ticker
                if 'date' in fundamentals_df.columns:
                    # Sort by date descending and take most recent per ticker
                    fundamentals_df = fundamentals_df.sort_values('date', ascending=False)
                    fundamentals_df_unique = fundamentals_df.drop_duplicates(subset=['ticker'], keep='first')
                else:
                    fundamentals_df_unique = fundamentals_df.drop_duplicates(subset=['ticker'], keep='first')
                
                # Map common column name variations
                rename_map = {}
                if 'pe' in fundamentals_df_unique.columns and 'pe_ratio' not in fundamentals_df_unique.columns:
                    rename_map['pe'] = 'pe_ratio'
                if 'pb' in fundamentals_df_unique.columns and 'pb_ratio' not in fundamentals_df_unique.columns:
                    rename_map['pb'] = 'pb_ratio'
                
                if rename_map:
                    fundamentals_df_unique = fundamentals_df_unique.rename(columns=rename_map)
                
                # Select only relevant columns for merge (exclude date if present)
                merge_cols = ['ticker'] + [c for c in fundamentals_df_unique.columns 
                                           if c not in ['ticker', 'date']]
                fundamentals_df_unique = fundamentals_df_unique[merge_cols]
                
                scores_df = scores_df.merge(
                    fundamentals_df_unique,
                    on='ticker',
                    how='left',
                    suffixes=('', '_fund')
                )
                
                # Store diagnostics for display
                available_cols = [c for c in scores_df.columns if c in ['pe_ratio', 'pb_ratio', 'pe', 'pb', 'roe', 'net_margin', 'gross_margin']]
                has_value_data = any(c in ['pe_ratio', 'pb_ratio', 'pe', 'pb'] for c in available_cols)
                has_quality_data = any(c in ['roe', 'net_margin', 'gross_margin'] for c in available_cols)
                
                value_col = next((c for c in ['pe_ratio', 'pe'] if c in scores_df.columns), None)
                merged_count = scores_df[value_col].notna().sum() if value_col else 0
                total_stocks = len(scores_df)
                coverage_pct = (merged_count / total_stocks * 100) if total_stocks > 0 else 0
                
                st.session_state['fundamentals_diagnostics'] = {
                    'available_cols': available_cols,
                    'has_value': has_value_data,
                    'has_quality': has_quality_data,
                    'merged_count': merged_count,
                    'total_stocks': total_stocks,
                    'coverage_pct': coverage_pct
                }
            
            # Compute domain scores
            analyzer = DomainAnalyzer(analysis_config, output_dir="output")
            model_scores = None
            if 'score' in scores_df.columns:
                scores_df_unique = scores_df.drop_duplicates(subset=['ticker'], keep='first')
                model_scores = pd.Series(
                    scores_df_unique['score'].values,
                    index=scores_df_unique['ticker'].values
                )
            
            scored_df = analyzer.compute_domain_score(scores_df, model_scores)
            
            # Store scores_df in session state for download section
            st.session_state['purchase_triggers_scores_df'] = scores_df
            
            # Debug: Check score differentiation
            if 'value_score' in scored_df.columns:
                value_unique = scored_df['value_score'].nunique()
                value_range = (scored_df['value_score'].min(), scored_df['value_score'].max())
                st.session_state['value_score_stats'] = {
                    'unique_count': value_unique,
                    'range': value_range,
                    'mean': scored_df['value_score'].mean()
                }
            
            if 'quality_score' in scored_df.columns:
                quality_unique = scored_df['quality_score'].nunique()
                quality_range = (scored_df['quality_score'].min(), scored_df['quality_score'].max())
                st.session_state['quality_score_stats'] = {
                    'unique_count': quality_unique,
                    'range': quality_range,
                    'mean': scored_df['quality_score'].mean()
                }
            
        finally:
            session.close()
    
    # Analysis timestamp (computed when page loads)
    analysis_timestamp = datetime.now()
    
    # Display configuration
    st.markdown("---")
    render_section_header("⚙️ Configuration", "⚙️")
    
    # Show fundamentals data availability and score diagnostics
    if 'fundamentals_diagnostics' in st.session_state:
        diag = st.session_state['fundamentals_diagnostics']
        
        if diag['has_value'] and diag['has_quality']:
            st.success(
                f"✅ **Fundamentals**: {diag['merged_count']}/{diag['total_stocks']} stocks "
                f"({diag['coverage_pct']:.1f}%) have value & quality data"
            )
        elif diag['has_value']:
            if diag['coverage_pct'] < 50:
                st.error(
                    f"❌ **Critical Issue**: Only {diag['merged_count']}/{diag['total_stocks']} stocks "
                    f"({diag['coverage_pct']:.1f}%) have fundamental data! "
                    f"**{diag['total_stocks'] - diag['merged_count']} stocks will have default value scores of 50.0.**\n\n"
                    f"**Also**: No quality data (ROE/margins) available. All quality scores default to 50.0.\n\n"
                    f"**Solution**: Download comprehensive fundamentals data below."
                )
            else:
                st.warning(
                    f"⚠️ **Fundamentals Warning**: {diag['merged_count']}/{diag['total_stocks']} stocks "
                    f"({diag['coverage_pct']:.1f}%) have value data (PE/PB), "
                    f"but **NO quality data** (ROE/margins). Quality scores will default to 50.0. "
                    f"Download fundamentals with ROE and margin data below."
                )
        else:
            st.error(
                f"❌ **No fundamental data available**. "
                f"All {diag['total_stocks']} stocks will have default value and quality scores of 50.0."
            )
        
        # Add download button if there are issues
        if diag['coverage_pct'] < 100 or not diag['has_quality']:
            st.markdown("---")
            with st.expander("📥 Download Fundamentals Data", expanded=True):
                scores_df_for_download = st.session_state.get('purchase_triggers_scores_df')
                _render_download_fundamentals_section(selected_run, scores_df_for_download)
    
    # Show score differentiation diagnostics
    if 'value_score_stats' in st.session_state:
        vstats = st.session_state['value_score_stats']
        if vstats['unique_count'] == 1:
            st.error(f"❌ **Value Score Issue**: All stocks have the same value score ({vstats['range'][0]:.1f}). This suggests fundamental data isn't differentiating stocks.")
        elif vstats['unique_count'] < 5:
            st.warning(f"⚠️ **Value Score Warning**: Only {vstats['unique_count']} unique value scores (range: {vstats['range'][0]:.1f}-{vstats['range'][1]:.1f}). Limited differentiation.")
        else:
            st.success(f"✅ Value scores differentiated: {vstats['unique_count']} unique values (range: {vstats['range'][0]:.1f}-{vstats['range'][1]:.1f})")
    
    if 'quality_score_stats' in st.session_state:
        qstats = st.session_state['quality_score_stats']
        if qstats['unique_count'] == 1:
            st.error(f"❌ **Quality Score Issue**: All stocks have the same quality score ({qstats['range'][0]:.1f}). Missing ROE/margin data or all stocks have identical fundamentals.")
        elif qstats['unique_count'] < 5:
            st.warning(f"⚠️ **Quality Score Warning**: Only {qstats['unique_count']} unique quality scores (range: {qstats['range'][0]:.1f}-{qstats['range'][1]:.1f}). Limited differentiation.")
        else:
            st.success(f"✅ Quality scores differentiated: {qstats['unique_count']} unique values (range: {qstats['range'][0]:.1f}-{qstats['range'][1]:.1f})")
    
    # Show analysis info with timestamps
    run_created = None
    if selected_run and selected_run.get('created_at'):
        run_created = selected_run['created_at']
        if hasattr(run_created, 'strftime'):
            run_created_str = run_created.strftime('%Y-%m-%d %H:%M:%S')
        else:
            run_created_str = str(run_created)
    else:
        run_created_str = "N/A"
    
    config_mtime = None
    if config_path.exists():
        config_mtime = datetime.fromtimestamp(config_path.stat().st_mtime)
        config_mtime_str = config_mtime.strftime('%Y-%m-%d %H:%M:%S')
    else:
        config_mtime_str = "N/A"
    
    st.caption(
        f"🕐 **Analysis computed**: {analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"📅 **Run created**: {run_created_str} | "
        f"⚙️ **Config modified**: {config_mtime_str}"
    )
    st.info("💡 **Note**: Purchase triggers are computed on-the-fly from existing run data. The analysis uses the current configuration, not the config from when the run was created. To get new results with updated filters/weights, create a new analysis run.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Domain Score Weights**")
        st.metric("Model Score", f"{analysis_config.w_model*100:.0f}%")
        st.metric("Value Score", f"{analysis_config.w_value*100:.0f}%")
        st.metric("Quality Score", f"{analysis_config.w_quality*100:.0f}%")
    
    with col2:
        st.markdown("**Hard Filters**")
        # Handle min_roe: 0.0 means no filter, > 0 means threshold
        if analysis_config.min_roe is not None and analysis_config.min_roe > 0:
            min_roe_display = f"{analysis_config.min_roe*100:.1f}%"
        else:
            min_roe_display = "None"
        
        # Handle min_net_margin: 0.0 means no filter, > 0 means threshold
        if analysis_config.min_net_margin is not None and analysis_config.min_net_margin > 0:
            min_margin_display = f"{analysis_config.min_net_margin*100:.1f}%"
        else:
            min_margin_display = "None"
        
        # Handle max_debt_to_equity
        if analysis_config.max_debt_to_equity is not None:
            max_debt_display = f"{analysis_config.max_debt_to_equity:.1f}"
        else:
            max_debt_display = "None"
        
        st.metric("Min ROE", min_roe_display)
        st.metric("Min Net Margin", min_margin_display)
        st.metric("Max Debt/Equity", max_debt_display)
    
    with col3:
        st.markdown("**Selection Settings**")
        st.metric("Top K per Sector", analysis_config.top_k_per_sector)
        st.metric("Portfolio Size", analysis_config.portfolio_size)
        st.metric("Max Position Weight", f"{analysis_config.max_position_weight*100:.0f}%")
    
    # Filter status
    st.markdown("---")
    render_section_header("🔍 Filter Status", "🔍")
    
    filter_results = []
    for idx, row in scored_df.iterrows():
        filters = check_filters(row, analysis_config)
        all_passed = all(filters.values())
        filter_results.append({
            'ticker': row.get('ticker', 'N/A'),
            'sector': row.get('sector', 'N/A'),
            'passed': all_passed,
            'domain_score': row.get('domain_score', 0),
        })
    
    filter_df = pd.DataFrame(filter_results)
    passed_count = filter_df['passed'].sum()
    failed_count = (~filter_df['passed']).sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Passed Filters", passed_count, delta=None)
    with col2:
        st.metric("❌ Failed Filters", failed_count, delta=None)
    
    # Sector filter
    st.markdown("---")
    render_section_header("📊 Sector Rankings", "📊")
    
    sectors = sorted(scored_df['sector'].unique()) if 'sector' in scored_df.columns else ['Unknown']
    
    selected_sector = st.selectbox(
        "Filter by Sector",
        options=["All Sectors"] + sectors,
        index=0
    )
    
    if selected_sector != "All Sectors":
        sectors = [s for s in sectors if s == selected_sector]
    
    # Display sector rankings
    for sector in sectors:
        sector_df = scored_df[scored_df['sector'] == sector].copy()
        if len(sector_df) == 0:
            continue
        
        # Filter to passed stocks
        sector_passed = filter_df[filter_df['sector'] == sector]
        sector_df = sector_df[sector_passed['passed']].copy()
        
        if len(sector_df) == 0:
            continue
        
        sector_df = sector_df.sort_values('domain_score', ascending=False)
        top_k = sector_df.head(analysis_config.top_k_per_sector)
        
        st.markdown(f"### 📊 {sector}")
        st.markdown(f"*Top {len(top_k)} of {len(sector_df)} candidates*")
        
        # Create DataFrame for display
        display_data = []
        for rank, (idx, row) in enumerate(top_k.iterrows(), 1):
            display_data.append({
                'Rank': rank,
                'Ticker': row.get('ticker', 'N/A'),
                'Domain Score': row.get('domain_score', 0),
                'Model Score': row.get('model_score', 0),
                'Value Score': row.get('value_score', 0),
                'Quality Score': row.get('quality_score', 0),
                'Status': '✅ SELECTED' if rank <= analysis_config.top_k_per_sector else '⏳ CANDIDATE'
            })
        
        display_df = pd.DataFrame(display_data)
        
        # Style the DataFrame
        def color_scores(val):
            if isinstance(val, (int, float)):
                if val >= 80:
                    return f'background-color: rgba(16, 185, 129, 0.1); color: {COLORS["success"]}'
                elif val >= 60:
                    return f'background-color: rgba(245, 158, 11, 0.1); color: {COLORS["warning"]}'
                elif val >= 40:
                    return f'background-color: rgba(239, 68, 68, 0.1); color: {COLORS["danger"]}'
            return ''
        
        styled_df = display_df.style.map(
            color_scores,
            subset=['Domain Score', 'Model Score', 'Value Score', 'Quality Score']
        ).format({
            'Domain Score': '{:.1f}',
            'Model Score': '{:.1f}',
            'Value Score': '{:.1f}',
            'Quality Score': '{:.1f}',
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Score breakdown chart
        if len(top_k) > 0:
            fig = go.Figure()
            
            tickers = top_k['ticker'].tolist()
            model_scores = top_k['model_score'].fillna(0).tolist()
            value_scores = top_k['value_score'].fillna(0).tolist()
            quality_scores = top_k['quality_score'].fillna(0).tolist()
            
            fig.add_trace(go.Bar(
                name='Model Score',
                x=tickers,
                y=model_scores,
                marker_color=COLORS['primary'],
                text=[f'{s:.1f}' for s in model_scores],
                textposition='outside'
            ))
            fig.add_trace(go.Bar(
                name='Value Score',
                x=tickers,
                y=value_scores,
                marker_color=COLORS['accent'],
                text=[f'{s:.1f}' for s in value_scores],
                textposition='outside'
            ))
            fig.add_trace(go.Bar(
                name='Quality Score',
                x=tickers,
                y=quality_scores,
                marker_color=COLORS['success'],
                text=[f'{s:.1f}' for s in quality_scores],
                textposition='outside'
            ))
            
            fig.update_layout(
                title=f"{sector} - Score Breakdown",
                xaxis_title="Stock",
                yaxis_title="Score",
                barmode='group',
                height=400,
                showlegend=True,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    # Overall top stocks
    st.markdown("---")
    render_section_header("🏆 Overall Top Stocks", "🏆")
    
    top_n = st.slider("Number of stocks to show", 10, 50, 20, 5)
    
    passed_df = scored_df[filter_df['passed']].copy()
    top_stocks = passed_df.sort_values('domain_score', ascending=False).head(top_n)
    
    # Create visualization
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=top_stocks['domain_score'],
        y=top_stocks['model_score'],
        mode='markers+text',
        text=top_stocks['ticker'],
        textposition='top center',
        marker=dict(
            size=10,
            color=top_stocks['domain_score'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Domain Score")
        ),
        name='Stocks'
    ))
    
    fig.update_layout(
        title="Top Stocks - Domain Score vs Model Score",
        xaxis_title="Domain Score",
        yaxis_title="Model Score",
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Table
    display_data = []
    for rank, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        display_data.append({
            'Rank': rank,
            'Ticker': row.get('ticker', 'N/A'),
            'Sector': row.get('sector', 'N/A'),
            'Domain Score': row.get('domain_score', 0),
            'Model Score': row.get('model_score', 0),
            'Value Score': row.get('value_score', 0),
            'Quality Score': row.get('quality_score', 0),
        })
    
    display_df = pd.DataFrame(display_data)
    styled_df = display_df.style.map(
        color_scores,
        subset=['Domain Score', 'Model Score', 'Value Score', 'Quality Score']
    ).format({
        'Domain Score': '{:.1f}',
        'Model Score': '{:.1f}',
        'Value Score': '{:.1f}',
        'Quality Score': '{:.1f}',
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Portfolio estimate
    st.markdown("---")
    render_section_header("🎯 Portfolio Selection Estimate", "🎯")
    
    # Simulate vertical + horizontal selection
    vertical_candidates = {}
    for sector in sectors:
        sector_df = passed_df[passed_df['sector'] == sector].copy()
        sector_df = sector_df.sort_values('domain_score', ascending=False)
        top_k = sector_df.head(analysis_config.top_k_per_sector)
        if len(top_k) > 0:
            vertical_candidates[sector] = top_k
    
    # Store final portfolio for AI commentary
    final_portfolio_for_ai = None
    
    if vertical_candidates:
        all_candidates = pd.concat(vertical_candidates.values(), ignore_index=True)
        all_candidates = all_candidates.sort_values('domain_score', ascending=False)
        final_portfolio = all_candidates.head(analysis_config.portfolio_size)
        final_portfolio_for_ai = final_portfolio
        
        # Estimate weights
        domain_scores = final_portfolio['domain_score'].values
        weights = domain_scores / domain_scores.sum() * 100
        
        st.info(f"**Estimated Final Portfolio** ({len(final_portfolio)} stocks based on current configuration)")
        
        portfolio_data = []
        for rank, (idx, row) in enumerate(final_portfolio.iterrows(), 1):
            portfolio_data.append({
                'Rank': rank,
                'Ticker': row.get('ticker', 'N/A'),
                'Sector': row.get('sector', 'N/A'),
                'Domain Score': row.get('domain_score', 0),
                'Est. Weight': f"{weights[rank - 1]:.1f}%"
            })
        
        portfolio_df = pd.DataFrame(portfolio_data)
        st.dataframe(portfolio_df, use_container_width=True, hide_index=True)
        
        # Weight distribution chart
        fig = go.Figure(data=[go.Pie(
            labels=final_portfolio['ticker'],
            values=weights,
            hole=0.4,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="Estimated Portfolio Weight Distribution",
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # AI Commentary Section
    st.markdown("---")
    render_section_header("🤖 AI Commentary", "🤖")
    
    # Check if AI is available
    try:
        from src.analytics.ai_insights import AIInsightsGenerator
        generator = AIInsightsGenerator()
        ai_available = generator.is_available
    except Exception:
        ai_available = False
        generator = None
    
    if not ai_available:
        st.info("💡 AI commentary requires Gemini API key. Configure it in Settings to enable AI insights.")
    else:
        # Generate commentary button
        if st.button("🚀 Generate AI Commentary", key="generate_ai_commentary", type="primary"):
            with st.spinner("Generating AI insights..."):
                try:
                    # Use the final portfolio we computed earlier
                    final_portfolio_data = final_portfolio_for_ai
                    
                    # Convert run to dict if needed
                    run_dict = run.to_dict() if hasattr(run, 'to_dict') else {
                        'run_id': getattr(run, 'run_id', 'N/A'),
                        'name': getattr(run, 'name', 'N/A'),
                    }
                    
                    commentary = _generate_purchase_triggers_commentary(
                        generator,
                        scored_df,
                        filter_df,
                        passed_df,
                        final_portfolio_data,
                        analysis_config,
                        run_dict
                    )
                    
                    st.session_state['purchase_triggers_commentary'] = commentary
                    st.success("AI commentary generated!")
                except Exception as e:
                    st.error(f"Failed to generate commentary: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display commentary if available
        if 'purchase_triggers_commentary' in st.session_state:
            st.markdown("### 📝 AI Analysis")
            st.markdown(st.session_state['purchase_triggers_commentary'])
            
            # Download button
            st.download_button(
                "📥 Download Commentary",
                st.session_state['purchase_triggers_commentary'],
                file_name=f"purchase_triggers_commentary_{selected_run_id[:8]}.md",
                mime="text/markdown",
                key="download_commentary"
            )


def _generate_purchase_triggers_commentary(
    generator: 'AIInsightsGenerator',
    scored_df: pd.DataFrame,
    filter_df: pd.DataFrame,
    passed_df: pd.DataFrame,
    final_portfolio: Optional[pd.DataFrame],
    config: AnalysisConfig,
    run: dict
) -> str:
    """Generate AI commentary for purchase triggers analysis."""
    from datetime import datetime
    
    # Build context
    passed_count = filter_df['passed'].sum()
    failed_count = (~filter_df['passed']).sum()
    
    # Top stocks by domain score
    top_stocks = passed_df.sort_values('domain_score', ascending=False).head(10)
    top_stocks_info = []
    for idx, row in top_stocks.iterrows():
        top_stocks_info.append({
            'ticker': row.get('ticker', 'N/A'),
            'sector': row.get('sector', 'N/A'),
            'domain_score': row.get('domain_score', 0),
            'model_score': row.get('model_score', 0),
            'value_score': row.get('value_score', 0),
            'quality_score': row.get('quality_score', 0),
        })
    
    # Sector breakdown
    sector_breakdown = {}
    if 'sector' in passed_df.columns:
        for sector in passed_df['sector'].unique():
            sector_stocks = passed_df[passed_df['sector'] == sector]
            if len(sector_stocks) > 0:
                sector_breakdown[sector] = {
                    'count': len(sector_stocks),
                    'avg_domain_score': sector_stocks['domain_score'].mean(),
                    'top_ticker': sector_stocks.nlargest(1, 'domain_score')['ticker'].iloc[0]
                }
    
    # Portfolio composition
    portfolio_info = None
    if final_portfolio is not None and len(final_portfolio) > 0:
        portfolio_info = {
            'size': len(final_portfolio),
            'tickers': final_portfolio['ticker'].tolist(),
            'sectors': final_portfolio['sector'].value_counts().to_dict() if 'sector' in final_portfolio.columns else {},
            'avg_domain_score': final_portfolio['domain_score'].mean(),
        }
    
    # Build prompt
    prompt = f"""You are analyzing a stock portfolio selection system that uses purchase triggers to select stocks.

## Configuration
- Domain Score Weights: Model {config.w_model*100:.0f}%, Value {config.w_value*100:.0f}%, Quality {config.w_quality*100:.0f}%
- Filters: Min ROE={config.min_roe or 'None'}, Min Net Margin={config.min_net_margin or 'None'}, Max Debt/Equity={config.max_debt_to_equity or 'None'}
- Selection: Top {config.top_k_per_sector} per sector, Final portfolio size: {config.portfolio_size}

## Filter Results
- ✅ Passed: {passed_count} stocks
- ❌ Failed: {failed_count} stocks

## Top 10 Stocks by Domain Score
{chr(10).join([f"{i+1}. {s['ticker']} ({s['sector']}): Domain={s['domain_score']:.1f}, Model={s['model_score']:.1f}, Value={s['value_score']:.1f}, Quality={s['quality_score']:.1f}" for i, s in enumerate(top_stocks_info)])}

## Sector Breakdown
{chr(10).join([f"- {sector}: {info['count']} stocks, Avg Domain Score={info['avg_domain_score']:.1f}, Top={info['top_ticker']}" for sector, info in sector_breakdown.items()])}

## Portfolio Composition
{f"Portfolio size: {portfolio_info['size']} stocks" if portfolio_info else "No portfolio selected yet"}
{f", Sectors: {portfolio_info['sectors']}" if portfolio_info and portfolio_info['sectors'] else ""}
{f", Avg Domain Score: {portfolio_info['avg_domain_score']:.1f}" if portfolio_info else ""}

## Analysis Request
Please provide a comprehensive analysis covering:

1. **Filter Effectiveness**: Comment on the filter results - are the filters too strict or too lenient? What does the pass/fail ratio tell us?

2. **Score Distribution**: Analyze the domain score breakdown. Are there clear winners, or is the scoring competitive? What does the balance between model, value, and quality scores reveal?

3. **Sector Insights**: Which sectors are well-represented? Are there any sector biases or opportunities?

4. **Top Stock Analysis**: What do the top stocks have in common? Are there patterns in their model/value/quality scores?

5. **Portfolio Composition**: If a portfolio was selected, comment on its diversification, sector allocation, and overall quality.

6. **Recommendations**: Suggest any improvements to the selection criteria or highlight any concerns about the selected stocks.

Write in a clear, professional tone suitable for investment analysis. Be specific and data-driven."""
    
    try:
        response = generator._model.generate_content(prompt)
        commentary = response.text
        
        # Add metadata
        metadata = f"""---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Run ID: {run.get('run_id', 'N/A')}
Run Name: {run.get('name', 'N/A')}
---

"""
        return metadata + commentary
    except Exception as e:
        return f"Error generating commentary: {e}"


def _render_download_fundamentals_section(run: Optional[Dict], scores_df: Optional[pd.DataFrame] = None):
    """Render the download fundamentals section."""
    st.markdown("""
    **Download comprehensive fundamentals data** to fix missing value/quality scores.
    
    This will download PE, PB, ROE, and margin data from Yahoo Finance for all tickers in your run.
    """)
    
    # Get tickers from run or scores_df
    tickers = []
    if scores_df is not None and 'ticker' in scores_df.columns:
        tickers = sorted(scores_df['ticker'].unique().tolist())
    elif run:
        # Try to get tickers from run
        db = get_db("data/analysis.db")
        session = db.get_session()
        try:
            run_obj = session.query(Run).filter_by(run_id=run['run_id']).first()
            if run_obj:
                scores = session.query(StockScore).filter_by(run_id=run_obj.run_id).all()
                tickers = sorted(list(set([s.ticker for s in scores])))
        finally:
            session.close()
    
    if not tickers:
        st.warning("Could not determine tickers from run. Please use the CLI script instead.")
        st.code("python scripts/download_fundamentals.py --watchlist <watchlist_name>")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(f"📋 Will download fundamentals for **{len(tickers)} tickers**: {', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}")
    
    with col2:
        if st.button("🚀 Download Fundamentals", type="primary", key="download_fundamentals_btn"):
            _download_fundamentals_gui(tickers)


def _download_fundamentals_gui(tickers: List[str]):
    """Download fundamentals with GUI progress display."""
    import sys
    from pathlib import Path
    
    # Import the download function
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    try:
        import yfinance as yf
    except ImportError:
        st.error("❌ yfinance not installed. Install with: `pip install yfinance`")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    results = []
    failed = []
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Downloading {ticker}... ({i+1}/{total})")
        progress_bar.progress((i + 1) / total)
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            data = {
                'ticker': ticker,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'pe': info.get('trailingPE') or info.get('forwardPE'),
                'pb': info.get('priceToBook'),
                'roe': info.get('returnOnEquity'),
                'net_margin': info.get('profitMargins'),
                'gross_margin': info.get('grossMargins'),
                'operating_margin': info.get('operatingMargins'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'market_cap': info.get('marketCap'),
            }
            results.append(data)
        except Exception as e:
            failed.append(ticker)
        
        # Rate limiting
        if i < total - 1:
            time.sleep(0.5)
    
    # Save to CSV
    if results:
        df = pd.DataFrame(results)
        output_path = Path("data/fundamentals.csv")
        
        # Merge with existing data
        if output_path.exists():
            existing_df = pd.read_csv(output_path)
            # Remove old entries for these tickers
            existing_df = existing_df[~existing_df['ticker'].isin(tickers)]
            df = pd.concat([existing_df, df], ignore_index=True)
            df = df.sort_values(['ticker', 'date'], ascending=[True, False])
            df = df.drop_duplicates(subset=['ticker', 'date'], keep='first')
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        # Show results
        with results_container:
            st.success(f"✅ Downloaded fundamentals for {len(results)} tickers!")
            
            if failed:
                st.warning(f"⚠️ Failed to download {len(failed)} tickers: {', '.join(failed[:10])}")
            
            # Show summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                st.metric("Unique Tickers", df['ticker'].nunique())
            with col3:
                pe_count = df['pe'].notna().sum()
                st.metric("PE Data", f"{pe_count}/{len(df)}")
            with col4:
                roe_count = df['roe'].notna().sum()
                st.metric("ROE Data", f"{roe_count}/{len(df)}")
            
            st.info("🔄 **Refresh the page** to see updated value and quality scores!")
    else:
        st.error("❌ No data downloaded. Check your internet connection and try again.")
    
    progress_bar.empty()
    status_text.empty()
