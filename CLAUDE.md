# CLAUDE.md - MeerK40t Development Guide

## Project Overview

MeerK40t (pronounced "MeerKat") is an open-source laser cutting/engraving control software. It provides a highly extensible, plugin-based platform supporting multiple laser hardware types including K40 (Lihuiyu), GRBL, Ruida, Moshiboard, and galvo lasers.

**Version:** 0.9.9000 (Active Development)
**License:** MIT
**Python:** 3.6+
**Platforms:** Windows, macOS, Linux, Raspberry Pi

## Quick Commands

```bash
# Install with all features
pip install meerk40t[all]

# Run application
python -m meerk40t              # Full GUI
python -m meerk40t --no-gui     # Console mode
python -m meerk40t --simpleui   # Simplified interface

# Run tests
python -m unittest discover test -v
pytest -v

# Code quality
flake8 meerk40t test
black --check meerk40t test
mypy meerk40t
```

## Architecture

### Plugin-Based System

Everything is a plugin with lifecycle phases:
```
plugins → preregister → register → configure → boot → postboot → start
```

Standard plugin pattern:
```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("path/to/item", item)
    elif lifecycle == "boot":
        # Initialize
        pass
```

### Key Layers

1. **Kernel** (`meerk40t/kernel/`) - Service bus, plugin system, settings, messaging
2. **Core** (`meerk40t/core/`) - Element tree, operations, cutcode, planning, execution
3. **Device** (`meerk40t/device/`) - Hardware abstraction layer
4. **GUI** (`meerk40t/gui/`) - wxPython interface with AUI docking
5. **Drivers** - Hardware-specific: `grbl/`, `lihuiyu/`, `ruida/`, `moshi/`, `newly/`, `balormk/`

## Directory Structure

```
meerk40t/
├── meerk40t/
│   ├── kernel/          # Core service bus & plugin system
│   ├── core/            # Element tree, operations, planning
│   ├── device/          # Hardware abstraction
│   ├── gui/             # wxPython UI
│   ├── grbl/            # GRBL driver
│   ├── lihuiyu/         # K40 driver
│   ├── ruida/           # Ruida driver
│   ├── moshi/           # Moshiboard driver
│   ├── balormk/         # Galvo driver
│   ├── image/           # Image processing
│   ├── fill/            # Hatch/wobble fills
│   ├── tools/           # Geometric algorithms
│   ├── svgelements.py   # Embedded SVG library
│   └── main.py          # CLI entry point
├── test/                # Test suite
└── locale/              # Translations
```

## Core Concepts

### Element Tree
- Node-based hierarchical document structure
- Elements (shapes) and Operations (laser actions) as separate branches
- Undo/redo via snapshots

### Operations
- `op cut` - Vector cutting
- `op engrave` - Vector engraving
- `op raster` - Raster/image engraving
- `op image` - Direct image operations

### CutCode
Hierarchical laser operation data structure representing actual machine commands.

### Geomstr (`core/geomstr.py`)
High-performance geometry processing using numpy arrays. Complex numbers represent points.

## Code Patterns

### Console Commands
```python
@kernel.console_command("mycommand", help="Description")
def my_cmd(command, channel, _, **kwargs):
    channel("Output message")
```

### Services
```python
from meerk40t.kernel import Service

class MyService(Service):
    def __init__(self, kernel, path):
        super().__init__(kernel, path)

    def service_attach(self):
        pass  # Called when activated
```

### Channel Communication
```python
channel = kernel.channel("console")
channel("Message")
kernel.signal("event_name", data)
```

### Settings
```python
kernel.setting(type, "key", default_value)
context.setting(type, "key", default_value)
```

## Code Style

- **Formatter:** Black (88 char line length)
- **Linter:** flake8, pylint
- **Type Hints:** MyPy strict mode supported
- **Classes:** PascalCase
- **Functions:** snake_case
- **Constants:** UPPER_CASE
- **Private:** Leading underscore

## Testing

Tests use unittest with bootstrap system in `test/bootstrap.py`:
```python
from test import bootstrap
kernel = bootstrap.bootstrap()
```

Run specific test:
```bash
python -m unittest test.test_core
```

## Dependencies

**Core:**
- numpy, pyusb, pyserial, Pillow, requests, ezdxf

**GUI:**
- wxPython >= 4.0.0

**Development:**
- pytest, flake8, black, mypy, pylint

## Adding a Device Driver

1. Create `meerk40t/newdevice/` directory
2. Implement: `device.py`, `controller.py`, `driver.py`
3. Create `plugin.py` with registration
4. Register in `internal_plugins.py`

## Key Files

- `main.py` - CLI entry with argument parsing
- `internal_plugins.py` - Plugin registry
- `kernel/kernel.py` - Main kernel implementation
- `core/core.py` - Core plugin registrations
- `core/elements.py` - Element tree implementation
- `core/cutcode.py` - Laser operation structures
