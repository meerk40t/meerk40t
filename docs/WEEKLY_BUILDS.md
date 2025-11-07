# Weekly Binary Builds

This repository uses GitHub Actions to automatically build weekly binary releases of MeerK40t for Windows, macOS, and Linux.

## Workflows

### `weekly-binaries.yml`
- **Trigger**: Every Monday at 2 AM UTC (scheduled) or manual dispatch
- **Purpose**: Builds binaries for all supported platforms and creates a GitHub release
- **Platforms**:
  - Windows (32-bit executable)
  - macOS (universal binary)
  - Linux (AppImage-style executable)
- **Output**: Creates a new GitHub release tagged `weekly-{run_number}` with all binaries attached

### `cleanup-weekly-builds.yml`
- **Trigger**: Every day at 3 AM UTC (scheduled) or manual dispatch
- **Purpose**: Removes weekly releases older than 60 days
- **Behavior**:
  - Identifies all releases with tags starting with `weekly-`
  - Deletes releases created more than 60 days ago
  - Provides detailed logging of cleanup actions

## Binary Storage

Weekly binaries are stored as GitHub releases with the following naming convention:
- `MeerK40t-windows-{run_number}.exe` (Windows)
- `MeerK40t-macos-{run_number}` (macOS)
- `MeerK40t-linux-{run_number}` (Linux)

## Manual Triggers

Both workflows can be triggered manually:
1. Go to the Actions tab in GitHub
2. Select the desired workflow
3. Click "Run workflow"

## Retention Policy

- **Artifacts**: Kept for 60 days (GitHub Actions default)
- **Releases**: Kept for 60 days, then automatically cleaned up
- **Cleanup**: Runs daily to ensure old releases are removed

## Build Process

The build process uses PyInstaller to create standalone executables:

1. **Dependencies**: Installs all required Python packages and system dependencies
2. **Bootloader**: Compiles PyInstaller bootloaders for deterministic builds
3. **Build**: Uses platform-specific PyInstaller specs from `.github/workflows/{platform}/`
4. **Package**: Creates compressed executables ready for distribution

## Platform-Specific Notes

### Windows
- Builds 32-bit executables for compatibility with libusb
- Uses custom PyInstaller spec file for optimal packaging

### macOS
- Creates universal binaries compatible with Intel and Apple Silicon
- Includes all required frameworks and libraries

### Linux
- Builds AppImage-style executables
- Includes system library dependencies

## Troubleshooting

### Build Failures
- Check the Actions logs for detailed error messages
- Ensure all dependencies are properly specified in requirements files
- Verify PyInstaller spec files are up to date

### Cleanup Issues
- Cleanup failures are logged but don't affect the build process
- Manual cleanup can be performed by running the cleanup workflow manually
- Check repository permissions if cleanup fails due to API access issues

## Security Considerations

- Builds run in isolated GitHub Actions environments
- No sensitive data is stored in the repository
- All artifacts are publicly accessible via GitHub releases
- Automatic cleanup prevents accumulation of old binaries
