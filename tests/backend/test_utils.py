"""Tests for utility functions."""

import os
import tempfile
from pathlib import Path

import pytest

from backend.utils.file_storage import file_exists, load_file, save_file
from backend.utils.slug import create_slug


class TestSlugUtils:
    """Tests for slug generation utilities."""

    def test_create_slug_basic(self):
        """Test basic slug creation."""
        assert create_slug("Acme Corporation") == "acme-corporation"

    def test_create_slug_with_special_chars(self):
        """Test slug creation with special characters."""
        assert create_slug("AT&T Inc.") == "at-t-inc"
        assert create_slug("Google, LLC") == "google-llc"

    def test_create_slug_with_spaces(self):
        """Test slug creation with multiple spaces."""
        assert create_slug("Big   Tech   Company") == "big-tech-company"

    def test_create_slug_already_lowercase(self):
        """Test slug creation with already lowercase text."""
        assert create_slug("acme-corp") == "acme-corp"

    def test_create_slug_with_numbers(self):
        """Test slug creation with numbers."""
        assert create_slug("Company 123") == "company-123"

    def test_create_slug_unicode(self):
        """Test slug creation with unicode characters."""
        assert create_slug("Café Résumé") == "cafe-resume"


class TestFileStorageUtils:
    """Tests for file storage utilities."""

    def test_save_and_load_file(self):
        """Test saving and loading a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            content = "Hello, World!"
            
            save_file(content, filepath)
            loaded_content = load_file(filepath)
            
            assert loaded_content == content

    def test_save_file_creates_directories(self):
        """Test that save_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "nested", "dir", "test.txt")
            content = "Test content"
            
            save_file(content, filepath)
            
            assert os.path.exists(filepath)
            assert load_file(filepath) == content

    def test_save_file_overwrites_existing(self):
        """Test that save_file overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            
            save_file("First content", filepath)
            save_file("Second content", filepath)
            
            assert load_file(filepath) == "Second content"

    def test_load_file_not_found(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_file("/nonexistent/path/file.txt")

    def test_file_exists_true(self):
        """Test file_exists returns True for existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            save_file("content", filepath)
            
            assert file_exists(filepath) is True

    def test_file_exists_false(self):
        """Test file_exists returns False for non-existent file."""
        assert file_exists("/nonexistent/path/file.txt") is False

    def test_save_file_with_unicode(self):
        """Test saving and loading file with unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "unicode.txt")
            content = "Hello 世界 🌍"
            
            save_file(content, filepath)
            loaded_content = load_file(filepath)
            
            assert loaded_content == content

    def test_save_file_multiline(self):
        """Test saving and loading multiline content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "multiline.txt")
            content = "Line 1\nLine 2\nLine 3"
            
            save_file(content, filepath)
            loaded_content = load_file(filepath)
            
            assert loaded_content == content
