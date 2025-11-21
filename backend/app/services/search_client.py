"""
Search API client for query-seeded crawling.
Supports Perplexity API (primary) and Google Custom Search API (fallback).
"""
import logging
from typing import List, Optional
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchClient:
    """
    Search API client for getting seed URLs from natural language queries.
    
    Supports multiple providers:
    - Perplexity API (primary)
    - Google Custom Search API (fallback)
    """
    
    def __init__(self):
        """Initialize search client with API keys from settings."""
        self.provider = getattr(settings, 'search_api_provider', 'perplexity')
        self.perplexity_api_key = getattr(settings, 'perplexity_api_key', '')
        self.google_search_api_key = getattr(settings, 'google_search_api_key', '')
        self.google_search_engine_id = getattr(settings, 'google_search_engine_id', '')
    
    async def get_seed_urls(self, query: str, top_k: int = 10) -> List[dict]:
        """
        Get seed URLs from a search query with metadata.
        
        Args:
            query: Natural language search query (e.g., "EU AI Act high-risk obligations")
            top_k: Number of URLs to return (default: 10)
            
        Returns:
            List of dictionaries with:
            - url: URL string
            - title: Optional page title from search results
            - snippet: Optional snippet from search results
            - search_engine: Provider name ("perplexity" or "google")
        """
        if self.provider == 'perplexity' and self.perplexity_api_key:
            return await self._get_perplexity_urls(query, top_k)
        elif self.provider == 'google' and self.google_search_api_key and self.google_search_engine_id:
            return await self._get_google_urls(query, top_k)
        else:
            logger.warning(f"Search API not configured (provider={self.provider}). Returning empty list.")
            return []
    
    async def _get_perplexity_urls(self, query: str, top_k: int) -> List[dict]:
        """
        Get URLs from Perplexity API with metadata.
        
        Args:
            query: Search query
            top_k: Number of URLs to return
            
        Returns:
            List of dictionaries with url, title, snippet, search_engine
        """
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts URLs with titles and snippets from search results. Return a JSON array of objects with 'url', 'title', and 'snippet' fields."
                    },
                    {
                        "role": "user",
                        "content": f"Search for: {query}. Return the top {top_k} authoritative URLs with their titles and snippets as a JSON array of objects."
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        
                        # Try to parse as JSON array of objects
                        import json
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, list):
                                results = []
                                for item in parsed[:top_k]:
                                    if isinstance(item, dict) and item.get('url'):
                                        results.append({
                                            "url": item.get('url', ''),
                                            "title": item.get('title'),
                                            "snippet": item.get('snippet'),
                                            "search_engine": "perplexity"
                                        })
                                    elif isinstance(item, str) and item.startswith(('http://', 'https://')):
                                        # Fallback: just URL string
                                        results.append({
                                            "url": item,
                                            "title": None,
                                            "snippet": None,
                                            "search_engine": "perplexity"
                                        })
                                return results
                        except:
                            pass
                        
                        # Fallback: extract URLs from text
                        urls = self._extract_urls_from_text(content)
                        return [
                            {
                                "url": url_str,
                                "title": None,
                                "snippet": None,
                                "search_engine": "perplexity"
                            }
                            for url_str in urls[:top_k]
                        ]
                    else:
                        error_text = await response.text()
                        logger.error(f"Perplexity API error (status {response.status}): {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}")
            return []
    
    async def _get_google_urls(self, query: str, top_k: int) -> List[dict]:
        """
        Get URLs from Google Custom Search API with metadata.
        
        Args:
            query: Search query
            top_k: Number of URLs to return
            
        Returns:
            List of dictionaries with url, title, snippet, search_engine
        """
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_search_api_key,
                "cx": self.google_search_engine_id,
                "q": query,
                "num": min(top_k, 10)  # Google API max is 10 per request
            }
            
            results = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        for item in items[:top_k]:
                            if item.get('link'):
                                results.append({
                                    "url": item.get('link', ''),
                                    "title": item.get('title'),
                                    "snippet": item.get('snippet'),
                                    "search_engine": "google"
                                })
                        return results
                    else:
                        error_text = await response.text()
                        logger.error(f"Google Search API error (status {response.status}): {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Google Search API: {e}")
            return []
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """
        Extract URLs from text (handles JSON arrays, plain text, etc.).
        
        Args:
            text: Text that may contain URLs
            
        Returns:
            List of extracted URLs
        """
        import re
        import json
        
        urls = []
        
        # Try to parse as JSON array first
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                urls = [str(item) for item in parsed if isinstance(item, str) and item.startswith(('http://', 'https://'))]
                return urls
        except:
            pass
        
        # Extract URLs using regex
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, text)
        
        # Clean up URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in found_urls:
            # Remove trailing punctuation
            url = url.rstrip('.,;:!?)')
            if url.startswith(('http://', 'https://')):
                cleaned_urls.append(url)
        
        return cleaned_urls


# Global search client instance
search_client = SearchClient()


