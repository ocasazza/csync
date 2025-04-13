# -*- coding: utf-8 -*-

"""
CSync - A command line program for Confluence page management.

This package provides tools for synchronizing Confluence pages with a local
file system.
"""

__version__ = "0.1.0"

# Import main components for easier access
from src.api.client import ConfluenceClient
from src.sync.engine import SyncEngine
from src.storage.fs import LocalStorage

# Define public API
__all__ = [
    "ConfluenceClient",
    "SyncEngine",
    "LocalStorage",
]
