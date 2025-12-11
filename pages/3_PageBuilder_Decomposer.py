#!/usr/bin/env python3
"""
PageBuilder Decomposer - Luminate Cookbook Tool

Decompose Luminate Online PageBuilders into their nested component structure.
Download all nested PageBuilders as separate HTML files in a ZIP archive.
"""

import streamlit as st
import zipfile
import io
import os
from typing import Optional
from lib.pagebuilder_decomposer_lib import HierarchicalLuminateWorkflow


def _safe_debug_log(data: dict):
    """Safely write to debug log, creating directory if needed. Silently fails on errors."""
    try:
        debug_log_path = '/workspaces/luminate-cookbook/.cursor/debug.log'
        debug_log_dir = os.path.dirname(debug_log_path)
        # Create directory if it doesn't exist
        os.makedirs(debug_log_dir, exist_ok=True)
        # Write to log file
        import json
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps(data) + '\n')
    except Exception:
        pass  # Silently fail - debug logging should never break functionality

# Page configuration
st.set_page_config(
    page_title="PageBuilder Decomposer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    .info-box {
        padding: 1em;
        background-color: #e7f3ff;
        border-radius: 5px;
        border: 1px solid #b3d9ff;
        margin: 1em 0;
    }
    .success-box {
        padding: 1em;
        background-color: #d4edda;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 1em 0;
    }
    .tree-node {
        padding-left: 1em;
        font-family: monospace;
        font-size: 0.9em;
    }
    .hierarchy-tree {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.95em;
        line-height: 1.6;
        padding: 1em;
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        overflow-x: auto;
    }
    .tree-item {
        display: flex;
        align-items: center;
        padding: 0.35em 0.5em;
        min-height: 1.8em;
        position: relative;
        margin: 0.1em 0;
    }
    .tree-item-wrapper {
        display: flex;
        align-items: center;
        flex: 1;
        padding-left: 0.5em;
    }
    .tree-connector-wrapper {
        display: flex;
        align-items: center;
        width: 1.5em;
        flex-shrink: 0;
        position: relative;
    }
    .tree-connector {
        display: inline-block;
        width: 1.5em;
        height: 1.2em;
        position: relative;
        flex-shrink: 0;
    }
    .tree-connector-middle::before {
        content: '├';
        position: absolute;
        left: 0;
        top: 0;
        color: #6c757d;
        font-size: 1.2em;
        line-height: 1;
    }
    .tree-connector-middle::after {
        content: '';
        position: absolute;
        left: 0.75em;
        top: 0.6em;
        width: 0.75em;
        height: 1px;
        background-color: #6c757d;
    }
    .tree-connector-end::before {
        content: '└';
        position: absolute;
        left: 0;
        top: 0;
        color: #6c757d;
        font-size: 1.2em;
        line-height: 1;
    }
    .tree-connector-end::after {
        content: '';
        position: absolute;
        left: 0.75em;
        top: 0.6em;
        width: 0.75em;
        height: 1px;
        background-color: #6c757d;
    }
    .tree-label {
        font-weight: 500;
        word-break: break-word;
        flex: 1;
    }
    .tree-included {
        color: #28a745;
    }
    .tree-excluded {
        color: #dc3545;
    }
    .tree-reference {
        color: #6c757d;
        font-style: italic;
        font-size: 0.9em;
        margin-left: 0.5em;
    }
    .tree-children {
        margin-left: 1.5em;
        position: relative;
        padding-left: 0.5em;
    }
    .tree-children::before {
        content: '';
        position: absolute;
        left: 0.75em;
        top: 0;
        bottom: 0;
        width: 1px;
        background-color: #dee2e6;
    }
    .tree-item:has(+ .tree-children .tree-item:last-child) .tree-children::before {
        height: 0.6em;
    }
    .tree-item:hover {
        background-color: #e9ecef;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)


def create_zip_from_files(files: dict, main_pagename: str) -> bytes:
    """Create a ZIP file containing all decomposed PageBuilder files."""
    zip_buffer = io.BytesIO()
    
    # #region agent log
    _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"ZIP","location":"3_PageBuilder_Decomposer.py:53","message":"create_zip_from_files: starting","data":{"files_count":len(files),"main_pagename":main_pagename,"file_keys_sample":list(files.keys())[:10]}})
    # #endregion
    
    files_added = 0
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add main file
        if main_pagename in files:
            zip_file.writestr(f"{main_pagename}.html", files[main_pagename])
            files_added += 1
        
        # Add all component files
        for file_path, content in files.items():
            if file_path != main_pagename:  # Already added main file
                zip_file.writestr(file_path, content)
                files_added += 1
    
    # #region agent log
    _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"ZIP","location":"3_PageBuilder_Decomposer.py:75","message":"create_zip_from_files: completed","data":{"files_added":files_added,"zip_size":len(zip_buffer.getvalue())}})
    # #endregion
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def format_hierarchy_tree(hierarchy: dict, root: str, inclusion_status: dict, is_last: bool = True, visited: Optional[set] = None, level: int = 0) -> str:
    """Format hierarchy as a tree structure for display with color coding using structured HTML/CSS.
    
    Args:
        hierarchy: Dictionary mapping parent -> [children]
        root: The root node to display
        inclusion_status: Dictionary mapping pagename -> bool (included/excluded)
        is_last: Whether this is the last child of its parent
        visited: Set of already-visited nodes to prevent duplicates (defaults to empty set)
        level: Current nesting level (for indentation)
    """
    # Initialize visited set if not provided
    if visited is None:
        visited = set()
    
    # Escape HTML in root name
    import html
    escaped_root = html.escape(root)
    
    # Check if this node has already been displayed
    if root in visited:
        # Show a reference indicator instead of recursing
        connector_class = "tree-connector tree-connector-end" if is_last else "tree-connector tree-connector-middle"
        is_included = inclusion_status.get(root, True)
        status_class = "tree-included" if is_included else "tree-excluded"
        
        return f'<div class="tree-item"><div class="tree-connector-wrapper"><div class="{connector_class}"></div></div><div class="tree-item-wrapper"><span class="tree-label {status_class}">{escaped_root}</span><span class="tree-reference">(see above)</span></div></div>'
    
    # Mark this node as visited
    visited.add(root)
    
    # Determine color based on inclusion status
    is_included = inclusion_status.get(root, True)
    status_class = "tree-included" if is_included else "tree-excluded"
    
    # Build connector HTML (only for nested levels)
    if level > 0:
        connector_class = "tree-connector tree-connector-end" if is_last else "tree-connector tree-connector-middle"
        connector_html = f'<div class="tree-connector-wrapper"><div class="{connector_class}"></div></div>'
    else:
        connector_html = ''
    
    # Build the current node (compact format to avoid code block rendering)
    html_parts = [f'<div class="tree-item">{connector_html}<div class="tree-item-wrapper"><span class="tree-label {status_class}">{escaped_root}</span></div></div>']
    
    # Process children
    children = hierarchy.get(root, [])
    if children:
        children_html = []
        # Filter children: separate already-visited from new ones
        # This matches the download logic which skips already-processed components
        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            
            # Check if child is already visited before processing
            if child in visited:
                # Show "(see above)" for already-visited children without recursing
                # This prevents processing descendants of already-displayed nodes
                escaped_child = html.escape(child)
                is_child_included = inclusion_status.get(child, True)
                child_status_class = "tree-included" if is_child_included else "tree-excluded"
                connector_class = "tree-connector tree-connector-end" if is_last_child else "tree-connector tree-connector-middle"
                child_html = f'<div class="tree-item"><div class="tree-connector-wrapper"><div class="{connector_class}"></div></div><div class="tree-item-wrapper"><span class="tree-label {child_status_class}">{escaped_child}</span><span class="tree-reference">(see above)</span></div></div>'
            else:
                # Only recursively process children that haven't been visited yet
                child_html = format_hierarchy_tree(hierarchy, child, inclusion_status, is_last_child, visited, level + 1)
            
            children_html.append(child_html)
        
        if children_html:
            html_parts.append(f'<div class="tree-children">{"".join(children_html)}</div>')
    
    return "".join(html_parts)


def main():
    st.title("🔍 PageBuilder Decomposer")
    st.markdown("---")
    
    st.markdown("""
    <div class="info-box">
    <strong>Decompose PageBuilders</strong> - Enter a PageBuilder URL or name to extract all nested 
    PageBuilders as separate HTML files. No login required - works with public Luminate Online pages.
    </div>
    """, unsafe_allow_html=True)
    
    # Input section
    st.subheader("📝 Enter PageBuilder URL or Name")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url_or_name = st.text_input(
            "PageBuilder URL or Name",
            value=st.session_state.get('last_pagename', ''),
            placeholder="e.g., https://danafarber.jimmyfund.org/site/SPageServer?pagename=imaginedisplay_cancer or imaginedisplay_cancer",
            help="Enter a full URL or just the PageBuilder name"
        )
    
    with col2:
        base_url = st.text_input(
            "Base URL",
            value="https://danafarber.jimmyfund.org",
            help="Luminate Online base URL"
        )
    
    # Options section
    st.markdown("---")
    st.subheader("⚙️ Options")
    
    ignore_global_stylesheet = st.checkbox(
        "Ignore global stylesheet components",
        value=True,
        help="Exclude 'reus_dm_global_stylesheet' and all its nested PageBuilders from the download. "
             "This is usually not important to end users and can significantly reduce file count."
    )
    
    # Decompose button
    if st.button("🚀 Decompose PageBuilder", type="primary", use_container_width=True):
        # Clear previous results
        for key in ['decomposed_files', 'decomposed_hierarchy', 'all_pagebuilders', 'current_pagename', 'ignored_pagebuilders']:
            if key in st.session_state:
                del st.session_state[key]
        
        if not url_or_name:
            st.error("Please enter a PageBuilder URL or name")
            return
        
        # Initialize workflow
        workflow = HierarchicalLuminateWorkflow(base_url=base_url)
        
        # Extract pagename
        try:
            pagename = workflow.extract_pagename_from_url(url_or_name)
            st.session_state.last_pagename = url_or_name
        except Exception as e:
            st.error(f"Error parsing input: {e}")
            return
        
        if not pagename:
            st.error("Could not extract PageBuilder name from input")
            return
        
        # Store in session state
        st.session_state.current_pagename = pagename
        st.session_state.current_base_url = base_url
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        processed_count = [0]  # Use list to allow modification in nested function
        
        def progress_callback(current: str, parent: Optional[str] = None):
            processed_count[0] += 1
            parent_info = f" (child of {parent})" if parent else ""
            status_text.text(f"📋 Processing: {current}{parent_info}")
            # Progress is approximate since we don't know total count upfront
            progress_bar.progress(min(0.95, processed_count[0] / 50))
        
        # Prepare ignore list
        ignore_list = []
        if ignore_global_stylesheet:
            ignore_list.append("reus_dm_global_stylesheet")
        
        # Decompose
        try:
            # #region agent log
            _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"3_PageBuilder_Decomposer.py:179","message":"Streamlit: about to call decompose_pagebuilder","data":{"pagename":pagename,"ignore_list":ignore_list}})
            # #endregion
            status_text.info(f"🔍 Starting decomposition of '{pagename}'...")
            if ignore_list:
                status_text.info(f"⏭️ Ignoring: {', '.join(ignore_list)}")
            files, inclusion_status, complete_hierarchy = workflow.decompose_pagebuilder(pagename, progress_callback, ignore_pagebuilders=ignore_list)
            
            # #region agent log
            _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"ALL","location":"3_PageBuilder_Decomposer.py:191","message":"Streamlit: decompose_pagebuilder returned","data":{"files_count":len(files),"file_keys":list(files.keys())[:20],"all_keys":list(files.keys())}})
            # #endregion
            
            if not files:
                st.error("No files were generated. Please check the PageBuilder name and try again.")
                return
            
            # Store results
            st.session_state.decomposed_files = files
            st.session_state.decomposed_hierarchy = complete_hierarchy
            st.session_state.inclusion_status = inclusion_status
            st.session_state.all_pagebuilders = list(workflow.all_pagebuilders)
            st.session_state.ignored_pagebuilders = ignore_list
            
            progress_bar.progress(1.0)
            status_text.success(f"✅ Successfully decomposed {len(files)} PageBuilder(s)!")
            
        except Exception as e:
            st.error(f"❌ Error during decomposition: {str(e)}")
            st.info("Please verify the PageBuilder name and base URL are correct.")
            return
    
    # Display results if available (only if they match current input)
    if 'decomposed_files' in st.session_state and 'current_pagename' in st.session_state:
        # Verify the results match the current input
        current_input_pagename = None
        if url_or_name:
            try:
                workflow_temp = HierarchicalLuminateWorkflow(base_url=base_url)
                current_input_pagename = workflow_temp.extract_pagename_from_url(url_or_name)
            except:
                pass
        
        # Only show results if they match current input or if no current input
        if current_input_pagename is None or st.session_state.current_pagename == current_input_pagename:
            files = st.session_state.decomposed_files
            hierarchy = st.session_state.decomposed_hierarchy
            inclusion_status = st.session_state.get('inclusion_status', {})
            # If inclusion_status is empty, default all to True (backward compatibility)
            if not inclusion_status:
                inclusion_status = {pb: True for pb in st.session_state.all_pagebuilders}
            all_pagebuilders = st.session_state.all_pagebuilders
            pagename = st.session_state.current_pagename
            
            st.markdown("---")
            st.subheader("📊 Decomposition Results")
            
            # Summary metrics
            included_count = sum(1 for status in inclusion_status.values() if status)
            excluded_count = len(inclusion_status) - included_count
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total PageBuilders", len(all_pagebuilders))
            col2.metric("Files Generated", len(files))
            col3.metric("Included", included_count)
            col4.metric("Excluded", excluded_count)
            
            # Show ignored PageBuilders if any
            if 'ignored_pagebuilders' in st.session_state and st.session_state.ignored_pagebuilders:
                ignored = st.session_state.ignored_pagebuilders
                st.info(f"ℹ️ Ignored PageBuilders: {', '.join(ignored)} (and all components only nested under them)")
            
            # Hierarchy visualization
            st.markdown("---")
            st.subheader("🌳 PageBuilder Hierarchy")
            st.markdown("""
            <div style="margin-bottom: 1em;">
                <span style="color: #28a745; font-weight: bold;">● Green</span> = Included (will be downloaded) &nbsp;&nbsp;
                <span style="color: #dc3545; font-weight: bold;">● Red</span> = Excluded (only nested under ignored PageBuilders)
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View complete hierarchy tree", expanded=True):
                tree_html = format_hierarchy_tree(hierarchy, pagename, inclusion_status, visited=set())
                # Construct HTML and render - ensure no code block interpretation
                full_html = '<div class="hierarchy-tree">' + tree_html + '</div>'
                # Use markdown with unsafe_allow_html to render HTML
                st.markdown(full_html, unsafe_allow_html=True)
            
            # File list
            st.markdown("---")
            st.subheader("📁 Generated Files")
            
            with st.expander("View all files in ZIP", expanded=False):
                # Group files by directory
                file_groups = {}
                for file_path in sorted(files.keys()):
                    if '/' in file_path:
                        dir_name = '/'.join(file_path.split('/')[:-1])
                        if dir_name not in file_groups:
                            file_groups[dir_name] = []
                        file_groups[dir_name].append(file_path.split('/')[-1])
                    else:
                        if 'root' not in file_groups:
                            file_groups['root'] = []
                        file_groups['root'].append(file_path)
                
                for dir_name in sorted(file_groups.keys()):
                    if dir_name == 'root':
                        st.markdown("**Root:**")
                    else:
                        st.markdown(f"**{dir_name}/:**")
                    for filename in sorted(file_groups[dir_name]):
                        st.text(f"  • {filename}")
            
            # Download section
            st.markdown("---")
            st.subheader("📥 Download")
            
            zip_data = create_zip_from_files(files, pagename)
            zip_filename = f"{pagename}_decomposed.zip"
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    label="📥 Download All PageBuilders (ZIP)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
            
            st.info(f"💡 The ZIP file contains {len(files)} HTML files organized in a hierarchical folder structure.")
            
            # Reset button
            if st.button("🔄 Decompose Another PageBuilder", use_container_width=True):
                for key in ['decomposed_files', 'decomposed_hierarchy', 'inclusion_status', 'all_pagebuilders', 'current_pagename', 'ignored_pagebuilders']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    else:
        # Empty state
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 60px; color: #888;">
            <h3>👆 Enter a PageBuilder URL or name to get started</h3>
            <p>Example: <code>imaginedisplay_cancer</code> or a full Luminate Online URL</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.9em;">
        <p>PageBuilder Decomposer • Built with Streamlit</p>
        <p>💡 Tip: Works with any public Luminate Online PageBuilder - no login required!</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

