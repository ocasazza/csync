#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
csync - A command line program used to move around confluence pages in bulk.

This module serves as the entry point for the application.
"""

import sys
from csync.cli.commands import cli


def main():
    """Main entry point for the application."""
    return cli()


if __name__ == "__main__":
    sys.exit(main())
