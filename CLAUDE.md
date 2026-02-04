# CLAUDE.md - MeerK40t Development Guide

## Project Overview

MeerK40t (pronounced "MeerKat") is an open-source laser cutting/engraving control software. It provides a highly extensible, plugin-based platform supporting multiple laser hardware types including K40 (Lihuiyu), GRBL, Ruida, Moshiboard, Newly, and galvo (Balor) lasers.

**Version:** 0.9.9000 (Active Development)
**License:** MIT
**Python:** 3.6+
**Platforms:** Windows, macOS, Linux, Raspberry Pi

See `NOTES.md` for current device stability status. See `.github/copilot-instructions.md` for an additional development reference.

---

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

---

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

1. **Kernel** (`meerk40t/kernel/`) - Service bus, plugin system, signals, channels, settings, jobs
2. **Core** (`meerk40t/core/`) - Element/node tree, operations, cutcode, planning, spooling, units
3. **Device** (`meerk40t/device/`) - Hardware abstraction layer and base device
4. **GUI** (`meerk40t/gui/`) - wxPython interface with AUI docking
5. **Drivers** - Hardware-specific: `grbl/`, `lihuiyu/`, `ruida/`, `moshi/`, `newly/`, `balormk/`
6. **Extra** (`meerk40t/extra/`) - File format parsers, tracing, fonts, parametric shapes, utilities

---

## Directory Structure

```
meerk40t/
├── meerk40t/
│   ├── kernel/          # Service bus, signals, channels, settings, jobs (15 files)
│   ├── core/            # Element/node tree, planning, cutcode, units, drivers (27+ files)
│   │   ├── node/        #   Node base class and all node type implementations
│   │   ├── elements/    #   Element tree service (management, selection, undo)
│   │   └── cutcode/     #   CutCode data structures and primitives
│   ├── device/          # Hardware abstraction (basedevice.py)
│   ├── gui/             # wxPython UI panels, dialogs, scene rendering
│   ├── grbl/            # GRBL driver
│   ├── lihuiyu/         # K40 (Lihuiyu) driver
│   ├── ruida/           # Ruida driver
│   ├── moshi/           # Moshiboard driver
│   ├── newly/           # Newly driver
│   ├── balormk/         # Balor galvo driver
│   ├── image/           # Image processing and rasterization tools
│   ├── fill/            # Hatch fills (scanline, Eulerian) and wobble patterns
│   ├── tools/           # Geometric algorithms
│   ├── extra/           # File parsers, tracing, fonts, utilities (22 modules)
│   ├── camera/          # OpenCV-based camera integration
│   ├── network/         # TCP/UDP/WebSocket servers for remote control
│   ├── dxf/             # DXF file I/O
│   ├── cylinder/        # Cylindrical material support
│   ├── rotary/          # Rotary engraving support
│   ├── ch341/           # USB communication driver
│   ├── svgelements.py   # Embedded SVG library (9,670 lines, v1.9.6 — excluded from lint/mypy)
│   ├── internal_plugins.py  # Registry of all built-in plugins (30+)
│   ├── external_plugins.py  # External plugin discovery via setuptools entry_points
│   └── main.py          # CLI entry point
├── test/                # 68 test files + bootstrap.py
├── testgui/             # GUI-specific tests (use mock_context)
├── docs/                # Build docs, performance notes, hardware PDFs
└── locale/              # Translations (use _() for user-facing strings)
```

---

## Kernel Internals (`kernel/`)

| File | Purpose |
|------|---------|
| `kernel.py` | Main kernel: plugin loading, signal queue, job scheduler, registration |
| `context.py` | Path-scoped wrapper around kernel; delegates signal/listen to kernel |
| `service.py` | `Service(Context)` — swappable named services with attach/detach lifecycle |
| `channel.py` | One-way broadcast channels (console output, device logs) |
| `settings.py` | ConfigParser-backed persistent settings (read/write on disk) |
| `jobs.py` | Schedulable `Job` objects (interval-based, repeating or one-shot) |
| `lifecycles.py` | Numeric lifecycle stage constants (not signals — passed to plugin functions) |
| `module.py` | Lightweight attachable modules (subset of Service) |
| `states.py` | State machine helpers |
| `inhibitor.py` | OS sleep prevention during long operations |
| `functions.py` | Shared utility functions |
| `exceptions.py` | Custom kernel exceptions |

---

## Signal & Channel System

### Signals — Event Broadcasting

Signals are the primary inter-component event mechanism. They are **kernel-global**, indexed by a string code. There is **no bubbling or hierarchical routing** — every listener registered for a code receives every signal with that code, regardless of which context emitted it.

```python
# Emit a signal (queued, not immediate)
context.signal("element_changed", some_data)
# Internally becomes: kernel.signal("element_changed", context._path, some_data)

# Listen for a signal
kernel.listen("element_changed", my_handler)

# Handler signature: first arg is the origin path, then the signal payload
def my_handler(origin, some_data):
    print(f"Signal from {origin}: {some_data}")

# Unregister
kernel.unlisten("element_changed", my_handler)
```

Key rules:
- **Deferred execution.** `signal()` and `listen()` queue work; actual dispatch happens in `process_queue()`, which runs at ~20 Hz via a scheduler job.
- **Late-binding.** A listener attached after a signal has fired receives the last message for that code immediately on attachment.
- **Lifecycle-object cookie.** Pass a cookie to `listen()` to batch-remove all listeners sharing that cookie later.
- **`@signal_listener` decorator.** Flag methods for automatic attachment when a service/module is registered:

```python
from meerk40t.kernel import signal_listener

class MyService(Service):
    @signal_listener("element_changed")
    def on_element_changed(self, origin, data):
        ...
```

### Channels — One-Way Output Streams

Channels are for output (console text, device logs). They do not participate in signal routing.

```python
channel = kernel.channel("console")
channel("This text goes to all watchers of 'console'")

# Subscribe / unsubscribe
channel.watch(my_print_function)
channel.unwatch(my_print_function)
```

Channels support optional circular buffers; new watchers can replay buffered history.

---

## Node Tree & Element System

### Tree Structure

The document is a strict hierarchy rooted at `RootNode`. It has exactly three top-level branches:

```
RootNode
├── BranchOperationsNode ("branch ops")
│   ├── CutOpNode ("op cut")
│   │   └── ReferenceNode ("reference") → points to an element
│   ├── EngraveOpNode ("op engrave")
│   ├── RasterOpNode ("op raster")
│   ├── ImageOpNode ("op image")
│   ├── DotsOpNode ("op dots")
│   ├── HatchEffectNode ("effect hatch")
│   ├── WobbleEffectNode ("effect wobble")
│   └── util nodes (console, wait, home, goto, input, output)
│
├── BranchElementsNode ("branch elems")
│   ├── FileNode / GroupNode / LayerNode  (containers)
│   └── element nodes:
│       ├── RectNode ("elem rect")
│       ├── PathNode ("elem path")
│       ├── EllipseNode ("elem ellipse")
│       ├── LineNode ("elem line")
│       ├── PolylineNode ("elem polyline")
│       ├── PointNode ("elem point")
│       ├── ImageNode ("elem image")
│       ├── TextNode ("elem text")
│       └── BlobNode ("blob")
│
└── BranchRegmarkNode ("branch reg")
    └── registration-mark elements
```

Operations do not directly contain elements. Instead they hold **ReferenceNodes** that point to elements in the elements branch. This keeps the element and operation graphs independent while allowing many-to-many relationships.

### Node Base Class (`core/node/node.py`)

Every node has: `type` (string), `_parent`, `_root`, `_children`, `_references`, and selection flags (`_emphasized`, `_highlighted`, `_targeted`).

Key operations:
```python
child = parent.add(type="elem rect", x=10, y=20, width=100, height=50)
parent.add_node(existing_node, pos=2)          # insert at index
operation.add_reference(element_node)          # creates a ReferenceNode
node.remove_node(children=True, destroy=True)
new_parent.append_child(node)                  # move node to new parent
```

Use `fast=True` on bulk operations to suppress per-node notifications and emit a single `structure_changed` instead.

### Node Notifications (Bubble Up to Root)

When a node changes, it calls `self.notify_*(node)`. The notification propagates up through `_parent` until it reaches `RootNode`. The root then dispatches to registered **tree listeners** (objects with matching `node_*` methods) and emits kernel signals.

```
node.notify_changed(node)
  → parent.notify_changed(node)
    → ... → RootNode.notify_changed(node)
              → for listener in self.listeners:
                    listener.node_changed(node)
              → kernel.signal("element_property_update", ...)
```

Common notify methods: `notify_created`, `notify_destroyed`, `notify_attached`, `notify_detached`, `notify_changed`, `notify_modified`, `notify_translated`, `notify_scaled`, `notify_reorder`.

Common kernel signals from tree operations: `"tree_changed"`, `"rebuild_tree"`, `"refresh_tree"`, `"element_property_update"`, `"refresh_scene"`, `"undoredo"`.

### Undo / Redo

Undo is snapshot-based: `undo.mark("description")` captures a full backup of the tree branches. Use the context-manager pattern for bulk changes:

```python
with elements_service.undoscope("My operation"):
    # perform tree modifications — notifications are paused
# single undo point created; "tree_changed" signal emitted on exit
```

---

## Job Pipeline

The path from user-facing operations to actual laser commands:

```
Operations (in tree)
    │
    ▼  copy selected ops
CutPlan.copy()
    │
    ▼  scene→device coordinate transform
CutPlan.preprocess()
    │
    ▼  validate constraints
CutPlan.validate()
    │
    ▼  convert ops/elements → CutCode primitives
CutPlan.blob()
    │
    ▼  add travel-optimization passes
CutPlan.preopt()
    │
    ▼  run optimizers (nearest-neighbor, inner-first, etc.)
CutPlan.optimize()
    │
    ▼  wrap in LaserJob
Spooler.laserjob(job)
    │
    ▼  execute items against driver
Driver.move_abs / laser_on / laser_off / ...
```

**CutCode primitives** (`core/cutcode/`): `LineCut`, `QuadCut`, `CubicCut`, `PlotCut`, `RasterCut`, `DwellCut`, `Homecut`, `GotoCut`, `WaitCut`, `InputCut`, `OutputCut`.

**PlotPlanner** (`core/plotplanner.py`) handles raster scan generation: converts CutCode into single-step (x, y, on/off) streams through a pipeline of manipulators (Single → PPI → Shift → Group).

**Driver interface** (`core/drivers.py`): Only `hold_work(priority)`, `get()`, `set()`, and `status()` are required. Everything else (`move_abs`, `laser_on`, etc.) is optional — calling code checks with `hasattr`.

---

## Core Concepts

### Units (`core/units.py`)

The internal unit is the **Tat** (1 inch = 65535 Tats). The `Length` class handles parsing and conversion:

```python
from meerk40t.core.units import Length

l = Length("5mm")
print(l.mm)          # 5.0
print(l.inches)      # 0.1968...
print(l.pixels)      # value at 96 DPI

# Relative lengths
half = Length("50%", relative_length="10cm")  # = 5cm
```

`Angle` works similarly with units: `rad`, `deg`, `grad`, `turn`.

### Geomstr (`core/geomstr.py`)

High-performance geometry engine using numpy arrays. Points are represented as complex numbers (`complex(x, y)`). Supports lines, quadratic/cubic beziers, arcs, polygons, scanline fill, boolean clipping, and pattern generation.

### svgelements.py

A 9,670-line embedded SVG path/shape library (based on svg.path and svgpathtools). Provides `Path`, `Line`, `CubicBezier`, `Arc`, `Rect`, `Circle`, `Matrix`, and SVG parsing. Excluded from linting and type checking due to size.

---

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
        pass  # Called when this service is activated

    def service_detach(self):
        pass  # Called when switching away
```

### Settings
```python
# Declare with type, key, and default — persisted to disk automatically
kernel.setting(int, "my_speed", 100)
context.setting(str, "label", "default")
```

### Tree Operations (context-menu items per node type)
```python
from meerk40t.core.treeop import tree_operation, tree_conditional

@tree_operation(registration, "my_op", node_type="elem rect", help="Do something")
@tree_conditional(lambda node: node.parent.type == "group")
def my_tree_op(node, **kwargs):
    # Modify node or tree
    pass
```

---

## Code Style

- **Formatter:** Black (88 char line length)
- **Linter:** flake8, pylint
- **Type Hints:** MyPy strict mode (excludes `svgelements.py`)
- **Classes:** PascalCase
- **Functions:** snake_case
- **Constants:** UPPER_CASE
- **Private:** Leading underscore
- **i18n:** Wrap all user-facing strings in `_()`

---

## Testing

Tests use unittest. The bootstrap system (`test/bootstrap.py`) spins up a full kernel with all core plugins, a dummy device, and fresh (non-persisted) settings:

```python
from test import bootstrap

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        kernel = bootstrap.bootstrap()
        try:
            # Run console commands
            kernel.console("rect 2cm 2cm 1cm 1cm\n")
            # Access services
            elements = kernel.elements
            # Assert
            self.assertEqual(...)
        finally:
            kernel()  # shutdown
```

Common patterns:
- **Console pipeline:** Build shapes, assign operations, plan, and generate output all via console commands chained with `\n`.
- **Profile isolation:** `bootstrap.bootstrap(profile="MyTest_GRBL")` prevents test state leaking.
- **Driver output tests:** Generate a laser job, save to file, compare G-code line-by-line.
- **Signal tests:** Call `kernel.signal(...)` then `kernel.process_queue()` to flush, then assert handler was called.

---

## Dependencies

**Core:** numpy, pyusb, pyserial, Pillow, requests

**Optional extras (defined in setup.py):**
- `gui` — wxPython >= 4.0.0, Pillow >= 7.0.0
- `dxf` — ezdxf >= 0.14.0
- `cam` — opencv-python-headless
- `camhead` — opencv-python (with GUI)

**Development:** pytest, flake8, black, mypy, pylint, isort

---

## Plugin Registry

### Internal Plugins (`internal_plugins.py`)

All 30+ built-in plugins registered at startup:

| Category | Plugins |
|----------|---------|
| Core | `core.core`, `device.basedevice`, `network.kernelserver` |
| Drivers | `lihuiyu`, `moshi`, `grbl`, `ruida`, `newly`, `balormk` |
| Hardware support | `rotary`, `cylinder`, `coolant` |
| Image & Fill | `image.imagetools`, `fill.fills`, `fill.patterns` |
| File formats | `dxf.plugin`, `extra.ezd`, `extra.lbrn`, `extra.xcs_reader` |
| Tracing | `extra.vectrace`, `extra.potrace`, `extra.vtracer` |
| Fonts & Shapes | `extra.hershey`, `extra.param_functions` |
| Integration | `extra.inkscape`, `extra.serial_exchange`, `extra.updater` |
| Camera | `camera.plugin` |
| GUI | `gui.plugin` |
| Other | `extra.imageactions`, `extra.outerworld`, `extra.winsleep`, `extra.cag` |

### External Plugins

Discovered automatically via the `meerk40t.extension` setuptools entry-point group. Each must expose a `plugin(kernel, lifecycle)` callable. Disabled with `--no-plugins` or if `lifecycle == "invalidate"` returns True.

---

## How-To Guides

### Add a Device Driver

1. Create `meerk40t/newdevice/` directory.
2. Implement three files:
   - `device.py` — `Service` subclass managing device state and settings.
   - `controller.py` — Low-level communication (USB/serial/network).
   - `driver.py` — Implements the driver interface (`hold_work`, `move_abs`, `laser_on`, etc.).
3. Create `plugin.py` with a `plugin(kernel, lifecycle)` function that registers the device.
4. Add the import to `internal_plugins.py`.

### Add a File Format

1. Create a module (new file in `extra/` or a new package).
2. Implement a reader function that parses the format and produces element nodes (call `elements.add_node(...)` or use console commands like `elem path ...`).
3. Register via `kernel.register("format/myformat", reader_func)` in your plugin's `"register"` lifecycle.
4. Add to `internal_plugins.py`.

### Add a New Operation Type

1. Create a node class in `core/node/` (subclass `Node`, set a `type` string like `"op myop"`).
2. Register it in `core/node/bootstrap.py` in the `bootstrap` dict.
3. Implement `as_cutobjects()` to produce CutCode primitives — this is what `CutPlan.blob()` calls.
4. Add any tree-operation context-menu entries using the `@tree_operation` decorator.

### Add a Console Command (end-to-end)

```python
# In your plugin's "register" lifecycle:
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":

        @kernel.console_command("greet", help="Greet the user")
        def greet_cmd(command, channel, _, name=None, **kwargs):
            channel(f"Hello, {name or 'world'}!")

        # With a subcommand that takes an argument:
        @kernel.console_argument("name", type=str, help="Name to greet")
        @kernel.console_command("greet", help="Greet someone")
        def greet_named(command, channel, _, name, **kwargs):
            channel(f"Hello, {name}!")
```

---

## Key Files

| File | Role |
|------|------|
| `main.py` | CLI entry point, argument parsing |
| `internal_plugins.py` | Built-in plugin registry |
| `external_plugins.py` | External plugin discovery (entry_points) |
| `kernel/kernel.py` | Kernel: plugin loading, signal queue, scheduler |
| `kernel/context.py` | Context: path-scoped kernel wrapper |
| `kernel/service.py` | Service: swappable named context |
| `kernel/channel.py` | Channel: one-way broadcast streams |
| `core/core.py` | Core plugin — registers elements service, operations |
| `core/node/node.py` | Base Node class, tree manipulation, notifications |
| `core/node/rootnode.py` | RootNode — tree root, listener dispatch |
| `core/elements/` | Element tree service (add/remove/select/undo) |
| `core/cutplan.py` | CutPlan — stages from operations to optimized CutCode |
| `core/spoolers.py` | Spooler — threaded job queue executor |
| `core/laserjob.py` | LaserJob — concrete job holding items for the driver |
| `core/plotplanner.py` | Raster plot stream generation |
| `core/drivers.py` | Abstract driver interface |
| `core/units.py` | Length / Angle unit system (native unit: Tat) |
| `core/geomstr.py` | High-performance numpy geometry engine |
| `core/undos.py` | Snapshot-based undo/redo |
| `core/treeop.py` | Tree operation (context-menu) registration decorators |
| `svgelements.py` | Embedded SVG path/shape library |
| `test/bootstrap.py` | Test kernel setup with all core plugins |
