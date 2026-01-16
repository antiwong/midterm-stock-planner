"""
Watchlist Manager Page
======================
Create, edit, and delete custom watchlists.
"""

import streamlit as st
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_alert
from ..data import (
    load_watchlists,
    load_custom_watchlists,
    load_custom_watchlist_by_id,
    create_custom_watchlist,
    update_custom_watchlist,
    delete_custom_watchlist,
    add_symbols_to_custom_watchlist,
    remove_symbols_from_custom_watchlist,
    create_watchlist_from_sources,
    get_all_available_watchlists,
    get_watchlist_categories,
)
from ..config import COLORS


# Sector color scheme - distinct colors for each sector
SECTOR_COLORS = {
    'Technology': '#3b82f6',              # Blue
    'Financial Services': '#10b981',      # Green
    'Healthcare': '#ef4444',              # Red
    'Consumer Cyclical': '#f59e0b',      # Amber
    'Consumer Defensive': '#8b5cf6',      # Purple
    'Communication Services': '#06b6d4',  # Cyan
    'Energy': '#f97316',                  # Orange
    'Utilities': '#14b8a6',              # Teal
    'Industrials': '#6366f1',             # Indigo
    'Basic Materials': '#84cc16',          # Lime
    'Real Estate': '#ec4899',             # Pink
    'ETF - Other': '#64748b',             # Slate
    'Other': '#94a3b8',                   # Light Slate
}


@st.cache_data(ttl=3600)  # Cache for 1 hour
def _load_sector_mapping() -> Dict[str, str]:
    """
    Load sector mapping for stocks.
    
    Priority:
    1. Cached sector data from data/sectors.json
    2. Fallback hardcoded mapping for common tickers
    
    Returns:
        Dictionary mapping ticker -> sector
    """
    # Fallback mapping for common tickers
    fallback_mapping = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
        'AMZN': 'Consumer Cyclical', 'META': 'Technology', 'NVDA': 'Technology',
        'TSLA': 'Consumer Cyclical', 'AMD': 'Technology', 'INTC': 'Technology',
        'CRM': 'Technology', 'ADBE': 'Technology', 'NFLX': 'Communication Services',
        'JPM': 'Financial Services', 'BAC': 'Financial Services', 'WFC': 'Financial Services',
        'GS': 'Financial Services', 'MS': 'Financial Services', 'C': 'Financial Services',
        'V': 'Financial Services', 'MA': 'Financial Services', 'AXP': 'Financial Services',
        'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
        'MRK': 'Healthcare', 'ABBV': 'Healthcare', 'LLY': 'Healthcare',
        'PG': 'Consumer Defensive', 'KO': 'Consumer Defensive', 'PEP': 'Consumer Defensive',
        'WMT': 'Consumer Defensive', 'COST': 'Consumer Defensive', 'TGT': 'Consumer Cyclical',
        'HD': 'Consumer Cyclical', 'NKE': 'Consumer Cyclical', 'MCD': 'Consumer Cyclical',
        'DIS': 'Communication Services', 'CMCSA': 'Communication Services',
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
        'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials',
        'MMM': 'Industrials', 'HON': 'Industrials', 'UPS': 'Industrials',
    }
    
    # Try to load cached sector data
    project_root = Path(__file__).parent.parent.parent.parent
    sector_cache_path = project_root / "data" / "sectors.json"
    
    if sector_cache_path.exists():
        try:
            with open(sector_cache_path, 'r') as f:
                cached_mapping = json.load(f)
            # Merge: cached data takes precedence over fallback
            merged = {**fallback_mapping, **cached_mapping}
            return merged
        except Exception:
            pass
    
    return fallback_mapping


def _fetch_sector_for_ticker(ticker: str) -> Optional[str]:
    """
    Fetch sector for a single ticker using yfinance.
    
    Returns:
        Sector name or None if not found
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get('sector', '')
        
        # Handle ETFs
        if info.get('quoteType') == 'ETF' and not sector:
            # Try to classify ETF
            name = info.get('shortName', info.get('longName', ''))
            ticker_upper = ticker.upper()
            name_lower = (name or '').lower()
            
            # Precious metals
            if any(x in ticker_upper for x in ['GLD', 'SLV', 'GOLD', 'PALL', 'PPLT']):
                return 'Precious Metals'
            if any(x in name_lower for x in ['gold', 'silver', 'platinum', 'palladium']):
                return 'Precious Metals'
            
            # Energy/Uranium
            if any(x in ticker_upper for x in ['URA', 'URNM', 'NLR', 'XLE', 'OIH']):
                return 'Energy'
            
            # Technology
            if any(x in ticker_upper for x in ['QQQ', 'XLK', 'VGT', 'ARKK', 'ARKW']):
                return 'Technology'
            
            # Financials
            if any(x in ticker_upper for x in ['XLF', 'VFH', 'KRE']):
                return 'Financial Services'
            
            # Healthcare
            if any(x in ticker_upper for x in ['XLV', 'VHT', 'IBB', 'XBI']):
                return 'Healthcare'
            
            # Real Estate
            if any(x in ticker_upper for x in ['VNQ', 'XLRE', 'IYR']):
                return 'Real Estate'
            
            return 'ETF - Other'
        
        return sector if sector else None
    except Exception:
        return None


def _update_sector_cache(ticker: str, sector: str):
    """
    Update the sector cache file with a new ticker-sector mapping.
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        sector_cache_path = project_root / "data" / "sectors.json"
        
        # Load existing cache
        if sector_cache_path.exists():
            with open(sector_cache_path, 'r') as f:
                cache = json.load(f)
        else:
            cache = {}
        
        # Update cache
        cache[ticker.upper()] = sector
        
        # Save cache
        sector_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sector_cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        
        # Clear the cached function to reload (if using Streamlit cache)
        try:
            _load_sector_mapping.clear()
        except:
            pass
    except Exception:
        pass  # Silently fail if cache update fails


def _get_sector_color(sector: Optional[str]) -> str:
    """Get color for a sector."""
    if not sector:
        return SECTOR_COLORS.get('Other', '#94a3b8')
    return SECTOR_COLORS.get(sector, SECTOR_COLORS.get('Other', '#94a3b8'))


def render_watchlist_manager():
    """Render the watchlist manager page."""
    render_page_header(
        "Watchlist Manager",
        "Create and manage custom watchlists"
    )
    
    # Check if we should show success message
    if st.session_state.get('watchlist_created'):
        st.success(f"✅ Watchlist '{st.session_state.get('watchlist_created_name', '')}' created successfully!")
        st.balloons()
        # Clear the flag
        del st.session_state['watchlist_created']
        if 'watchlist_created_name' in st.session_state:
            del st.session_state['watchlist_created_name']
    
    # Tabs for different actions
    tab1, tab2, tab3, tab4 = st.tabs(["📋 My Watchlists", "➕ Create New", "🔧 Quick Edit", "🔄 Update Sectors"])
    
    with tab1:
        _render_watchlists_overview()
    
    with tab2:
        _render_create_watchlist()
    
    with tab3:
        _render_quick_edit()
    
    with tab4:
        _render_update_sectors()


def _render_watchlists_overview():
    """Render overview of all custom watchlists."""
    render_section_header("Custom Watchlists", "📁")
    
    custom_watchlists = load_custom_watchlists()
    
    if not custom_watchlists:
        st.info("No custom watchlists yet. Create one using the 'Create New' tab!")
        
        # Show available standard watchlists for reference
        st.markdown("---")
        render_section_header("Available Standard Watchlists", "📚")
        _render_standard_watchlists_grid()
        return
    
    # Display custom watchlists as cards
    for wl in custom_watchlists:
        with st.expander(f"📊 {wl['name']} ({wl['count']} stocks)", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**ID:** `{wl['watchlist_id']}`")
                st.markdown(f"**Description:** {wl.get('description', 'No description')}")
                st.markdown(f"**Category:** {wl.get('category', 'custom')}")
                
                if wl.get('source_watchlists'):
                    st.markdown(f"**Source Watchlists:** {', '.join(wl['source_watchlists'])}")
                
                st.markdown(f"**Created:** {wl.get('created_at', 'N/A')[:19] if wl.get('created_at') else 'N/A'}")
                
                # Display symbols
                symbols = wl.get('symbols', [])
                if symbols:
                    st.markdown("**Symbols:**")
                    _render_symbols_grid(symbols)
            
            with col2:
                # Action buttons
                if st.button("✏️ Edit", key=f"edit_{wl['watchlist_id']}", use_container_width=True):
                    st.session_state['editing_watchlist'] = wl['watchlist_id']
                    st.rerun()
                
                if st.button("🗑️ Delete", key=f"delete_{wl['watchlist_id']}", use_container_width=True):
                    st.session_state['confirm_delete'] = wl['watchlist_id']
                
                if wl.get('is_default'):
                    st.success("✓ Default")
                else:
                    if st.button("⭐ Set Default", key=f"default_{wl['watchlist_id']}", use_container_width=True):
                        update_custom_watchlist(wl['watchlist_id'], is_default=True)
                        st.success("Set as default!")
                        st.rerun()
    
    # Handle delete confirmation
    if 'confirm_delete' in st.session_state:
        wl_id = st.session_state['confirm_delete']
        st.warning(f"⚠️ Are you sure you want to delete '{wl_id}'?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", type="primary"):
                delete_custom_watchlist(wl_id)
                del st.session_state['confirm_delete']
                st.success(f"Deleted '{wl_id}'")
                st.rerun()
        with col2:
            if st.button("Cancel"):
                del st.session_state['confirm_delete']
                st.rerun()
    
    # Handle editing
    if 'editing_watchlist' in st.session_state:
        st.markdown("---")
        _render_edit_watchlist(st.session_state['editing_watchlist'])


def _render_standard_watchlists_grid():
    """Render grid of standard watchlists."""
    watchlists = load_watchlists()
    categories = get_watchlist_categories()
    
    for category, wl_ids in categories.items():
        st.markdown(f"**{category.upper()}**")
        cols = st.columns(4)
        for i, wl_id in enumerate(wl_ids):
            wl = watchlists.get(wl_id, {})
            with cols[i % 4]:
                # Use Streamlit components instead of raw HTML to avoid CSS display issues
                with st.container():
                    st.markdown(f"**{wl.get('name', wl_id)}**")
                    st.caption(f"{wl.get('count', 0)} stocks")


def _render_create_watchlist():
    """Render the create watchlist form."""
    render_section_header("Create New Watchlist", "➕")
    
    # Two creation methods
    method = st.radio(
        "Creation Method",
        ["🔀 Combine Existing Watchlists", "✍️ Manual Entry"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if method == "🔀 Combine Existing Watchlists":
        _render_combine_watchlists_form()
    else:
        _render_manual_entry_form()


def _render_combine_watchlists_form():
    """Render form to create watchlist by combining others."""
    st.markdown("### Combine Watchlists")
    st.info("Select multiple watchlists to combine their symbols into a new custom watchlist.")
    
    # Watchlist ID
    col1, col2 = st.columns(2)
    with col1:
        watchlist_id = st.text_input(
            "Watchlist ID",
            placeholder="my_combined_list",
            help="Unique identifier (lowercase, no spaces)"
        )
    with col2:
        name = st.text_input(
            "Display Name",
            placeholder="My Combined List",
            help="Human-readable name"
        )
    
    description = st.text_area(
        "Description",
        placeholder="Description of this watchlist...",
        height=80
    )
    
    # Source watchlist selection
    st.markdown("### Select Source Watchlists")
    
    all_watchlists = get_all_available_watchlists()
    categories = {}
    for wl_id, wl in all_watchlists.items():
        cat = wl.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((wl_id, wl))
    
    selected_sources = []
    
    for category, watchlists in sorted(categories.items()):
        st.markdown(f"**{category.upper()}**")
        cols = st.columns(3)
        for i, (wl_id, wl) in enumerate(watchlists):
            with cols[i % 3]:
                if st.checkbox(
                    f"{wl.get('name', wl_id)} ({wl.get('count', 0)})",
                    key=f"source_{wl_id}"
                ):
                    selected_sources.append(wl_id)
    
    # Preview
    if selected_sources:
        st.markdown("---")
        st.markdown("### Preview")
        
        # Combine symbols
        all_symbols = set()
        for source_id in selected_sources:
            wl = all_watchlists.get(source_id, {})
            all_symbols.update(wl.get('symbols', []))
        
        preview_symbols = sorted(all_symbols)
        st.markdown(f"**Total unique symbols:** {len(preview_symbols)}")
        _render_symbols_grid(preview_symbols[:50])  # Show first 50
        if len(preview_symbols) > 50:
            st.caption(f"... and {len(preview_symbols) - 50} more")
    
    # Create button
    st.markdown("---")
    if st.button("✅ Create Watchlist", type="primary", disabled=not (watchlist_id and name and selected_sources)):
        try:
            # Validate ID
            if not re.match(r'^[a-z][a-z0-9_]*$', watchlist_id):
                st.error("ID must be lowercase, start with a letter, and contain only letters, numbers, and underscores")
                return
            
            result = create_watchlist_from_sources(
                watchlist_id=watchlist_id,
                name=name,
                source_watchlist_ids=selected_sources,
                description=description,
            )
            # Set flag to show success on main tab
            st.session_state['watchlist_created'] = True
            st.session_state['watchlist_created_name'] = name
            st.rerun()
        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Failed to create watchlist: {e}")


def _render_manual_entry_form():
    """Render form for manual symbol entry."""
    st.markdown("### Manual Entry")
    st.info("Enter symbols manually to create a custom watchlist.")
    
    # Watchlist ID
    col1, col2 = st.columns(2)
    with col1:
        watchlist_id = st.text_input(
            "Watchlist ID",
            placeholder="my_watchlist",
            help="Unique identifier (lowercase, no spaces)",
            key="manual_id"
        )
    with col2:
        name = st.text_input(
            "Display Name",
            placeholder="My Watchlist",
            help="Human-readable name",
            key="manual_name"
        )
    
    description = st.text_area(
        "Description",
        placeholder="Description of this watchlist...",
        height=80,
        key="manual_desc"
    )
    
    category = st.selectbox(
        "Category",
        ["custom", "sector", "strategy", "theme", "index", "market_cap"],
        index=0,
        key="manual_category"
    )
    
    # Symbol entry
    st.markdown("### Enter Symbols")
    symbols_text = st.text_area(
        "Symbols",
        placeholder="AAPL, MSFT, GOOGL, AMZN...\n(comma or space separated)",
        height=150,
        help="Enter ticker symbols separated by commas, spaces, or newlines",
        key="manual_symbols"
    )
    
    # Parse symbols
    symbols = []
    if symbols_text:
        # Split by comma, space, or newline
        raw_symbols = re.split(r'[,\s\n]+', symbols_text)
        symbols = [s.strip().upper() for s in raw_symbols if s.strip()]
        symbols = list(dict.fromkeys(symbols))  # Remove duplicates
        
        st.markdown(f"**Parsed symbols:** {len(symbols)}")
        
        # Validate symbols (with existence check and Tiger format detection)
        with st.spinner("Validating symbols..."):
            from ..data import validate_watchlist_symbols
            validation = validate_watchlist_symbols(symbols, check_existence=True, detect_tiger_format=True)
            
            # Show Tiger format detection
            if validation.get('tiger_format_detected'):
                st.info("🐅 Tiger Trading format detected and converted automatically")
            
            valid_symbols = validation['valid_symbols']
            invalid_symbols = validation.get('invalid', [])
            non_existent = validation.get('non_existent', [])
            unknown = validation.get('unknown_symbols', [])
            
            if invalid_symbols:
                st.warning(f"⚠️ {len(invalid_symbols)} invalid format symbols: {', '.join(invalid_symbols[:10])}")
            if non_existent:
                st.error(f"❌ {len(non_existent)} symbols do not exist: {', '.join(non_existent[:10])}")
            if unknown:
                st.info(f"ℹ️ {len(unknown)} symbols could not be validated: {', '.join(unknown[:10])}")
            
            if valid_symbols:
                st.success(f"✅ {len(valid_symbols)} valid symbols")
                _render_symbols_grid(valid_symbols)
            
            # Update symbols to only valid ones
            symbols = valid_symbols
    
    # Create button
    st.markdown("---")
    if st.button("✅ Create Watchlist", type="primary", key="create_manual", 
                 disabled=not (watchlist_id and name and symbols)):
        try:
            # Validate ID
            if not re.match(r'^[a-z][a-z0-9_]*$', watchlist_id):
                st.error("ID must be lowercase, start with a letter, and contain only letters, numbers, and underscores")
                return
            
            result = create_custom_watchlist(
                watchlist_id=watchlist_id,
                name=name,
                symbols=symbols,
                description=description,
                category=category,
            )
            # Set flag to show success on main tab
            st.session_state['watchlist_created'] = True
            st.session_state['watchlist_created_name'] = name
            st.rerun()
        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Failed to create watchlist: {e}")


def _render_quick_edit():
    """Render quick edit interface."""
    render_section_header("Quick Edit", "🔧")
    
    custom_watchlists = load_custom_watchlists()
    
    if not custom_watchlists:
        st.info("No custom watchlists to edit. Create one first!")
        return
    
    # Select watchlist
    watchlist_options = {wl['watchlist_id']: f"{wl['name']} ({wl['count']} stocks)" for wl in custom_watchlists}
    selected_id = st.selectbox(
        "Select Watchlist",
        options=list(watchlist_options.keys()),
        format_func=lambda x: watchlist_options[x]
    )
    
    if not selected_id:
        return
    
    watchlist = load_custom_watchlist_by_id(selected_id)
    if not watchlist:
        st.error("Watchlist not found")
        return
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Add Symbols")
        add_symbols_text = st.text_input(
            "Symbols to Add",
            placeholder="TSLA, NVDA, AMD",
            help="Comma-separated symbols to add"
        )
        
        if st.button("➕ Add Symbols", disabled=not add_symbols_text):
            symbols_to_add = [s.strip().upper() for s in add_symbols_text.split(',') if s.strip()]
            if symbols_to_add:
                result = add_symbols_to_custom_watchlist(selected_id, symbols_to_add)
                if result:
                    st.success(f"Added {len(symbols_to_add)} symbols. Total: {result['count']}")
                    st.rerun()
    
    with col2:
        st.markdown("### Remove Symbols")
        remove_symbols_text = st.text_input(
            "Symbols to Remove",
            placeholder="AAPL, MSFT",
            help="Comma-separated symbols to remove"
        )
        
        if st.button("➖ Remove Symbols", disabled=not remove_symbols_text):
            symbols_to_remove = [s.strip().upper() for s in remove_symbols_text.split(',') if s.strip()]
            if symbols_to_remove:
                result = remove_symbols_from_custom_watchlist(selected_id, symbols_to_remove)
                if result:
                    st.success(f"Removed {len(symbols_to_remove)} symbols. Total: {result['count']}")
                    st.rerun()
    
    # Current symbols
    st.markdown("---")
    st.markdown(f"### Current Symbols ({watchlist['count']})")
    _render_symbols_grid(watchlist.get('symbols', []))


def _render_edit_watchlist(watchlist_id: str):
    """Render edit form for a specific watchlist."""
    render_section_header("Edit Watchlist", "✏️")
    
    watchlist = load_custom_watchlist_by_id(watchlist_id)
    if not watchlist:
        st.error("Watchlist not found")
        if st.button("Cancel"):
            del st.session_state['editing_watchlist']
            st.rerun()
        return
    
    # Edit form
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Name", value=watchlist['name'])
    with col2:
        new_category = st.selectbox(
            "Category",
            ["custom", "sector", "strategy", "theme", "index", "market_cap"],
            index=["custom", "sector", "strategy", "theme", "index", "market_cap"].index(
                watchlist.get('category', 'custom')
            )
        )
    
    new_description = st.text_area("Description", value=watchlist.get('description', ''))
    
    # Symbols
    st.markdown("### Symbols")
    symbols_text = st.text_area(
        "Edit Symbols",
        value=', '.join(watchlist.get('symbols', [])),
        height=150,
        help="Edit the list of symbols (comma-separated)"
    )
    
    # Parse new symbols
    new_symbols = []
    if symbols_text:
        raw_symbols = re.split(r'[,\s\n]+', symbols_text)
        new_symbols = [s.strip().upper() for s in raw_symbols if s.strip()]
        new_symbols = list(dict.fromkeys(new_symbols))
    
    st.caption(f"Symbols: {len(new_symbols)}")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save Changes", type="primary"):
            result = update_custom_watchlist(
                watchlist_id=watchlist_id,
                name=new_name,
                description=new_description,
                category=new_category,
                symbols=new_symbols,
            )
            if result:
                st.success("Changes saved!")
                del st.session_state['editing_watchlist']
                st.rerun()
            else:
                st.error("Failed to save changes")
    
    with col2:
        if st.button("Cancel"):
            del st.session_state['editing_watchlist']
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete", type="secondary"):
            st.session_state['confirm_delete'] = watchlist_id
            del st.session_state['editing_watchlist']
            st.rerun()


def _render_symbols_grid(symbols: List[str], cols_per_row: int = 10, auto_fetch: bool = False):
    """
    Render symbols in a grid layout with color coding by sector.
    
    Args:
        symbols: List of stock symbols
        cols_per_row: Number of columns per row
        auto_fetch: If True, automatically fetch sectors for unknown stocks using yfinance
    """
    if not symbols:
        return
    
    # Load sector mapping
    sector_mapping = _load_sector_mapping()
    
    # Group symbols by sector for better organization
    symbols_by_sector: Dict[str, List[str]] = {}
    unknown_sector = []
    symbols_to_fetch = []
    
    for symbol in symbols:
        sector = sector_mapping.get(symbol.upper())
        if sector:
            if sector not in symbols_by_sector:
                symbols_by_sector[sector] = []
            symbols_by_sector[sector].append(symbol)
        else:
            unknown_sector.append(symbol)
            if auto_fetch:
                symbols_to_fetch.append(symbol)
    
    # Auto-fetch sectors for unknown stocks
    if auto_fetch and symbols_to_fetch:
        # Limit to first 20 to avoid rate limiting
        symbols_to_fetch = symbols_to_fetch[:20]
        
        with st.spinner(f"Fetching sector data for {len(symbols_to_fetch)} stocks..."):
            fetched_count = 0
            for symbol in symbols_to_fetch:
                sector = _fetch_sector_for_ticker(symbol)
                if sector:
                    # Update cache
                    _update_sector_cache(symbol, sector)
                    
                    # Add to sector group
                    if sector not in symbols_by_sector:
                        symbols_by_sector[sector] = []
                    symbols_by_sector[sector].append(symbol)
                    
                    # Remove from unknown
                    if symbol in unknown_sector:
                        unknown_sector.remove(symbol)
                    
                    fetched_count += 1
        
        if fetched_count > 0:
            st.success(f"✅ Fetched sector data for {fetched_count} stocks")
            # Reload sector mapping
            sector_mapping = _load_sector_mapping()
            st.rerun()
    
    # Render symbols grouped by sector
    if symbols_by_sector:
        for sector, sector_symbols in sorted(symbols_by_sector.items()):
            sector_color = _get_sector_color(sector)
            st.markdown(f"**{sector}** ({len(sector_symbols)})")
            
            # Render symbols in grid for this sector
            num_rows = (len(sector_symbols) + cols_per_row - 1) // cols_per_row
            
            for row in range(num_rows):
                cols = st.columns(cols_per_row)
                start_idx = row * cols_per_row
                end_idx = min(start_idx + cols_per_row, len(sector_symbols))
                
                for i, symbol in enumerate(sector_symbols[start_idx:end_idx]):
                    with cols[i]:
                        # Use HTML badge with sector color
                        st.markdown(
                            f'<span style="display: inline-block; background: {sector_color}; '
                            f'color: white; padding: 0.2rem 0.5rem; border-radius: 4px; '
                            f'font-family: monospace; font-size: 0.8rem; font-weight: 600;">{symbol}</span>',
                            unsafe_allow_html=True
                        )
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Render unknown sector symbols if any
    if unknown_sector:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Other/Unknown** ({len(unknown_sector)})")
        with col2:
            if st.button("🔍 Fetch Sectors", key=f"fetch_sectors_{hash(tuple(unknown_sector))}", 
                        help="Fetch sector data for unknown stocks from Yahoo Finance"):
                with st.spinner(f"Fetching sector data for {len(unknown_sector)} stocks..."):
                    fetched_count = 0
                    failed = []
                    for symbol in unknown_sector:
                        sector = _fetch_sector_for_ticker(symbol)
                        if sector:
                            _update_sector_cache(symbol, sector)
                            fetched_count += 1
                        else:
                            failed.append(symbol)
                        # Small delay to avoid rate limiting
                        import time
                        time.sleep(0.2)
                    
                    if fetched_count > 0:
                        st.success(f"✅ Fetched sector data for {fetched_count} stocks")
                        if failed:
                            st.warning(f"⚠️ Could not fetch data for {len(failed)} stocks: {', '.join(failed[:10])}")
                        # Clear cache and rerun
                        try:
                            _load_sector_mapping.clear()
                        except:
                            pass
                        st.rerun()
                    else:
                        st.error("❌ Could not fetch sector data. Please try again or run `python scripts/fetch_sector_data.py`")
        
        if len(unknown_sector) > 0:
            st.info(f"💡 {len(unknown_sector)} stocks without sector data. Click 'Fetch Sectors' to assign them automatically.")
        
        other_color = _get_sector_color('Other')
        num_rows = (len(unknown_sector) + cols_per_row - 1) // cols_per_row
        
        for row in range(num_rows):
            cols = st.columns(cols_per_row)
            start_idx = row * cols_per_row
            end_idx = min(start_idx + cols_per_row, len(unknown_sector))
            
            for i, symbol in enumerate(unknown_sector[start_idx:end_idx]):
                with cols[i]:
                    st.markdown(
                        f'<span style="display: inline-block; background: {other_color}; '
                        f'color: white; padding: 0.2rem 0.5rem; border-radius: 4px; '
                        f'font-family: monospace; font-size: 0.8rem; font-weight: 600;">{symbol}</span>',
                        unsafe_allow_html=True
                    )


def _render_update_sectors():
    """Render the sector update section."""
    render_section_header("Update Sector Data", "🔄")
    
    st.markdown("""
    This tool fetches and updates sector classifications for all stocks in your watchlists.
    Sector data is fetched from Yahoo Finance and cached for faster access.
    """)
    
    # Get all unique tickers from all watchlists
    all_watchlists = get_all_available_watchlists()
    all_tickers = set()
    watchlist_counts = {}
    
    for wl_id, wl in all_watchlists.items():
        symbols = wl.get('symbols', [])
        all_tickers.update(s.upper() for s in symbols)
        watchlist_counts[wl_id] = len(symbols)
    
    total_tickers = len(all_tickers)
    
    # Load current sector mapping
    sector_mapping = _load_sector_mapping()
    classified_count = sum(1 for t in all_tickers if t in sector_mapping)
    unclassified_count = total_tickers - classified_count
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Stocks", total_tickers)
    with col2:
        st.metric("Classified", classified_count, delta=f"{classified_count/total_tickers*100:.1f}%" if total_tickers > 0 else "0%")
    with col3:
        st.metric("Unclassified", unclassified_count, delta=f"-{unclassified_count}" if unclassified_count > 0 else "0", delta_color="inverse")
    
    st.markdown("---")
    
    # Show watchlist breakdown
    with st.expander("📊 Watchlist Breakdown", expanded=False):
        st.markdown("**Stocks by Watchlist:**")
        for wl_id, wl in sorted(all_watchlists.items()):
            symbols = wl.get('symbols', [])
            classified = sum(1 for s in symbols if s.upper() in sector_mapping)
            unclassified = len(symbols) - classified
            st.markdown(f"• **{wl.get('name', wl_id)}**: {len(symbols)} stocks ({classified} classified, {unclassified} unclassified)")
    
    st.markdown("---")
    
    # Update options
    st.markdown("### Update Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        update_all = st.button(
            "🔄 Update All Stocks",
            type="primary",
            use_container_width=True,
            help="Fetch sector data for all stocks in all watchlists"
        )
    
    with col2:
        force_refresh = st.button(
            "🔄 Force Refresh All",
            use_container_width=True,
            help="Re-fetch sector data even for already classified stocks"
        )
    
    if update_all or force_refresh:
        # Get all tickers
        tickers_to_fetch = list(all_tickers) if force_refresh else [t for t in all_tickers if t not in sector_mapping]
        
        if not tickers_to_fetch:
            st.success("✅ All stocks are already classified!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_area = st.empty()
            
            fetched_count = 0
            failed = []
            updated = []
            
            for i, ticker in enumerate(tickers_to_fetch):
                progress = (i + 1) / len(tickers_to_fetch)
                progress_bar.progress(progress)
                status_text.text(f"Fetching sector data... {i+1}/{len(tickers_to_fetch)} ({ticker})")
                
                sector = _fetch_sector_for_ticker(ticker)
                if sector:
                    _update_sector_cache(ticker, sector)
                    fetched_count += 1
                    updated.append(ticker)
                else:
                    failed.append(ticker)
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.2)
                
                # Update results every 10 stocks
                if (i + 1) % 10 == 0 or i == len(tickers_to_fetch) - 1:
                    with results_area.container():
                        st.markdown(f"**Progress:** {i+1}/{len(tickers_to_fetch)} stocks processed")
                        st.markdown(f"✅ Fetched: {fetched_count} | ❌ Failed: {len(failed)}")
            
            progress_bar.empty()
            status_text.empty()
            
            # Final results
            st.markdown("---")
            st.markdown("### Update Results")
            
            if fetched_count > 0:
                st.success(f"✅ Successfully fetched sector data for {fetched_count} stocks!")
                
                # Show updated stocks
                if len(updated) <= 20:
                    st.markdown(f"**Updated stocks:** {', '.join(updated)}")
                else:
                    with st.expander(f"View all {len(updated)} updated stocks"):
                        st.markdown(', '.join(updated))
                
                # Clear cache and show refresh message
                try:
                    _load_sector_mapping.clear()
                except:
                    pass
                
                st.info("💡 The page will refresh to show updated sector classifications.")
                st.rerun()
            
            if failed:
                st.warning(f"⚠️ Could not fetch sector data for {len(failed)} stocks:")
                if len(failed) <= 20:
                    st.code(', '.join(failed))
                else:
                    st.code(', '.join(failed[:20]) + f" ... and {len(failed) - 20} more")
                st.info("💡 These stocks may be invalid tickers or may require manual classification.")
    
    st.markdown("---")
    
    # Show current sector distribution
    st.markdown("### Current Sector Distribution")
    
    # Count stocks by sector
    sector_counts = {}
    for ticker in all_tickers:
        sector = sector_mapping.get(ticker, 'Other/Unknown')
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    if sector_counts:
        # Display as columns
        sectors_sorted = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        num_cols = 3
        cols = st.columns(num_cols)
        
        for i, (sector, count) in enumerate(sectors_sorted):
            with cols[i % num_cols]:
                sector_color = _get_sector_color(sector)
                st.markdown(
                    f'<div style="background: {sector_color}20; padding: 0.5rem; border-radius: 8px; '
                    f'border-left: 4px solid {sector_color}; margin-bottom: 0.5rem;">'
                    f'<strong>{sector}</strong><br>'
                    f'<span style="font-size: 1.2rem; font-weight: 700;">{count}</span> stocks'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.info("No sector data available. Click 'Update All Stocks' to fetch sector classifications.")
