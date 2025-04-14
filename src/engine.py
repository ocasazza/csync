# -*- coding: utf-8 -*-

"""
Sync engine for csync.

This module provides the core functionality for syncing Confluence pages.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Optional
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
            client=client, show_progress=show_progress, recurse=recurse, dry_run=dry_run
        )

        self.push_ops = PushOperations(
            client=client, show_progress=show_progress, recurse=recurse, dry_run=dry_run
        )

    def pull(self, source: str, destination: str) -> Dict[str, int]:
        """
        Pull Confluence pages to local storage using tree-based sync strategy.

        Args:
            source: The URL of the Confluence page or space to pull from.
            destination: The local directory to save the pages to.

        Returns:
            A dictionary containing sync statistics.
        """
        # Parse the source URL to get page ID or space key
        parsed = self.parse_page_url(source)

        # Initialize local storage
        storage = LocalStorage(destination)

        # Step 1: Build a complete tree of pages to pull
        logger.info("Building page tree...")
        page_tree = self._build_page_tree(parsed["page_id"])

        # Step 2: Compare with local metadata to create sync plan
        logger.info("Analyzing changes...")
        sync_plan = self._create_sync_plan(page_tree, storage)

        # Convert Path objects to strings for JSON serialization
        serializable_plan = {
            "to_update": [
                {**item, "local_dir": str(item["local_dir"])}
                for item in sync_plan["to_update"]
            ],
            "to_create": [
                {
                    **item,
                    "parent_dir": (
                        str(item["parent_dir"]) if item["parent_dir"] else None
                    ),
                }
                for item in sync_plan["to_create"]
            ],
            "unchanged": sync_plan["unchanged"],
            "to_rename": [
                {**item, "local_dir": str(item["local_dir"])}
                for item in sync_plan["to_rename"]
            ],
            "stats": sync_plan["stats"],
        }

        # Save the sync plan for resumability
        plan_file = storage.metadata_dir / "sync_plan.json"
        with open(plan_file, "w") as f:
            json.dump(serializable_plan, f, indent=2)

        # Step 3: Execute the sync plan
        stats = sync_plan["stats"]
        logger.info(
            "Executing sync plan:\n"
            f"  Updates: {stats['to_update']}\n"
            f"  New: {stats['to_create']}\n"
            f"  Renames: {stats['to_rename']}\n"
            f"  Unchanged: {stats['unchanged']}"
        )

        if not self.dry_run:
            self._execute_sync_plan(sync_plan, storage)
        else:
            logger.info("Dry run - no changes made")

        return sync_plan["stats"]

    def _build_page_tree(self, page_id: str) -> Dict:
        """Build a complete tree of pages starting from the given page ID."""
        # Get the root page with minimal expansion to save bandwidth
        root_page = self.client.get_page_by_id(
            page_id,
            expand=(
                "body.storage,version,space,"
                "metadata.properties.editor,"
                "metadata.properties.emoji_title_published,"
                "children.page"
            ),
        )

        # Create the tree structure
        tree = {
            "id": root_page["id"],
            "title": root_page["title"],
            "version": root_page["version"]["number"],
            "children": [],
            "metadata": root_page,  # Store full metadata for later use
        }

        # Get all children
        has_children = (
            "children" in root_page
            and "page" in root_page["children"]
            and "results" in root_page["children"]["page"]
        )
        if has_children:
            children = root_page["children"]["page"]["results"]
            for child in children:
                child_tree = self._build_page_tree(child["id"])
                tree["children"].append(child_tree)

        return tree

    def _create_sync_plan(self, page_tree: Dict, storage: LocalStorage) -> Dict:
        """Create a sync plan by comparing the page tree with local metadata."""
        plan = {
            "to_update": [],
            "to_create": [],
            "unchanged": [],
            "to_rename": [],
            "stats": {"to_update": 0, "to_create": 0, "unchanged": 0, "to_rename": 0},
        }

        # Process the tree recursively
        self._analyze_page(page_tree, None, storage, plan)

        return plan

    def _analyze_page(
        self, page: Dict, parent_dir: Optional[Path], storage: LocalStorage, plan: Dict
    ) -> None:
        """Analyze a page and its children to determine what actions are needed."""
        # Check if the page exists locally by ID
        local_dir = storage.get_page_dir_by_id(page["id"])

        if not local_dir:
            # Page doesn't exist locally, need to create it
            plan["to_create"].append(
                {
                    "id": page["id"],
                    "title": page["title"],
                    "parent_dir": parent_dir,
                    "metadata": page["metadata"],
                }
            )
            plan["stats"]["to_create"] += 1

            # For new pages, we'll need to process all children as new too
            if parent_dir:
                new_parent_dir = storage.get_child_dir(parent_dir, page["title"])
            else:
                new_parent_dir = storage.get_page_dir(page["title"])

            # Process children
            for child in page["children"]:
                self._analyze_page(child, new_parent_dir, storage, plan)
        else:
            # Page exists, check if it needs updating
            metadata = storage.get_page_metadata(local_dir)

            if not metadata:
                # Metadata missing, treat as new
                plan["to_create"].append(
                    {
                        "id": page["id"],
                        "title": page["title"],
                        "parent_dir": parent_dir,
                        "metadata": page["metadata"],
                    }
                )
                plan["stats"]["to_create"] += 1
            elif metadata["title"] != page["title"]:
                # Title has changed, need to rename
                plan["to_rename"].append(
                    {
                        "id": page["id"],
                        "old_title": metadata["title"],
                        "new_title": page["title"],
                        "local_dir": local_dir,
                        "metadata": page["metadata"],
                    }
                )
                plan["stats"]["to_rename"] += 1
            elif metadata["version"]["number"] < page["version"]:
                # Version is older, need to update
                plan["to_update"].append(
                    {
                        "id": page["id"],
                        "title": page["title"],
                        "local_dir": local_dir,
                        "metadata": page["metadata"],
                    }
                )
                plan["stats"]["to_update"] += 1
            else:
                # No changes needed
                plan["unchanged"].append({"id": page["id"], "title": page["title"]})
                plan["stats"]["unchanged"] += 1

            # Process children
            for child in page["children"]:
                self._analyze_page(child, local_dir, storage, plan)

    def _execute_sync_plan(self, plan: Dict, storage: LocalStorage) -> None:
        """Execute the sync plan."""
        # First handle renames to avoid conflicts
        for item in plan["to_rename"]:
            self.pull_ops.handle_renamed_page(item["id"], item["new_title"], storage)

        # Then create new pages
        for item in plan["to_create"]:
            self.pull_ops.pull_page(
                page_id=item["id"],
                storage=storage,
                parent_dir=item["parent_dir"],
                metadata=item["metadata"],
            )

        # Finally update existing pages
        for item in plan["to_update"]:
            self.pull_ops.pull_page(
                page_id=item["id"],
                storage=storage,
                parent_dir=item["local_dir"].parent,
                metadata=item["metadata"],
            )

    def push(self, source: str, destination: str) -> None:
        """
        Push local pages to Confluence.

        Args:
            source: The local directory containing the pages to push.
            destination: The URL of the Confluence page or space to push to.
        """
        # Parse the destination URL to get page ID or space key
        parsed = self.parse_page_url(destination)
        push_root_page_id = parsed["page_id"]

        # Push to the specified parent page
        self.push_ops.push_page_tree(
            storage=LocalStorage(source),
            local_dir=Path(source),
            parent_id=push_root_page_id,
        )

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
