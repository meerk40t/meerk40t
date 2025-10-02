# MeerK40t AI Coding Agent Instructions

## Architecture Overview

MeerK40t is a plugin-based laser cutting software built around a **Kernel** ecosystem. The system uses a sophisticated plugin lifecycle system where functionality is dynamically loaded and registered.

### Core Architecture Pattern
- **Kernel** (`meerk40t/kernel/`) - Central service bus providing signals, channels, settings, console commands
- **Core** (`meerk40t/core/`) - MeerK40t-specific ecosystem requirements (elements tree, cutplan optimization, etc.)
- **Device Drivers** (`meerk40t/{grbl,lihuiyu,ruida,moshi,newly}/`) - Hardware-specific laser control implementations
- **GUI** (`meerk40t/gui/`) - wxPython-based interface with AUI docking framework

### Critical Plugin Lifecycle
All modules follow the plugin pattern with lifecycle hooks:
```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/grbl", GRBLDevice)
    elif lifecycle == "postboot":
        init_commands(kernel)
```

Lifecycle phases: `plugins` → `preregister` → `register` → `configure` → `boot` → `postboot` → `start`

## Essential Development Patterns

### Device Driver Pattern
Each device type follows this structure:
- `device.py` - Main Device class inheriting from `Service` and `Status`
- `controller.py` - Communication protocol handler
- `driver.py` - Command translation layer (laser operations → device commands)
- `gui/` - Device-specific UI panels

Example: `meerk40t/grbl/device.py` shows the complete pattern with 700+ lines of device choices registration.

### Console Command Registration
Use decorators for command registration:
```python
@self.console_command("command_name", help=_("Description"))
def command_handler(channel, _, **kwargs):
    # Implementation
```

### Service Registration Pattern
Services are registered with domains and activated:
```python
kernel.add_service("elements", Elemental(kernel))
kernel.activate("elements", service)
```

### Node Tree Architecture
The elements system uses a tree structure (`meerk40t/core/node/node.py`):
- All objects inherit from `Node` with parent/children relationships
- Use `union_bounds()` for calculating bounding boxes across node collections
- Operations become nodes in the tree with type-specific behaviors

## Critical Workflows

### Testing
```bash
# Run all tests
python -m unittest discover test -v

# Run specific test
python -m unittest test.test_drivers_grbl
```

### Cut Planning Algorithm
The `CutPlan` system (`meerk40t/core/cutplan.py`) handles complex optimization:
- **Inner-first optimization**: Burns inner closed paths before outer paths
- **Travel optimization**: Minimizes laser head movement
- **Group optimization**: Processes related cuts together
- **Raster optimization**: Splits and optimizes raster operations

**Important**: When both `opt_inner_first=True` and `opt_inners_grouped=True`, ensure compatibility - the algorithms expect different input types (CutGroups vs individual cuts).

### Device Communication Flow
1. **LaserJob** creates cut operations
2. **Driver** translates to device-specific commands (G-code for GRBL, LHY-MicroGL for Lihuiyu)
3. **Controller** handles communication protocol
4. **Spooler** manages job queue and execution

## Common Conventions

### Error Handling
Use kernel channels for user communication:
```python
channel(_("Error message"))  # Translated message to user
```

### Settings Management
Device settings use choice dictionaries:
```python
choices = [{
    "attr": "setting_name",
    "object": self,
    "default": value,
    "type": bool,
    "label": _("Display Label"),
    "section": "_10_Category"
}]
self.register_choices("category", choices)
```

### Translation
Always wrap user-facing strings: `_("Text to translate")`

### Performance Optimization with Numba
When using Numba's `@njit` decorator, avoid redundant parameters:
```python
@njit(cache=True)  # Correct - nopython=True is implicit
def fast_function():
    pass
```
**Avoid**: `@njit(cache=True, nopython=True)` - causes runtime warnings

## Integration Points

### GRBL Variant Detection
`meerk40t/grbl/controller.py` implements sophisticated GRBL variant detection but results must be applied to:
- Buffer size configuration
- Command compatibility checking
- Timeout handling

### External Software Integration
- **Lightburn compatibility**: `ruidacontrol` command creates Ruida emulation
- **GRBL TCP**: `grblcontrol` command for remote GRBL access
- **File format support**: SVG, DXF import through dedicated modules

### Critical Performance Areas
- `union_bounds()` in Node.py - heavily used for GUI rendering
- Cut plan optimization algorithms - affect job execution time
- Raster processing - memory intensive for large images

## Testing Strategy

Focus test files are in `test/` directory:
- `test_drivers_*.py` - Hardware driver validation
- `test_cutplan_*.py` - Cut optimization algorithm validation
- `test_core_*.py` - Core functionality testing

When modifying cutplan algorithms, always run `test_grouped_inner_enhancement.py` to ensure inner-first optimization compatibility.
