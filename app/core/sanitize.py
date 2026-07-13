"""
Sanaie Platform — Input Sanitization Utilities
Prevents XSS and injection attacks by cleaning user-provided text.
"""
import re
import html
from typing import Optional


def sanitize_text(text: Optional[str], max_length: int = None) -> Optional[str]:
    """
    Sanitize user input text:
    - Escapes HTML special characters
    - Strips leading/trailing whitespace
    - Optionally truncates to max_length
    """
    if text is None:
        return None

    # Escape HTML entities (&, <, >, ", ')
    cleaned = html.escape(text.strip())

    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_search(query: Optional[str]) -> Optional[str]:
    """Sanitize search queries — remove SQL-like injection patterns."""
    if query is None:
        return None

    # Remove common SQL injection patterns
    cleaned = re.sub(r"[;'\"\-\-\/\*]", "", query.strip())
    return cleaned[:200]  # Cap search length


def strip_html_tags(text: Optional[str]) -> Optional[str]:
    """Remove all HTML tags from text."""
    if text is None:
        return None
    return re.sub(r"<[^>]+>", "", text)
