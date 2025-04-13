#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example of programmatic usage of the csync library.

This script demonstrates how to use the csync library in your own Python code,
rather than through the command-line interface.
"""

from src.api.client import ConfluenceClient
from src.sync.engine import SyncEngine
from src.utils.config import load_config


def main():
    """Demonstrate programmatic usage of csync."""
    # Load configuration from .env file and environment variables
    config = load_config()
    
    # Configuration (will be loaded from .env file if available)
    confluence_url = config.get("CONFLUENCE_URL")
    username = config.get("CONFLUENCE_USERNAME")
    token = config.get("ATLASSIAN_TOKEN")
    
    # Source and destination
    # Example Confluence page URL
    source_url = ("https://your-instance.atlassian.net/wiki/spaces/SPACE/"
                  "pages/123456/Page+Title")
    destination_dir = "./confluence_pages"
    
    # Initialize the Confluence client
    client = ConfluenceClient(
        url=confluence_url,
        username=username,
        token=token
    )
    
    # Initialize the sync engine
    engine = SyncEngine(
        client=client,
        show_progress=True,
        recurse=True,
        dry_run=False
    )
    
    # Pull example
    print("Pulling pages from Confluence...")
    engine.pull(source_url, destination_dir)
    print(f"Pages pulled to {destination_dir}")
    
    # Push example (commented out to prevent accidental execution)
    """
    print("Pushing pages to Confluence...")
    engine.push(destination_dir, source_url)
    print("Pages pushed to Confluence")
    """


if __name__ == "__main__":
    main()
