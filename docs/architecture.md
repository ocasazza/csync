# CSync Architecture

CSync is a command-line tool for synchronizing Confluence pages with a local file system. It allows users to pull pages from Confluence to their local machine, make changes, and push those changes back to Confluence.

## Overview

The application follows a modular design with clear separation of concerns:

1. **CLI Layer**: Handles command-line arguments and user interaction
2. **Sync Engine**: Core logic for synchronizing content between Confluence and local storage
3. **API Client**: Wrapper around the Atlassian Python API for Confluence interactions
4. **Storage Layer**: Manages local file system operations

## Component Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│  CLI Layer  │────▶│ Sync Engine │────▶│  API Client │────▶│  Confluence │
│             │     │             │     │             │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │             │     │             │
                    │   Storage   │────▶│ File System │
                    │             │     │             │
                    └─────────────┘     └─────────────┘
```

## Directory Structure

```
csync/
├── __init__.py
├── main.py                 # Entry point
├── api/
│   ├── __init__.py
│   └── client.py           # Confluence API client
├── cli/
│   ├── __init__.py
│   └── commands.py         # CLI commands and options
├── storage/
│   ├── __init__.py
│   └── fs.py               # File system operations
├── sync/
│   ├── __init__.py
│   └── engine.py           # Sync engine
└── utils/
    ├── __init__.py
    └── config.py           # Configuration utilities
```

## Key Components

### CLI Layer (`csync/cli/commands.py`)

The CLI layer uses Click to define commands and options. It provides two main commands:

- `pull`: Download pages from Confluence to local storage
- `push`: Upload local changes to Confluence

### Sync Engine (`csync/sync/engine.py`)

The sync engine is responsible for orchestrating the synchronization process. It:

1. Parses Confluence URLs to determine what to sync
2. Compares local and remote versions to determine what needs updating
3. Handles recursive processing of child pages
4. Manages attachments

### API Client (`csync/api/client.py`)

The API client wraps the Atlassian Python API to provide a simpler interface for:

- Fetching pages and their content
- Creating and updating pages
- Managing attachments
- Parsing Confluence URLs

### Storage Layer (`csync/storage/fs.py`)

The storage layer manages the local file system representation of Confluence pages:

- Pages are stored as directories with content and metadata files
- Child pages are stored in a "children" subdirectory
- Attachments are stored in an "attachments" subdirectory
- Metadata is stored in JSON format

## Data Flow

### Pull Operation

1. User provides a Confluence URL and local destination
2. CLI layer parses arguments and initializes components
3. Sync engine determines what to pull based on the URL
4. API client fetches page content and metadata
5. Storage layer saves content and metadata to the file system
6. Process repeats recursively for child pages if enabled

### Push Operation

1. User provides a local source directory and Confluence URL
2. CLI layer parses arguments and initializes components
3. Sync engine reads local content and metadata
4. API client creates or updates pages in Confluence
5. Process repeats recursively for child pages if enabled

## Configuration

Configuration is loaded from:

1. Environment variables
2. Configuration files in standard locations
3. Command-line arguments

Priority is given to command-line arguments, then environment variables, then configuration files.

## File Format

Each page is represented as a directory with the following structure:

```
page-title/
├── content.html           # HTML content of the page
├── metadata.json          # Page metadata (ID, version, etc.)
├── attachments/           # Directory for attachments
│   ├── image.png
│   └── document.pdf
└── children/              # Directory for child pages
    └── child-page/
        ├── content.html
        ├── metadata.json
        └── ...
```

The metadata.json file contains:

```json
{
  "id": "123456",
  "title": "Page Title",
  "version": 5,
  "space_key": "SPACE",
  "last_modified": "2023-01-01T12:00:00.000Z",
  "last_modified_by": "User Name"
}
```

## Optimization

The sync engine implements several optimizations:

1. **Version checking**: Only updates pages that have changed
2. **Progress bars**: Visual feedback for long-running operations
3. **Dry run mode**: Preview changes without making them
4. **Recursive control**: Option to include or exclude child pages

These optimizations make the tool efficient for both small and large Confluence spaces.
