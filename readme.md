# CSync

A command line program for synchronizing Confluence pages with a local file system.

## Features

- [x] Pull Confluence pages (and their children) to a local filesystem path.
    - For each page the remote metadata is fetched.
    - If the local metadata version equals the remote version, the page has not been changed and the file can be skipped. 
    - These steps then happen recursively for all child pages such that the entire tree of child pages is fetched.

- [x] Push local changes back to Confluence, creating or updating pages as needed.

- [x] Local confluence representation contains version metadata, preventing unnecessary fetching of pages if no changes have been made.

- [x] Support for attachments, allowing files to be downloaded and uploaded along with page content.

## Installation

### From Source

```sh
git clone https://github.com/example/csync.git
cd csync
pip install -e .
```

### Using pip

```sh
pip install csync
```

## Configuration

CSync can be configured using environment variables or a configuration file:

### Environment Variables

```sh
export CONFLUENCE_URL="https://your-instance.atlassian.net"
export CONFLUENCE_USERNAME="your-email@example.com"
export ATLASSIAN_TOKEN="your-api-token"
```

### Configuration File

Create a file at `~/.config/csync/config.json` or `.csync.json` in your current directory:

```json
{
  "CONFLUENCE_URL": "https://your-instance.atlassian.net",
  "CONFLUENCE_USERNAME": "your-email@example.com",
  "ATLASSIAN_TOKEN": "your-api-token"
}
```

## Future Plans
- [ ] Sync directly between Confluence spaces
- [ ] Introduce worker threads for parallel processing

# Usage

Setup using atlassian cloud account API key: 


Pull remote changes from confluence to local file system

```sh
csync pull $REMOTE_SOURCE_PAGE_ROOT_URL $LOCAL_DIRECTORY_DESTINATION
```


Push local filesystem changes to confluence
```sh
csync push $LOCAL_DIRECTORY_SOURCE $REMOTE_DESTINATION_PAGE_ROOT
```

Options: 
```sh
csync --help

    --progress # show progress bars
    --recurse # push or pull the entire tree for child pages given the source page
    --dry-run # highlights the changes that will be made without writing to destination
```
