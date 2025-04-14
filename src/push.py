# -*- coding: utf-8 -*-

"""
Push operations for csync.

This module provides functionality for pushing local content to Confluence.
"""

import logging
from pathlib import Path
from tqdm import tqdm
from src.fs import LocalStorage
from atlassian import Confluence
import json

logger = logging.getLogger(__name__)


class PushOperations:
    """Operations for pushing local content to Confluence."""

    def __init__(
        self,
        client: Confluence,
        show_progress: bool = True,
        recurse: bool = True,
        dry_run: bool = False,
    ):
        """
        Initialize the push operations.

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

    def push_page(
        self, storage: LocalStorage, local_dir: Path, parent_id: str = None
    ) -> str:
        assert local_dir is not None and parent_id is not None
        """
        Push a single page to Confluence.

        Args:
            storage: The local storage to read from.
            local_dir: The local directory containing the page.
            parent_id: Optional ID of the parent page.

        Returns:
            The ID of the created/updated page.
        """

        content = storage.get_page_content(local_dir) or "<p>todo</p>"
        metadata = storage.get_page_metadata(local_dir)

        assert content != "" and content is not None
        assert "title" in metadata

        print(f"[push_page]: local_dir: {local_dir}, parent_id: {parent_id}")

        if self.dry_run:
            print(f"[DRY RUN]: push_page({local_dir}, {parent_id})")

        created_page = None
        try:
            created_page = self.client.update_or_create(
                parent_id=parent_id,
                title=metadata["title"],
                body=content,
                representation="storage",
                minor_edit=True,
                editor="v2",
                full_width=True,
            )


            # todo should be a storage layer metadata function
            emoji = metadata["metadata"]["properties"]["emoji-title-published"]
            del emoji["id"]
            del emoji["version"]
            del emoji["_expandable"]
            del emoji["_links"]

            self.client.update_page_property(
                created_page["id"],  emoji
            )

            # todo: similar to emoji but we probably need to sanitize even more fields
            # self.client.update_page_property(
            #     created_page["id"],  metadata["version"]
            # )

        except Exception as e:
            logger.error(f"Failed to create/update page: {str(e)}")
            return ""

        # Push attachments
        assert created_page["id"] is not None
        self.push_attachments(created_page["id"], local_dir)

        return created_page["id"]

    def push_page_tree(
        self,
        storage: LocalStorage,
        local_dir: Path,
        parent_id: str = None,
    ) -> str:
        """
        Push a page and all its children to Confluence.

        Args:
            storage: The local storage to read from.
            local_dir: The local directory containing the pages.
            parent_id: Optional ID of the parent page.

        Returns:
            The ID of the root page that was pushed.
        """
        # Push the page itself
        print(f"[push_page_tree]: local_dir: {local_dir}, parent_id: {parent_id}")
        page_id = self.push_page(storage, local_dir, parent_id)

        # Push children if recursive mode is enabled
        if self.recurse:
            children_dir = local_dir / "children"
            print(f"[push_page_tree] children_dir: {children_dir}")
            if children_dir.exists() and children_dir.is_dir():
                # Get all child directories
                child_dirs = [d for d in children_dir.iterdir() if d.is_dir()]
                print(f"[push_page_tree] child_dirs: {child_dirs}")

                # Create a progress bar if enabled
                if self.show_progress and child_dirs:
                    child_dirs_iter = tqdm(
                        child_dirs, desc="Pushing child pages", unit="page"
                    )
                else:
                    child_dirs_iter = child_dirs

                # Process each child directory using the new parent info
                for child_dir in child_dirs_iter:
                    # Push child with new parent ID
                    self.push_page_tree(storage, child_dir, page_id)

        return page_id

    def push_attachments(self, page_id: str, local_dir: Path) -> None:
        """
        Push the attachments of a page.

        Args:
            page_id: The ID of the page.
            local_dir: The local directory of the page.
        """
        print(f"push_attachments: page_id{page_id} | local_dir: {local_dir}")
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
                unit="file",
            )
        else:
            attachments_iter = attachments

        # Process each attachment
        for attachment_path in attachments_iter:
            if not self.dry_run:
                # Read the file content and attach it to the page
                file_name = attachment_path.name

                # Attach the file to the page
                # If the attachment already exists, it will be versioned
                with open(attachment_path, "rb") as file:
                    self.client.attach_content(
                        name=file_name,
                        content=file.read(),
                        page_id=page_id,
                    )

            # Log the action
            action = "Would upload" if self.dry_run else "Uploaded"
            logger.debug(f"{action} attachment '{attachment_path.name}'")
