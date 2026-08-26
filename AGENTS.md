# AGENTS.md - MeerK40t Development Guide

This is the single source of truth for AI coding agents working on MeerK40t.
Other agent instruction files (`CLAUDE.md`, `.github/copilot-instructions.md`)
point here and must not be treated as separate references.

## Project Overview

MeerK40t (pronounced "MeerKat") is an open-source laser cutting/engraving control software. It provides a highly extensible, plugin-based platform supporting multiple laser hardware types including K40 (Lihuiyu), GRBL, Ruida, Moshiboard, Newly, and galvo (Balor) lasers.

**License:** MIT
**Python:** 3.6+
**Platforms:** Windows, macOS, Linux, Raspberry Pi
**Version:** defined as `APPLICATION_VERSION` in `meerk40t/main.py` (avoid hard-coding it here — check the source)

See `NOTES.md` for current device stability status.

---

## Quick Commands

```bash
# Install with all features
pip install meerk40t[all]

# Run application
meerk40t                        # Installed console script (full GUI)
python meerk40t.py              # From a source checkout
python meerk40t.py --no-gui     # Console mode
python meerk40t.py --simpleui   # Simplified interface

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

Standard plugin pattern (the `plugin()` function **must** be defined at module level):
```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("path/to/item", item)
    elif lifecycle == "postboot":
        init_commands(kernel)
    elif lifecycle == "boot":
        # Initialize during boot phase
        pass
```

Lifecycle phase usage:
- `register`: Register providers, services, and formats
- `boot`: Early initialization that doesn't depend on other plugins
- `postboot`: Initialize commands that depend on registered services

### Internal vs External Plugins

**Internal Plugins** (`meerk40t/internal_plugins.py`): Core functionality bundled with MeerK40t, registered during the `plugins` lifecycle phase. To add one, import it and append to the plugins list.

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

**External Plugins** (`meerk40t/external_plugins.py`): Third-party extensions discovered automatically via the `meerk40t.extension` setuptools entry-point group:

```python
entry_points={
    "meerk40t.extension": [
        "myplugin = mypackage.plugin:plugin",
    ],
}
```

External plugins are disabled with `--no-plugins`, disabled in frozen builds (PyInstaller executables; use `external_plugins_build.py` for hardcoded plugins there), and invalidated if `lifecycle == "invalidate"` returns True.

### Key Layers

1. **Kernel** (`meerk40t/kernel/`) - Service bus, plugin system, signals, channels, settings, jobs
2. **Core** (`meerk40t/core/`) - Element/node tree, operations, cutcode, planning, spooling, units
3. **Device** (`meerk40t/device/`) - Hardware abstraction layer and base device
4. **GUI** (`meerk40t/gui/`) - wxPython interface with AUI docking
5. **Drivers** - Hardware-specific integrations under `vendors/`: `grbl/`, `lihuiyu/`, `ruida/`, `moshi/`, `newly/`, `balormk/`, `ch341/`
6. **Extra** (`meerk40t/extra/`) - File format parsers, tracing, fonts, parametric shapes, utilities

---

## Directory Structure

```
meerk40t/
├── meerk40t/
│   ├── kernel/          # Service bus, signals, channels, settings, jobs
│   ├── core/            # Element/node tree, planning, cutcode, units, drivers
│   │   ├── node/        #   Node base class and all node type implementations
│   │   ├── elements/    #   Element tree service (management, selection, undo)
│   │   └── cutcode/     #   CutCode data structures and primitives
│   ├── device/          # Hardware abstraction (basedevice.py)
│   ├── vendors/         # Vendor-specific device drivers (incl. grbl/, lihuiyu/, ruida/, moshi/, newly/, balormk/, ch341/)
│   ├── gui/             # wxPython UI panels, dialogs, scene rendering
│   ├── image/           # Image processing and rasterization tools
│   ├── fill/            # Hatch fills (scanline, Eulerian) and wobble patterns
│   ├── tools/           # Geometric algorithms
│   ├── extra/           # File parsers, tracing, fonts, utilities
│   ├── camera/          # OpenCV-based camera integration
│   ├── network/         # TCP/UDP/WebSocket servers for remote control
│   ├── dxf/             # DXF file I/O
│   ├── cylinder/        # Cylindrical material support
│   ├── rotary/          # Rotary engraving support
│   ├── ch341/           # USB communication driver
│   ├── svgelements.py   # Embedded SVG library (9,670 lines — excluded from lint/mypy)
│   ├── internal_plugins.py  # Registry of all built-in plugins (30+)
│   ├── external_plugins.py  # External plugin discovery via setuptools entry_points
│   └── main.py          # CLI entry point
├── test/                # Unit tests + bootstrap.py
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
| `settings.py` | ConfigParser-backed persistent settings |
| `jobs.py` | Schedulable `Job` objects (interval-based, repeating or one-shot) |
| `lifecycles.py` | Numeric lifecycle stage constants (passed to plugin functions) |
| `module.py` | Lightweight attachable modules (subset of Service) |
| `states.py` | State machine helpers |
| `inhibitor.py` | OS sleep prevention during long operations |
| `functions.py` | Shared utility functions (incl. console command decorators) |
| `exceptions.py` | Custom kernel exceptions |

---

## Signal & Channel System

### Signals — Event Broadcasting

Signals are the primary inter-component event mechanism. They are **kernel-global**, indexed by a string code. There is **no bubbling or hierarchical routing** — every listener registered for a code receives every signal with that code.

```python
# Emit a signal (queued, not immediate)
context.signal("element_changed", some_data)

# Listen / unlisten
def my_handler(origin, some_data):  # first arg is origin path
    ...
kernel.listen("element_changed", my_handler)
kernel.unlisten("element_changed", my_handler)
```

Key rules:
- **Deferred execution.** Dispatch happens in `process_queue()` at ~20 Hz via a scheduler job.
- **Late-binding.** A listener attached after a signal has fired receives the last message for that code immediately on attachment.
- **Lifecycle-object cookie.** Pass a cookie to `listen()` to batch-remove listeners later.
- **`@signal_listener` decorator** flags methods for automatic attachment when the service/module is registered:

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
channel.watch(my_print_function)
channel.unwatch(my_print_function)
```

Channels support optional circular buffers; new watchers can replay buffered history.

---

## Node Tree & Element System

The document is a strict hierarchy rooted at `RootNode` (`core/node/rootnode.py`) with exactly three top-level branches:

```
RootNode
├── BranchOperationsNode ("branch ops")
│   ├── CutOpNode ("op cut"), EngraveOpNode, RasterOpNode,
│   │   ImageOpNode, DotsOpNode
│   ├── HatchEffectNode ("effect hatch"), WobbleEffectNode
│   ├── ReferenceNode → points to an element
│   └── util nodes (console, wait, home, goto, input, output)
├── BranchElementsNode ("branch elems")
│   ├── FileNode / GroupNode / LayerNode (containers)
│   └── element nodes: RectNode, PathNode, EllipseNode, LineNode,
│       PolylineNode, PointNode, ImageNode, TextNode, BlobNode
└── BranchRegmarkNode ("branch reg")
    └── registration-mark elements
```

Operations do not directly contain elements — they hold **ReferenceNodes** pointing at elements in the elements branch, keeping the two graphs independent while allowing many-to-many relationships.

### Node Base Class (`core/node/node.py`)

Every node has: `type` (string), `_parent`, `_root`, `_children`, `_references`, and selection flags (`_emphasized`, `_highlighted`, `_targeted`).

```python
child = parent.add(type="elem rect", x=10, y=20, width=100, height=50)
parent.add_node(existing_node, pos=2)          # insert at index
operation.add_reference(element_node)          # creates a ReferenceNode
node.remove_node(children=True, destroy=True)
new_parent.append_child(node)                  # move node to new parent
```

Use `fast=True` on bulk operations to suppress per-node notifications and emit a single `structure_changed` instead.

When working with nodes:
- Call `node.added()` and `node.removed()` lifecycle methods appropriately.
- Update parent references when moving nodes.
- Be careful with circular references in parent/child relationships.

### Node Notifications (Bubble Up to Root)

When a node changes it calls `self.notify_*(node)`; the call propagates up through `_parent` to `RootNode`, which dispatches to registered tree listeners and emits kernel signals.

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

```
Operations (in tree)
  → CutPlan.copy()            # copy selected ops
  → CutPlan.preprocess()      # scene→device coordinate transform
  → CutPlan.validate()        # validate constraints
  → CutPlan.blob()            # ops/elements → CutCode primitives
  → CutPlan.preopt()          # add travel-optimization passes
  → CutPlan.optimize()        # optimizers (nearest-neighbor, inner-first...)
  → Spooler.laserjob(job)     # wrap in LaserJob
  → Driver.move_abs/laser_on/laser_off/...   # execute against driver
```

- **CutCode primitives** (`core/cutcode/`): `LineCut`, `QuadCut`, `CubicCut`, `PlotCut`, `RasterCut`, `DwellCut`, `Homecut`, `GotoCut`, `WaitCut`, `InputCut`, `OutputCut`.
- **PlotPlanner** (`core/plotplanner.py`) converts CutCode into single-step (x, y, on/off) streams via manipulators (Single → PPI → Shift → Group).
- **Driver interface** (`core/drivers.py`): Only `hold_work(priority)`, `get()`, `set()`, and `status()` are required; everything else (`move_abs`, `laser_on`, ...) is optional and checked with `hasattr`.

---

## Core Concepts

### Units (`core/units.py`)

The internal unit is the **Tat** (1 inch = 65535 Tats). The `Length` class handles parsing/conversion:

```python
from meerk40t.core.units import Length
l = Length("5mm")
l.mm        # 5.0
l.inches    # 0.1968...
half = Length("50%", relative_length="10cm")  # = 5cm
```

`Angle` supports `rad`, `deg`, `grad`, `turn`.

### Geomstr (`core/geomstr.py`)

High-performance geometry engine using numpy arrays. Points are complex numbers (`complex(x, y)`). Supports lines, beziers, arcs, polygons, scanline fill, boolean clipping, and pattern generation.

### svgelements.py

A 9,670-line embedded SVG path/shape library providing `Path`, `Line`, `CubicBezier`, `Arc`, `Rect`, `Circle`, `Matrix`, and SVG parsing. Excluded from linting and type checking due to size.

---

## Code Patterns

### Console Commands

Three registration styles depending on context:

```python
from meerk40t.kernel.functions import console_command, kernel_console_command

# Service-level (inside a Service class):
@console_command("service_command", help=_("Service command description"))
def my_command(self, command, channel, _, **kwargs):
    """Long help text in docstring"""
    channel(_("Service command executed"))

# Kernel instance (when you have a kernel reference):
@kernel.console_command("greet", help="Greet the user")
def greet_cmd(command, channel, _, name=None, **kwargs):
    channel(f"Hello, {name or 'world'}!")

# With an argument:
@kernel.console_argument("name", type=str, help="Name to greet")
@kernel.console_command("greet2", help="Greet someone")
def greet_named(command, channel, _, name, **kwargs):
    channel(f"Hello, {name}!")
```

Key points:
- The second parameter (often `_`) is the remainder string after command parsing.
- Return value can be `(context_type, data)` to pass data down the command pipeline.
- Help text is short description; docstring is long help.
- **Never** use `@self.console_command` outside a Service class — use `kernel_console_command` or a kernel instance instead.

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

def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        service = MyService(kernel, "mydomain")
        kernel.add_service("mydomain", service)
        kernel.activate("mydomain", service)  # optional immediate activation
```

Services extend the kernel context with domain-specific attributes accessible via `kernel.domain_name`.

### Settings

```python
# Simple persistent setting
kernel.setting(int, "my_speed", 100)
context.setting(str, "label", "default")

# Device choices structure (shows up in settings UI)
class MyDevice(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        choices = [{
            "attr": "setting_name",
            "object": self,
            "default": default_value,
            "type": bool,               # bool, int, float, str
            "label": _("Display Label"),
            "section": "_10_Category",  # sorted by prefix
            "tip": _("Helpful tooltip"),
        }]
        self.register_choices("category", choices)
```

Section naming: use numeric prefixes for ordering (e.g. `_10_General`, `_20_Advanced`).

### Tree Operations (context-menu items per node type)

```python
from meerk40t.core.treeop import tree_operation, tree_conditional

@tree_operation(registration, "my_op", node_type="elem rect", help="Do something")
@tree_conditional(lambda node: node.parent.type == "group")
def my_tree_op(node, **kwargs):
    pass
```

### Device Communication Flow

1. **LaserJob** creates cut operations from the elements tree.
2. **Driver** (`driver.py`) translates them to device-specific commands (GRBL G-code, Lihuiyu LHY-MicroGL protocol, Ruida protocol...).
3. **Controller** (`controller.py`) handles the low-level communication protocol.
4. **Spooler** manages the job queue and execution.

Follow existing driver patterns (see `meerk40t/vendors/grbl/` as reference); implement proper error handling and reconnection logic; use kernel channels for status updates; keep communication operations thread-safe.

---

## Translation (Internationalization)

Always wrap user-facing strings with `_()`:

```python
channel(_("Text to translate"))
label = _("Button Label")
```

Where translation is NOT needed: internal variable names, technical identifiers, debug messages not shown to users.

Translation workflow:
- Files in `locale/`; main file `locale/messages.po`; locale files under `locale/{lang}/LC_MESSAGES/messages.po`.
- `python translate.py` (compile), `--force` (recompile), `--integrate` (integrate delta files), or pass locales: `python translate.py de fr es`.
- Run translation checks (`translate_check.py`) before committing changes that add new translatable strings.

---

## Performance Optimization with Numba

```python
from numba import njit

@njit(cache=True)   # Correct - nopython=True is implicit
def fast_function(data):
    ...
```

Avoid `@njit(cache=True, nopython=True)` — `nopython=True` is implicit and causes runtime warnings. Numba requires specific patterns: avoid Python objects, use NumPy arrays, keep logic simple.

---

## Critical Performance Areas

Handle with care and test thoroughly:
- `union_bounds()` in the node code — heavily used by GUI rendering; must stay efficient.
- Cut plan optimization algorithms — directly affect job execution time.
- Raster processing — memory-intensive; watch for leaks.
- Geomstr operations — geometric calculations used throughout the codebase.

---

## Code Style

Configured in `pyproject.toml`:

```bash
black meerk40t/           # format (line length: 88)
isort meerk40t/           # sort imports (Black profile)
flake8 meerk40t/          # lint (max line 88, max complexity 10)
pylint meerk40t/          # deeper analysis (slow)
mypy meerk40t/            # type check (excludes svgelements.py)
```

Guidelines: PEP 8; PascalCase classes; snake_case functions/variables; UPPER_CASE constants; leading underscore for private; docstrings for public APIs; type hints where appropriate.

Import patterns:
```python
from meerk40t.kernel import Kernel
from meerk40t.kernel.functions import kernel_console_command, console_command
from meerk40t.kernel.service import Service
from meerk40t.core.node.node import Node
```

---

## Testing

Tests use unittest. Bootstrap (`test/bootstrap.py`) spins up a full kernel with all core plugins, a dummy device, and fresh non-persisted settings. GUI tests live in `testgui/` and require wxPython + `testgui.mock_context`.

```python
from test import bootstrap

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("rect 2cm 2cm 1cm 1cm\n")
            elements = kernel.elements
            self.assertEqual(...)
        finally:
            kernel()  # shutdown
```

Common patterns:
- **Console pipeline:** build shapes, assign operations, plan, generate output via chained console commands.
- **Profile isolation:** `bootstrap.bootstrap(profile="MyTest_GRBL")` prevents state leaking between tests.
- **Driver output tests:** generate a laser job, save to file, compare output line-by-line.
- **Signal tests:** call `kernel.signal(...)`, then `kernel.process_queue()` to flush, then assert handler was called.

Run tests before and after changes; run specific suites related to your change; test both positive and negative cases.

Priority test files:
- `test_core_*.py`, `test_kernel.py` — core system
- `test_cutplan_optimization.py`, `test_cutplan_travel_optimization.py`, `test_grouped_inner_enhancement.py` — cut planning (**must run** the grouped-inner one when touching inner-first/grouped optimization)
- `test_drivers_*.py` — the specific driver you modify
- `test_node_*.py` — node tree operations

---

## How-To Guides

### Add a Device Driver

1. Create `meerk40t/newdevice/` directory.
2. Implement three files: `device.py` (Service subclass managing state/settings), `controller.py` (low-level USB/serial/network comm), `driver.py` (driver interface: `hold_work`, `move_abs`, `laser_on`, ...).
3. Create `plugin.py` registering `provider/device/newdevice` in the `register` lifecycle; add GUI components in a `gui/` subdirectory if needed.
4. Add the import to `internal_plugins.py`.
5. Add tests in `test/test_drivers_newdevice.py`.

### Add a File Format

1. Create a module in `meerk40t/extra/` or a new package.
2. Implement a reader producing element nodes (`elements.add_node(...)` or console commands like `elem path ...`).
3. Register via `kernel.register("format/myformat", reader_func)` in your plugin's `register` lifecycle.
4. Add to `internal_plugins.py`.

### Add a New Operation Type

1. Create a node class in `core/node/` (subclass `Node`, set a `type` string like `"op myop"`).
2. Register it in `core/node/bootstrap.py`'s `bootstrap` dict.
3. Implement `as_cutobjects()` producing CutCode primitives — called by `CutPlan.blob()`.
4. Add tree-operation context-menu entries with `@tree_operation`.

### Add a Console Command (end-to-end)

```python
# In your plugin's "register" lifecycle:
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":

        @kernel.console_command("greet", help="Greet the user")
        def greet_cmd(command, channel, _, name=None, **kwargs):
            channel(f"Hello, {name or 'world'}!")
```

Use the `postboot` lifecycle instead if the command depends on registered services.

---

## Common Pitfalls

1. **Incorrect console command registration** — `@self.console_command` only works inside a Service class; otherwise use `kernel_console_command` or a kernel instance.
2. **Forgetting translation** — wrap user-visible strings in `_()`.
3. **Using print() instead of channel()** — always use `channel()`; it provides proper user interface integration.
4. **Breaking CutPlan compatibility** — `opt_inner_first=True` combined with `opt_inners_grouped=True` is fragile: the algorithms expect different input types (CutGroups vs individual cuts). Always check input-type expectations in the optimization functions and run `test_grouped_inner_enhancement.py` plus the cutplan tests when touching cutplan code. Verify both optimization modes work independently and together.
5. **Incorrect plugin lifecycle phase** — `register` for providers/services; `postboot` for commands that depend on registered services; `boot` for early init without cross-plugin dependencies.
6. **Numba decorator misuse** — never pass `nopython=True` explicitly to `@njit`; it is implicit and causes runtime warnings.
7. **Thread safety issues** — don't modify shared state without locking in device communication; use kernel threading utilities and existing driver patterns.
8. **Platform assumptions** — use commands appropriate for your shell (PowerShell on Windows, sh/bash elsewhere); prefer script files over complex inline quoting.

---

## Dependencies & Requirements

**Core:** numpy, pyusb, pyserial, Pillow, requests

**Optional extras (defined in setup.py):**
- `gui` — wxPython >= 4.0.0, Pillow >= 7.0.0
- `dxf` — ezdxf >= 0.14.0
- `cam` — opencv-python-headless
- `camhead` — opencv-python (with GUI)

**Development:** pytest, flake8, black, mypy, pylint, isort

```bash
pip install -r requirements.txt                 # full install with GUI
pip install -r requirements.txt -r requirements-dev.txt   # dev environment
pip install -r requirements-nogui.txt           # headless (no wxPython)
pip install meerk40t[all]                       # all optional dependencies
```

Also see `requirements-optional-*.txt` for platform-specific optional dependencies.

---

## Application Entry Point

The main entry point is `meerk40t/main.py`:
- Defines `APPLICATION_NAME` and `APPLICATION_VERSION`.
- Version detection appends "git", "src", or "pkg" based on environment.
- Initializes the Kernel and loads internal/external plugins.
- Invoked via the root-level `meerk40t.py` launcher, or the installed `meerk40t` console script (`setup.cfg`: `meerk40t = meerk40t.main:run`). Note that `meerk40t/main.py` has no `if __name__ == "__main__"` block, so `python -m meerk40t.main` does nothing.

Key CLI arguments:
- `-z, --no-gui` — run without GUI
- `-c, --console` — start as console
- `-e, --execute` — execute console command
- `-a, --auto` — start running laser automatically
- `-p, --no-plugins` — disable external plugins
- `-s, --simpleui` — simplified interface

---

## Integration Points

- **LightBurn compatibility:** `ruidacontrol` command creates Ruida emulation.
- **GRBL TCP:** `grblcontrol` command for remote GRBL access.
- **File formats:** SVG via embedded `svgelements.py`, DXF via `meerk40t/dxf/`.

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
