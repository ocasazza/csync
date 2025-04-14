
## #csync-1
- [ ] cli arguments are not working as expected: 

```sh
venv➜  csync git:(main) ✗ csync push --help
Usage: csync push [OPTIONS] SOURCE DESTINATION

  Push local filesystem changes to Confluence.

  SOURCE: The local directory containing the pages to push. DESTINATION: The
  URL of the Confluence page or space to push to.

Options:
  --help  Show this message and exit.
.venv➜  csync git:(main) ✗ csync -help      
Usage: csync [OPTIONS] COMMAND [ARGS]...
Try 'csync --help' for help.

Error: No such option: -h
.venv➜  csync git:(main) ✗ csync help
Usage: csync [OPTIONS] COMMAND [ARGS]...
Try 'csync --help' for help.

Error: No such command 'help'.
.venv➜  csync git:(main) ✗ csync
Usage: csync [OPTIONS] COMMAND [ARGS]...

  csync - A command line program for Confluence page management.

  This tool allows you to pull Confluence pages to a local filesystem and push
  local changes back to Confluence.

Options:
  --version                   Show the version and exit.
  --progress / --no-progress  Show progress bars
  --recurse / --no-recurse    Process child pages recursively
  --dry-run                   Preview changes without writing
  --help                      Show this message and exit.

Commands:
  pull  Pull remote changes from Confluence to local file system.
  push  Push local filesystem changes to Confluence.
.venv➜  csync git:(main) ✗ csync push ./data/confluence/ITLC/Teams  https://schrodinger-sandbox.atlassian.net/wiki/spaces/ITLC/pages/225050695/Test+Teams --dry-run
Usage: csync push [OPTIONS] SOURCE DESTINATION
Try 'csync push --help' for help.

Error: No such option: --dry-run
```