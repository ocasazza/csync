# -*- coding: utf-8 -*-

"""
File system operations for csync.

This module provides functions for interacting with the local file system.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class LocalStorage:
    """Handles local file system operations for Confluence pages."""

    def __init__(self, base_dir: str):
        """
        Initialize the local storage.

        Args:
            base_dir: The base directory for storing pages.
        """
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / ".csync"

        # Create the base directory if it doesn't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or load the ID-to-path mapping
        self.id_map_file = self.metadata_dir / "id_map.json"
        if self.id_map_file.exists():
            with open(self.id_map_file, "r", encoding="utf-8") as f:
                self.id_map = json.load(f)
        else:
            self.id_map = {}

    def get_page_dir_by_id(self, page_id: str) -> Optional[Path]:
        """
        Get the directory for a page by its ID.

        Args:
            page_id: The ID of the page.

        Returns:
            The path to the page directory, or None if not found.
        """
        # Check the ID-to-path mapping
        if page_id in self.id_map:
            path = Path(self.id_map[page_id])
            if path.exists():
                return path

        # If not found in map or path doesn't exist, search all metadata files
        for metadata_file in self.base_dir.glob("**/metadata.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    if metadata.get("id") == page_id:
                        # Update the map with the found path
                        path = metadata_file.parent
                        self.update_id_map(page_id, str(path))
                        return path
            except:
                continue

        return None

    def update_id_map(self, page_id: str, path: str) -> None:
        """
        Update the ID-to-path mapping.

        Args:
            page_id: The ID of the page.
            path: The path to the page directory.
        """
        self.id_map[page_id] = path
        with open(self.id_map_file, "w", encoding="utf-8") as f:
            json.dump(self.id_map, f, indent=2, ensure_ascii=False)

    def get_page_dir(self, title: str) -> Path:
        """
        Get the directory for a page.

        Args:
            page_id: The ID of the page.
            title: The title of the page.

        Returns:
            The path to the page directory.
        """
        # Use a sanitized version of the title as the directory name
        safe_title = self._sanitize_filename(title)

        # Create a directory with the sanitized title
        page_dir = self.base_dir / safe_title
        return page_dir

    def get_child_dir(self, parent_dir: Path, title: str) -> Path:
        """
        Get the directory for a child page.

        Args:
            parent_dir: The directory of the parent page.
            page_id: The ID of the child page.
            title: The title of the child page.

        Returns:
            The path to the child page directory.
        """
        # Use a sanitized version of the title as the directory name
        safe_title = self._sanitize_filename(title)

        # Create a directory for the child page
        child_dir = parent_dir / "children" / safe_title
        return child_dir

    def save_page_content(self, page_dir: Path, content: str) -> None:
        """
        Save the content of a page.

        Args:
            page_dir: The directory of the page.
            content: The HTML content of the page.
        """
        # Create the page directory if it doesn't exist
        page_dir.mkdir(parents=True, exist_ok=True)

        # Write the content to a file
        with open(page_dir / "content.html", "w", encoding="utf-8") as f:
            f.write(content)

    def save_page_metadata(self, page_dir: Path, metadata: Dict[str, Any]) -> None:
        """
        Save the metadata of a page.

        Args:
            page_dir: The directory of the page.
            metadata: The metadata of the page.
        """
        # Create the page directory if it doesn't exist
        page_dir.mkdir(parents=True, exist_ok=True)

        # Write the metadata to a file
        with open(page_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def get_page_metadata(self, page_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Get the metadata of a page.

        Args:
            page_dir: The directory of the page.

        Returns:
            The metadata of the page, or None if not found.
        """
        metadata_file = page_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_page_content(self, page_dir: Path) -> Optional[str]:
        """
        Get the content of a page.

        Args:
            page_dir: The directory of the page.

        Returns:
            The HTML content of the page, or None if not found.
        """
        content_file = page_dir / "content.html"
        if not content_file.exists():
            return None

        with open(content_file, "r", encoding="utf-8") as f:
            return f.read()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to be safe for the file system.

        Args:
            filename: The filename to sanitize.

        Returns:
            A sanitized filename.
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Limit the length of the filename
        if len(filename) > 255:
            filename = filename[:255]

        return filename
