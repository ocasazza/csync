# -*- coding: utf-8 -*-

"""
Pull operations for csync.

This module provides functionality for pulling Confluence pages to local storage.
"""

import logging
import io
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from tqdm import tqdm
from src.fs import LocalStorage
from atlassian import Confluence

logger = logging.getLogger(__name__)

# Configure tqdm to work properly with terminal output
tqdm.monitor_interval = 0  # Disable monitor thread to avoid issues


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

        # Check if the page exists locally and if it has been renamed
        local_dir = storage.get_page_dir_by_id(page_id)
        if local_dir:
            metadata = storage.get_page_metadata(local_dir)
            if metadata and metadata['title'] != page['title']:
                # Handle rename
                logger.info(f"Detected renamed page: {metadata['title']} -> {page['title']}")
                local_dir = self.handle_renamed_page(page_id, page['title'], storage)

        # Pull the page itself
        page_dir = self.pull_page(page_id, storage, parent_dir, metadata=page)

        # Pull children if recursive mode is enabled
        if self.recurse:
            self.pull_children(page_id, storage, page_dir)

        return page_dir

    def collect_all_child_pages(self, page_id: str) -> List[Dict]:
        """
        Recursively collect all child pages of a page.
        
        Args:
            page_id: The ID of the parent page.
            
        Returns:
            A list of all child pages.
        """
        result = []
        
        # Get direct child pages
        children = self.client.get_child_pages(page_id=page_id)
        result.extend(children)
        
        # If recursive mode is enabled, get children of children
        if self.recurse:
            for child in children:
                result.extend(self.collect_all_child_pages(child['id']))
                
        return result
    
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

        # Get all child pages (direct children only, we'll handle recursion differently)
        # Convert to list to ensure we can get the length
        children = list(self.client.get_child_pages(page_id=page_id))
        
        if not children:
            return
            
        # Process each child page
        for i, child in enumerate(children):
            # Use a simple progress message instead of tqdm
            if self.show_progress:
                # Get the parent page title
                parent_title = "Unknown"
                try:
                    parent_page = self.client.get_page_by_id(page_id, expand="title")
                    parent_title = parent_page.get('title', 'Unknown')
                except:
                    pass
                
                # Clear the line and write the progress with parent info
                sys.stdout.write(f"\rPulling child pages of '{parent_title}': {i+1}/{len(children)}")
                sys.stdout.flush()
                
            # Pull the page and its children
            child_dir = self.pull_page(child['id'], storage, parent_dir)
            
            # Recursively pull children if needed
            if self.recurse:
                self.pull_children(child['id'], storage, child_dir)
                
        # Print a newline after we're done
        if self.show_progress and children:
            # Get the parent page title if we haven't already
            if 'parent_title' not in locals():
                parent_title = "Unknown"
                try:
                    parent_page = self.client.get_page_by_id(page_id, expand="title")
                    parent_title = parent_page.get('title', 'Unknown')
                except Exception as e:
                    logger.debug(f"Failed to get parent title: {e}")
                    
            sys.stdout.write(f"\rPulling child pages of '{parent_title}': {len(children)}/{len(children)} - Complete\n")
            sys.stdout.flush()

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
