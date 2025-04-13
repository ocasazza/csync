#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSync - A command line program for Confluence page management.

This module serves as the entry point for the application.
"""

import sys
from src.cli.commands import cli
from src.utils.config import load_config


def main():
    """Main entry point for the application."""
    # Load configuration from .env file and environment variables
    load_config()
    return cli()


if __name__ == "__main__":
    sys.exit(main())
