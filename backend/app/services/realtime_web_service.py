"""
Real-time web retrieval service for on-demand web fetching.
Provides just-in-time web search and crawling for fresh content.
"""
import logging
from typing import List, Dict, Optional
from app.services.hybrid_crawler import hybrid_crawler
from app.services.search_client import search_client

logger = logging.getLogger(__name__)


def requires_freshness(query: str) -> bool:
    """
    Detect if a query requires fresh/live web content.
    
    Checks for temporal keywords and phrases that indicate the user
    wants current, recent, or updated information.
    
    Args:
        query: User's search query
        
    Returns:
        True if query requires fresh content, False otherwise
    """
    if not query:
        return False
    
    query_lower = query.lower()
    
    # Temporal keywords that indicate freshness requirement
    freshness_keywords = [
        'latest', 'recent', 'current', 'new', 'updated', 'today', 'now',
        '2025', '2024', 'this year', 'this month', 'this week',
        'draft', 'proposed', 'amendment', 'revision', 'change',
        'announcement', 'news', 'update', 'breaking'
    ]
    
    # Check if any freshness keyword is in the query
    for keyword in freshness_keywords:
        if keyword in query_lower:
            return True
    
    return False


class RealtimeWebService:
    """
    Service for real-time web retrieval and crawling.
    
    Provides on-demand web search and fast crawling for fresh content
    when local knowledge base is insufficient or query requires freshness.
    """
    
    def __init__(self):
        """Initialize real-time web service."""
        self.search_client = search_client
        self.hybrid_crawler = hybrid_crawler
    
    async def fetch_fresh_content(
        self,
        query: str,
        max_pages: int = 10,
        max_depth: int = 1,
        max_seconds: float = 5.0
    ) -> List[Dict]:
        """
        Fetch fresh content from the web for a query.
        
        Performs a fast, shallow crawl of search results to get
        current information. Designed for real-time use in RAG queries.
        
        Args:
            query: Search query
            max_pages: Maximum number of pages to crawl (default: 10)
            max_depth: Maximum crawl depth (default: 1 for speed)
            max_seconds: Maximum time budget in seconds (default: 5.0)
            
        Returns:
            List of crawl result dictionaries with fresh content
        """
        import asyncio
        from app.core.config import settings
        
        logger.info(f"Fetching fresh content for query: {query[:100]}...")
        
        try:
            # Use query-seeded crawl with strict limits for speed
            results = await asyncio.wait_for(
                self.hybrid_crawler.crawl_query_seeded(
                    query=query,
                    top_k=min(max_pages, 10),  # Limit seed URLs
                    max_depth=max_depth,
                    max_pages=max_pages
                ),
                timeout=max_seconds
            )
            
            # Tag all results as real-time web content
            for result in results:
                result["metadata"]["source_type"] = "web_live"
                result["metadata"]["fetched_at"] = asyncio.get_event_loop().time()
            
            logger.info(f"Fetched {len(results)} pages of fresh content")
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"Fresh content fetch timed out after {max_seconds}s for query: {query[:100]}")
            return []
        except Exception as e:
            logger.error(f"Error fetching fresh content: {e}")
            return []


# Global real-time web service instance
realtime_web_service = RealtimeWebService()

