# -*- coding: utf-8 -*-

"""
Sync engine for csync.

This module provides the core functionality for syncing Confluence pages.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from src.api.client import ConfluenceClient
from src.storage.fs import LocalStorage

logger = logging.getLogger(__name__)


class SyncEngine:
    """Engine for syncing Confluence pages with local storage."""

    def __init__(
        self,
        client: ConfluenceClient,
        show_progress: bool = True,
        recurse: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize the sync engine.
        
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
    
    def pull(self, source: str, destination: str) -> None:
        """
        Pull Confluence pages to local storage.
        
        Args:
            source: The URL of the Confluence page or space to pull from.
            destination: The local directory to save the pages to.
        """
        # Parse the source URL to get page ID or space key
        parsed = self.client.parse_page_url(source)
        
        # Initialize local storage
        storage = LocalStorage(destination)
        
        if parsed["type"] == "page" and parsed["page_id"]:
            # Pull a single page and its children
            self._pull_page_tree(
                page_id=parsed["page_id"],
                storage=storage,
                parent_dir=None
            )
        elif parsed["type"] == "space" and parsed["space_key"]:
            # Pull an entire space
            self._pull_space(
                space_key=parsed["space_key"],
                storage=storage
            )
        else:
            raise ValueError(
                f"Invalid source URL: {source}. "
                "Must be a Confluence page or space URL."
            )
    
    def push(self, source: str, destination: str) -> None:
        """
        Push local pages to Confluence.
        
        Args:
            source: The local directory containing the pages to push.
            destination: The URL of the Confluence page or space to push to.
        """
        # Parse the destination URL to get page ID or space key
        parsed = self.client.parse_page_url(destination)
        
        # Initialize local storage
        storage = LocalStorage(source)
        
        if parsed["type"] == "page" and parsed["page_id"]:
            # Push to a specific page as parent
            self._push_to_page(
                parent_id=parsed["page_id"],
                storage=storage,
                local_dir=Path(source)
            )
        elif parsed["type"] == "space" and parsed["space_key"]:
            # Push to a space
            self._push_to_space(
                space_key=parsed["space_key"],
                storage=storage,
                local_dir=Path(source)
            )
        else:
            raise ValueError(
                f"Invalid destination URL: {destination}. "
                "Must be a Confluence page or space URL."
            )
    
    def _pull_page_tree(
        self,
        page_id: str,
        storage: LocalStorage,
        parent_dir: Optional[Path] = None
    ) -> Path:
        """
        Pull a page and its children recursively.
        
        Args:
            page_id: The ID of the page to pull.
            storage: The local storage to save to.
            parent_dir: The parent directory, if any.
            
        Returns:
            The path to the page directory.
        """
        # Get the page from Confluence
        page = self.client.get_page(page_id)
        title = page["title"]
        
        # Determine the page directory
        if parent_dir is None:
            page_dir = storage.get_page_dir(page_id, title)
        else:
            page_dir = storage.get_child_dir(parent_dir, page_id, title)
        
        # Check if the page has been modified
        local_metadata = storage.get_page_metadata(page_dir)
        remote_version = page["version"]["number"]
        
        if (local_metadata and
                local_metadata.get("version") == remote_version and
                not self.dry_run):
            logger.info(f"Page '{title}' is up to date, skipping")
            
            # Still process children if recursion is enabled
            if self.recurse:
                self._pull_children(page_id, storage, page_dir)
            
            return page_dir
        
        # Page has been modified or doesn't exist locally
        if not self.dry_run:
            # Get the page content
            content = self.client.get_page_content(page_id)
            
            # Save the page content
            storage.save_page_content(page_dir, content)
            
            # Save the page metadata
            metadata = {
                "id": page_id,
                "title": title,
                "version": remote_version,
                "space_key": page["space"]["key"],
                "last_modified": page["version"]["when"],
                "last_modified_by": page["version"]["by"]["displayName"]
            }
            storage.save_page_metadata(page_dir, metadata)
            
            # Pull attachments
            self._pull_attachments(page_id, storage, page_dir)
        
        # Log the action
        action = "Would pull" if self.dry_run else "Pulled"
        logger.info(f"{action} page '{title}' (version {remote_version})")
        
        # Process children if recursion is enabled
        if self.recurse:
            self._pull_children(page_id, storage, page_dir)
        
        return page_dir
    
    def _pull_children(
        self, page_id: str, storage: LocalStorage, parent_dir: Path
    ) -> None:
        """
        Pull the children of a page.
        
        Args:
            page_id: The ID of the parent page.
            storage: The local storage to save to.
            parent_dir: The parent directory.
        """
        # Get the children of the page
        children = self.client.get_page_children(page_id)
        
        if not children:
            return
        
        # Create a progress bar if enabled
        if self.show_progress:
            children_iter = tqdm(
                children,
                desc=f"Processing {len(children)} child pages",
                unit="page"
            )
        else:
            children_iter = children
        
        # Process each child
        for child in children_iter:
            self._pull_page_tree(
                page_id=child["id"],
                storage=storage,
                parent_dir=parent_dir
            )
    
    def _pull_attachments(
        self, page_id: str, storage: LocalStorage, page_dir: Path
    ) -> None:
        """
        Pull the attachments of a page.
        
        Args:
            page_id: The ID of the page.
            storage: The local storage to save to.
            page_dir: The page directory.
        """
        # Get the attachments of the page
        attachments = self.client.get_attachments(page_id)
        
        if not attachments:
            return
        
        # Create a progress bar if enabled
        if self.show_progress:
            attachments_iter = tqdm(
                attachments,
                desc=f"Downloading {len(attachments)} attachments",
                unit="file"
            )
        else:
            attachments_iter = attachments
        
        # Process each attachment
        for attachment in attachments_iter:
            attachment_id = attachment["id"]
            filename = attachment["title"]
            
            # Download the attachment
            attachment_path = storage.get_attachment_path(page_dir, filename)
            os.makedirs(os.path.dirname(attachment_path), exist_ok=True)
            
            if not self.dry_run:
                self.client.download_attachment(
                    page_id, attachment_id, str(attachment_path)
                )
            
            # Log the action
            action = "Would download" if self.dry_run else "Downloaded"
            logger.debug(f"{action} attachment '{filename}'")
    
    def _pull_space(self, space_key: str, storage: LocalStorage) -> None:
        """
        Pull an entire space.
        
        Args:
            space_key: The key of the space to pull.
            storage: The local storage to save to.
        """
        # Get the root pages of the space
        # This is a simplified approach; in a real implementation,
        # you would need to handle pagination for spaces with many pages
        space_content = self.client.client.get_space_content(
            space_key=space_key,
            expand="body.view",
            limit=100
        )
        
        root_pages = space_content.get("page", {}).get("results", [])
        
        if not root_pages:
            logger.warning(f"No pages found in space {space_key}")
            return
        
        # Create a progress bar if enabled
        if self.show_progress:
            pages_iter = tqdm(
                root_pages,
                desc=f"Processing {len(root_pages)} root pages",
                unit="page"
            )
        else:
            pages_iter = root_pages
        
        # Process each root page
        for page in pages_iter:
            self._pull_page_tree(
                page_id=page["id"],
                storage=storage
            )
    
    def _push_to_page(
        self, parent_id: str, storage: LocalStorage, local_dir: Path
    ) -> None:
        """
        Push local pages to a Confluence page as parent.
        
        Args:
            parent_id: The ID of the parent page in Confluence.
            storage: The local storage to read from.
            local_dir: The local directory containing the pages.
        """
        # Get the parent page to determine the space
        parent_page = self.client.get_page(parent_id)
        space_key = parent_page["space"]["key"]
        
        # Get the metadata for the local directory
        metadata = storage.get_page_metadata(local_dir)
        
        if not metadata:
            # This is a directory without metadata, treat each subdirectory
            # as a separate page to push
            for item in local_dir.iterdir():
                if item.is_dir() and item.name != ".csync":
                    self._push_directory(
                        space_key=space_key,
                        storage=storage,
                        local_dir=item,
                        parent_id=parent_id
                    )
        else:
            # This is a page directory, push it as a child of the parent
            self._push_directory(
                space_key=space_key,
                storage=storage,
                local_dir=local_dir,
                parent_id=parent_id
            )
    
    def _push_to_space(
        self, space_key: str, storage: LocalStorage, local_dir: Path
    ) -> None:
        """
        Push local pages to a Confluence space.
        
        Args:
            space_key: The key of the space to push to.
            storage: The local storage to read from.
            local_dir: The local directory containing the pages.
        """
        # Get the metadata for the local directory
        metadata = storage.get_page_metadata(local_dir)
        
        if not metadata:
            # This is a directory without metadata, treat each subdirectory
            # as a separate page to push
            for item in local_dir.iterdir():
                if item.is_dir() and item.name != ".csync":
                    self._push_directory(
                        space_key=space_key,
                        storage=storage,
                        local_dir=item,
                        parent_id=None
                    )
        else:
            # This is a page directory, push it as a root page in the space
            self._push_directory(
                space_key=space_key,
                storage=storage,
                local_dir=local_dir,
                parent_id=None
            )
    
    def _push_directory(
        self,
        space_key: str,
        storage: LocalStorage,
        local_dir: Path,
        parent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Push a directory to Confluence.
        
        Args:
            space_key: The key of the space to push to.
            storage: The local storage to read from.
            local_dir: The local directory to push.
            parent_id: The ID of the parent page, if any.
            
        Returns:
            The ID of the pushed page, or None if not pushed.
        """
        # Get the metadata for the directory
        metadata = storage.get_page_metadata(local_dir)
        
        if not metadata:
            logger.warning(
                f"Directory {local_dir} does not contain metadata, skipping"
            )
            return None
        
        # Get the content of the page
        content = storage.get_page_content(local_dir)
        
        if not content:
            logger.warning(
                f"Directory {local_dir} does not contain content, skipping"
            )
            return None
        
        # Check if the page exists in Confluence
        page_id = metadata.get("id")
        title = metadata.get("title", local_dir.name)
        
        if page_id:
            try:
                remote_page = self.client.get_page(page_id)
                remote_version = remote_page["version"]["number"]
                
                # Check if the page has been modified locally
                if (metadata.get("version") == remote_version and
                        not self.dry_run):
                    logger.info(f"Page '{title}' is up to date, skipping")
                    
                    # Still process children if recursion is enabled
                    if self.recurse:
                        self._push_children(
                            page_id=page_id,
                            space_key=space_key,
                            storage=storage,
                            local_dir=local_dir
                        )
                    
                    return page_id
                
                # Update the page
                if not self.dry_run:
                    updated_page = self.client.update_page(
                        page_id=page_id,
                        title=title,
                        body=content,
                        version=remote_version
                    )
                    
                    # Update the metadata with the new version
                    metadata["version"] = updated_page["version"]["number"]
                    storage.save_page_metadata(local_dir, metadata)
                    
                    # Push attachments
                    self._push_attachments(
                        page_id=page_id,
                        storage=storage,
                        local_dir=local_dir
                    )
                
                # Log the action
                action = "Would update" if self.dry_run else "Updated"
                logger.info(
                    f"{action} page '{title}' "
                    f"(version {remote_version} -> {remote_version + 1})"
                )
                
                # Process children if recursion is enabled
                if self.recurse:
                    self._push_children(
                        page_id=page_id,
                        space_key=space_key,
                        storage=storage,
                        local_dir=local_dir
                    )
                
                return page_id
            except Exception as e:
                logger.warning(
                    f"Failed to update page '{title}': {e}. "
                    "Creating a new page instead."
                )
                page_id = None
        
        if not page_id:
            # Create a new page
            if not self.dry_run:
                result = self.client.create_page(
                    space=space_key,
                    title=title,
                    body=content,
                    parent_id=parent_id
                )
                
                # Update the metadata with the new page ID
                page_id = result["id"]
                metadata["id"] = page_id
                metadata["version"] = result["version"]["number"]
                metadata["space_key"] = space_key
                storage.save_page_metadata(local_dir, metadata)
                
                # Push attachments
                self._push_attachments(
                    page_id=page_id,
                    storage=storage,
                    local_dir=local_dir
                )
            
            # Log the action
            action = "Would create" if self.dry_run else "Created"
            logger.info(f"{action} page '{title}'")
            
            # Process children if recursion is enabled
            if self.recurse and page_id:
                self._push_children(
                    page_id=page_id,
                    space_key=space_key,
                    storage=storage,
                    local_dir=local_dir
                )
            
            return page_id
    
    def _push_children(
        self,
        page_id: str,
        space_key: str,
        storage: LocalStorage,
        local_dir: Path
    ) -> None:
        """
        Push the children of a page.
        
        Args:
            page_id: The ID of the parent page.
            space_key: The key of the space.
            storage: The local storage to read from.
            local_dir: The local directory of the parent page.
        """
        # Get the children directory
        children_dir = local_dir / "children"
        if not children_dir.exists() or not children_dir.is_dir():
            return
        
        # Get the children directories
        children = [d for d in children_dir.iterdir() if d.is_dir()]
        
        if not children:
            return
        
        # Create a progress bar if enabled
        if self.show_progress:
            children_iter = tqdm(
                children,
                desc=f"Processing {len(children)} child pages",
                unit="page"
            )
        else:
            children_iter = children
        
        # Process each child
        for child_dir in children_iter:
            self._push_directory(
                space_key=space_key,
                storage=storage,
                local_dir=child_dir,
                parent_id=page_id
            )
    
    def _push_attachments(
        self,
        page_id: str,
        storage: LocalStorage,
        local_dir: Path
    ) -> None:
        """
        Push the attachments of a page.
        
        Args:
            page_id: The ID of the page.
            storage: The local storage to read from.
            local_dir: The local directory of the page.
        """
        # Get the attachments directory
        attachments_dir = local_dir / "attachments"
        if not attachments_dir.exists() or not attachments_dir.is_dir():
            return
        
        # Get the attachments
        attachments = [f for f in attachments_dir.iterdir() if f.is_file()]
        
        if not attachments:
            return
        
        # Create a progress bar if enabled
        if self.show_progress:
            attachments_iter = tqdm(
                attachments,
                desc=f"Uploading {len(attachments)} attachments",
                unit="file"
            )
        else:
            attachments_iter = attachments
        
        # Process each attachment
        for attachment_path in attachments_iter:
            if not self.dry_run:
                self.client.upload_attachment(
                    page_id=page_id,
                    filepath=str(attachment_path)
                )
            
            # Log the action
            action = "Would upload" if self.dry_run else "Uploaded"
            logger.debug(f"{action} attachment '{attachment_path.name}'")
