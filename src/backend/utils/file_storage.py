"""File storage utilities for saving and loading job data."""

import os
from pathlib import Path


def save_file(content: str, filepath: str) -> None:
    """
    Save content to a file, creating directories if needed.
    
    Args:
        content: The content to save
        filepath: The path where the file should be saved
        
    Raises:
        IOError: If the file cannot be written
        
    Examples:
        >>> save_file("<html>...</html>", "data/jobs/raw/acme-corp/123.html")
        >>> save_file("# Job Description", "data/jobs/cleaned/acme-corp/123.md")
    """
    # Create parent directories if they don't exist
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Write the content to the file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def load_file(filepath: str) -> str:
    """
    Load content from a file.
    
    Args:
        filepath: The path to the file to load
        
    Returns:
        The file content as a string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If the file cannot be read
        
    Examples:
        >>> html = load_file("data/jobs/raw/acme-corp/123.html")
        >>> markdown = load_file("data/jobs/cleaned/acme-corp/123.md")
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def file_exists(filepath: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        filepath: The path to check
        
    Returns:
        True if the file exists, False otherwise
        
    Examples:
        >>> file_exists("data/jobs/raw/acme-corp/123.html")
        True
    """
    return os.path.exists(filepath)
