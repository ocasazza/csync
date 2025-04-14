# -*- coding: utf-8 -*-

"""
Pull operations for csync.

This module provides functionality for pulling Confluence pages to local storage.
"""

import logging
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from src.fs import LocalStorage
from atlassian import Confluence

logger = logging.getLogger(__name__)


class PullOperations:
    """Operations for pulling Confluence pages to local storage."""
    
    def __init__(
        self,
        client: Confluence,
        show_progress: bool = True,
        recurse: bool = True,
        dry_run: bool = False,
    ):
        """
        Initialize the pull operations.

        Args:
            client: The Confluence client to use.
            show_progress: Whether to show progress bars.
            recurse: Whether to recursively process child pages.
            dry_run: Whether to perform a dry run (no changes).
        """
        self.client = client
        self.show_progress = show_progress
        self.recurse = recurse
        self.dry_run = dry_run

    def pull_page(
        self,
        page_id: str,
        storage: LocalStorage,
        parent_dir: Optional[Path],
        metadata: Optional[dict] = None
    ) -> Path:
        """
        Pull a single page from Confluence.

        Args:
            page_id: The ID of the page to pull.
            storage: The local storage to save to.
            parent_dir: The parent directory to save in.
            metadata: Optional pre-fetched metadata for the page.

        Returns:
            The path to the page directory.
        """
        if self.dry_run:
            logger.info(f"Would pull page {page_id}")
            return Path()

        # If metadata wasn't provided, fetch it
        if not metadata:
            page = self.client.get_page_by_id(
                page_id,
                expand="body.storage,version,space,metadata.properties.editor,metadata.properties.emoji_title_published"
            )
            metadata = page

        # Get the page content
        content = metadata['body']['storage']['value']

        # Determine the page directory
        if parent_dir:
            page_dir = storage.get_child_dir(parent_dir, metadata['title'])
        else:
            page_dir = storage.get_page_dir(metadata['title'])

        # Save the content and metadata
        storage.save_page_content(page_dir, content)
        storage.save_page_metadata(page_dir, metadata)

        # Pull attachments
        self.pull_attachments(page_id, page_dir)

        return page_dir

    def pull_page_tree(
        self, page_id: str, storage: LocalStorage, parent_dir: Optional[Path] = None
    ) -> Path:
        """
        Pull a page and all its children from Confluence.

        Args:
            page_id: The ID of the page to pull.
            storage: The local storage to save to.
            parent_dir: The parent directory to save in.

        Returns:
            The path to the page directory.
        """
        # Get the page with all necessary expansions
        page = self.client.get_page_by_id(
            page_id,
            expand="body.storage,version,space,metadata.properties.editor,metadata.properties.emoji_title_published,children.page"
        )

        # Pull the page itself
        page_dir = self.pull_page(page_id, storage, parent_dir)

        # Pull children if recursive mode is enabled
        if self.recurse:
            self.pull_children(page_id, storage, page_dir)

        return page_dir

    def pull_children(
        self, page_id: str, storage: LocalStorage, parent_dir: Path
    ) -> None:
        """
        Pull all child pages of a page.

        Args:
            page_id: The ID of the parent page.
            storage: The local storage to save to.
            parent_dir: The parent directory to save in.
        """
        if self.dry_run:
            logger.info(f"Would pull children of page {page_id}")
            return

        # Get all child pages
        children = self.client.get_page_child_by_type(page_id, type='page')

        if not children or 'results' not in children or not children['results']:
            return

        # Create a progress bar if enabled
        if self.show_progress:
            children_iter = tqdm(
                children['results'],
                desc="Pulling child pages",
                unit="page"
            )
        else:
            children_iter = children['results']

        # Process each child page
        for child in children_iter:
            self.pull_page_tree(child['id'], storage, parent_dir)

    def handle_renamed_page(
        self, page_id: str, new_title: str, storage: LocalStorage
    ) -> Path:
        """
        Handle a page that has been renamed.

        Args:
            page_id: The ID of the page.
            new_title: The new title of the page.
            storage: The local storage instance.

        Returns:
            The path to the renamed page directory.
        """
        # Find the current directory for this page ID
        current_dir = storage.get_page_dir_by_id(page_id)

        if not current_dir:
            # Page not found locally, treat as new
            return storage.get_page_dir(new_title)

        # Get the current title from metadata
        metadata = storage.get_page_metadata(current_dir)
        old_title = metadata['title']

        # Update the metadata with the new title
        metadata['title'] = new_title
        storage.save_page_metadata(current_dir, metadata)

        # Determine if this is a child page
        is_child = "children" in str(current_dir)

        # Get the appropriate parent directory
        if is_child:
            parent_dir = current_dir.parent.parent  # Go up two levels: children/old_name -> parent
            new_dir = parent_dir / "children" / storage._sanitize_filename(new_title)
        else:
            parent_dir = current_dir.parent
            new_dir = parent_dir / storage._sanitize_filename(new_title)

        # If the new directory already exists, handle it
        if new_dir.exists() and new_dir != current_dir:
            # Create a unique name by appending the page ID
            new_dir = parent_dir / f"{storage._sanitize_filename(new_title)}_{page_id}"

        # Only rename if the directory name would actually change
        if current_dir != new_dir:
            # Create parent directories if needed
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            current_dir.rename(new_dir)
            logger.info(
                f"Renamed directory from '{current_dir.name}' to '{new_dir.name}'"
                " to match remote title change"
            )

        # Update the ID map
        storage.update_id_map(page_id, str(new_dir))

        return new_dir

    def pull_attachments(
        self, page_id: str, page_dir: Path
    ) -> None:
        """
        Pull the attachments of a page.

        Args:
            page_id: The ID of the page.
            storage: The local storage to save to.
            page_dir: The page directory.
        """
        # Create the attachments directory
        attachments_dir = page_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            logger.info(f"Would download attachments for page {page_id}")
            return

        # Use the download_attachments_from_page method to download everything
        # This is more reliable than downloading individual attachments
        try:
            # Download all attachments to the attachments directory
            self.client.download_attachments_from_page(page_id, str(attachments_dir))
            logger.info(f"Downloaded attachments for page {page_id}")

        except Exception as e:
            logger.error(f"Failed to download attachments: {e}")
