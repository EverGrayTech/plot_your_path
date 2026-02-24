"""Slug generation utilities."""

from slugify import slugify


def create_slug(text: str) -> str:
    """
    Create a URL-friendly slug from text.
    
    Args:
        text: The text to convert to a slug
        
    Returns:
        A lowercase, hyphenated slug
        
    Examples:
        >>> create_slug("Acme Corporation")
        'acme-corporation'
        >>> create_slug("Google LLC")
        'google-llc'
        >>> create_slug("AT&T Inc.")
        'att-inc'
    """
    return slugify(text, lowercase=True, separator="-")
