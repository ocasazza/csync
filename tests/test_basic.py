#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Basic tests for the csync package.

This module contains simple tests to verify that the package can be imported
and that the main components are accessible.
"""

import unittest
import os
from pathlib import Path

# Test that the package can be imported
import csync
from csync import ConfluenceClient, SyncEngine, LocalStorage


class TestBasic(unittest.TestCase):
    """Basic tests for the csync package."""

    def test_version(self):
        """Test that the version is defined."""
        self.assertIsNotNone(csync.__version__)
        self.assertIsInstance(csync.__version__, str)

    def test_client_import(self):
        """Test that the ConfluenceClient can be imported."""
        self.assertIsNotNone(ConfluenceClient)

    def test_engine_import(self):
        """Test that the SyncEngine can be imported."""
        self.assertIsNotNone(SyncEngine)

    def test_storage_import(self):
        """Test that the LocalStorage can be imported."""
        self.assertIsNotNone(LocalStorage)

    def test_client_init(self):
        """Test that the ConfluenceClient can be initialized."""
        # Skip if no credentials are available
        if not os.environ.get("CONFLUENCE_URL"):
            self.skipTest("No Confluence credentials available")
        
        client = ConfluenceClient(
            url=os.environ.get("CONFLUENCE_URL"),
            username=os.environ.get("CONFLUENCE_USERNAME"),
            token=os.environ.get("ATLASSIAN_TOKEN")
        )
        self.assertIsNotNone(client)

    def test_storage_init(self):
        """Test that the LocalStorage can be initialized."""
        storage = LocalStorage("./test_storage")
        self.assertIsNotNone(storage)
        
        # Clean up
        if Path("./test_storage").exists():
            import shutil
            shutil.rmtree("./test_storage")


if __name__ == "__main__":
    unittest.main()
