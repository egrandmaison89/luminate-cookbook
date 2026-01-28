"""
PageBuilder Decomposer Service.

Handles PageBuilder decomposition using the existing library.
"""

import io
import zipfile
from typing import Dict, List, Optional, Tuple, Any

# Import the existing library
from lib.pagebuilder_decomposer_lib import HierarchicalLuminateWorkflow


async def analyze_pagebuilder(
    url_or_name: str,
    base_url: str = "https://danafarber.jimmyfund.org",
    ignore_global_stylesheet: bool = True,
) -> Dict[str, Any]:
    """
    Analyze a PageBuilder structure without downloading.
    
    Returns hierarchy information for preview.
    """
    try:
        workflow = HierarchicalLuminateWorkflow(base_url=base_url)
        
        # Extract pagename
        pagename = workflow.extract_pagename_from_url(url_or_name)
        if not pagename:
            return {
                "success": False,
                "error": "Could not extract PageBuilder name from input",
            }
        
        # Prepare ignore list
        ignore_list = []
        if ignore_global_stylesheet:
            ignore_list.append("reus_dm_global_stylesheet")
        
        # Decompose
        files, inclusion_status, complete_hierarchy = workflow.decompose_pagebuilder(
            pagename,
            progress_callback=None,
            ignore_pagebuilders=ignore_list
        )
        
        if not files:
            return {
                "success": False,
                "error": "No files were generated. Please check the PageBuilder name.",
            }
        
        # Build components list
        components = []
        all_pagebuilders = list(workflow.all_pagebuilders)
        
        for pb_name in all_pagebuilders:
            is_included = inclusion_status.get(pb_name, True)
            children = complete_hierarchy.get(pb_name, [])
            components.append({
                "name": pb_name,
                "is_included": is_included,
                "children": children,
            })
        
        included_count = sum(1 for status in inclusion_status.values() if status)
        excluded_count = len(inclusion_status) - included_count
        
        return {
            "success": True,
            "pagename": pagename,
            "total_components": len(all_pagebuilders),
            "included_components": included_count,
            "excluded_components": excluded_count,
            "hierarchy": complete_hierarchy,
            "components": components,
            "message": f"Found {len(all_pagebuilders)} PageBuilder(s)",
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def decompose_pagebuilder(
    url_or_name: str,
    base_url: str = "https://danafarber.jimmyfund.org",
    ignore_global_stylesheet: bool = True,
) -> Tuple[Optional[bytes], Dict[str, Any]]:
    """
    Decompose a PageBuilder and return a ZIP file.
    
    Returns:
        Tuple of (zip_bytes or None, response_data dict)
    """
    try:
        workflow = HierarchicalLuminateWorkflow(base_url=base_url)
        
        # Extract pagename
        pagename = workflow.extract_pagename_from_url(url_or_name)
        if not pagename:
            return None, {
                "success": False,
                "error": "Could not extract PageBuilder name from input",
            }
        
        # Prepare ignore list
        ignore_list = []
        if ignore_global_stylesheet:
            ignore_list.append("reus_dm_global_stylesheet")
        
        # Decompose
        files, inclusion_status, complete_hierarchy = workflow.decompose_pagebuilder(
            pagename,
            progress_callback=None,
            ignore_pagebuilders=ignore_list
        )
        
        if not files:
            return None, {
                "success": False,
                "error": "No files were generated. Please check the PageBuilder name.",
            }
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        files_added = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main file
            if pagename in files:
                zip_file.writestr(f"{pagename}.html", files[pagename])
                files_added += 1
            
            # Add all component files
            for file_path, content in files.items():
                if file_path != pagename:
                    zip_file.writestr(file_path, content)
                    files_added += 1
        
        zip_buffer.seek(0)
        
        return zip_buffer.getvalue(), {
            "success": True,
            "pagename": pagename,
            "files_count": files_added,
        }
        
    except Exception as e:
        return None, {
            "success": False,
            "error": str(e),
        }
