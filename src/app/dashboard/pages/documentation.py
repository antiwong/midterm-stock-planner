"""
Documentation Page
==================
Browse and view documentation from the docs folder.
"""

import streamlit as st
from pathlib import Path
from typing import List, Dict, Optional
import re

from ..components.sidebar import render_page_header
from ..utils import get_project_root


def render_documentation():
    """Render the documentation browser page."""
    render_page_header(
        "📚 Documentation",
        "Browse project documentation and guides"
    )
    
    # Get docs folder
    project_root = get_project_root()
    docs_folder = project_root / "docs"
    
    # Debug info
    with st.expander("🔍 Debug Info", expanded=False):
        st.write(f"**Project Root:** `{project_root}`")
        st.write(f"**Docs Folder:** `{docs_folder}`")
        st.write(f"**Docs Folder Exists:** {docs_folder.exists()}")
        if docs_folder.exists():
            all_files = list(docs_folder.glob("*.md"))
            st.write(f"**Found {len(all_files)} markdown files**")
            st.write("Files:", [f.name for f in all_files[:10]])
    
    if not docs_folder.exists():
        st.error(f"Documentation folder not found at: {docs_folder}")
        st.info(f"Expected location: {docs_folder.absolute()}")
        return
    
    # Get all markdown files
    doc_files = _get_documentation_files(docs_folder)
    
    if not doc_files:
        st.warning("No documentation files found in the docs folder.")
        # Show what files exist
        all_files = list(docs_folder.glob("*"))
        if all_files:
            st.info(f"Found {len(all_files)} files in docs folder (none are .md files)")
        return
    
    # Show count
    st.info(f"📚 Found {len(doc_files)} documentation files")
    
    # Sidebar: Document selector
    st.sidebar.markdown("### 📖 Select Document")
    
    # Group documents by category
    categories = _categorize_documents(doc_files)
    
    # Create a flat list with category prefixes for selectbox
    # Use a list to maintain order
    doc_options_list = []
    doc_options_dict = {}
    for category, files in categories.items():
        for file_info in files:
            display_label = f"{category} > {file_info['display_name']}"
            doc_options_list.append((display_label, file_info))
            doc_options_dict[display_label] = file_info
    
    # Initialize session state for selected document
    if 'selected_doc_name' not in st.session_state:
        st.session_state.selected_doc_name = doc_files[0]['name']
    
    # Create option labels list (maintain order)
    option_labels = [label for label, _ in doc_options_list]
    
    # Find current selection index
    current_index = 0
    for idx, (label, file_info) in enumerate(doc_options_list):
        if file_info['name'] == st.session_state.selected_doc_name:
            current_index = idx
            break
    
    # Document selector dropdown
    selected_label = st.sidebar.selectbox(
        "Choose a document",
        options=option_labels,
        index=current_index,
        label_visibility="collapsed",
        key="doc_selector"
    )
    
    # Update selected document when selection changes
    selected_doc = doc_options_dict[selected_label]
    if st.session_state.selected_doc_name != selected_doc['name']:
        st.session_state.selected_doc_name = selected_doc['name']
        st.rerun()
    
    # Show category breakdown in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 Categories")
    for category, files in categories.items():
        with st.sidebar.expander(f"{category} ({len(files)})", expanded=False):
            for file_info in files:
                if file_info['name'] == st.session_state.selected_doc_name:
                    st.markdown(f"**{file_info['display_name']}** (current)")
                else:
                    st.markdown(file_info['display_name'])
    
    # Main content: Display selected document
    st.markdown("---")
    
    if selected_doc:
        _display_document(selected_doc, doc_files)
    else:
        st.error("No document selected. Please select a document from the sidebar.")
    
    # Footer: Show all available documents with clickable links
    st.markdown("---")
    with st.expander("📋 All Available Documents", expanded=True):
        st.markdown("### Documentation Index")
        st.caption("Click on a document name to select it")
        
        for category, files in categories.items():
            st.markdown(f"#### {category}")
            for file_info in files:
                is_current = file_info['name'] == st.session_state.selected_doc_name
                if is_current:
                    st.markdown(f"- **{file_info['display_name']}** `{file_info['name']}` ← *current*")
                else:
                    if st.button(
                        f"📄 {file_info['display_name']}",
                        key=f"doc_link_{file_info['name']}",
                        use_container_width=False
                    ):
                        st.session_state.selected_doc_name = file_info['name']
                        st.rerun()


def _get_documentation_files(docs_folder: Path) -> List[Dict[str, any]]:
    """Get all markdown documentation files."""
    files = []
    
    for file_path in sorted(docs_folder.glob("*.md")):
        # Read first few lines to get title
        title = _extract_title(file_path)
        
        files.append({
            'path': file_path,
            'name': file_path.stem,
            'display_name': title or file_path.stem.replace('-', ' ').title(),
            'full_name': file_path.name
        })
    
    return files


def _extract_title(file_path: Path) -> Optional[str]:
    """Extract title from markdown file (first # heading)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
                elif line.startswith('#'):
                    return line[1:].strip()
    except Exception:
        pass
    return None


def _categorize_documents(files: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize documents by their name patterns."""
    categories = {
        'Getting Started': [],
        'Configuration': [],
        'Analysis & Features': [],
        'Data & Integration': [],
        'Advanced Topics': [],
        'Other': []
    }
    
    # Category patterns
    getting_started = ['readme', 'requirements', 'getting-started', 'quick-start']
    configuration = ['config', 'settings', 'api-configuration']
    analysis = ['analysis', 'portfolio', 'purchase', 'risk', 'backtest', 'domain', 'sentiment', 'technical', 'explainability', 'ai-insights', 'data-validation']
    data = ['data', 'fundamental', 'download', 'filter', 'analytics']
    advanced = ['deployment', 'design', 'model-training', 'comparison', 'risk-parity']
    
    for file_info in files:
        name_lower = file_info['name'].lower()
        categorized = False
        
        if any(pattern in name_lower for pattern in getting_started):
            categories['Getting Started'].append(file_info)
            categorized = True
        elif any(pattern in name_lower for pattern in configuration):
            categories['Configuration'].append(file_info)
            categorized = True
        elif any(pattern in name_lower for pattern in analysis):
            categories['Analysis & Features'].append(file_info)
            categorized = True
        elif any(pattern in name_lower for pattern in data):
            categories['Data & Integration'].append(file_info)
            categorized = True
        elif any(pattern in name_lower for pattern in advanced):
            categories['Advanced Topics'].append(file_info)
            categorized = True
        
        if not categorized:
            categories['Other'].append(file_info)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def _display_document(file_info: Dict, all_docs: List[Dict]):
    """Display a markdown document."""
    file_path = file_info['path']
    
    # Header
    st.markdown(f"## {file_info['display_name']}")
    st.caption(f"📄 `{file_info['full_name']}`")
    
    # Debug info (can be removed later)
    if not file_path.exists():
        st.error(f"❌ File not found: {file_path}")
        st.info(f"Looking for file at: {file_path.absolute()}")
        return
    
    # Read and display content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content:
            st.warning("⚠️ Document is empty.")
            return
        
        # Process markdown for better display (convert relative links)
        processed_content = _process_markdown(content, all_docs, file_info)
        
        # Split content by markdown links and render with interactive buttons
        _render_markdown_with_links(processed_content, all_docs)
        
        # Download button (original content)
        st.download_button(
            label="📥 Download Document",
            data=content,
            file_name=file_info['full_name'],
            mime="text/markdown"
        )
        
    except PermissionError as e:
        st.error(f"❌ Permission denied reading file: {e}")
    except UnicodeDecodeError as e:
        st.error(f"❌ Encoding error reading file: {e}")
        st.info("Try opening the file in a text editor and saving it as UTF-8.")
    except Exception as e:
        st.error(f"❌ Error reading document: {e}")
        st.exception(e)


def _process_markdown(content: str, all_docs: List[Dict], current_doc: Dict) -> Dict[str, any]:
    """Process markdown content and extract relative links.
    
    Returns:
        Dictionary with 'content' (processed text) and 'links' (list of link info)
    """
    # Create a mapping of file names to document info
    doc_map = {}
    for doc in all_docs:
        # Map both with and without .md extension
        doc_map[doc['name'].lower()] = doc
        doc_map[doc['full_name'].lower()] = doc
        doc_map[doc['name'].lower() + '.md'] = doc
        doc_map[doc['full_name'].lower()] = doc
    
    # Find all markdown links: [text](link)
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    links = []
    processed_parts = []
    last_end = 0
    
    for match in re.finditer(link_pattern, content):
        # Get text before the link
        processed_parts.append(content[last_end:match.start()])
        
        link_text = match.group(1)
        link_url = match.group(2)
        
        # Check if it's a relative .md file link
        is_relative_md = False
        target_doc = None
        
        # Handle different link formats:
        # - file.md
        # - ./file.md
        # - ../file.md
        # - docs/file.md
        link_path = link_url.strip()
        if link_path.endswith('.md'):
            # Remove leading ./ or ../
            link_path = link_path.lstrip('./')
            # Remove any path components, just get filename
            link_name = Path(link_path).stem.lower()
            
            if link_name in doc_map:
                target_doc = doc_map[link_name]
                is_relative_md = True
        
        if is_relative_md and target_doc:
            # Store link info for rendering as button
            links.append({
                'text': link_text,
                'target_doc': target_doc,
                'position': len(''.join(processed_parts)),
                'original': match.group(0)
            })
            # Replace with placeholder that we'll render as button
            processed_parts.append(f"__DOC_LINK_{len(links)-1}__")
        else:
            # Keep external links and non-md links as-is
            processed_parts.append(match.group(0))
        
        last_end = match.end()
    
    # Add remaining content
    processed_parts.append(content[last_end:])
    
    return {
        'content': ''.join(processed_parts),
        'links': links
    }


def _render_markdown_with_links(processed: Dict[str, any], all_docs: List[Dict]):
    """Render markdown content with interactive document links."""
    content = processed['content']
    links = processed['links']
    
    if not links:
        # No links to process, just render normally
        st.markdown(content)
        return
    
    # Split content by link placeholders and render
    parts = re.split(r'__DOC_LINK_(\d+)__', content)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Regular content
            if part:
                st.markdown(part)
        else:
            # Link placeholder - render as clickable link with button
            link_idx = int(part)
            if link_idx < len(links):
                link_info = links[link_idx]
                target_doc = link_info['target_doc']
                
                # Render as inline: text + small button
                col1, col2 = st.columns([20, 1])
                with col1:
                    # Show link text styled as a link
                    st.markdown(
                        f'<span style="color: #1f77b4; text-decoration: underline; cursor: pointer;">'
                        f'📄 {link_info["text"]}</span> '
                        f'<span style="color: #666; font-size: 0.9em;">→ {target_doc["display_name"]}</span>',
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("🔗", key=f"doc_link_{link_idx}_{target_doc['name']}", help=f"Open {target_doc['display_name']}"):
                        st.session_state.selected_doc_name = target_doc['name']
                        st.rerun()


# Export for use in app.py
def render_documentation_page():
    """Wrapper function for app.py routing."""
    render_documentation()
