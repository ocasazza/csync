# -*- coding: utf-8 -*-

"""
Command-line interface for csync.

This module defines the CLI commands and options for the csync application.
"""

import os
import click
from src.api.client import ConfluenceClient
from src.sync.engine import SyncEngine
from src.utils.config import load_config


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--progress/--no-progress", default=True, help="Show progress bars"
)
@click.option(
    "--recurse/--no-recurse", 
    default=True, 
    help="Process child pages recursively"
)
@click.option(
    "--dry-run", is_flag=True, help="Preview changes without writing"
)
@click.pass_context
def cli(ctx, progress, recurse, dry_run):
    """
    csync - A command line program for Confluence page management.
    
    This tool allows you to pull Confluence pages to a local filesystem
    and push local changes back to Confluence.
    """
    # Initialize the context object with our options
    ctx.ensure_object(dict)
    ctx.obj["PROGRESS"] = progress
    ctx.obj["RECURSE"] = recurse
    ctx.obj["DRY_RUN"] = dry_run
    
    # Load configuration from environment or config file
    ctx.obj["CONFIG"] = load_config()


@cli.command()
@click.argument("source", required=True)
@click.argument("destination", required=True)
@click.pass_context
def pull(ctx, source, destination):
    """
    Pull remote changes from Confluence to local file system.
    
    SOURCE: The URL of the Confluence page or space to pull from.
    DESTINATION: The local directory to save the pages to.
    """
    config = ctx.obj["CONFIG"]
    
    # Create the destination directory if it doesn't exist
    os.makedirs(destination, exist_ok=True)
    
    # Initialize the Confluence client
    client = ConfluenceClient(
        url=config.get("CONFLUENCE_URL"),
        username=config.get("CONFLUENCE_USERNAME"),
        token=config.get("ATLASSIAN_TOKEN")
    )
    
    # Initialize the sync engine
    engine = SyncEngine(
        client=client,
        show_progress=ctx.obj["PROGRESS"],
        recurse=ctx.obj["RECURSE"],
        dry_run=ctx.obj["DRY_RUN"]
    )
    
    # Perform the pull operation
    engine.pull(source, destination)
    
    if ctx.obj["DRY_RUN"]:
        click.echo("Dry run completed. No changes were made.")
    else:
        click.echo(
            f"Successfully pulled content from {source} to {destination}"
        )


@cli.command()
@click.argument("source", required=True)
@click.argument("destination", required=True)
@click.pass_context
def push(ctx, source, destination):
    """
    Push local filesystem changes to Confluence.
    
    SOURCE: The local directory containing the pages to push.
    DESTINATION: The URL of the Confluence page or space to push to.
    """
    config = ctx.obj["CONFIG"]
    
    # Check if the source directory exists
    if not os.path.isdir(source):
        raise click.ClickException(f"Source directory {source} does not exist")
    
    # Initialize the Confluence client
    client = ConfluenceClient(
        url=config.get("CONFLUENCE_URL"),
        username=config.get("CONFLUENCE_USERNAME"),
        token=config.get("ATLASSIAN_TOKEN")
    )
    
    # Initialize the sync engine
    engine = SyncEngine(
        client=client,
        show_progress=ctx.obj["PROGRESS"],
        recurse=ctx.obj["RECURSE"],
        dry_run=ctx.obj["DRY_RUN"]
    )
    
    # Perform the push operation
    engine.push(source, destination)
    
    if ctx.obj["DRY_RUN"]:
        click.echo("Dry run completed. No changes were made.")
    else:
        click.echo(
            f"Successfully pushed content from {source} to {destination}"
        )
