#!/usr/bin/env python3
"""
PageBuilder Decomposer Library

Core functionality for decomposing Luminate Online PageBuilders into their
hierarchical component structure. Returns in-memory data structures suitable
for Streamlit download operations.
"""

import re
import requests
import os
from typing import Dict, List, Set, Optional, Callable, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from collections import defaultdict


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


class HierarchicalLuminateWorkflow:
    """Decompose Luminate PageBuilders into hierarchical component structure."""
    
    def __init__(self, base_url: str = "https://danafarber.jimmyfund.org"):
        self.base_url = base_url
        self.debug_url_template = f"{base_url}/site/SPageServer/?pagename={{pagename}}&s_debug=true&pgwrap=n"
        self.clean_url_template = f"{base_url}/site/SPageServer/?pagename={{pagename}}&pgwrap=n"
        self.hierarchy = defaultdict(list)  # parent -> [children]
        self.all_pagebuilders = set()
    
    def _reset(self):
        """Reset internal state for a new decomposition."""
        self.hierarchy = defaultdict(list)
        self.all_pagebuilders = set()
    
    def extract_pagename_from_url(self, url_or_name: str) -> str:
        """Extract pagename from a full URL or return the name if it's already a pagename."""
        # If it looks like a URL, try to extract pagename
        if url_or_name.startswith('http://') or url_or_name.startswith('https://'):
            try:
                parsed = urlparse(url_or_name)
                params = parse_qs(parsed.query)
                if 'pagename' in params:
                    return params['pagename'][0]
                # If no pagename param, try to extract from path
                path_parts = parsed.path.strip('/').split('/')
                if path_parts:
                    return path_parts[-1]
            except Exception:
                pass
        # Otherwise assume it's already a pagename
        return url_or_name.strip()
    
    def fetch_debug_html(self, pagename: str) -> str:
        """Fetch the debug version of a PageBuilder."""
        url = self.debug_url_template.format(pagename=pagename)
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Error fetching {pagename}: {e}")
    
    def fetch_clean_html(self, pagename: str) -> str:
        """Fetch the clean version (no debug) of a PageBuilder."""
        url = self.clean_url_template.format(pagename=pagename)
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Error fetching clean version of {pagename}: {e}")
    
    def extract_direct_s51_tags(self, html_content: str) -> List[str]:
        """Extract S51 tags directly from HTML content (not from debug comments)."""
        pattern = r'\[\[S51:([^\]]+)\]\]'
        matches = re.findall(pattern, html_content)
        return [match.strip() for match in matches]
    
    def extract_pagebuilders_from_debug(self, debug_html: str) -> List[str]:
        """Extract all PageBuilder names from debug HTML comments."""
        pattern = r'<!-- Begin content from page: ([^>]+?) -->'
        matches = re.findall(pattern, debug_html)
        pagebuilders = []
        for match in matches:
            clean_name = match.strip().rstrip(' -')
            if clean_name and clean_name not in pagebuilders:
                pagebuilders.append(clean_name)
        return pagebuilders
    
    def extract_content_blocks(self, debug_html: str) -> Dict[str, str]:
        """Extract content blocks between debug comments."""
        content_blocks = {}
        pattern = r'<!-- Begin content from page: ([^>]+?) -->(.*?)<!-- End of page content from page: \1 -->'
        matches = re.findall(pattern, debug_html, re.DOTALL)
        for pagename, content in matches:
            clean_name = pagename.strip().rstrip(' -')
            content = content.strip()
            content_blocks[clean_name] = content
        return content_blocks
    
    def reconstruct_with_s51_tags(self, main_pagename: str, debug_html: str, content_blocks: Dict[str, str]) -> str:
        """Reconstruct the HTML with S51 tags instead of rendered content."""
        reconstructed = debug_html
        for pagename, content in content_blocks.items():
            if content.strip():
                block_pattern = re.escape(f'<!-- Begin content from page: {pagename}') + r'[^>]*?-->' + \
                               r'(.*?)' + \
                               re.escape(f'<!-- End of page content from page: {pagename}') + r'[^>]*?-->'
                s51_tag = f"[[S51:{pagename}]]"
                reconstructed = re.sub(block_pattern, s51_tag, reconstructed, flags=re.DOTALL)
        
        # Clean up remaining debug comments
        reconstructed = re.sub(r'<!-- Begin content from page: [^>]*? -->', '', reconstructed)
        reconstructed = re.sub(r'<!-- End of page content from page: [^>]*? -->', '', reconstructed)
        reconstructed = re.sub(r'\n\s*\n\s*\n+', '\n\n', reconstructed)
        return reconstructed.strip()
    
    def build_hierarchy_map(self, main_pagename: str, progress_callback: Optional[Callable[[str, Optional[str]], None]] = None, 
                           ignore_pagebuilders: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Build a complete hierarchy map of PageBuilder relationships."""
        if ignore_pagebuilders is None:
            ignore_pagebuilders = []
        ignore_set = set(ignore_pagebuilders)
        
        hierarchy = defaultdict(list)
        processed = set()
        to_process = [(main_pagename, None)]  # (pagename, parent)
        
        while to_process:
            current, parent = to_process.pop(0)
            if current in processed:
                continue
            
            # Skip if this PageBuilder should be ignored (check before processing)
            if current in ignore_set:
                processed.add(current)  # Mark as processed so we don't try again
                continue
            
            processed.add(current)
            self.all_pagebuilders.add(current)
            
            if progress_callback:
                progress_callback(current, parent)
            
            # Fetch debug HTML to find what this PageBuilder references
            try:
                debug_html = self.fetch_debug_html(current)
            except Exception:
                continue
            
            # Extract direct children using the same logic as download:
            # Reconstruct with S51 tags and extract only direct children (not nested descendants)
            content_blocks = self.extract_content_blocks(debug_html)
            reconstructed = self.reconstruct_with_s51_tags(current, debug_html, content_blocks)
            children = self.extract_direct_s51_tags(reconstructed)
            
            # Filter out ignored PageBuilders from children
            filtered_children = [child for child in children if child not in ignore_set]
            
            # Add to hierarchy
            if filtered_children:
                hierarchy[current].extend(filtered_children)
            
            # Queue children for processing (only non-ignored ones)
            for child in filtered_children:
                if child not in processed:
                    to_process.append((child, current))
        
        # Clean up: remove any ignored PageBuilders that might have been added as keys
        # (this shouldn't happen, but just to be safe)
        cleaned_hierarchy = {}
        for parent, children in hierarchy.items():
            if parent not in ignore_set:
                # Only include children that aren't ignored
                cleaned_children = [child for child in children if child not in ignore_set]
                if cleaned_children:
                    cleaned_hierarchy[parent] = cleaned_children
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"pagebuilder_decomposer_lib.py:172","message":"build_hierarchy_map: cleaned hierarchy","data":{"original_size":len(hierarchy),"cleaned_size":len(cleaned_hierarchy),"cleaned_keys":list(cleaned_hierarchy.keys())[:10]}})
        # #endregion
        
        return cleaned_hierarchy
    
    def decompose_pagebuilder(self, main_pagename: str, progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
                             ignore_pagebuilders: Optional[List[str]] = None) -> Tuple[Dict[str, str], Dict[str, bool], Dict[str, List[str]]]:
        """
        Decompose a PageBuilder and all its nested dependencies.
        
        Args:
            main_pagename: The main PageBuilder to decompose
            progress_callback: Optional callback for progress updates
            ignore_pagebuilders: Optional list of PageBuilder names to ignore (and their children)
        
        Returns:
            Tuple of:
            - Dict mapping pagename -> HTML content (with hierarchical file paths as keys)
            - Dict mapping pagename -> bool (inclusion status: True=included, False=excluded)
            - Dict mapping parent -> [children] (complete hierarchy for display)
        """
        if ignore_pagebuilders is None:
            ignore_pagebuilders = []
        ignore_set = set(ignore_pagebuilders)
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"pagebuilder_decomposer_lib.py:188","message":"decompose_pagebuilder: FUNCTION CALLED","data":{"main_pagename":main_pagename,"ignore_pagebuilders":ignore_pagebuilders}})
        # #endregion
        
        # Reset internal state for new decomposition
        self._reset()
        
        # Build complete hierarchy (including ignored PageBuilders) to calculate inclusion status
        complete_hierarchy = self.build_complete_hierarchy_map(main_pagename, progress_callback, ignore_pagebuilders)
        
        # Calculate inclusion status: which PageBuilders should be included vs excluded
        inclusion_status = self.calculate_inclusion_status(complete_hierarchy, main_pagename, ignore_pagebuilders)
        
        # Build filtered hierarchy for processing (only included PageBuilders)
        hierarchy = {}
        for parent, children in complete_hierarchy.items():
            if inclusion_status.get(parent, True):  # Only include parents that are included
                filtered_children = [child for child in children if inclusion_status.get(child, True)]
                if filtered_children:
                    hierarchy[parent] = filtered_children
        
        # Get main PageBuilder content
        main_debug_html = self.fetch_debug_html(main_pagename)
        
        # Extract and reconstruct main PageBuilder
        # Note: We keep all content blocks for reconstruction (to create S51 tags),
        # but we'll filter based on inclusion status when processing children
        main_content_blocks = self.extract_content_blocks(main_debug_html)
        reconstructed_main = self.reconstruct_with_s51_tags(main_pagename, main_debug_html, main_content_blocks)
        
        # Store main PageBuilder
        files = {main_pagename: reconstructed_main}
        
        # Get direct children of main PageBuilder
        main_direct_children = self.extract_direct_s51_tags(reconstructed_main)
        
        # Filter based on inclusion status (not just ignore_set)
        filtered_children = [child for child in main_direct_children if inclusion_status.get(child, True)]
        
        # Track processed components to avoid duplicates
        processed_components = set()
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C,D,E","location":"pagebuilder_decomposer_lib.py:234","message":"decompose_pagebuilder: starting","data":{"main_pagename":main_pagename,"main_direct_children":main_direct_children,"filtered_children":filtered_children,"filtered_count":len(filtered_children),"ignore_pagebuilders":ignore_pagebuilders,"hierarchy_keys":list(hierarchy.keys())[:10],"hierarchy_size":len(hierarchy)}})
        # #endregion
        
        # Process components hierarchically
        for component in filtered_children:
            # #region agent log
            _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"B,C","location":"pagebuilder_decomposer_lib.py:300","message":"decompose_pagebuilder: processing component","data":{"component":component,"already_processed":component in processed_components,"hierarchy_children":hierarchy.get(component, [])[:5],"included":inclusion_status.get(component, True)}})
            # #endregion
            # Only process if included and not already processed
            # Check processed_components here to skip duplicates in filtered_children
            # The component will be marked as processed inside _create_component_hierarchy
            if component not in processed_components and inclusion_status.get(component, True):
                result = self._create_component_hierarchy(
                    component, hierarchy, "components", level=1, progress_callback=progress_callback,
                    ignore_pagebuilders=ignore_pagebuilders, processed_components=processed_components,
                    inclusion_status=inclusion_status
                )
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,D","location":"pagebuilder_decomposer_lib.py:252","message":"decompose_pagebuilder: got result from _create_component_hierarchy","data":{"component":component,"result_files_count":len(result),"result_keys":list(result.keys())[:5]}})
                # #endregion
                files.update(result)
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:290","message":"decompose_pagebuilder: final result","data":{"total_files":len(files),"file_keys":list(files.keys())[:10]}})
        # #endregion
        return files, inclusion_status, complete_hierarchy
    
    def _create_component_hierarchy(self, pagename: str, hierarchy: Dict[str, List[str]], 
                                   parent_path: str, level: int = 1,
                                   progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
                                   ignore_pagebuilders: Optional[List[str]] = None,
                                   processed_components: Optional[Set[str]] = None,
                                   inclusion_status: Optional[Dict[str, bool]] = None) -> Dict[str, str]:
        """Recursively create component hierarchy, returning in-memory file structure."""
        if ignore_pagebuilders is None:
            ignore_pagebuilders = []
        if processed_components is None:
            processed_components = set()
        if inclusion_status is None:
            inclusion_status = {}
        ignore_set = set(ignore_pagebuilders)
        
        files = {}
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,C,D","location":"pagebuilder_decomposer_lib.py:320","message":"_create_component_hierarchy: entry","data":{"pagename":pagename,"parent_path":parent_path,"in_ignore_set":pagename in ignore_set,"in_processed":pagename in processed_components,"included":inclusion_status.get(pagename, True),"processed_count":len(processed_components)}})
        # #endregion
        
        # Skip if this PageBuilder should be ignored or excluded
        if pagename in ignore_set or not inclusion_status.get(pagename, True):
            # #region agent log
            _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"pagebuilder_decomposer_lib.py:250","message":"_create_component_hierarchy: skipped (ignored)","data":{"pagename":pagename}})
            # #endregion
            return files
        
        # Skip if already processed (avoid duplicates)
        # This check is critical to prevent processing the same component multiple times
        # when it appears as a child of multiple parents
        if pagename in processed_components:
            # #region agent log
            _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,C,D","location":"pagebuilder_decomposer_lib.py:256","message":"_create_component_hierarchy: skipped (already processed)","data":{"pagename":pagename,"parent_path":parent_path}})
            # #endregion
            return files
        
        # Mark as processed immediately after skip checks to prevent duplicate processing
        # This ensures that if this component is encountered again through a different parent path,
        # it will be skipped
        processed_components.add(pagename)
        
        if progress_callback:
            progress_callback(pagename, None)
        
        # Check if this component has children
        children = hierarchy.get(pagename, [])
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"B,E","location":"pagebuilder_decomposer_lib.py:264","message":"_create_component_hierarchy: checking children","data":{"pagename":pagename,"children_count":len(children),"children":children[:5]}})
        # #endregion
        
        if children:
            # Component has nested dependencies, so fetch debug HTML and reconstruct with S51 tags
            try:
                debug_html = self.fetch_debug_html(pagename)
                content_blocks = self.extract_content_blocks(debug_html)
                reconstructed_html = self.reconstruct_with_s51_tags(pagename, debug_html, content_blocks)
                file_path = f"{parent_path}/{pagename}.html"
                files[file_path] = reconstructed_html
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:335","message":"_create_component_hierarchy: created file (with children)","data":{"pagename":pagename,"file_path":file_path,"file_size":len(reconstructed_html)}})
                # #endregion
            except Exception as e:
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:345","message":"_create_component_hierarchy: error creating file (with children)","data":{"pagename":pagename,"error":str(e),"error_type":type(e).__name__}})
                # #endregion
                return files
        else:
            # Component has no children, so use clean HTML
            try:
                clean_html = self.fetch_clean_html(pagename)
                file_path = f"{parent_path}/{pagename}.html"
                files[file_path] = clean_html
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:360","message":"_create_component_hierarchy: created file (no children)","data":{"pagename":pagename,"file_path":file_path,"file_size":len(clean_html)}})
                # #endregion
            except Exception as e:
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run2","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:370","message":"_create_component_hierarchy: error creating file (no children)","data":{"pagename":pagename,"error":str(e),"error_type":type(e).__name__}})
                # #endregion
                return files
        
        # Process children recursively (only non-ignored ones, and only if not already processed)
        if children:
            children_dir = f"{parent_path}/{pagename}_components"
            for child in children:
                # #region agent log
                _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"B,E","location":"pagebuilder_decomposer_lib.py:303","message":"_create_component_hierarchy: processing child","data":{"parent":pagename,"child":child,"child_ignored":child in ignore_set,"child_processed":child in processed_components}})
                # #endregion
                if child not in ignore_set and child not in processed_components and inclusion_status.get(child, True):
                    child_result = self._create_component_hierarchy(
                        child, hierarchy, children_dir, level + 1, progress_callback, ignore_pagebuilders, processed_components, inclusion_status
                    )
                    # #region agent log
                    _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,D","location":"pagebuilder_decomposer_lib.py:310","message":"_create_component_hierarchy: got child result","data":{"parent":pagename,"child":child,"child_result_count":len(child_result)}})
                    # #endregion
                    files.update(child_result)
        
        # #region agent log
        _safe_debug_log({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"pagebuilder_decomposer_lib.py:316","message":"_create_component_hierarchy: returning","data":{"pagename":pagename,"files_count":len(files),"file_keys":list(files.keys())}})
        # #endregion
        return files
    
    def build_complete_hierarchy_map(self, main_pagename: str, progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
                                    ignore_pagebuilders: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Build a complete hierarchy map including ignored PageBuilders (for display)."""
        if ignore_pagebuilders is None:
            ignore_pagebuilders = []
        ignore_set = set(ignore_pagebuilders)
        
        hierarchy = defaultdict(list)
        processed = set()
        to_process = [(main_pagename, None)]  # (pagename, parent)
        
        while to_process:
            current, parent = to_process.pop(0)
            if current in processed:
                continue
            
            processed.add(current)
            self.all_pagebuilders.add(current)
            
            if progress_callback:
                progress_callback(current, parent)
            
            # Fetch debug HTML to find what this PageBuilder references
            try:
                debug_html = self.fetch_debug_html(current)
            except Exception:
                continue
            
            # Extract direct children using the same logic as download:
            # Reconstruct with S51 tags and extract only direct children (not nested descendants)
            content_blocks = self.extract_content_blocks(debug_html)
            reconstructed = self.reconstruct_with_s51_tags(current, debug_html, content_blocks)
            children = self.extract_direct_s51_tags(reconstructed)
            
            # Add to hierarchy (include all children, even ignored ones)
            if children:
                hierarchy[current].extend(children)
            
            # Queue children for processing (include ignored ones for complete hierarchy)
            for child in children:
                if child not in processed:
                    to_process.append((child, current))
        
        return dict(hierarchy)
    
    def calculate_inclusion_status(self, hierarchy: Dict[str, List[str]], main_pagename: str,
                                  ignore_pagebuilders: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Calculate which PageBuilders should be included (True) or excluded (False).
        A PageBuilder is excluded if it appears as a descendant of any ignored PageBuilder.
        A PageBuilder is included only if it does NOT appear under any ignored PageBuilder.
        """
        if ignore_pagebuilders is None:
            ignore_pagebuilders = []
        ignore_set = set(ignore_pagebuilders)
        
        # Track which PageBuilders are descendants of ignored PageBuilders
        excluded_by_ignored = set()
        
        def mark_excluded_from_ignored(pagename: str):
            """Recursively mark PageBuilder and all its descendants as excluded."""
            if pagename in excluded_by_ignored:
                return  # Already processed
            
            excluded_by_ignored.add(pagename)
            
            # Mark all children as excluded
            for child in hierarchy.get(pagename, []):
                mark_excluded_from_ignored(child)
        
        # Mark all ignored PageBuilders and their descendants as excluded
        for ignored_pb in ignore_set:
            if ignored_pb in hierarchy or ignored_pb == main_pagename:
                mark_excluded_from_ignored(ignored_pb)
        
        # Build inclusion map: True if included, False if excluded
        inclusion_map = {}
        all_pagebuilders = set([main_pagename])
        for children in hierarchy.values():
            all_pagebuilders.update(children)
        
        for pagename in all_pagebuilders:
            if pagename in ignore_set:
                inclusion_map[pagename] = False  # Ignored PageBuilders are always excluded
            elif pagename in excluded_by_ignored:
                inclusion_map[pagename] = False  # Descendants of ignored PageBuilders are excluded
            else:
                inclusion_map[pagename] = True  # All others are included
        
        return inclusion_map
    
    def get_hierarchy_tree(self, main_pagename: str, ignore_pagebuilders: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Get the hierarchy map for visualization purposes."""
        return self.build_hierarchy_map(main_pagename, ignore_pagebuilders=ignore_pagebuilders)

