#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSync - A command line program for Confluence page management.

This module serves as the entry point for the application.
"""

import sys
import os
import logging
import click
from dotenv import load_dotenv
from atlassian import Confluence
from src.engine import SyncEngine

# Required environment variables
REQUIRED_ENV_VARS = {
    'CONFLUENCE_URL': 'The base URL of your Confluence instance',
    'CONFLUENCE_USERNAME': 'Your Confluence username',
    'ATLASSIAN_TOKEN': 'Your Atlassian API token'
}

def check_environment():
    """Check if all required environment variables are set."""
    missing = []
    for var, desc in REQUIRED_ENV_VARS.items():
        if not os.environ.get(var):
            missing.append(f"{var} - {desc}")
    
    if missing:
        click.echo("Error: Missing required environment variables:", err=True)
        for var in missing:
            click.echo(f"  {var}", err=True)
        click.echo("\nCreate a .env file with these variables or set them in your environment.", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0")
@click.option("--progress", default=True, 
              help="Show progress bars during operations")
@click.option("--recurse", default=True,
              help="Process child pages recursively")
@click.option("--dry-run", is_flag=True,
              help="Preview changes without making any modifications")
@click.pass_context
def cli(ctx, progress, recurse, dry_run):
    """
    csync - Synchronize Confluence pages with your local filesystem.

    This tool allows you to:
    - Pull Confluence pages to your local filesystem
    - Push local changes back to Confluence
    - Track page history and changes
    - Handle page renames and moves
    - Sync attachments

    Configuration:
    Create a .env file with:
    - CONFLUENCE_URL: Your Confluence instance URL
    - CONFLUENCE_USERNAME: Your username
    - ATLASSIAN_TOKEN: Your API token

    Example Usage:
    $ csync pull "https://<confluence-url>/wiki/spaces/SPACE/pages/123" ./docs
    $ csync push ./docs "https://<confluence-url>/wiki/spaces/SPACE/pages/123"
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Check environment variables
    check_environment()

    # Initialize the context object with our options
    ctx.ensure_object(dict)
    ctx.obj.update({
        "PROGRESS": progress,
        "RECURSE": recurse,
        "DRY_RUN": dry_run,
        "CONFLUENCE_URL": os.environ["CONFLUENCE_URL"],
        "CONFLUENCE_USERNAME": os.environ["CONFLUENCE_USERNAME"],
        "ATLASSIAN_TOKEN": os.environ["ATLASSIAN_TOKEN"]
    })


@cli.command()
@click.argument("source", required=True)
@click.argument("destination", required=True, type=click.Path())
@click.option("--recurse/--no-recurse", default=True,
              help="Process child pages recursively")
@click.pass_context
def pull(ctx, source, destination, recurse):
    """
    Pull Confluence pages to your local filesystem.

    SOURCE: The URL of the Confluence page or space to pull from
    DESTINATION: The local directory to save the pages to

    Examples:
    \b
    Pull a single page:
    $ csync pull "https://<confluence-url>/wiki/spaces/SPACE/pages/123" ./docs

    \b
    Pull without child pages:
    $ csync pull --no-recurse "https://<confluence-url>/wiki/spaces/SPACE/pages/123" ./docs

    \b
    Preview changes without pulling:
    $ csync --dry-run pull "https://<confluence-url>/wiki/spaces/SPACE/pages/123" ./docs
    """
    try:
        # Create the destination directory if it doesn't exist
        os.makedirs(destination, exist_ok=True)

        # Initialize the sync engine
        engine = SyncEngine(
            client=Confluence(
                url=ctx.obj["CONFLUENCE_URL"],
                username=ctx.obj["CONFLUENCE_USERNAME"],
                password=ctx.obj["ATLASSIAN_TOKEN"],
                cloud=True,
            ),
            show_progress=ctx.obj["PROGRESS"],
            recurse=recurse,  # Use the command-level recurse parameter
            dry_run=ctx.obj["DRY_RUN"],
        )

        # Perform the pull operation
        engine.pull(source, destination)

        if ctx.obj["DRY_RUN"]:
            click.echo("Dry run completed. No changes were made.")
        else:
            click.echo(f"Successfully pulled content from {source} to {destination}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("source", required=True, type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("destination", required=True)
@click.option("--recurse/--no-recurse", default=True,
              help="Process child pages recursively")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def push(ctx, source, destination, recurse, debug):
    """
    Push local changes back to Confluence.

    SOURCE: The local directory containing the pages to push
    DESTINATION: The URL of the Confluence page or space to push to

    Examples:
    \b
    Push changes to a page:
    $ csync push ./docs "https://<confluence-url>/wiki/spaces/SPACE/pages/123"

    \b
    Push without child pages:
    $ csync push --no-recurse ./docs "https://<confluence-url>/wiki/spaces/SPACE/pages/123"

    \b
    Preview changes without pushing:
    $ csync --dry-run push ./docs "https://<confluence-url>/wiki/spaces/SPACE/pages/123"
    
    \b
    Enable debug logging:
    $ csync push --debug ./docs "https://<confluence-url>/wiki/spaces/SPACE/pages/123"
    """
    try:
        # Set up logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            click.echo("Debug logging enabled")
        
        # Validate the destination URL format
        if not destination.startswith("http"):
            click.echo("Error: Destination URL must start with http:// or https://", err=True)
            click.echo("Example: https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/PAGE_ID", err=True)
            sys.exit(1)
            
        if "/wiki/spaces/" not in destination:
            click.echo("Error: Destination URL must be in the format:", err=True)
            click.echo("https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/PAGE_ID", err=True)
            sys.exit(1)
            
        # Initialize the sync engine
        try:
            client = Confluence(
                url=ctx.obj["CONFLUENCE_URL"],
                username=ctx.obj["CONFLUENCE_USERNAME"],
                password=ctx.obj["ATLASSIAN_TOKEN"],
                cloud=True,
            )
                
            engine = SyncEngine(
                client=client,
                show_progress=ctx.obj["PROGRESS"],
                recurse=recurse,  # Use the command-level recurse parameter
                dry_run=ctx.obj["DRY_RUN"],
            )
        except Exception as e:
            click.echo(f"Error initializing Confluence client: {str(e)}", err=True)
            sys.exit(1)

        # Perform the push operation
        click.echo(f"Pushing content from {source} to {destination}")
        engine.push(source, destination)

        if ctx.obj["DRY_RUN"]:
            click.echo("Dry run completed. No changes were made.")
        else:
            click.echo(f"Successfully pushed content from {source} to {destination}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if debug:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


def main():
    """Main entry point for the application."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
