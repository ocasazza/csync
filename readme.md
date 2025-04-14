# CSync

A command line program for synchronizing Confluence pages with a local file system.

## Features

- [x] Pull Confluence pages (and their children) to a local filesystem path.

- [x] Push local changes back to Confluence, creating or updating pages as needed.

- [x] Local confluence representation contains version metadata, attachments

- [x] Support for attachments, allowing files to be downloaded and uploaded along with page content.

- [ ] Preserve version history (with possibilty for rollbacks)

- [ ] Better support for true sync features and edge cases. Github like blocked push if remote changes are needed. 

- [ ] Edit metadata (title, version, etc...) locally and have page metadata updated on the remote upon push 

- [ ] Better dry run visualization

- [ ] Parallelism for larger migrations

## Installation

### From Source

```sh
git clone https://github.com/ocasazza/csync.git
cd csync
pip install -e .
```

### Using pip

```sh
pip install csync
```

## Configuration

CSync can be configured using environment variables, a .env file, or a configuration file:

### Environment Variables

```sh
export CONFLUENCE_URL="https://your-instance.atlassian.net"
export CONFLUENCE_USERNAME="your-email@example.com"
export ATLASSIAN_TOKEN="your-api-token"
```

### .env File

Create a `.env` file in your current directory:

```
CONFLUENCE_URL=https://your-instance.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
ATLASSIAN_TOKEN=your-api-token
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

## Usage

### Command Line Interface

CSync provides a simple command-line interface for synchronizing Confluence pages with your local file system.

#### Basic Commands

```sh
# Get help
csync --help

# Get help for a specific command
csync pull --help
csync push --help
```

#### Pulling Pages from Confluence

```sh
# Pull a single page from Confluence to a local directory
csync pull https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages

# Pull a page and all its children recursively
csync pull --recurse https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages

# Pull with progress bars for better visibility
csync pull --progress https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages

# Perform a dry run to see what would be pulled without making changes
csync pull --dry-run https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages

# Combine options
csync pull --recurse --progress --dry-run https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages
```

#### Pushing Pages to Confluence

```sh
# Push a single page from a local directory to Confluence
csync push ./local-pages/my-page https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456

# Push a directory and all its subdirectories recursively
csync push --recurse ./local-pages https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456

# Push with progress bars for better visibility
csync push --progress ./local-pages https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456

# Perform a dry run to see what would be pushed without making changes
csync push --dry-run ./local-pages https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456

# Combine options
csync push --recurse --progress --dry-run ./local-pages https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456
```

#### Working with Spaces

```sh
# Pull an entire space
csync pull https://your-instance.atlassian.net/wiki/spaces/SPACE ./local-spaces/SPACE

# Push changes to an entire space
csync push ./local-spaces/SPACE https://your-instance.atlassian.net/wiki/spaces/SPACE
```

#### Advanced Usage

```sh
# Pull only pages that have changed since the last sync
csync pull --skip-unchanged https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages

# Push only pages that have changed locally
csync push --skip-unchanged ./local-pages https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456

# Specify a custom configuration file
csync pull --config /path/to/config.json https://your-instance.atlassian.net/wiki/spaces/SPACE/pages/123456 ./local-pages
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--progress` | Show progress bars during operations |
| `--recurse` | Process child pages recursively |
| `--dry-run` | Show changes without making them |
| `--skip-unchanged` | Skip pages that haven't changed |
| `--config PATH` | Specify a custom configuration file |
| `--verbose` | Enable verbose logging |
| `--quiet` | Suppress all output except errors |
