# -*- coding: utf-8 -*-

"""
Sync engine for csync.

This module provides the core functionality for syncing Confluence pages.
"""

import logging
from pathlib import Path
from typing import Dict
from atlassian import Confluence
from urllib.parse import urlparse

from src.fs import LocalStorage
from src.pull import PullOperations
from src.push import PushOperations

logger = logging.getLogger(__name__)


class SyncEngine:
    """Engine for syncing Confluence pages with local storage."""

    def __init__(
        self,
        client: Confluence,
        show_progress: bool = True,
        recurse: bool = True,
        dry_run: bool = False,
    ):
        """
        Initialize the sync engine.

        Args:
            client: The Confluence client to use.
            url: The URL of the Confluence instance.
            username: The username for authentication.
            token: The API token for authentication.
            show_progress: Whether to show progress bars.
            recurse: Whether to recursively process child pages.
            dry_run: Whether to perform a dry run (no changes).
        """
        self.client = client
        self.show_progress = show_progress
        self.recurse = recurse
        self.dry_run = dry_run

        # Initialize operations
        self.pull_ops = PullOperations(
            client=client, 
            show_progress=show_progress, 
            recurse=recurse, 
            dry_run=dry_run
        )

        self.push_ops = PushOperations(
            client=client, 
            show_progress=show_progress, 
            recurse=recurse, 
            dry_run=dry_run
        )

    def push(self, source: str, destination: str) -> None:
        """
        Push local pages to Confluence.

        Args:
            source: The local directory containing the pages to push.
            destination: The URL of the Confluence page or space to push to.
        """
        # Parse the destination URL to get page ID
        parsed = self.parse_page_url(destination)
        page_id = parsed["page_id"]

        # Push to the specified parent page
        storage = LocalStorage(source)
        local_dir = Path(source)
        self.push_ops.push_page_tree(
            storage=storage,
            local_dir=local_dir,
            parent_id=page_id,
        )

    def pull(self, source: str, destination: str) -> Dict[str, int]:
        """
        Pull Confluence pages to local storage using a simple recursive 
        approach.

        Args:
            source: The URL of the Confluence page or space to pull from.
            destination: The local directory to save the pages to.

        Returns:
            A dictionary containing sync statistics.
        """
        # Parse the source URL to get page ID
        parsed = self.parse_page_url(source)
        page_id = parsed["page_id"]
        
        # Initialize local storage
        storage = LocalStorage(destination)
        
        if self.dry_run:
            logger.info(f"Dry run - would pull page tree from {page_id}")
            return {"pulled": 0}
        
        # Simply pull the page tree recursively
        logger.info(f"Pulling page tree from {page_id}")
        self.pull_ops.pull_page_tree(page_id, storage)
        
        return {"pulled": 1}  # Basic stats, could be enhanced if needed

    def parse_page_url(self, url: str) -> Dict[str, str]:
        """
        Parse a Confluence page URL to extract space key and page title/ID.

        Args:
            url: The URL of the Confluence page.

        Returns:
            A dictionary containing the parsed components.
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        # Initialize result with defaults
        result = {
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
            "type": "page",
            "space_key": None,
            "page_id": None,
            "title": None,
        }

        # Extract space key, page ID, and title from the URL
        if (
            len(path_parts) >= 3
            and path_parts[0] == "wiki"
            and path_parts[1] == "spaces"
        ):
            # Space key is always the third part
            result["space_key"] = path_parts[2]

            # Page ID and title if they exist
            if len(path_parts) >= 5 and path_parts[3] == "pages":
                result["page_id"] = path_parts[4]
                if len(path_parts) >= 6:
                    result["title"] = path_parts[5]

        # Handle direct API URLs (for compatibility)
        elif (
            len(path_parts) >= 4
            and path_parts[0] == "rest"
            and path_parts[1] == "api"
            and path_parts[2] == "content"
        ):
            result["page_id"] = path_parts[3]
            # We'll need to fetch the space key from the page itself later

        # Debug output
        print(f"Final parsed result: {result}")

        return result
