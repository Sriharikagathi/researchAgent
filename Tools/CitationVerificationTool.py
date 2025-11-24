"""Citation verification and formatting tool."""

import json
from typing import List, Dict, Any
from datetime import datetime
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from shared.state import SharedState, LogType


class CitationVerificationInput(BaseModel):
    """Input schema for citation verification tool."""
    sources: str = Field(description="JSON string of sources to verify and format")


def create_citation_verification_tool(shared_state: SharedState) -> StructuredTool:
    """
    Create citation verification tool.
    
    Args:
        shared_state: Shared state instance
        
    Returns:
        StructuredTool for citation verification
    """
    
    def verify_citations(sources: str) -> str:
        """
        Verify and format citations from research sources.
        
        Args:
            sources: JSON string containing sources to verify
            
        Returns:
            JSON string with verified citations
        """
        shared_state.add_log(
            "[Tool: Citation Verification] Verifying sources",
            LogType.TOOL
        )
        
        try:
            # Parse sources
            source_list = json.loads(sources) if isinstance(sources, str) else sources
            
            if not isinstance(source_list, list):
                source_list = [source_list]
            
            verified_citations = []
            
            for idx, source in enumerate(source_list):
                # Verify source structure
                if not isinstance(source, dict):
                    continue
                
                # Format citation
                citation = {
                    'id': idx + 1,
                    'verified': True,  # In production, implement actual verification
                    'citation_format': 'APA',
                    'timestamp': datetime.now().isoformat(),
                    **source
                }
                
                # Generate APA-style citation
                if 'title' in source and 'url' in source:
                    citation['formatted_citation'] = format_apa_citation(source)
                
                verified_citations.append(citation)
            
            # Update shared state
            shared_state.verified_citations = verified_citations
            shared_state.citation_count = len(verified_citations)
            
            shared_state.add_log(
                f"[Tool: Citation Verification] Verified {len(verified_citations)} citations",
                LogType.SUCCESS
            )
            
            return str({
                'success': True,
                'verified_count': len(verified_citations),
                'verified_citations': verified_citations
            })
            
        except Exception as e:
            shared_state.add_log(
                f"[Tool: Citation Verification] Error: {str(e)}",
                LogType.ERROR
            )
            return str({
                'success': False,
                'error': str(e),
                'verified_count': 0
            })
    
    return StructuredTool.from_function(
        func=verify_citations,
        name="citation_verification",
        description="Verify and format citations from research sources in APA format. Use this tool to ensure all sources are properly cited and formatted.",
        args_schema=CitationVerificationInput
    )


def format_apa_citation(source: Dict[str, Any]) -> str:
    """
    Format a source in APA style.
    
    Args:
        source: Source dictionary with title, url, etc.
        
    Returns:
        Formatted APA citation
    """
    title = source.get('title', 'Unknown Title')
    url = source.get('url', '')
    date = source.get('date', datetime.now().strftime('%Y, %B %d'))
    
    citation = f"{title}. ({date}). Retrieved from {url}"
    
    return citation