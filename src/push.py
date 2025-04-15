# -*- coding: utf-8 -*-

"""
Push operations for csync.

This module provides functionality for pushing local content to Confluence.
"""

import logging
import sys
from pathlib import Path
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
        logger.debug(f"[push_page]: local_dir: {local_dir}, parent_id: {parent_id}")
        if self.dry_run:
            logger.info(f"[DRY RUN]: push_page({local_dir}, {parent_id})")
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
            # Set emoji title published property if it exists in metadata
            try:
                logger.debug(f"Metadata keys: {metadata.keys()}")
                if "metadata" in metadata and "properties" in metadata["metadata"]:
                    properties = metadata["metadata"]["properties"]
                    logger.debug(f"Properties found: {list(properties.keys())}")

                    if "emoji-title-published" in properties:
                        emoji_data = properties["emoji-title-published"]
                        logger.debug(f"Emoji data found: {emoji_data}")

                        # Extract the emoji value
                        emoji_value = emoji_data.get("value")
                        logger.debug(f"Extracted emoji value: {emoji_value}")

                        if emoji_value:
                            # Update the emoji property using the correct API method
                            property_data = {
                                "key": "emoji-title-published",
                                "value": emoji_value
                            }
                            logger.debug(f"Setting page property with data: {property_data}")
                            try:
                                response = self.client.set_page_property(
                                    created_page["id"],
                                    property_data
                                )
                                logger.debug(f"Response from set_page_property: {response}")
                            except Exception as prop_error:
                                logger.error(f"Error setting page property: {str(prop_error)}")
                                logger.debug("Property error details:", exc_info=True)
                                # Try with a different format as fallback
                                try:
                                    logger.debug("Trying alternative property format...")
                                    response = self.client.set_page_property(
                                        page_id=created_page["id"],
                                        data={"key": "emoji-title-published", "value": emoji_value}
                                    )
                                    logger.debug(f"Alternative format response: {response}")
                                except Exception as alt_error:
                                    logger.error(f"Alternative format also failed: {str(alt_error)}")
                                    logger.debug("Alternative error details:", exc_info=True)
                            logger.debug(
                                f"Response from update_or_create_content_property: {response}"
                            )
                            logger.info(
                                f"Updated emoji-title-published property for page {created_page['id']}"
                            )
                        else:
                            logger.warning("Emoji value is missing in metadata")
                else:
                    logger.debug("No properties found in metadata")
            except Exception as e:
                logger.warning(
                    f"Failed to update emoji-title-published property: {str(e)}"
                )
                logger.debug("Exception details:", exc_info=True)
            # todo: similar to emoji but we probably need to sanitize even more fields
            # self.client.update_page_property(
            #     created_page["id"],  metadata["version"]
            # )
        except Exception as e:
            logger.error(f"Failed to create/update page: {str(e)}", exc_info=True)
            return ""
        # Push attachments
        assert created_page["id"] is not None
        self.push_attachments(created_page["id"], local_dir, storage)
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

                # Process each child directory using the new parent info
                for i, child_dir in enumerate(child_dirs):
                    # Use a simple progress message instead of tqdm
                    if self.show_progress:
                        # Get the parent page title from the local directory
                        parent_metadata = storage.get_page_metadata(local_dir)
                        parent_title = (
                            parent_metadata.get("title", "Unknown")
                            if parent_metadata
                            else "Unknown"
                        )

                        # Clear the line and write the progress with parent info
                        sys.stdout.write(
                            f"\rPushing child pages of '{parent_title}': {i+1}/{len(child_dirs)}"
                        )
                        sys.stdout.flush()

                    # Push child with new parent ID
                    self.push_page_tree(storage, child_dir, page_id)

                # Print a newline after we're done
                if self.show_progress and child_dirs:
                    # Get the parent page title if we haven't already
                    if "parent_title" not in locals():
                        parent_metadata = storage.get_page_metadata(local_dir)
                        parent_title = (
                            parent_metadata.get("title", "Unknown")
                            if parent_metadata
                            else "Unknown"
                        )

                    sys.stdout.write(
                        f"\rPushing child pages of '{parent_title}': {len(child_dirs)}/{len(child_dirs)} - Complete\n"
                    )
                    sys.stdout.flush()

        return page_id

    def push_attachments(
        self, page_id: str, local_dir: Path, storage: LocalStorage = None
    ) -> None:
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

        # Process each attachment
        for i, attachment_path in enumerate(attachments):
            # Use a simple progress message instead of tqdm
            if self.show_progress:
                # Get the page title
                page_metadata = storage.get_page_metadata(local_dir)
                page_title = (
                    page_metadata.get("title", "Unknown")
                    if page_metadata
                    else "Unknown"
                )

                # Clear the line and write the progress with page info
                sys.stdout.write(
                    f"\rUploading attachments for '{page_title}': {i+1}/{len(attachments)}"
                )
                sys.stdout.flush()

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

        # Print a newline after we're done
        if self.show_progress and attachments:
            # Get the page title if we haven't already
            if "page_title" not in locals():
                page_metadata = storage.get_page_metadata(local_dir)
                page_title = (
                    page_metadata.get("title", "Unknown")
                    if page_metadata
                    else "Unknown"
                )

            sys.stdout.write(
                f"\rUploading attachments for '{page_title}': {len(attachments)}/{len(attachments)} - Complete\n"
            )
            sys.stdout.flush()
