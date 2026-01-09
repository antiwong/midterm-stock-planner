"""
Watchlist Manager Page
======================
Create, edit, and delete custom watchlists.
"""

import streamlit as st
import re
from typing import List, Dict, Any

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
    tab1, tab2, tab3 = st.tabs(["📋 My Watchlists", "➕ Create New", "🔧 Quick Edit"])
    
    with tab1:
        _render_watchlists_overview()
    
    with tab2:
        _render_create_watchlist()
    
    with tab3:
        _render_quick_edit()


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
                st.markdown(f"""
                <div style="background: {COLORS['light']}; padding: 0.5rem; 
                            border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.85rem;">
                    <strong>{wl.get('name', wl_id)}</strong><br>
                    <span style="color: {COLORS['muted']};">{wl.get('count', 0)} stocks</span>
                </div>
                """, unsafe_allow_html=True)


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
        _render_symbols_grid(symbols)
    
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


def _render_symbols_grid(symbols: List[str], cols_per_row: int = 10):
    """Render symbols in a grid layout."""
    if not symbols:
        return
    
    # Create HTML grid
    html_parts = ['<div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">']
    for symbol in symbols:
        html_parts.append(f'''
            <span style="background: {COLORS['light']}; padding: 0.2rem 0.5rem; 
                         border-radius: 4px; font-family: monospace; font-size: 0.8rem;">
                {symbol}
            </span>
        ''')
    html_parts.append('</div>')
    
    st.markdown(''.join(html_parts), unsafe_allow_html=True)
