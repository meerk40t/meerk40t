# Development Tools

This directory contains build scripts, development utilities, and automation tools for MeerK40t development and deployment.

## Build Scripts

### Windows Build Scripts

#### build_win.cmd
Windows batch script for building MeerK40t executables using PyInstaller.

**Features:**
- Configures build-specific plugin loading
- Handles file renaming conflicts with PyInstaller
- Creates Windows executable distributions
- Restores original file structure after build

**Usage:**
```cmd
# Build Windows executable
tools\build_win.cmd
```

**Requirements:**
- Python environment with MeerK40t installed
- PyInstaller installed
- Windows development environment

#### build_icon.cmd
Windows script for generating application icons with version overlays.

**Features:**
- Creates multi-resolution ICO files for Windows
- Generates ICNS files for macOS
- Adds version number overlays to icons
- Produces PNG versions for Linux AppImages

**Usage:**
```cmd
# Generate icons with version number
tools\build_icon.cmd 0.9.75
```

**Requirements:**
- ImageMagick installed and in PATH
- Source images in `images/` directory:
  - `meerk40t.png` (main icon)
  - `meerk40t_simple.png` (overlay icon)

**Generated Files:**
- `meerk40t.ico` - Windows icon (16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
- `.github\workflows\mac\meerk40t.icns` - macOS icon
- `meerk40t.png` - Linux AppImage icon (256x256)

#### build_pypi.cmd
Script for building and publishing Python packages to PyPI.

**Features:**
- Creates source distributions and wheels
- Handles package metadata and dependencies
- Supports PyPI upload automation

### Unix Build Scripts

#### build.sh
Unix shell script for building MeerK40t executables on Linux/macOS.

**Features:**
- Cross-platform executable building
- Virtual environment detection
- Automatic file management for builds
- Distribution naming with platform information

**Usage:**
```bash
# Build executable
./tools/build.sh
```

**Requirements:**
- Python environment with MeerK40t installed
- PyInstaller (in venv, local, or system-wide)
- Linux/macOS development environment

**Output:**
- Creates `dist/MeerK40t-Linux-Ubuntu-22.04` directory

#### build_icon.sh
Shell script equivalent of build_icon.cmd for Unix systems.

**Features:**
- ImageMagick-based icon generation
- Version overlay support
- Cross-platform icon format generation

## Development Utilities

### analyze_wiki_quality.py
Python script for analyzing the quality and completeness of generated wiki documentation.

**Features:**
- Scans wiki pages for placeholder content
- Identifies insufficient documentation
- Provides quality metrics and recommendations
- Categorizes pages by documentation completeness

**Usage:**
```bash
# Analyze wiki quality
python tools/analyze_wiki_quality.py

# Analyze specific wiki directory
python tools/analyze_wiki_quality.py /path/to/wiki
```

**Analysis Categories:**
- **Insufficient**: Pages with placeholder content or minimal information
- **Minimal**: Basic documentation present but needs expansion
- **Adequate**: Good coverage with room for improvement
- **Good**: Comprehensive documentation

**Detection Patterns:**
- Placeholder text like "*Add a detailed description*"
- TODO/FIXME markers
- Empty or skeleton sections
- Missing screenshots or examples

### generate_help_wiki.py
Comprehensive script for extracting help documentation from the MeerK40t codebase and generating wiki pages.

**Features:**
- Parses Python source code for docstrings and help text
- Extracts console command documentation
- Generates structured markdown wiki pages
- Supports automatic upload to GitHub wiki repository

**Usage:**
```bash
# Generate wiki pages locally
python tools/generate_help_wiki.py

# Generate and upload to wiki repository
python tools/generate_help_wiki.py --upload
```

**Generated Content:**
- Console command documentation
- Feature explanations
- Usage examples
- Troubleshooting guides
- API references

**Output Structure:**
- Creates `../wiki-pages/` directory
- Generates `Online-Help-{section}.md` files
- Preserves existing wiki content when possible
- Updates with new documentation from code

## CI/CD Integration

### GitHub Actions Integration

These tools are designed to work with MeerK40t's GitHub Actions workflows:

**Build Workflows:**
- `build_win.cmd` → `.github/workflows/win/`
- `build.sh` → `.github/workflows/linux/`
- `build_icon.*` → Icon generation for all platforms

**Documentation Workflows:**
- `generate_help_wiki.py` → Automated wiki updates
- `analyze_wiki_quality.py` → Documentation quality checks

### Automated Builds

**Windows CI:**
```yaml
- name: Build Windows executable
  run: tools\build_win.cmd
```

**Linux CI:**
```yaml
- name: Build Linux executable
  run: ./tools/build.sh
```

**Icon Generation:**
```yaml
- name: Generate icons
  run: tools/build_icon.cmd ${{ github.ref_name }}
```

## Development Workflow

### Building for Development

1. **Prepare Environment:**
   ```bash
   # Install build dependencies
   pip install pyinstaller

   # For icon generation
   # Install ImageMagick (platform-specific)
   ```

2. **Build Executable:**
   ```bash
   # Windows
   tools\build_win.cmd

   # Linux/macOS
   ./tools/build.sh
   ```

3. **Generate Icons:**
   ```bash
   # Windows
   tools\build_icon.cmd 0.9.75

   # Linux/macOS
   ./tools/build_icon.sh 0.9.75
   ```

### Documentation Maintenance

1. **Update Wiki Documentation:**
   ```bash
   # Generate new wiki pages
   python tools/generate_help_wiki.py

   # Analyze documentation quality
   python tools/analyze_wiki_quality.py
   ```

2. **Review and Upload:**
   - Review generated files in `../wiki-pages/`
   - Upload to GitHub wiki repository
   - Address any quality issues identified

## Requirements

### System Dependencies

**ImageMagick (for icon generation):**
```bash
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick

# Windows
# Download from https://imagemagick.org/
# Add to PATH
```

**PyInstaller (for executable building):**
```bash
pip install pyinstaller
```

### Python Dependencies

**Wiki Documentation Tools:**
```bash
pip install -r requirements-dev.txt  # Includes required packages
```

## File Organization

```
tools/
├── build_win.cmd          # Windows executable build
├── build.sh               # Unix executable build
├── build_icon.cmd         # Windows icon generation
├── build_icon.sh          # Unix icon generation
├── build_pypi.cmd         # PyPI package build
├── analyze_wiki_quality.py # Wiki quality analysis
└── generate_help_wiki.py  # Wiki documentation generation
```

## Contributing

### Adding New Build Scripts

1. **Follow naming conventions:**
   - `build_*.cmd` for Windows batch scripts
   - `build_*.sh` for Unix shell scripts
   - `*.py` for Python utilities

2. **Include documentation:**
   - Usage examples
   - Requirements
   - Platform compatibility
   - Error handling

3. **Test across platforms:**
   - Windows, macOS, Linux compatibility
   - CI/CD integration testing
   - Error condition handling

### Updating Documentation Tools

1. **Maintain backward compatibility**
2. **Update analysis patterns** in `analyze_wiki_quality.py`
3. **Test with existing wiki content**
4. **Validate generated markdown syntax**

## Troubleshooting

### Common Build Issues

**PyInstaller File Conflicts:**
- Scripts handle `meerk40t.py` renaming automatically
- Ensure no files are locked during build

**Icon Generation Failures:**
- Verify ImageMagick installation: `magick -version`
- Check source image paths in `images/` directory
- Ensure write permissions for output directories

**Wiki Generation Issues:**
- Check Python path and imports
- Verify GitHub wiki repository access for `--upload`
- Review generated markdown for syntax errors

### Platform-Specific Notes

**Windows:**
- Use `build_*.cmd` scripts
- Ensure ImageMagick is in PATH
- Run as Administrator for system integration

**macOS:**
- Use `build_*.sh` scripts
- Install ImageMagick via Homebrew
- Code signing may be required for distribution

**Linux:**
- Use `build_*.sh` scripts
- Install ImageMagick via package manager
- Test with different desktop environments

This tools directory provides the infrastructure for MeerK40t's build pipeline, documentation system, and development workflow automation.