"""
Topic filtering module for policy-focused content filtering.
Determines if crawled content is relevant to AI governance and policy topics.
"""
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

# Policy-related keywords for content relevance detection
POLICY_KEYWORDS = [
    'artificial intelligence', 'ai governance', 'ai regulation', 'ai act',
    'risk management', 'compliance', 'regulatory', 'framework', 'guideline',
    'policy', 'legislation', 'regulation', 'standard', 'guidance', 'audit',
    'oversight', 'ethics', 'algorithmic', 'machine learning', 'ml governance',
    'data protection', 'privacy', 'transparency', 'accountability', 'bias',
    'discrimination', 'high-risk', 'prohibited', 'conformity assessment'
]

# Minimum keyword threshold for policy relevance
DEFAULT_POLICY_KEYWORD_THRESHOLD = 3

# Minimum content length to be considered (characters)
MIN_CONTENT_LENGTH = 100


def is_policy_relevant(
    content: str,
    threshold: int = DEFAULT_POLICY_KEYWORD_THRESHOLD
) -> Tuple[bool, float]:
    """
    Determine if content is relevant to AI governance and policy topics.
    
    Uses keyword-based heuristics to detect policy-relevant content.
    Returns both a boolean decision and a relevance score.
    
    Args:
        content: Text content to evaluate (markdown or plain text)
        threshold: Minimum number of policy keywords required (default: 3)
        
    Returns:
        Tuple of (is_relevant: bool, relevance_score: float)
        - is_relevant: True if content meets threshold
        - relevance_score: Number of policy keyword matches found
    """
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        return False, 0.0
    
    content_lower = content.lower()
    
    # Count policy keyword matches
    keyword_matches = sum(1 for keyword in POLICY_KEYWORDS if keyword in content_lower)
    
    # Determine relevance
    is_relevant = keyword_matches >= threshold
    
    return is_relevant, float(keyword_matches)


def get_relevance_score(content: str) -> float:
    """
    Get a relevance score for content (0.0 to 1.0).
    
    Args:
        content: Text content to evaluate
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        return 0.0
    
    content_lower = content.lower()
    keyword_matches = sum(1 for keyword in POLICY_KEYWORDS if keyword in content_lower)
    
    # Normalize to 0.0-1.0 range (max score = number of keywords)
    max_possible = len(POLICY_KEYWORDS)
    if max_possible == 0:
        return 0.0
    
    return min(keyword_matches / max_possible, 1.0)


class PolicyRelevanceScorer:
    """
    Policy relevance scorer with configurable threshold.
    
    Can be extended in the future with ML-based classification.
    """
    
    def __init__(self, threshold: int = DEFAULT_POLICY_KEYWORD_THRESHOLD):
        """
        Initialize policy relevance scorer.
        
        Args:
            threshold: Minimum keyword matches required for relevance
        """
        self.threshold = threshold
    
    def score(self, content: str) -> Tuple[bool, float]:
        """
        Score content for policy relevance.
        
        Args:
            content: Text content to score
            
        Returns:
            Tuple of (is_relevant: bool, score: float)
        """
        return is_policy_relevant(content, self.threshold)
    
    def is_relevant(self, content: str) -> bool:
        """
        Check if content is policy-relevant.
        
        Args:
            content: Text content to check
            
        Returns:
            True if content is policy-relevant
        """
        is_rel, _ = self.score(content)
        return is_rel


class ContentQualityFilter:
    """
    Filters low-quality content (spam, boilerplate, etc.).
    """
    
    def __init__(self, min_length: int = MIN_CONTENT_LENGTH):
        """
        Initialize content quality filter.
        
        Args:
            min_length: Minimum content length in characters
        """
        self.min_length = min_length
    
    def is_high_quality(self, content: str) -> bool:
        """
        Check if content meets quality thresholds.
        
        Args:
            content: Text content to check
            
        Returns:
            True if content is high quality
        """
        if not content:
            return False
        
        content_stripped = content.strip()
        
        # Check minimum length
        if len(content_stripped) < self.min_length:
            return False
        
        # Basic spam/boilerplate detection (can be extended)
        # Check for excessive repetition
        words = content_stripped.split()
        if len(words) < 10:
            return False
        
        # Check for reasonable word diversity
        unique_words = len(set(word.lower() for word in words))
        if unique_words < len(words) * 0.3:  # Less than 30% unique words
            return False
        
        return True

