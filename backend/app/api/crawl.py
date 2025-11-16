"""
Crawling API endpoints for testing and manual crawling.
"""
from fastapi import APIRouter, Query, HTTPException, status
from app.services.crawling_service import crawl_url

router = APIRouter()


@router.get("/crawl")
async def crawl_endpoint(url: str = Query(..., description="URL to crawl")):
    """
    Crawl a URL using Crawl4AI and return structured content.
    
    This endpoint is primarily for testing and internal/admin usage.
    Supports both HTML pages and PDFs.
    
    Args:
        url: The URL to crawl
        
    Returns:
        Structured dictionary with:
        - url: Original URL
        - markdown: Main content in markdown format
        - raw_html: Optional raw HTML
        - metadata: Dict with title, status_code, content_type, etc.
        - error: Optional error message
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Crawl endpoint called for URL: {url}")
        result = await crawl_url(url)
        
        if result.get("error"):
            logger.warning(f"Crawl returned error: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Crawl successful for URL: {url}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception(f"Exception in crawl endpoint for URL {url}: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error crawling URL: {str(e)}. Check server logs for details."
        )

