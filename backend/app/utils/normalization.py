"""
Text normalization utility for search functionality.

Normalizes text by:
- Converting to lowercase (with Unicode casefold support)
- Trimming leading/trailing whitespace
- Collapsing consecutive whitespace to single space
- Stripping common punctuation characters
- Preserving alphanumerics and Thai characters
"""

import re
import unicodedata


# Punctuation characters to strip (as per US-N1 requirements)
PUNCTUATION_TO_STRIP = r'[-_.,/()\[\]:;\'"]'


def normalize_search_text(text: str | None) -> str:
    """
    Normalize text for search indexing and querying.
    
    Rules:
    1. Lowercase (ASCII + Unicode casefold)
    2. Trim leading/trailing whitespace
    3. Collapse consecutive whitespace to single space
    4. Strip common punctuation: - _ . , / ( ) [ ] : ; ' "
    5. Preserve alphanumerics and Thai characters
    
    Args:
        text: Input text to normalize (can be None)
        
    Returns:
        Normalized string (empty string if input is None or empty)
        
    Examples:
        >>> normalize_search_text("K-USX")
        'kusx'
        >>> normalize_search_text("  Kasikorn   US   Equity  ")
        'kasikorn us equity'
        >>> normalize_search_text("K.USX")
        'kusx'
        >>> normalize_search_text("กสิกร US Equity")
        'กสิกร us equity'
    """
    if not text:
        return ""
    
    # Step 1: Convert to lowercase with Unicode casefold
    normalized = text.casefold()
    
    # Step 2: Strip specified punctuation characters
    normalized = re.sub(PUNCTUATION_TO_STRIP, '', normalized)
    
    # Step 3: Collapse consecutive whitespace to single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Step 4: Trim leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


def normalize_search_text_idempotent(text: str | None) -> str:
    """
    Normalize text (idempotent version).
    
    Applying normalization twice produces the same result as applying it once.
    This is useful for ensuring consistency.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized string
    """
    return normalize_search_text(text)

