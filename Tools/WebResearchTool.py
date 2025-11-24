"""Web research tool - Alternative without DuckDuckGo dependency."""

import json
from typing import List, Dict, Any
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup
from shared.state import SharedState, LogType
import urllib.parse


class WebResearchInput(BaseModel):
    """Input schema for web research tool."""
    query: str = Field(description="The search query for web research")
    max_results: int = Field(default=5, description="Maximum number of results to return")


def create_web_research_tool(shared_state: SharedState) -> StructuredTool:
    """
    Create web research tool using SerpAPI alternative or direct scraping.
    
    Args:
        shared_state: Shared state instance
        
    Returns:
        StructuredTool for web research
    """
    
    def search_web(query: str, max_results: int = 5) -> str:
        """
        Search the web for current information.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            JSON string with search results
        """
        shared_state.add_log(
            "[Tool: Web Research] Starting web search",
            LogType.TOOL,
            metadata={"query": query[:100], "max_results": max_results}
        )
        
        results = []
        
        try:
            # Method 1: Try DuckDuckGo HTML scraping (no API needed)
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract search results
                result_divs = soup.find_all('div', class_='result', limit=max_results)
                
                for idx, result_div in enumerate(result_divs):
                    title_elem = result_div.find('a', class_='result__a')
                    snippet_elem = result_div.find('a', class_='result__snippet')
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        results.append({
                            'rank': idx + 1,
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'source': 'duckduckgo_html'
                        })
                
                if not results:
                    shared_state.add_log(
                        "[Tool: Web Research] No results found via HTML scraping",
                        LogType.WARNING
                    )
            
        except Exception as e:
            shared_state.add_log(
                f"[Tool: Web Research] Error with DuckDuckGo: {str(e)}",
                LogType.WARNING
            )
        
        # Fallback: If no results, provide informative mock data
        if not results:
            shared_state.add_log(
                "[Tool: Web Research] Using knowledge-based response (web search unavailable)",
                LogType.WARNING
            )
            
            results = [
                {
                    'rank': 1,
                    'title': f'Information about: {query}',
                    'url': f'https://www.google.com/search?q={urllib.parse.quote(query)}',
                    'snippet': 'Web search is currently unavailable. The agent will use its training data and document database to answer your query.',
                    'source': 'fallback'
                }
            ]
        
        # Update shared state
        shared_state.web_results = results
        shared_state.web_sources = [r['url'] for r in results]
        
        shared_state.add_log(
            f"[Tool: Web Research] Found {len(results)} web sources",
            LogType.SUCCESS
        )
        
        return str({
            'success': True,
            'result_count': len(results),
            'results': results,
            'note': 'Web search may have limited results. Using knowledge base and documents for comprehensive answers.'
        })
    
    return StructuredTool.from_function(
        func=search_web,
        name="web_research",
        description="Search the web for current information, news, and recent developments on a given query. Use this when you need up-to-date information not available in the document database. Note: Web search may have limited availability, but the agent can still provide comprehensive answers using its knowledge base.",
        args_schema=WebResearchInput
    )


def fetch_webpage_content(url: str, shared_state: SharedState) -> Dict[str, Any]:
    """
    Fetch and extract text content from a webpage.
    
    Args:
        url: URL to fetch
        shared_state: Shared state instance
        
    Returns:
        Dictionary with webpage content
    """
    shared_state.add_log(
        f"[Tool: Web Fetch] Fetching content from {url}",
        LogType.TOOL
    )
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        shared_state.add_log(
            f"[Tool: Web Fetch] Successfully fetched content ({len(text)} chars)",
            LogType.SUCCESS
        )
        
        return {
            'success': True,
            'url': url,
            'content': text[:5000],  # Limit content length
            'length': len(text)
        }
        
    except Exception as e:
        shared_state.add_log(
            f"[Tool: Web Fetch] Error fetching {url}: {str(e)}",
            LogType.ERROR
        )
        return {
            'success': False,
            'url': url,
            'error': str(e)
        }