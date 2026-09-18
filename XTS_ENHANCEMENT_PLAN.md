# XTS Enhancement Implementation Plan

## Completed Today
✅ XTS Schema (JSON Schema for validation)
✅ XTS Validator (validate command with --verbose, --json)
✅ XTS Wizard (interactive create/edit with CTRL-C save/resume)
✅ XTS Tools Plugin (validate, create, edit commands)
✅ Fixed xts installation and xts_allocator.xts YAML error

## Requested Enhancements

### 1. og.xts Conversion (High Priority)
Convert ~/git/fast/git-tools/og bash script to .xts format

**og Commands to Convert:**
- `current_branch` (-cb) - Display current branch with oneline info
- `branch` (-b) - Display branch info for current directory
- `branches` (-B) - Display branch info for all directories
- `status` (st) - Perform git status on directories
- `cmd` (-c) - Run custom command in each repo
- `url` (-u) - Get clickable URLs from git remote
- `remote` (-r) - Display git remotes
- `review` (-rv) - Run review.sh if present
- `.` - List all git repos found recursively

**Switches:**
- `--search` (-s) - Add search criteria
- `--line` (-l) - Add line spacing
- `--directory` (-d) - Restrict directory pattern
- `--num` (-n) - Limit lines displayed
- `--verbose` (-v) - Verbose output

### 2. Enhanced Alias System (High Priority)

#### Directory Scanning
```bash
# Add single file
xts alias add mytools /path/to/config.xts

# Add all .xts in directory
xts alias add mytools /path/to/directory/

# Recursive directory scan
xts alias add mytools -r /path/to/directory/

# Remote URL
xts alias add allocator http://server:5000/xts_allocator.xts

# Remote directory (GitHub/GitLab)
xts alias add rdktools https://github.com/user/repo/tree/main/xts-configs/
```

#### Features Needed:
- Scan directories for `*.xts` files
- Recursive `-r` flag
- Absolute path conversion for local files
- URL support for remote files
- Prompt for confirmation when multiple files found

### 3. Remote File Caching (High Priority)
**Cache Location:** `~/.xts/cache/`

**Metadata Stored:**
```json
{
  "url": "http://server:5000/xts_allocator.xts",
  "local_path": "~/.xts/cache/allocator_xts_allocator.xts",
  "last_modified": "2026-02-09T14:00:00Z",
  "etag": "abc123def456",
  "hash": "sha256:...",
  "cached_at": "2026-02-09T14:00:00Z"
}
```

**Features:**
- Download remote .xts on first use
- Store HTTP headers (Last-Modified, ETag)
- Check for updates on command execution
- `xts alias refresh <name>` to force update
- Show update indicator in `xts alias list`

### 4. Include/Import Mechanism (Medium Priority)
**Schema Extension:**
```yaml
includes:
  - /absolute/path/to/common.xts
  - ~/.xts/shared/formatters.xts
  - relative/path/utils.xts

functions:
  # Local functions

commands:
  # Local commands
```

**Features:**
- Merge included files recursively
- Detect circular dependencies
- Override resolution (local > included)
- Relative paths resolved from parent file location

### 5. Absolute Path Resolution (High Priority)
- Convert relative paths to absolute on `xts alias add`
- Store absolute paths in alias config
- Works from any directory after registration
- Resolve `~` to actual home directory

### 6. Version Tracking & Updates (High Priority)
**Alias List with Updates:**
```
Available aliases:
  allocator     [↑ UPDATE AVAILABLE]
  og            [✓ UP TO DATE]
  mytools       [LOCAL]
```

**Commands:**
```bash
xts alias list           # Show all with update status
xts alias check <name>   # Check specific alias for updates
xts alias refresh <name> # Force refresh from source
xts alias refresh --all  # Refresh all remote aliases
```

### 7. Deprecation System (Medium Priority)
**Schema Extension:**
```yaml
commands:
  old_command:
    description: "Legacy command (deprecated)"
    deprecated: true
    deprecated_message: "Use 'new_command' instead"
    deprecated_since: "2.0.0"
    removal_in: "3.0.0"
    command: echo "Running deprecated command"
```

**User Experience:**
```bash
$ xts myalias old_command
⚠️  WARNING: Command 'old_command' is deprecated since v2.0.0
    Use 'new_command' instead
    This command will be removed in v3.0.0
    
[command output...]
```

## Implementation Priority

### Phase 1 (This Session - Critical)
1. ✅ XTS validation & creation tools (DONE)
2. Enhanced alias system with directory scanning
3. Absolute path resolution
4. Basic remote URL support

### Phase 2 (Next Session - High Value)
5. Remote file caching with update tracking
6. Update notifications in alias list
7. og.xts conversion

### Phase 3 (Future - Nice to Have)
8. Include/import mechanism
9. Deprecation warnings system
10. Advanced caching strategies

## Files to Modify

### xts_core Changes:
- `src/xts_core/xts_alias.py` - Enhanced alias management
- `src/xts_core/xts_schema.json` - Add includes, deprecated fields
- `src/xts_core/xts.py` - Include resolution logic
- `src/xts_core/utils.py` - Add caching utilities
- `requirements.txt` - Add `requests` for URL fetching

### New Files:
- `~/.xts/config.json` - Alias configuration with metadata
- `~/.xts/cache/` - Remote file cache directory
- `xts_allocator_server/og.xts` - Converted og tool

## Current Status
- ✅ Core validation infrastructure complete
- ✅ Interactive wizard with progress saving
- ⏳ Ready to implement alias enhancements
- ⏳ Ready to convert og tool

## Next Steps
Would you like me to:
1. Start with enhanced alias system (directory scanning + absolute paths)?
2. Convert og tool to og.xts first?
3. Implement remote caching system?

The most logical order would be: alias enhancements → og conversion → caching system
