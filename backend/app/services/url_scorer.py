"""
URL scoring module for policy-focused crawling.
Provides priority scoring for URLs based on policy relevance indicators.
"""
import logging
import re
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Policy-related keywords that indicate high relevance
POLICY_KEYWORDS = [
    'ai-act', 'artificial-intelligence', 'ai-regulation', 'governance',
    'risk-management', 'compliance', 'guidelines', 'regulation', 'regulatory',
    'framework', 'policy', 'policies', 'legislation', 'act', 'directive',
    'standard', 'standards', 'guidance', 'audit', 'oversight'
]

# Policy-related path patterns that indicate high relevance
POLICY_PATH_PATTERNS = [
    r'/legislation/', r'/regulation/', r'/regulations/', r'/policy/',
    r'/policies/', r'/standards/', r'/guidance/', r'/guidelines/',
    r'/compliance/', r'/governance/', r'/framework/', r'/acts/',
    r'/directives/', r'/rules/', r'/law/', r'/laws/'
]

# Low-value path patterns that indicate low relevance
LOW_VALUE_PATH_PATTERNS = [
    r'/news/', r'/press/', r'/blog/', r'/blogs/', r'/jobs/',
    r'/media/', r'/events/', r'/event/', r'/calendar/', r'/contact/',
    r'/about/', r'/team/', r'/careers/', r'/privacy/', r'/terms/',
    r'/cookie/', r'/sitemap', r'/search', r'/login', r'/register'
]

# High-authority domain patterns
AUTHORITY_DOMAINS = [
    '.gov', '.eu', '.org', '.edu', '.mil'
]


def score_url(
    url: str,
    source_domain: Optional[str] = None,
    title: Optional[str] = None,
    snippet: Optional[str] = None
) -> float:
    """
    Score a URL based on policy relevance indicators.
    
    Higher scores indicate higher priority for crawling.
    
    Scoring factors:
    - Policy keywords in URL: +2.0 points per keyword
    - Policy path patterns: +3.0 points per match
    - Low-value paths: -2.0 points per match
    - Authority domains (.gov, .eu, .org): +1.0 points
    - Same-domain bonus: +1.0 points
    - Policy keywords in title/snippet: +1.0 points per keyword
    
    Args:
        url: URL to score
        source_domain: Optional source domain for same-domain bonus
        title: Optional page title from search results
        snippet: Optional snippet from search results
        
    Returns:
        Priority score (float, can be negative)
    """
    score = 0.0
    url_lower = url.lower()
    
    # Check for policy keywords in URL
    keyword_matches = sum(1 for keyword in POLICY_KEYWORDS if keyword in url_lower)
    score += keyword_matches * 2.0
    
    # Check for policy path patterns
    parsed = urlparse(url)
    url_path = parsed.path.lower()
    
    for pattern in POLICY_PATH_PATTERNS:
        if re.search(pattern, url_path):
            score += 3.0
            break  # Only count once
    
    # Check for low-value paths (penalty)
    for pattern in LOW_VALUE_PATH_PATTERNS:
        if re.search(pattern, url_path):
            score -= 2.0
            break  # Only count once
    
    # Authority domain bonus
    domain = parsed.netloc.lower()
    if any(auth_domain in domain for auth_domain in AUTHORITY_DOMAINS):
        score += 1.0
    
    # Same-domain bonus
    if source_domain and source_domain.lower() in domain:
        score += 1.0
    
    # Title and snippet scoring (if available from search results)
    if title:
        title_lower = title.lower()
        title_keywords = sum(1 for keyword in POLICY_KEYWORDS if keyword in title_lower)
        score += title_keywords * 1.0
    
    if snippet:
        snippet_lower = snippet.lower()
        snippet_keywords = sum(1 for keyword in POLICY_KEYWORDS if keyword in snippet_lower)
        score += snippet_keywords * 1.0
    
    return score

