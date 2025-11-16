"""
Crawl4AI-based web crawling service.
All web crawling must go through this service using Crawl4AI.
"""
import logging
import os
import sys
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# Fix Windows console encoding for Crawl4AI BEFORE importing
if sys.platform == 'win32':
    # Set UTF-8 encoding for stdout/stderr to handle Unicode characters
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    # Set environment variable for subprocesses
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    # Disable Rich's terminal detection to avoid encoding issues
    os.environ['NO_COLOR'] = '1'
    os.environ['TERM'] = 'dumb'
    os.environ['FORCE_COLOR'] = '0'
    os.environ['RICH_NO_COLOR'] = '1'
    
    # Monkey-patch Rich console to suppress output on Windows BEFORE any imports
    # This must happen before Crawl4AI imports Rich
    try:
        # Import and patch Rich before Crawl4AI uses it
        import rich.console
        import io
        
        # Create a safe console that doesn't write to stdout
        class SafeConsole(rich.console.Console):
            def print(self, *args, **kwargs):
                # Suppress all output to prevent encoding errors
                pass
            
            def _check_buffer(self):
                # Suppress buffer checking
                pass
        
        # Replace the default console
        original_console_init = rich.console.Console.__init__
        def safe_console_init(self, *args, **kwargs):
            # Force file to None or a safe file-like object
            kwargs['file'] = io.StringIO()
            kwargs['force_terminal'] = False
            kwargs['no_color'] = True
            return original_console_init(self, *args, **kwargs)
        
        rich.console.Console.__init__ = safe_console_init
        
        # Also patch the print method directly
        def null_print(self, *args, **kwargs):
            pass
        rich.console.Console.print = null_print
        
    except Exception as patch_error:
        # If patching fails, log but continue
        pass

# Now import Crawl4AI after setting up encoding
CRAWL4AI_AVAILABLE = False
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except Exception as import_error:
    # If import fails, log it
    logging.error(f"Crawl4AI import failed: {import_error}. Please ensure crawl4ai is installed and crawl4ai-setup has been run.")

logger = logging.getLogger(__name__)


async def check_playwright_browsers_async() -> Tuple[bool, str]:
    """
    Check if Playwright browsers are installed using async-only method.
    
    This function uses async Playwright API only to avoid conflicts with asyncio event loop.
    
    Returns:
        Tuple of (is_installed, error_message)
    """
    try:
        # Ensure Windows event loop policy is set for subprocess support
        import sys
        import asyncio
        
        # Log current state for debugging
        try:
            current_loop = asyncio.get_running_loop()
            loop_info = f"Running loop: {type(current_loop).__name__}"
        except RuntimeError:
            loop_info = "No running loop"
        
        current_policy = asyncio.get_event_loop_policy()
        policy_info = f"Event loop policy: {type(current_policy).__name__}"
        logger.debug(f"Playwright check - {loop_info}, {policy_info}")
        
        if sys.platform.startswith("win"):
            try:
                # Always ensure ProactorEventLoopPolicy is set on Windows
                if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
                    logger.warning(f"Event loop policy is {type(current_policy).__name__}, setting to WindowsProactorEventLoopPolicy")
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    logger.debug("Set WindowsProactorEventLoopPolicy in check_playwright_browsers_async")
                else:
                    logger.debug("Event loop policy is already WindowsProactorEventLoopPolicy")
            except Exception as policy_error:
                logger.error(f"Could not set event loop policy: {policy_error}")
                import traceback
                logger.error(f"Policy error traceback: {''.join(traceback.format_exception(type(policy_error), policy_error, policy_error.__traceback__))}")
        
        from playwright.async_api import async_playwright
        
        # Before launching browser, test if subprocess operations are supported
        # This helps diagnose the NotImplementedError issue
        if sys.platform.startswith("win"):
            try:
                # Quick test: try to create a subprocess to verify event loop supports it
                test_proc = await asyncio.create_subprocess_exec(
                    sys.executable, '-c', 'print("test")',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await test_proc.wait()
                logger.debug("Subprocess test passed - event loop supports subprocess operations")
            except NotImplementedError as subprocess_error:
                error_msg = (
                    f"Event loop does not support subprocess operations (NotImplementedError). "
                    f"This is required for Playwright. Current loop: {type(asyncio.get_running_loop()).__name__}, "
                    f"Policy: {type(asyncio.get_event_loop_policy()).__name__}. "
                    f"Please ensure the server is started with WindowsProactorEventLoopPolicy."
                )
                logger.error(error_msg)
                return False, error_msg
            except Exception as subprocess_test_error:
                # Subprocess test failed for other reasons (e.g., Python not found), but that's OK
                # The real test is whether Playwright can launch
                logger.debug(f"Subprocess test had non-critical error: {subprocess_test_error}")
        
        async with async_playwright() as p:
            try:
                # Try to launch browser with detailed error capture
                logger.debug("Attempting to launch Chromium browser...")
                browser = await p.chromium.launch(
                    headless=True,
                    timeout=15000,
                    args=['--no-sandbox', '--disable-setuid-sandbox']  # Additional args for better compatibility
                )
                logger.debug("Browser launched successfully, closing...")
                await browser.close()
                logger.debug("Playwright async check passed")
                return True, ""
            except NotImplementedError as not_impl:
                # Capture full exception details including traceback
                import traceback
                tb_str = ''.join(traceback.format_exception(type(not_impl), not_impl, not_impl.__traceback__))
                
                # Log detailed context about the error
                try:
                    current_loop = asyncio.get_running_loop()
                    loop_type = type(current_loop).__name__
                except RuntimeError:
                    loop_type = "No running loop"
                
                current_policy = asyncio.get_event_loop_policy()
                policy_type = type(current_policy).__name__
                
                logger.error(f"NotImplementedError occurred with event loop: {loop_type}, policy: {policy_type}")
                
                # Try multiple ways to get error details
                error_details = str(not_impl) if str(not_impl) else repr(not_impl)
                if not error_details or error_details == "NotImplementedError()":
                    # Try to get more info from args or traceback
                    if hasattr(not_impl, 'args') and not_impl.args:
                        error_details = f"NotImplementedError({', '.join(repr(arg) for arg in not_impl.args)})"
                    else:
                        error_details = f"NotImplementedError (subprocess transport not supported - event loop: {loop_type}, policy: {policy_type})"
                
                error_msg = f"Playwright browsers not installed (NotImplementedError: {error_details}). Please run: playwright install chromium"
                logger.error(f"Playwright NotImplementedError: {error_msg}\nEvent loop: {loop_type}, Policy: {policy_type}\nTraceback:\n{tb_str}")
                return False, error_msg
            except Exception as browser_error:
                # Capture full exception details
                import traceback
                tb_str = ''.join(traceback.format_exception(type(browser_error), browser_error, browser_error.__traceback__))
                error_type = type(browser_error).__name__
                error_str = str(browser_error) if str(browser_error) else repr(browser_error)
                error_msg = f"Playwright browser launch failed ({error_type}: {error_str}). Please run: playwright install chromium"
                logger.error(f"Playwright browser launch error: {error_msg}\nTraceback:\n{tb_str}")
                return False, error_msg
    except ImportError as import_err:
        error_msg = f"Playwright is not installed (ImportError: {str(import_err)}). Please run: pip install playwright && playwright install chromium"
        logger.error(f"Playwright import error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_type = type(e).__name__
        error_str = str(e) if str(e) else repr(e)
        error_msg = f"Playwright check failed ({error_type}: {error_str}). Please run: playwright install chromium"
        logger.error(f"Playwright async check failed: {error_msg}")
        return False, error_msg


def check_playwright_browsers() -> Tuple[bool, str]:
    """
    Check if Playwright browsers are installed (async wrapper for sync contexts).
    
    This is a sync wrapper that creates an async context to check Playwright.
    For async contexts, use check_playwright_browsers_async() directly.
    
    Returns:
        Tuple of (is_installed, error_message)
    """
    try:
        import asyncio
        from playwright.async_api import async_playwright
        
        async def async_check():
            return await check_playwright_browsers_async()
        
        # Try to get existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use run_until_complete
                # In this case, assume browsers are available (check will happen during actual crawl)
                logger.debug("Event loop is running, skipping Playwright check (will check during crawl)")
                return True, ""
            else:
                result = loop.run_until_complete(async_check())
                return result
        except RuntimeError:
            # No event loop, create one with proper policy for Windows
            if sys.platform.startswith("win"):
                try:
                    # Ensure ProactorEventLoopPolicy is set for subprocess support
                    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except:
                    pass
            result = asyncio.run(async_check())
            return result
    except Exception as e:
        logger.warning(f"Error checking Playwright browsers: {str(e)}")
        # Return True to allow crawl attempt (will fail gracefully if browsers aren't installed)
        return True, ""


def check_crawl4ai_initialized() -> Tuple[bool, str]:
    """
    Check if Crawl4AI is properly initialized and available.
    
    Returns:
        Tuple of (is_available, error_message)
    """
    if not CRAWL4AI_AVAILABLE:
        return False, "Crawl4AI is not installed or failed to import. Please run: pip install crawl4ai && crawl4ai-setup"
    
    # Check if Playwright browsers are installed
    playwright_ok, playwright_error = check_playwright_browsers()
    if not playwright_ok:
        return False, playwright_error
    
    # Try to create a crawler instance to verify initialization
    try:
        # Just check if we can import, actual initialization happens in crawl_url
        return True, ""
    except Exception as e:
        return False, f"Crawl4AI initialization check failed: {str(e)}. Please run: crawl4ai-setup"


async def crawl_url(url: str) -> Dict:
    """
    Crawl a URL using Crawl4AI and return structured content.
    
    Supports both HTML pages and PDFs. Uses Crawl4AI's AsyncWebCrawler
    for all crawling operations.
    
    Args:
        url: The URL to crawl (can be HTML page or PDF)
        
    Returns:
        Dictionary with:
        - url: Original URL
        - markdown: Main content in markdown format (LLM-ready)
        - raw_html: Optional raw HTML if available
        - metadata: Dict with title, status_code, content_type, etc.
        - error: Optional error message if crawling failed
    """
    result = {
        "url": url,
        "markdown": "",
        "raw_html": None,
        "metadata": {},
        "error": None
    }
    
    # Check if Crawl4AI is available
    is_available, error_msg = check_crawl4ai_initialized()
    if not is_available:
        result["error"] = error_msg
        logger.error(error_msg)
        return result
    
    try:
        # Validate URL and prevent SSRF attacks
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        # Only allow http and https schemes
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Only http and https URLs are allowed: {url}")
        
        # Block private/internal IP ranges (SSRF prevention)
        hostname = parsed.hostname
        if hostname:
            # Block localhost and private IPs
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if hostname.lower() in blocked_hosts:
                raise ValueError(f"Local/internal URLs are not allowed for security: {url}")
            
            # Additional validation: check for private IP ranges
            # This is a basic check - in production, use a more robust solution
            if hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
                # Allow if it's a public domain, but block if it looks like a private IP
                if not any(c.isalpha() for c in hostname):
                    raise ValueError(f"Private IP ranges are not allowed for security: {url}")
        
        # Check if it's a PDF
        is_pdf = url.lower().endswith('.pdf') or 'pdf' in url.lower()
        
        # Check Playwright browsers before initializing crawler (async check)
        # Also verify event loop supports subprocess operations
        try:
            import asyncio
            current_loop = asyncio.get_running_loop()
            current_policy = asyncio.get_event_loop_policy()
            
            # Log event loop state for debugging
            logger.debug(
                f"Before Playwright check - Loop: {type(current_loop).__name__}, "
                f"Policy: {type(current_policy).__name__}"
            )
            
            # On Windows, verify we have ProactorEventLoop
            if sys.platform.startswith("win"):
                if not isinstance(current_loop, asyncio.ProactorEventLoop):
                    logger.warning(
                        f"Event loop is {type(current_loop).__name__}, not ProactorEventLoop. "
                        f"This may cause NotImplementedError with Playwright subprocess operations."
                    )
            
            playwright_ok, playwright_error = await check_playwright_browsers_async()
            if not playwright_ok:
                error_msg = playwright_error if playwright_error else "Playwright browsers check failed. Please run: playwright install chromium"
                result["error"] = error_msg
                logger.error(f"Playwright browser check failed for {url}: {error_msg}")
                return result
            logger.debug(f"Playwright browser check passed for {url}")
        except Exception as check_error:
            error_type = type(check_error).__name__
            error_str = str(check_error) if str(check_error) else repr(check_error)
            error_msg = f"Playwright check exception ({error_type}: {error_str}). Please run: playwright install chromium"
            result["error"] = error_msg
            logger.exception(f"Exception during Playwright check for {url}: {error_msg}")
            return result
        
        # Initialize Crawl4AI crawler with comprehensive error handling
        # Use proper async context manager - this is critical for proper resource management
        logger.info(f"Initializing Crawl4AI crawler for: {url}")
        
        try:
            # Use async context manager properly - this will catch NotImplementedError at initialization
            # Wrap the entire async with block to catch NotImplementedError from Crawl4AI initialization
            try:
                async with AsyncWebCrawler(
                    headless=True,
                    verbose=False
                ) as crawler:
                    logger.info("Crawler initialized successfully")
                    logger.info(f"Starting crawl for: {url}")
                    # Use arun with just the URL parameter
                    crawl_result = await crawler.arun(url=url)
                    
                    # Log the result structure for debugging
                    logger.info(f"Crawl result type: {type(crawl_result)}")
                    if crawl_result:
                        logger.info(f"Crawl result attributes: {dir(crawl_result)}")
                        # Log available attributes
                        attrs_to_check = ['success', 'markdown', 'text', 'cleaned_html', 'html', 'metadata', 'status_code', 'error', 'error_message']
                        available_attrs = {attr: hasattr(crawl_result, attr) for attr in attrs_to_check}
                        logger.info(f"Available attributes: {available_attrs}")
                    
                    # Check if crawl was successful
                    success = True
                    if crawl_result is None:
                        success = False
                        error_msg = "Crawl4AI returned None result"
                    elif hasattr(crawl_result, 'success'):
                        success = bool(crawl_result.success)
                        if not success:
                            error_msg = getattr(crawl_result, 'error_message', None) or getattr(crawl_result, 'error', None) or "Crawl failed (success=False)"
                    elif hasattr(crawl_result, 'error') and crawl_result.error:
                        success = False
                        error_msg = str(crawl_result.error)
                    elif hasattr(crawl_result, 'error_message') and crawl_result.error_message:
                        success = False
                        error_msg = str(crawl_result.error_message)
                    else:
                        # Assume success if no error indicators
                        success = True
                    
                    if not success:
                        result["error"] = error_msg
                        logger.error(f"Crawl failed for {url}: {error_msg}")
                        return result
                    
                    # Extract content - try multiple attributes in order of preference
                    markdown_content = ""
                    raw_html_content = None
                    
                    # Try markdown first (best for LLM ingestion)
                    if hasattr(crawl_result, 'markdown') and crawl_result.markdown:
                        markdown_content = str(crawl_result.markdown).strip()
                        logger.info(f"Extracted markdown content: {len(markdown_content)} characters")
                    
                    # If no markdown, try text
                    if not markdown_content and hasattr(crawl_result, 'text') and crawl_result.text:
                        markdown_content = str(crawl_result.text).strip()
                        logger.info(f"Extracted text content: {len(markdown_content)} characters")
                    
                    # If still no content, try cleaned_html
                    if not markdown_content and hasattr(crawl_result, 'cleaned_html') and crawl_result.cleaned_html:
                        markdown_content = str(crawl_result.cleaned_html).strip()
                        logger.info(f"Extracted cleaned_html content: {len(markdown_content)} characters")
                    
                    # Get raw HTML if available
                    if hasattr(crawl_result, 'html') and crawl_result.html:
                        raw_html_content = str(crawl_result.html)
                    elif hasattr(crawl_result, 'cleaned_html') and crawl_result.cleaned_html:
                        raw_html_content = str(crawl_result.cleaned_html)
                    
                    if not markdown_content:
                        error_msg = "No content extracted from URL (markdown, text, and cleaned_html all empty)"
                        result["error"] = error_msg
                        logger.error(f"{error_msg} for {url}")
                        return result
                    
                    result["markdown"] = markdown_content
                    result["raw_html"] = raw_html_content
                    
                    # Extract metadata
                    metadata_dict = {}
                    if hasattr(crawl_result, 'metadata') and crawl_result.metadata:
                        if isinstance(crawl_result.metadata, dict):
                            metadata_dict = crawl_result.metadata
                        else:
                            try:
                                metadata_dict = dict(crawl_result.metadata) if hasattr(crawl_result.metadata, '__dict__') else {}
                            except:
                                metadata_dict = {}
                    
                    # Extract title from metadata or HTML
                    title = ""
                    if metadata_dict and isinstance(metadata_dict, dict):
                        title = metadata_dict.get("title", "") or metadata_dict.get("Title", "")
                    
                    # If no title in metadata, try to extract from HTML
                    if not title and raw_html_content:
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(raw_html_content, 'html.parser')
                            title_tag = soup.find('title')
                            if title_tag:
                                title = title_tag.get_text().strip()
                        except ImportError:
                            logger.debug("BeautifulSoup4 not available, skipping HTML title extraction")
                        except Exception as e:
                            logger.debug(f"Could not extract title from HTML: {e}")
                    
                    # Get status code
                    status_code = None
                    if hasattr(crawl_result, 'status_code'):
                        status_code = crawl_result.status_code
                    elif metadata_dict and isinstance(metadata_dict, dict):
                        status_code = metadata_dict.get("status_code") or metadata_dict.get("statusCode")
                    
                    # Determine content type
                    content_type = "text/html"
                    if is_pdf:
                        content_type = "application/pdf"
                    elif metadata_dict and isinstance(metadata_dict, dict):
                        content_type = metadata_dict.get("content_type") or metadata_dict.get("contentType") or metadata_dict.get("Content-Type") or "text/html"
                    
                    result["metadata"] = {
                        "title": title or url.split('/')[-1] if '/' in url else url,
                        "content_type": content_type,
                        "status_code": status_code,
                        "source_type": "pdf" if is_pdf else "web"
                    }
                    
                    if is_pdf:
                        result["metadata"]["filename"] = url.split('/')[-1] if '/' in url else ""
                        result["metadata"]["page_count"] = None  # Could be extracted if available
                    
                    logger.info(f"Successfully crawled {url}: extracted {len(markdown_content)} characters, title: {result['metadata']['title']}")
            except NotImplementedError as init_not_impl:
                import traceback
                tb_str = ''.join(traceback.format_exception(type(init_not_impl), init_not_impl, init_not_impl.__traceback__))
                error_details = str(init_not_impl) if str(init_not_impl) else repr(init_not_impl)
                error_msg = f"Crawl4AI initialization failed (NotImplementedError: {error_details}). Please run: playwright install chromium"
                logger.error(f"NotImplementedError during Crawl4AI initialization: {error_msg}\nTraceback:\n{tb_str}")
                result["error"] = error_msg
                return result
        except NotImplementedError as not_impl_error:
            # Handle NotImplementedError - this usually means Playwright browsers aren't installed
            error_details = str(not_impl_error) if str(not_impl_error) else "NotImplementedError (empty message)"
            logger.exception(f"NotImplementedError during crawl: {error_details}")
            error_msg = f"Crawl4AI NotImplementedError: Playwright browsers are not installed. Please run: playwright install chromium"
            result["error"] = error_msg
            return result
        except UnicodeEncodeError as unicode_error:
            # Windows console encoding issue - try to continue anyway
            error_msg = f"Encoding error (Windows console issue): {str(unicode_error)}. This may be a logging issue, but crawling might still work."
            result["error"] = error_msg
            logger.error(error_msg)
            return result
        except Exception as crawl_error:
            # Handle other errors during crawling
            error_type = type(crawl_error).__name__
            error_details = str(crawl_error)
            logger.exception(f"Error during crawl ({error_type}): {error_details}")
            if isinstance(crawl_error, NotImplementedError):
                error_msg = f"Crawl4AI NotImplementedError: Playwright browsers are not installed. Please run: playwright install chromium"
            else:
                error_msg = f"Crawl error ({error_type}): {error_details}"
            result["error"] = error_msg
            return result
                    
    except ValueError as e:
        error_msg = f"Invalid URL: {str(e)}"
        result["error"] = error_msg
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"Error crawling {url}: {str(e)}"
        result["error"] = error_msg
        logger.exception(error_msg)
    
    return result

