# Cutcode Module

The Cutcode module is the core laser cutting data structure in SefroCut. It provides a hierarchical, extensible system for representing laser operations as a sequence of primitive cut objects that can be optimized, transformed, and executed by laser drivers.

## Overview

Cutcode is a hybrid datatype that combines geometric shapes with laser-specific parameters. Each cutcode object contains a `settings` object that holds laser parameters like `.speed`, `.power`, and other driver-specific settings. This modular design allows the same geometric data to be used with different laser configurations.

## Core Classes

### CutCode
The main container class that holds a sequence of cut objects. CutCode extends CutGroup and provides:

- **SVG Conversion**: `as_elements()` method converts cutcode to SVG paths
- **Statistics**: `provide_statistics()` generates detailed timing and distance metrics
- **Optimization**: Methods for calculating travel distances, cut lengths, and durations
- **Reordering**: `reordered()` method for optimizing cut sequences

### CutGroup
A hierarchical container that groups related cut objects together. Used to maintain relationships between inner and outer shapes for optimization.

- **Hierarchy Support**: Maintains `.contains` and `.inside` relationships
- **Candidate Generation**: `candidate()` method respects inner-first constraints
- **Flat Iteration**: `flat()` method provides depth-first traversal

### CutObject
The base class for all laser primitives. Provides common functionality:

- **Geometry**: `.start`, `.end` properties with normal/reverse support
- **Settings**: Laser parameters storage
- **Burn Tracking**: `.burns_done` for multi-pass operations
- **Hierarchy**: `.contains`, `.inside` for containment relationships

## Cut Types

### Vector Cuts

#### LineCut
Basic straight line cuts between two points.
- Uses ZinglPlotter for high-quality line rasterization
- Supports parametric point calculation with `point(t)`

#### QuadCut
Quadratic Bézier curve cuts with one control point.
- Smooth curved paths using quadratic Bézier mathematics
- Length calculation accounts for curve geometry
- Parametric point evaluation

#### CubicCut
Cubic Bézier curve cuts with two control points.
- More complex curved paths for precise shapes
- Higher-order curve mathematics

### Raster Operations

#### RasterCut
Image-based raster engraving operations.
- Supports "L" (grayscale) and "1" (monochrome) images
- Configurable scanning patterns (horizontal/vertical, bidirectional)
- Overscan and laser spot compensation
- Post-processing filters for power modulation

#### PlotCut
Point-by-point plotting operations.
- Arbitrary point sequences with laser on/off control
- Used for custom engraving patterns

### Control Operations

#### DwellCut
Laser dwell operations at a specific point.
- Configurable dwell time for spot burning
- Used for marking or material testing

#### GotoCut
Rapid positioning moves without laser operation.
- Pure movement commands for laser head positioning

#### WaitCut
Timed pauses in laser operation.
- Configurable wait times in milliseconds
- Used for material cooling or synchronization

#### HomeCut
Return to home position operations.

#### InputCut / OutputCut
I/O synchronization operations for external devices.

## Key Features

### Hierarchical Organization
Cutcode supports nested containment relationships where shapes can contain other shapes. This enables:

- **Inner-first optimization**: Burning inner shapes before outer shapes to prevent material shift
- **Constrained processing**: Respecting containment relationships during optimization
- **Group-based operations**: Processing related shapes together

### Multi-pass Support
All cut objects support multiple passes with burn tracking:

- `.passes`: Number of times to repeat the operation
- `.burns_done`: Tracking of completed passes
- Automatic pass management during optimization

### Settings Management
Flexible parameter system for laser configuration:

- **Shared Settings**: Settings can be shared across multiple cut objects
- **Driver-specific**: Parameters like frequency, dwell time, etc.
- **Dynamic Updates**: Settings can be modified without recreating cut objects

### Optimization Ready
Cutcode is designed for optimization algorithms:

- **Travel Calculation**: `length_travel()` for move distance optimization
- **Cut Length**: `length_cut()` for operation time estimation
- **Duration Estimation**: `duration_cut()`, `duration_travel()` for scheduling
- **Statistics**: Comprehensive performance metrics

## Usage Examples

### Creating Basic Cuts
```python
from sefrocut.core.cutcode import CutCode, LineCut

# Create a simple line cut
line = LineCut((0, 0), (100, 100), settings={'speed': 100, 'power': 100})
cutcode = CutCode([line])
```

### Working with Groups
```python
from sefrocut.core.cutcode import CutGroup

# Group related cuts together
group = CutGroup(None, [line1, line2], closed=True)
cutcode = CutCode([group])
```

### Raster Operations
```python
from sefrocut.core.cutcode import RasterCut
from PIL import Image

# Create raster engraving
image = Image.open('pattern.png')
raster = RasterCut(
    image=image,
    offset_x=0, offset_y=0,
    step_x=0.1, step_y=0.1,
    bidirectional=True
)
```

## Architecture Notes

### Inheritance Hierarchy
```
CutObject (base)
├── CutGroup (container)
│   └── CutCode (main container)
├── LineCut (primitives)
├── QuadCut
├── CubicCut
├── RasterCut
├── PlotCut
├── DwellCut (controls)
├── GotoCut
├── WaitCut
├── HomeCut
├── InputCut
└── OutputCut
```

### Design Principles
1. **Modularity**: Each cut type handles its own geometry and generation
2. **Extensibility**: New cut types can be added by inheriting from CutObject
3. **Optimization-friendly**: All cuts provide consistent interfaces for planning algorithms
4. **Driver-agnostic**: Settings system allows adaptation to different laser hardware

### Performance Considerations
- CutCode uses lazy evaluation for expensive operations
- Statistics are calculated on-demand
- Flat iteration avoids deep recursion
- Memory-efficient storage of geometric data

This module forms the foundation of SefroCut's laser cutting pipeline, providing a clean separation between geometric operations and laser control.
