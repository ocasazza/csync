# CSync Architecture

CSync is a command-line tool for synchronizing Confluence pages with a local file system. It allows users to pull pages from Confluence to their local machine, make changes, and push those changes back to Confluence.

## Overview

The application follows a modular design with clear separation of concerns:

1. **CLI Layer**: Handles command-line arguments and user interaction
2. **Sync Engine**: Core logic for synchronizing content between Confluence and local storage
3. **Storage Layer**: Manages local file system operations

## Component Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │
│  CLI Layer  │────▶│ Sync Engine │────▶│  Confluence │
│             │     │             │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │             │     │             │
                    │   Storage   │────▶│ File System │
                    │             │     │             │
                    └─────────────┘     └─────────────┘
```

## Key Components

### CLI Layer (`commands.py`)

The CLI layer uses Click to define commands and options. It provides two main commands:

- `pull`: Download pages from Confluence to local storage
- `push`: Upload local changes to Confluence

### Sync Engine (`engine.py`)

The sync engine is responsible for orchestrating the synchronization process. It:

1. Builds a complete tree of pages to sync
2. Compares local and remote versions to determine what needs updating
3. Creates a sync plan with actions (create, update, rename, skip)
4. Executes the sync plan efficiently
5. Handles renamed pages automatically
6. Manages attachments

### Storage Layer (`fs.py`)

The storage layer manages the local file system representation of Confluence pages:

- Pages are stored as directories with content and metadata files
- Child pages are stored in a "children" subdirectory
- Attachments are stored in an "attachments" subdirectory
- Metadata is stored in JSON format
- Maintains an ID-to-path mapping for efficient page lookup

## Data Flow

### Pull Operation

1. User provides a Confluence URL and local destination
2. CLI layer parses arguments and initializes components
3. Sync engine builds a complete tree of pages to sync
4. Sync engine compares the tree with local metadata to create a sync plan
5. Sync engine executes the plan, handling renames, updates, and new pages
6. Storage layer saves content and metadata to the file system

### Push Operation

1. User provides a local source directory and Confluence URL
2. CLI layer parses arguments and initializes components
3. Sync engine reads local content and metadata
4. Sync engine builds a tree of local pages to push
5. Sync engine compares with remote pages to create a sync plan
6. Sync engine executes the plan, creating or updating pages in Confluence

## Configuration

Configuration is loaded from:

1. Environment variables from .env file (if present)
2. System environment variables
3. Configuration files in standard locations
4. Command-line arguments

Priority is given to command-line arguments, then environment variables, then configuration files.

## File Format

Each page is represented as a directory with the following structure:

```
page-title/
├── content.html           # HTML content of the page
├── metadata.json         # Page metadata (ID, version, etc.)
├── attachments/          # Directory for attachments
│   ├── image.png
│   └── document.pdf
└── children/             # Directory for child pages
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
  ...
}
```

Additional metadata fields may be included based on the Confluence API response.

## Sync Strategy

### Tree-Based Sync

CSync uses a tree-based sync strategy for efficient operation:

1. **Tree Building**: First builds a complete tree of pages to sync
2. **Sync Planning**: Compares the tree with local state to create a sync plan
3. **Efficient Execution**: Executes the plan in optimal order (renames → creates → updates)

### Handling Renamed Pages

When a page is renamed in Confluence:

1. The local directory is renamed to match
2. The metadata is updated with the new title
3. The ID-to-path mapping is updated to maintain continuity

### Resumable Operations

Operations are designed to be resumable:

1. The sync plan is stored in the metadata directory
2. If an operation is interrupted, it can be resumed from the last successful step
3. Version checking prevents unnecessary transfers

## Optimization

The sync engine implements several optimizations:

1. **Tree-based sync**: Minimizes API calls by planning the entire sync operation
2. **Version checking**: Only updates pages that have changed
3. **ID-based tracking**: Efficiently handles renamed pages
4. **Progress bars**: Visual feedback for long-running operations
5. **Dry run mode**: Preview changes without making them
6. **Recursive control**: Option to include or exclude child pages

These optimizations make the tool efficient for both small and large Confluence spaces.
