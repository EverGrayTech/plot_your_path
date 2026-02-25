"""File storage utilities for saving and loading job data."""

import os
from pathlib import Path


def _resolve_path(filepath: str) -> str:
    """
    Resolve a file path to an absolute path.

    Relative paths are resolved under ``settings.data_root`` so that all job
    files land in the configured data directory (outside the repo).  Absolute
    paths are returned unchanged.

    Legacy paths that begin with ``data/`` have that prefix stripped before
    prepending the data root, so callers using the old ``data/jobs/raw/…``
    convention continue to work transparently.

    Args:
        filepath: An absolute or relative path string.

    Returns:
        Absolute path string.
    """
    if os.path.isabs(filepath):
        return filepath

    # Import here to avoid circular imports at module load time
    from backend.config import settings

    # Strip leading "data/" prefix (legacy convention) so the final path is
    # $DATA_ROOT/jobs/raw/… rather than $DATA_ROOT/data/jobs/raw/…
    rel = filepath.removeprefix("data/")
    return os.path.join(settings.data_root, rel)


def file_exists(filepath: str) -> bool:
    """
    Check if a file exists.

    Args:
        filepath: The path to check (absolute or relative to data_root).

    Returns:
        True if the file exists, False otherwise.

    Examples:
        >>> file_exists("data/jobs/raw/acme-corp/123.html")
        True
    """
    return os.path.exists(_resolve_path(filepath))


def load_file(filepath: str) -> str:
    """
    Load content from a file.

    Args:
        filepath: The path to the file to load (absolute or relative to data_root).

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        IOError: If the file cannot be read.

    Examples:
        >>> html = load_file("data/jobs/raw/acme-corp/123.html")
        >>> markdown = load_file("data/jobs/cleaned/acme-corp/123.md")
    """
    resolved = _resolve_path(filepath)
    with open(resolved, "r", encoding="utf-8") as f:
        return f.read()


def save_file(content: str, filepath: str) -> str:
    """
    Save content to a file, creating directories if needed.

    Args:
        content: The content to save.
        filepath: The destination path (absolute or relative to data_root).

    Returns:
        The absolute path where the file was saved.

    Raises:
        IOError: If the file cannot be written.

    Examples:
        >>> save_file("<html>...</html>", "data/jobs/raw/acme-corp/123.html")
        >>> save_file("# Job Description", "data/jobs/cleaned/acme-corp/123.md")
    """
    resolved = _resolve_path(filepath)
    Path(resolved).parent.mkdir(parents=True, exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as f:
        f.write(content)
    return resolved
