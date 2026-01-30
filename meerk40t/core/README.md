# MeerK40t Core Module

## Overview

The Core Module forms the heart of MeerK40t's laser cutting ecosystem, providing the fundamental data structures, services, and processing pipeline that transform user designs into laser operations. This module implements the complete laser workflow from element storage through optimization to hardware control.

## Architecture

```
meerk40t/core/
├── core.py                 # Main plugin registrar for all core services
├── drivers.py              # Driver abstraction layer for laser hardware
├── geomstr.py              # High-performance geometric data structures (9003 lines)
├── parameters.py           # Laser parameter definitions and validation (710 lines)
├── exceptions.py           # MeerK40t-specific exception hierarchy
├── logging.py              # Job execution logging and event tracking
├── laserjob.py             # Spooler job execution system
├── bindalias.py            # Bind/alias system for kernel commands
├── cutcode/                # Laser operation data structures
├── cutplan.py              # Cut planning and optimization algorithms
├── elements/               # Element tree and node management
├── laserjob.py             # Laser job execution framework
├── node/                   # Node type definitions and hierarchy
├── planner.py              # Job planning and cutcode generation
├── plotplanner.py          # Pulse-level laser control algorithms
├── space.py                # Coordinate system conversions
├── spoolers.py             # Job queue management system
├── svg_io.py               # SVG file input/output operations
├── treeop.py               # Tree operation decorators and utilities
├── undos.py                # Undo/redo system for tree state
├── units.py                # Unit conversion and management
├── view.py                 # Viewport transformation matrices
├── webhelp.py              # Web-based help system
└── wordlist.py             # Dynamic text replacement system
```

### Core Data Flow Pipeline

```
Elements → Operations → Planning → CutCode → LaserJob → Spooler → Driver → Hardware
    ↓         ↓           ↓         ↓         ↓         ↓         ↓         ↓
  Storage  Processing  Optimization  Execution  Queueing  Hardware  Control  Laser
```

## Core Services & Components

### Plugin Registration System (`core.py`)
The central orchestrator that registers all core services with the MeerK40t kernel:

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        return [
            spoolers.plugin,      # Job queue management
            space.plugin,         # Coordinate transformations
            elements.plugin,      # Element tree service
            penbox.plugin,        # Penbox operations
            logging.plugin,       # Event logging
            bindalias.plugin,     # Command binding
            webhelp.plugin,       # Help system
            planner.plugin,       # Job planning
            svg_io.plugin         # File I/O
        ]
```

### Driver Abstraction Layer (`drivers.py`)
Hardware-independent interface for laser control:

```python
class Driver:
    """Base driver class providing common laser control interface"""

    def hold_work(self, priority):  # Required by spooler
        """Pause job execution"""

    def move_abs(self, x, y):       # Absolute positioning
        """Move laser head to absolute coordinates"""

    def move_rel(self, dx, dy):     # Relative positioning
        """Move laser head relative to current position"""

    def laser_on(self, power):      # Laser activation
        """Enable laser with specified power"""

    def laser_off(self):            # Laser deactivation
        """Disable laser output"""
```

**Key Features:**
- Hardware abstraction for different laser types
- State management (rapid, program, raster modes)
- Settings storage and retrieval
- Error handling and status reporting

### Parameter Management System (`parameters.py`)
Comprehensive parameter definitions for laser operations (710 lines):

```python
INT_PARAMETERS = (
    "power", "passes", "loops", "acceleration",
    "dot_length", "jog_distance", "coolant"
)

FLOAT_PARAMETERS = (
    "speed", "rapid_speed", "dpi", "dratio",
    "dwell_time", "frequency", "kerf"
)

BOOL_PARAMETERS = (
    "laser_enabled", "job_enabled", "bidirectional",
    "ppi_enabled", "shift_enabled", "advanced"
)
```

**Features:**
- Type-safe parameter validation
- Unit conversion support
- Driver-specific parameter mapping
- Settings inheritance and override

### Geomstr Geometric Data Structure (`geomstr.py`)
High-performance geometric processing library (9003 lines) providing the foundation for all geometric operations in MeerK40t:

```python
class Geomstr:
    """High-performance geometric data structure using aligned numpy arrays"""

    def line(self, start, end):
        """Add line segment from start to end point"""

    def quad(self, start, control, end):
        """Add quadratic Bezier curve"""

    def cubic(self, start, control1, control2, end):
        """Add cubic Bezier curve"""

    def arc(self, start, control, end):
        """Add circular arc segment"""

    def transform(self, matrix):
        """Apply affine transformation to all geometry"""
```

**Key Features:**
- **Memory Efficient**: Aligned numpy arrays store geometric primitives in compact format
- **Primitive Types**: Lines, quadratic/cubic Bezier curves, arcs, points with complex number representation
- **Path Operations**: Run-based geometry with implicit connections between adjacent segments
- **Transformation Support**: Matrix-based affine transformations and coordinate system conversions
- **Performance Optimized**: Numba JIT compilation for critical geometric operations
- **Geometric Analysis**: Intersection detection, bounding box calculations, path simplification

**Core Architecture:**
- **Complex Number Storage**: Uses 5-element complex arrays per primitive: `[start, control1, type_info, control2, end]`
- **Type System**: 16 distinct geometric types (lines, curves, arcs, structural elements)
- **Vertex Topology**: Graph-based vertex relationships for complex path structures
- **Run Optimization**: Connected geometry segments processed as efficient runs

**Advanced Operations:**
- **Stitching**: Automatic geometry connection with tolerance-based endpoint matching
- **Scanbeam Processing**: Efficient polygon filling and clipping algorithms
- **Path Simplification**: Visvalingam-Wyatt algorithm for curve optimization
- **Intersection Detection**: Fast line-line and curve-curve intersection calculations

### Logging Service (`logging.py`)
Comprehensive job execution tracking:

```python
class Logging(Service):
    """Event logging and job execution tracking"""

    def event(self, event_dict):
        """Log structured event data"""

    def matching_events(self, prefix, **filters):
        """Query logged events with filtering"""
```

**Capabilities:**
- Job completion logging
- Performance metrics tracking
- Error event recording
- Persistent storage with settings system

### LaserJob Execution Framework (`laserjob.py`)
Spooler job implementation with advanced features:

```python
class LaserJob:
    def __init__(self, label, items, driver=None, priority=0, loops=1):
        self.items = items          # CutCode objects to execute
        self.loops = loops          # Number of execution passes
        self.priority = priority    # Queue priority
        self.runtime = 0            # Execution time tracking
        self.steps_done = 0         # Progress tracking
        self._estimate = 0          # Time estimation
```

**Features:**
- Multi-pass job execution
- Progress tracking and statistics
- Time estimation from CutCode analysis
- Loop management (including infinite loops)
- Priority-based queue ordering

## Major Subsystems

### CutCode System (`cutcode/`)
Hierarchical laser operation data structures (see `cutcode/README.md` for details):

**Cut Types:**
- **Vector Cuts**: LineCut, QuadCut, CubicCut for geometric shapes
- **Raster Operations**: RasterCut, PlotCut for image engraving
- **Control Operations**: DwellCut, GotoCut, WaitCut for laser control
- **Hierarchical**: CutGroup, CutCode for organization and optimization

**Key Features:**
- Inner-first optimization algorithms
- Multi-pass support with burn tracking
- Travel distance minimization
- Settings inheritance and sharing

### Elements System (`elements/`)
Complete element tree management (see `elements/README.md` for details):

**Functional Areas:**
- **Tree Operations**: Node manipulation, clipboard, undo/redo
- **Shape Management**: Creation, editing, alignment of geometric elements
- **Operations**: Laser operation definitions and management
- **Materials**: Material database and operation presets
- **Penbox**: Per-loop command modifications

### Node Hierarchy (`node/`)
Type system for all tree elements (see `node/README.md` for details):

**Node Categories:**
- **Structural**: RootNode, branch nodes (operations, elements, regmarks)
- **Operations**: op_cut, op_engrave, op_raster, op_image, op_dots
- **Elements**: elem_path, elem_rect, elem_ellipse, elem_text, elem_image
- **Effects**: effect_hatch, effect_warp, effect_wobble
- **Utilities**: util_wait, util_home, util_goto, util_input, util_output

### Planning & Optimization (`planner.py`, `cutplan.py`)
Job planning and cutcode generation:

```python
# Convert operations + elements to optimized cutcode
def plan_cutcode(elements_branch, operations_branch):
    """Generate optimized CutCode from scene elements"""
    # 1. Associate elements with operations
    # 2. Generate cutcode for each operation
    # 3. Apply optimization algorithms
    # 4. Return optimized CutCode sequence
```

**Optimization Features:**
- Travel minimization algorithms
- Inner-first processing
- Group optimization for related cuts
- Speed and power optimization

### Plot Planning (`plotplanner.py`)
Low-level pulse control for laser hardware:

**Algorithms:**
- Pulse plotting for vector cuts
- PPI (Pulses Per Inch) control
- Step direction optimization
- Power modulation for curves
- Dashing and pulsing patterns

**Hardware-Specific:**
- Optimized for Lihuiyu devices (limited line functions)
- Step-by-step movement generation
- Quality vs. speed tradeoffs

### Spooler System (`spoolers.py`)
Job queue management and execution:

```python
class Spooler(Service):
    """Job queue management service"""

    def queue(self, job):
        """Add job to execution queue"""

    def unqueue(self, job):
        """Remove job from queue"""

    def execute_next(self):
        """Execute next job in queue"""
```

**Features:**
- Priority-based job ordering
- Concurrent job execution
- Pause/resume capabilities
- Job status tracking and reporting

### Coordinate Systems (`space.py`)
Scene-to-device coordinate transformations:

```python
class Space(Service):
    """Coordinate system management"""

    def scene_to_device(self, x, y):
        """Convert scene coordinates to device coordinates"""

    def device_to_scene(self, x, y):
        """Convert device coordinates to scene coordinates"""
```

### Units Management (`units.py`)
Comprehensive unit conversion system:

```python
class Length:
    """Length with unit conversion"""
    def __init__(self, value, unit='mm'):
        self.value = value
        self.unit = unit

    def mm(self): return convert_to_mm(self.value, self.unit)
    def inch(self): return convert_to_inch(self.value, self.unit)
```

### View Transformations (`view.py`)
4-point to 4-point coordinate transformations:

```python
class View:
    """Viewport transformation matrix"""

    def transform(self, x, y):
        """Apply perspective transformation"""
```

### Undo/Redo System (`undos.py`)
Tree state management for editing operations:

```python
class Undo:
    """Undo/redo stack management"""

    def undo(self):
        """Revert to previous tree state"""

    def redo(self):
        """Restore previously undone state"""

    def save(self, description):
        """Save current state to undo stack"""
```

### Bind/Alias System (`bindalias.py`)
Dynamic command binding and aliasing:

```python
# Bind commands to keys or events
kernel.bind("command", "F1", "help")
kernel.alias("quit", "shutdown")
```

### Web Help System (`webhelp.py`)
Integrated help system with web-based documentation:

```python
# Register help URIs
kernel.register("webhelp/tutorial", "https://meerk40t.org/tutorial")
```

### Wordlist System (`wordlist.py`)
Dynamic text replacement for job customization.

The Wordlist system provides dynamic variable substitution for text elements used in
jobs (e.g., "Hello {NAME}"). It supports three *types* of variables:

- **Static** (single string value)
- **CSV/Array** (multiple values, with a current position)
- **Counter** (integer that increments)

Key points and API overview:

- Keys are normalized (trimmed and lower-cased). Passing `None`, non-string, or
  whitespace-only keys to set/get operations is treated as invalid and ignored.
- Common helpers:
  - `has_value(key, entry)` — returns `True` if the given entry exists for `key`.
  - `add_value_unique(key, entry, wtype=None)` — attempts to add `entry` and
    returns `(added: bool, reason: Optional[str])` where `reason` can be
    `"duplicate"`, `"empty"`, or `"invalid_key"` (or `None` when successfully added).
- Load/save and validation:
  - `load_data(filename)` loads persisted JSON and records any issues; query
    them with `get_load_warnings()` / `has_load_warnings()`.
  - `validate_content()` performs structural checks and returns a list of issues found.

Examples:

```python
# Simple use
wl = Wordlist("1.2.3")
wl.add("name", "John")
print(wl.translate("Hello {name}"))  # "Hello John"

# add_value_unique returns a tuple
added, reason = wl.add_value_unique("people", "Alice")
if not added:
    print("Not added:", reason)

# Inspect load warnings after loading from a file
wl.load_data("wordlist.json")
if wl.has_load_warnings():
    print(wl.get_load_warnings())

# Validate current content
issues = wl.validate_content()
if issues:
    for issue in issues:
        print("Wordlist issue:", issue)
```

This system is used by the GUI panel `WordlistPanel` and the mini controls `WordlistMiniPanel` for advancing and editing entries.
## Integration Patterns

### Service Registration
All core components register as services with the kernel:

```python
kernel.add_service("elements", Elemental(kernel))
kernel.add_service("spooler", Spooler(kernel))
kernel.activate("elements", service)
```

### Channel Communication
Components communicate through typed channels:

```python
# Create communication channels
status_channel = kernel.channel("status")
error_channel = kernel.channel("error")

# Send/receive messages
status_channel("Job completed")
error_channel.watch(error_handler)
```

### Settings Management
Hierarchical settings with inheritance:

```python
# Global settings
kernel.setting(str, "units", "mm")

# Device-specific overrides
device.setting(float, "bed_width", 300.0)

# Operation-specific parameters
operation.setting(int, "power", 1000)
```

## Usage Examples

### Basic Laser Job Creation
```python
from meerk40t.core.elements import Elemental
from meerk40t.core.planner import Planner

# Get services
elements = kernel.elements
planner = kernel.planner

# Create elements
rect = elements.add_rect(0, 0, 100, 100)

# Create operation
cut_op = elements.add_operation("Cut", speed=100, power=1000)
cut_op.add_reference(rect)

# Plan and execute
cutcode = planner.plan_cutcode()
job = LaserJob("Test Job", [cutcode])
kernel.spooler.queue(job)
```

### Custom Driver Implementation
```python
from meerk40t.core.drivers import Driver

class MyLaserDriver(Driver):
    def __init__(self, context):
        super().__init__(context, "my-laser")

    def move_abs(self, x, y):
        # Hardware-specific movement command
        self.send_command(f"MOVE {x},{y}")

    def laser_on(self, power):
        # Power control implementation
        self.send_command(f"LASER ON {power}")
```

### Parameter Validation
```python
from meerk40t.core.parameters import validate_parameter

# Validate laser parameters
power = validate_parameter("power", 1000, int)  # Returns validated int
speed = validate_parameter("speed", 50.0, float)  # Returns validated float
enabled = validate_parameter("laser_enabled", True, bool)  # Returns validated bool
```

## Performance & Optimization

### Cut Planning Optimizations
- **Travel Minimization**: Shortest path algorithms for laser head movement
- **Inner-First Processing**: Burn contained shapes before outer shapes
- **Group Optimization**: Process related operations together
- **Speed Optimization**: Adjust parameters for quality vs. speed tradeoffs

### Memory Management
- **Lazy Evaluation**: Expensive operations calculated on-demand
- **Reference Counting**: Efficient node sharing and cleanup
- **Streaming Processing**: Large jobs processed in chunks
- **Cache Management**: Frequently used data cached in memory

### Execution Optimization
- **Threading**: Concurrent job processing where possible
- **Priority Queues**: High-priority jobs executed first
- **Resource Pooling**: Connection and buffer reuse
- **Statistics Tracking**: Performance monitoring and optimization

## Error Handling & Validation

### Comprehensive Validation
- **Parameter Bounds Checking**: Prevent invalid laser settings
- **Geometry Validation**: Ensure valid cut paths
- **Resource Checking**: Verify hardware availability
- **State Validation**: Confirm system readiness

### Graceful Degradation
- **Fallback Modes**: Continue operation with reduced functionality
- **Error Recovery**: Automatic retry for transient failures
- **Logging**: Comprehensive error tracking and reporting
- **User Feedback**: Clear error messages through channels

## Testing & Quality Assurance

### Unit Testing
- Individual component testing
- Parameter validation testing
- Algorithm correctness verification
- Performance benchmarking

### Integration Testing
- End-to-end job execution testing
- Multi-device compatibility testing
- File format round-trip testing
- Network protocol testing

### Performance Testing
- Large job processing benchmarks
- Memory usage profiling
- CPU utilization monitoring
- Hardware interface latency testing

## Future Enhancements

### Planned Improvements
- **Advanced Optimization**: Machine learning-based path optimization
- **Real-time Processing**: Live parameter adjustment during execution
- **Cloud Integration**: Remote job processing and storage
- **Multi-head Support**: Coordinated multi-laser operations
- **Material Recognition**: Automatic parameter selection based on material
- **Quality Prediction**: AI-based quality assessment and correction

### Extension Points
- **Custom Drivers**: Hardware-specific driver implementations
- **New Operations**: Custom laser operation types
- **Optimization Plugins**: Third-party optimization algorithms
- **Import/Export**: Additional file format support
- **UI Extensions**: Custom control panels and tools

## Contributing

When contributing to the core module:

1. **Maintain Compatibility**: Ensure changes don't break existing APIs
2. **Add Tests**: Comprehensive test coverage for new functionality
3. **Document Changes**: Update relevant README files
4. **Performance Conscious**: Consider impact on large jobs and slow hardware
5. **Thread Safety**: Ensure thread-safe operation in multi-threaded environment
6. **Error Handling**: Robust error handling with clear user feedback
7. **Code Style**: Follow established patterns and conventions

## Related Modules

- **kernel**: Core service management and channel system
- **device**: Hardware-specific implementations and drivers
- **gui**: Graphical user interface components
- **tools**: Command-line utilities and batch processing
- **test**: Comprehensive test suite and validation tools

This core module provides the foundation for MeerK40t's laser cutting capabilities, implementing a sophisticated pipeline from design to hardware control with extensive optimization and error handling features.
