# MeerK40t AI Coding Agent Instructions

## Environment & Platform Context

**Operating System**: Windows (PowerShell)
- Use native PowerShell cmdlets (e.g., `Remove-Item` instead of `rm`, `Get-ChildItem` instead of `ls`, `Set-Location` instead of `cd`)
- For Python testing, create script files rather than inline execution to avoid PowerShell quoting issues
- When running tests, use: `python -m unittest discover test -v` (PowerShell-compatible)

## Architecture Overview

MeerK40t is a plugin-based laser cutting software built around a **Kernel** ecosystem. The system uses a sophisticated plugin lifecycle system where functionality is dynamically loaded and registered.

### Core Architecture Pattern
- **Kernel** (`meerk40t/kernel/`) - Central service bus providing signals, channels, settings, console commands
- **Core** (`meerk40t/core/`) - MeerK40t-specific ecosystem requirements (elements tree, cutplan optimization, etc.)
- **Device Drivers** (`meerk40t/{grbl,lihuiyu,ruida,moshi,newly,balormk}/`) - Hardware-specific laser control implementations
- **GUI** (`meerk40t/gui/`) - wxPython-based interface with AUI docking framework

### Critical Plugin Lifecycle
All modules follow the plugin pattern with lifecycle hooks. The plugin function must be defined at module level:

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/grbl", GRBLDevice)
    elif lifecycle == "postboot":
        init_commands(kernel)
    elif lifecycle == "boot":
        # Initialize during boot phase
        pass
```

Lifecycle phases (in order): `plugins` → `preregister` → `register` → `configure` → `boot` → `postboot` → `start`

**Where to add plugin code**: Each module should have a `plugin.py` file (or the main `__init__.py`) that exports the `plugin()` function.

### Internal vs External Plugins

**Internal Plugins** (`meerk40t/internal_plugins.py`):
- Core functionality bundled with MeerK40t
- Registered in `internal_plugins.py` during the `plugins` lifecycle phase
- Examples: core, device drivers, GUI components, image tools
- To add: Import and append to the plugins list in `internal_plugins.py`

**External Plugins** (`meerk40t/external_plugins.py`):
- Third-party extensions loaded via Python entry points
- Entry point group: `meerk40t.extension`
- Automatically discovered at runtime (not in frozen builds)
- To create: Define entry point in `setup.py` or `pyproject.toml`:
  ```python
  entry_points={
      "meerk40t.extension": [
          "myplugin = mypackage.plugin:plugin",
      ],
  }
  ```

**Important**: External plugins are disabled in frozen builds (PyInstaller executables). Use `external_plugins_build.py` for hardcoded plugins in builds.

## Essential Development Patterns

### Device Driver Pattern
Each device type follows this structure:
- `device.py` - Main Device class inheriting from `Service` and `Status`
- `controller.py` - Communication protocol handler
- `driver.py` - Command translation layer (laser operations → device commands)
- `gui/` - Device-specific UI panels
- `plugin.py` - Plugin lifecycle and registration

**Example location**: `meerk40t/grbl/device.py` shows the complete pattern with 1300+ lines of device choices registration.

**How to add a new device driver**:
1. Create a new directory under `meerk40t/` (e.g., `meerk40t/newdevice/`)
2. Implement `device.py`, `controller.py`, `driver.py` following existing driver patterns
3. Create `plugin.py` with registration in the `register` lifecycle phase
4. Register the device provider: `kernel.register("provider/device/newdevice", NewDevice)`
5. Add GUI components in `gui/` subdirectory if needed

### Console Command Registration

Console commands can be registered at the kernel level or service level. Use the appropriate decorator based on context:

**For Kernel-level commands** (available globally):
```python
from meerk40t.kernel.functions import kernel_console_command

@kernel_console_command("command_name", help=_("Description"))
def command_handler(command, channel, _, **kwargs):
    """Long help text goes in docstring"""
    channel(_("Command executed"))
    return "elements", data  # Optional: return context type and data
```

**For Service-level commands** (within a Service class):
```python
from meerk40t.kernel.functions import console_command

class MyService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        # Commands are registered automatically via decorator
    
    @console_command("service_command", help=_("Service command description"))
    def my_command(self, command, channel, _, **kwargs):
        """Long help text in docstring"""
        channel(_("Service command executed"))
        # self refers to the Service instance
```

**For Kernel instance commands** (when you have kernel reference):
```python
def init_commands(kernel):
    @kernel.console_command("init_command", help=_("Init command"))
    def cmd_handler(command, channel, _, **kwargs):
        channel(_("Initialized command"))
```

**Key points**:
- `channel` is used for user-visible messages (always use `_()` for translation)
- The second parameter (often `_`) is the remainder string after command parsing
- Return value can be `(context_type, data)` to pass data to next command in pipeline
- Help text is short description, docstring is long help

### Service Registration Pattern
Services are registered with domains and activated:

```python
from meerk40t.kernel.service import Service

class MyService(Service):
    def __init__(self, kernel):
        super().__init__(kernel, "domain_name")
        # Service initialization

def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        service = MyService(kernel)
        kernel.add_service("domain_name", service)
        kernel.activate("domain_name", service)  # Activate immediately
```

Services extend the kernel context with domain-specific attributes accessible via `kernel.domain_name`.

### Node Tree Architecture
The elements system uses a tree structure (`meerk40t/core/node/node.py`):
- All objects inherit from `Node` with parent/children relationships
- Use `union_bounds()` for calculating bounding boxes across node collections
- Operations become nodes in the tree with type-specific behaviors
- Nodes have lifecycle methods: `added()`, `removed()`, `modified()`

**Important**: When working with nodes, always update parent relationships properly and call appropriate lifecycle methods.

## Critical Workflows

### Adding a New Feature

**Step-by-step process**:

1. **Determine the appropriate module**:
   - **Core functionality** → `meerk40t/core/` - Elements tree, cutplan, operations, node system
   - **Device driver** → `meerk40t/{driver_name}/` - Hardware-specific implementations
   - **GUI component** → `meerk40t/gui/` - wxPython interface components
   - **Tool/utility** → `meerk40t/tools/` - Internal tools, or `meerk40t/extra/` - Optional features
   - **Hardware abstraction** → `meerk40t/device/` - Base device classes
   - **File format support** → `meerk40t/dxf/` - DXF import/export, SVG via `svgelements.py`
   - **Network features** → `meerk40t/network/` - Network protocols and servers
   - **Image processing** → `meerk40t/image/` - Image tools and processing
   - **Fill patterns** → `meerk40t/fill/` - Fill pattern generators

2. **Follow plugin pattern**:
   - Create or update `plugin.py` (or module `__init__.py`)
   - Implement `plugin(kernel, lifecycle=None)` function
   - Register components in appropriate lifecycle phase
   - For internal plugins: Add to `meerk40t/internal_plugins.py` if it's a new top-level module

3. **Add console commands** (if needed):
   - Use appropriate decorator (`@kernel_console_command` or `@console_command`)
   - Wrap user-facing strings with `_()` for translation
   - Use `channel()` for user messages

4. **Add tests**:
   - Create test file in `test/` directory (or `testgui/` for GUI tests)
   - Follow naming: `test_*.py`
   - Import test utilities from `test.bootstrap` or `testgui.bootstrap`
   - For GUI tests, use `testgui.mock_context` for mocking

5. **Update documentation**:
   - Add README.md in module directory if adding new module
   - Update relevant README files if extending existing functionality

6. **Run code quality checks** (see Code Quality Tools section)

### Testing

**Running tests in Windows PowerShell**:
```powershell
# Run all tests
python -m unittest discover test -v

# Run specific test module
python -m unittest test.test_drivers_grbl -v

# Run specific test class
python -m unittest test.test_drivers_grbl.TestGRBLDriver -v

# Run specific test method
python -m unittest test.test_drivers_grbl.TestGRBLDriver.test_specific_method -v
```

**Test file structure**:
```python
import unittest
from meerk40t.kernel import Kernel

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        self.kernel = Kernel()
        # Initialize kernel and register plugins
    
    def test_my_feature(self):
        # Test implementation
        pass
```

**Key test files by area**:
- `test_drivers_*.py` - Hardware driver validation
- `test_cutplan_*.py` - Cut optimization algorithm validation
- `test_core_*.py` - Core functionality testing
- `test_node_*.py` - Node tree operations
- `testgui/test_*.py` - GUI component testing (requires wxPython)

**GUI Testing**:
- GUI tests are in `testgui/` directory
- Use `testgui.mock_context` for creating mock kernel contexts
- GUI tests require wxPython and may need special setup

### Cut Planning Algorithm

The `CutPlan` system (`meerk40t/core/cutplan.py`) handles complex optimization:

**Optimization stages**:
1. **Inner-first optimization**: Burns inner closed paths before outer paths
2. **Travel optimization**: Minimizes laser head movement between cuts
3. **Group optimization**: Processes related cuts together
4. **Raster optimization**: Splits and optimizes raster operations

**Critical compatibility issue**: When both `opt_inner_first=True` and `opt_inners_grouped=True`:
- The algorithms expect different input types (CutGroups vs individual cuts)
- Always test with `test_grouped_inner_enhancement.py` when modifying cutplan code
- Ensure compatibility by checking input type expectations in optimization functions
- Look at how `preopt_inner_first()` and `preopt_inners_grouped()` handle input preparation

**When modifying cutplan code**:
1. Run `test_grouped_inner_enhancement.py` to verify compatibility
2. Run `test_cutplan_optimization.py` and `test_cutplan_travel_optimization.py`
3. Verify both optimization modes work independently and together

### Device Communication Flow

The device communication architecture follows this flow:

1. **LaserJob** creates cut operations from elements tree
2. **Driver** (`driver.py`) translates to device-specific commands:
   - GRBL: G-code commands
   - Lihuiyu: LHY-MicroGL protocol
   - Ruida: Ruida protocol commands
3. **Controller** (`controller.py`) handles low-level communication protocol
4. **Spooler** manages job queue and execution

**When implementing device communication**:
- Follow existing driver patterns (see `meerk40t/grbl/` as reference)
- Implement proper error handling and reconnection logic
- Use kernel channels for status updates to user
- Handle thread safety for communication operations

## Common Conventions

### Error Handling
Always use kernel channels for user communication:
```python
channel(_("Error: Device not connected"))  # Translated message to user
channel(_("Warning: Low power setting"))   # Warnings
channel(_("Info: Operation complete"))     # Informational messages
```

**Never use** `print()` for user-facing messages - always use `channel()`.

### Settings Management
Device settings use choice dictionaries with specific structure:

```python
from meerk40t.kernel import Kernel

class MyDevice(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        # Define choices
        choices = [{
            "attr": "setting_name",      # Attribute name on self
            "object": self,              # Object that has the attribute
            "default": default_value,    # Default value
            "type": bool,                # Type: bool, int, float, str
            "label": _("Display Label"), # User-visible label
            "section": "_10_Category",   # Settings section (sorted by prefix)
            "tip": _("Helpful tooltip"), # Optional tooltip
        }]
        # Register choices
        self.register_choices("category", choices)
```

**Section naming**: Use numeric prefixes for ordering (e.g., `_10_General`, `_20_Advanced`).

### Translation (Internationalization)
Always wrap user-facing strings with `_()` function:
```python
channel(_("Text to translate"))
label = _("Button Label")
help_text = _("Help text for users")
```

**Where translation is NOT needed**:
- Internal variable names
- Debug/logging messages (unless shown to user)
- Technical identifiers

The `_()` function is provided by the kernel's translation system.

**Translation Workflow**:
- Translation files are in `locale/` directory
- Main translation file: `locale/messages.po`
- Locale-specific files: `locale/{lang}/LC_MESSAGES/messages.po`
- Use `translate.py` script to manage translations:
  ```powershell
  # Compile translations
  python translate.py
  
  # Force recompilation
  python translate.py --force
  
  # Integrate delta files
  python translate.py --integrate
  
  # Process specific locales
  python translate.py de fr es
  ```
- Translation validation: `translate_check.py` checks for errors
- Always run translation checks before committing changes that add new translatable strings

### Code Style & Formatting

The project uses multiple code quality tools configured in `pyproject.toml`:

**Formatting Tools**:
- **Black**: Code formatter (line length: 88, Python 3.6+)
- **isort**: Import sorting (Black profile, line length: 88)

**Linting Tools**:
- **flake8**: Style guide enforcement (max line length: 88, max complexity: 10)
- **pylint**: Comprehensive code analysis (configured with extensive rules)
- **mypy**: Static type checking (excludes `svgelements.py`)

**Before committing code**:
1. Format with Black: `black meerk40t/`
2. Sort imports: `isort meerk40t/`
3. Check with flake8: `flake8 meerk40t/`
4. Run pylint if needed: `pylint meerk40t/`

**Code Style Guidelines**:
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names (snake_case for functions/variables, PascalCase for classes)
- Add docstrings for classes and public functions
- Keep functions focused and reasonably sized
- Maximum line length: 88 characters
- Maximum complexity: 10 (flake8 default)
- Use type hints where appropriate (mypy support)

### Performance Optimization with Numba

When using Numba's `@njit` decorator for performance-critical code:

```python
from numba import njit

@njit(cache=True)  # Correct - nopython=True is implicit
def fast_function(data):
    # Numba-optimized code
    return result
```

**Avoid**: `@njit(cache=True, nopython=True)` - `nopython=True` is implicit and causes runtime warnings.

**Important**: Numba requires specific code patterns - avoid Python objects, use NumPy arrays, and keep logic simple.

## Integration Points

### External Software Integration
- **Lightburn compatibility**: `ruidacontrol` command creates Ruida emulation
- **GRBL TCP**: `grblcontrol` command for remote GRBL access
- **File format support**: SVG, DXF import through dedicated modules (`meerk40t/dxf/`, SVG through `svgelements.py`)

### Critical Performance Areas
These areas are performance-critical and changes should be carefully tested:

- `union_bounds()` in `Node.py` - heavily used for GUI rendering, must be efficient
- Cut plan optimization algorithms - directly affect job execution time
- Raster processing - memory intensive for large images, watch for memory leaks
- Geomstr operations - geometric calculations used throughout the codebase

### Node Tree Operations

When working with the node tree:
- Always use `node.added()` and `node.removed()` lifecycle methods
- Update parent references when moving nodes
- Use `union_bounds()` for efficient bounding box calculations
- Be careful with circular references in parent/child relationships

## Common Pitfalls & How to Avoid Them

### Pitfall 1: Incorrect Console Command Registration
**Problem**: Using `@self.console_command` outside a Service class
**Solution**: Use `@kernel_console_command` for kernel-level commands, or ensure you're inside a Service class

### Pitfall 2: Forgetting Translation
**Problem**: User-facing strings not wrapped with `_()`
**Solution**: Always wrap user-visible text: `channel(_("Message"))`

### Pitfall 3: Using print() Instead of channel()
**Problem**: Using `print()` for user messages
**Solution**: Always use `channel()` - it provides proper user interface integration

### Pitfall 4: Breaking CutPlan Compatibility
**Problem**: Modifying cutplan algorithms without testing both optimization modes
**Solution**: Always run `test_grouped_inner_enhancement.py` and related tests

### Pitfall 5: Incorrect Plugin Lifecycle Phase
**Problem**: Registering services or commands in wrong lifecycle phase
**Solution**: 
- `register` phase: Register providers and services
- `postboot` phase: Initialize commands that depend on registered services
- `boot` phase: Early initialization that doesn't depend on other plugins

### Pitfall 6: Numba Decorator Misuse
**Problem**: Using `nopython=True` explicitly with `@njit`
**Solution**: Use `@njit(cache=True)` - `nopython=True` is implicit

### Pitfall 7: Thread Safety Issues
**Problem**: Modifying shared state without proper locking in device communication
**Solution**: Use kernel's threading utilities, check existing driver implementations for patterns

### Pitfall 8: Not Testing on Windows
**Problem**: Assuming Unix-style commands work in PowerShell
**Solution**: Use PowerShell cmdlets and create test scripts instead of inline commands

## Testing Strategy

### Priority Test Files
When making changes, run relevant test suites:

**Core functionality**:
- `test_core_*.py` - Core system tests
- `test_kernel.py` - Kernel functionality

**Cut planning** (critical for optimization changes):
- `test_cutplan_optimization.py` - General optimization
- `test_cutplan_travel_optimization.py` - Travel optimization
- `test_grouped_inner_enhancement.py` - **MUST RUN** when modifying inner-first/grouped optimization

**Device drivers**:
- `test_drivers_*.py` - Specific driver tests
- Test the specific driver you're modifying

**Node tree**:
- `test_node_*.py` - Node operations and tree integrity

### Test Execution Best Practices

1. **Run tests before and after changes** to catch regressions
2. **Run specific test suites** related to your changes
3. **Use verbose mode** (`-v`) to see detailed output
4. **Create test scripts** for complex test scenarios (PowerShell-friendly)
5. **Test both positive and negative cases**

## Dependencies & Requirements

The project uses multiple requirements files for different scenarios:

- **`requirements.txt`** - Core dependencies (numpy, pyusb, pyserial, wxPython, etc.)
- **`requirements-dev.txt`** - Development dependencies (pytest, flake8, polib, chardet)
- **`requirements-nogui.txt`** - Dependencies for headless operation (no wxPython)
- **`requirements-optional-*.txt`** - Platform-specific optional dependencies

**Installation**:
```powershell
# Full installation with GUI
pip install -r requirements.txt

# Development environment
pip install -r requirements.txt -r requirements-dev.txt

# Headless installation
pip install -r requirements-nogui.txt
```

**Setup.py extras**:
- `pip install meerk40t[all]` - All optional dependencies
- `pip install meerk40t[gui]` - GUI dependencies only
- `pip install meerk40t[cam]` - Camera support
- `pip install meerk40t[dxf]` - DXF import/export

## Application Entry Point

The main application entry point is `meerk40t/main.py`:
- Defines `APPLICATION_NAME` and `APPLICATION_VERSION`
- Version detection: Automatically appends "git", "src", or "pkg" based on environment
- Command-line argument parsing for various modes (GUI, console, daemon, etc.)
- Initializes Kernel and loads internal/external plugins
- Entry point: `meerk40t.py` or `python -m meerk40t.main`

**Key command-line arguments**:
- `-z, --no-gui` - Run without GUI
- `-c, --console` - Start as console
- `-e, --execute` - Execute console command
- `-a, --auto` - Start running laser automatically
- `-p, --no-plugins` - Disable external plugins

## Quick Reference

### File Locations
- **Core kernel**: `meerk40t/kernel/`
- **Core functionality**: `meerk40t/core/` (elements, cutplan, operations)
- **Device drivers**: `meerk40t/{grbl,lihuiyu,ruida,moshi,newly,balormk}/`
- **GUI components**: `meerk40t/gui/`
- **Tools**: `meerk40t/tools/` (internal) or `tools/` (build scripts)
- **Extra features**: `meerk40t/extra/` (optional features)
- **Tests**: `test/` (unit tests) and `testgui/` (GUI tests)
- **Documentation**: Module `README.md` files
- **Translations**: `locale/` directory
- **Build scripts**: `tools/` directory

### Import Patterns
```python
from meerk40t.kernel import Kernel
from meerk40t.kernel.functions import kernel_console_command, console_command
from meerk40t.kernel.service import Service
from meerk40t.core.node.node import Node
```

### Lifecycle Phases
`plugins` → `preregister` → `register` → `configure` → `boot` → `postboot` → `start`

### Key Decorators
- `@kernel_console_command(...)` - Kernel-level commands
- `@console_command(...)` - Service-level commands (within Service class)
- `@kernel.console_command(...)` - When you have kernel instance

### Essential Functions
- `channel(_("message"))` - User messaging
- `_("text")` - Translation wrapper
- `kernel.register("path", object)` - Register providers/services
- `kernel.add_service("domain", service)` - Register service
- `kernel.activate("domain", service)` - Activate service

### Module Organization Guide

**When to add code where**:
- **`meerk40t/kernel/`** - Core kernel functionality (don't modify unless extending kernel itself)
- **`meerk40t/core/`** - MeerK40t-specific core features (elements, operations, cutplan)
- **`meerk40t/device/`** - Base device classes and device management
- **`meerk40t/{driver}/`** - Specific device driver implementations
- **`meerk40t/gui/`** - All wxPython GUI components
- **`meerk40t/tools/`** - Internal tools and utilities used by the application
- **`meerk40t/extra/`** - Optional features (coolant, vectrace, potrace, etc.)
- **`meerk40t/image/`** - Image processing and tools
- **`meerk40t/fill/`** - Fill pattern generators
- **`meerk40t/dxf/`** - DXF file format support
- **`meerk40t/network/`** - Network protocols and server functionality
- **`tools/`** (root) - Build scripts and development utilities

### Code Quality Tools Quick Reference

**Formatting**:
```powershell
# Format code
black meerk40t/

# Sort imports
isort meerk40t/

# Check formatting (dry run)
black --check meerk40t/
```

**Linting**:
```powershell
# Run flake8
flake8 meerk40t/

# Run pylint (may be slow)
pylint meerk40t/

# Type checking
mypy meerk40t/
```

**Translation**:
```powershell
# Compile translations
python translate.py

# Check source code for new translatable strings
python translate_check.py all

# Check for translation errors
python translate_check.py --validate all
```
