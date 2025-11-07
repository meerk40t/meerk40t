# Fill Module

Fill provides wobble and fill capabilities that are registered within the kernel. This is primarily for the galvo laser
driver and to implement that hatch capabilities. This permits plugins to provide additional hatches and wobbles and
centralizes those types of algorithms within a more general area. There maybe some reasons to use hatches for other
drivers and wobbles could be extended to work in those cases as well.

## Architecture

The fill module provides advanced path processing algorithms for laser engraving and cutting, focusing on two main areas:

- **Hatch Fills**: Algorithms for filling closed shapes with parallel lines
- **Wobble Patterns**: Decorative path modifications that create textured effects along lines

```
meerk40t/fill/
├── fills.py           # Core hatch and wobble algorithms
├── patterns.py        # Living hinge and pattern generation
└── patternfill.py     # Legacy/obsolete pattern code
```

### Core Components

- **Hatch Algorithms**: `scanline_fill` and `eulerian_fill` for area filling
- **Wobble System**: `Wobble` class with multiple pattern algorithms
- **Pattern Generation**: Living hinge patterns and geometric fills
- **Plugin Registration**: Kernel integration for extensible algorithms

## Hatch Fill Algorithms

The module provides two primary algorithms for filling closed shapes with parallel lines.

### Scanline Fill

Traditional scanline algorithm that fills shapes with horizontal lines at specified intervals.

**Features:**
- **Angle Control**: Configurable fill angle for directional control
- **Distance Control**: Adjustable spacing between fill lines
- **Bidirectional**: Alternates direction for efficient laser movement
- **Matrix Support**: Handles transformations and scaling

**Algorithm:**
```python
def scanline_fill(settings, outlines, matrix, limit=None):
    # Transform outlines to fill coordinate system
    # Generate parallel lines at specified intervals
    # Clip lines to shape boundaries
    # Return optimized point sequence
```

### Eulerian Fill

Advanced optimization algorithm that creates an efficient traversal path for fill lines.

**Features:**
- **Graph Optimization**: Treats fill lines as graph nodes for optimal traversal
- **Minimal Retrace**: Reduces unnecessary laser movement between lines
- **Eulerian Path**: Finds path that visits each line exactly once
- **Scaffolding**: Adds minimal connecting lines when needed

**Algorithm:**
```python
def eulerian_fill(settings, outlines, matrix, limit=None):
    # Create graph of fill line segments
    # Solve for Eulerian path through graph
    # Optimize for minimal total travel distance
    # Return connected point sequence
```

### Configuration

Both algorithms accept settings dictionary:
```python
settings = {
    "hatch_distance": "1mm",    # Spacing between fill lines
    "hatch_angle": "0deg"       # Fill direction angle
}
```

## Wobble Patterns

Wobble patterns modify straight lines into decorative paths, creating textured effects during laser processing.

### Wobble System Architecture

The `Wobble` class provides the framework for all wobble patterns:

```python
class Wobble:
    def __init__(self, algorithm, radius=50, speed=50, interval=10):
        self.algorithm = algorithm    # Pattern function
        self.radius = radius         # Pattern amplitude
        self.speed = speed          # Pattern frequency
        self.interval = interval     # Sampling resolution
```

### Available Wobble Patterns

#### Circular Patterns
- **`circle`**: Circular motion around the line path
- **`circle_right`**: Circle offset to the right of the path
- **`circle_left`**: Circle offset to the left of the path

#### Wave Patterns
- **`sinewave`**: Smooth sinusoidal modulation
- **`sawtooth`**: Sharp triangular wave pattern
- **`jigsaw`**: Combined sine and sawtooth effects

#### Mechanical Patterns
- **`gear`**: Gear-tooth like rectangular pattern
- **`slowtooth`**: Smoothed version of sawtooth

#### Complex Patterns
- **`meander_1/2/3`**: Complex meandering patterns with multiple turns
- **`dashed_line`**: Dashed line effects with configurable patterns
- **`tabbed_path`**: Tabbed cuts for material handling

### Pattern Examples

#### Circle Wobble
Creates circular motion perpendicular to the path:
```python
# Parameters: radius=50, speed=50, interval=10
# Creates circles of radius 50 units along the path
```

#### Sinewave Wobble
Smooth sinusoidal modulation:
```python
# Creates smooth curves perpendicular to the path
# radius controls amplitude, speed controls frequency
```

#### Meander Patterns
Complex multi-turn patterns for decorative effects:
```python
# meander_1: Basic meandering with multiple turns
# meander_2: Simplified meander pattern
# meander_3: Complex bidirectional meander
```

## Living Hinge Patterns

The `LivingHinges` class generates patterns for creating flexible living hinges in materials.

### Features
- **Rectangular Areas**: Generates patterns within defined rectangles
- **Cell-Based**: Configurable cell size and spacing
- **Rotation Support**: Pattern rotation for different material orientations
- **Padding Control**: Adjustable spacing between pattern elements

### Pattern Types
- **Line Patterns**: Simple parallel lines
- **Geometric Patterns**: Circles, squares, and custom shapes
- **Hinge-Specific**: Optimized for material flexibility

### Configuration
```python
hinge = LivingHinges(xpos, ypos, width, height)
hinge.set_cell_values(width_percent=100, height_percent=100)
hinge.set_padding_values(horizontal=50, vertical=50)
hinge.set_rotation(angle_degrees)
```

## Technical Implementation

### Coordinate Systems

The fill module handles multiple coordinate transformations:

- **Device Coordinates**: Final output coordinates for laser control
- **Pattern Coordinates**: Local coordinate system for pattern generation
- **Matrix Transformations**: Affine transformations for scaling, rotation, translation

### Performance Optimizations

- **Limit Checking**: Prevents excessive computation for large areas
- **Incremental Processing**: Processes paths in segments to manage memory
- **Geometric Caching**: Reuses computed geometry where possible

### Error Handling

- **Invalid Inputs**: Graceful handling of malformed geometry
- **Division by Zero**: Protected against zero-length intervals
- **Memory Limits**: Configurable limits to prevent excessive memory usage

## Usage Examples

### Basic Hatch Fill
```python
from meerk40t.fill.fills import scanline_fill

# Fill a circle with parallel lines
settings = {"hatch_distance": "1mm", "hatch_angle": "45deg"}
outlines = [(0, 0), (100, 0), (100, 100), (0, 100), None]  # Rectangle
points = scanline_fill(settings, outlines, Matrix())
```

### Wobble Pattern Application
```python
from meerk40t.fill.fills import Wobble, circle

# Create circular wobble pattern
wobble = Wobble(circle, radius=25, speed=20, interval=5)

# Apply to a line segment
for x, y in wobble(0, 0, 100, 0):
    # Process wobbled points
    pass
```

### Living Hinge Generation
```python
from meerk40t.fill.patterns import LivingHinges

# Create living hinge pattern
hinge = LivingHinges(0, 0, 200, 50)
hinge.set_predefined_pattern(desired_pattern)
path = hinge.generate_path()
```

## Integration with MeerK40t

### Kernel Registration

The fill module registers its algorithms with the kernel:

```python
context.register("hatch/scanline", scanline_fill)
context.register("hatch/eulerian", eulerian_fill)
context.register("wobble/circle", circle)
# ... additional registrations
```

### Operation Integration

Hatch fills integrate with MeerK40t's operation system:
- **Engrave Operations**: Use hatch fills for area engraving
- **Cut Operations**: May use wobble patterns for decorative edges
- **Material Settings**: Distance and angle controlled by material properties

### GUI Integration

The fill patterns are accessible through:
- **Operation Properties**: Hatch settings in operation panels
- **Wobble Settings**: Pattern selection in path operation dialogs
- **Living Hinge Tools**: Specialized tools for flexible material cutting

## Performance Characteristics

### Algorithm Complexity
- **Scanline Fill**: O(n) where n is shape perimeter complexity
- **Eulerian Fill**: O(n log n) due to graph optimization
- **Wobble Patterns**: O(m) where m is path length / interval

### Memory Usage
- **Hatch Fills**: Linear with shape complexity
- **Wobble Patterns**: Linear with path length
- **Living Hinges**: Configurable based on cell count

### Optimization Strategies
- **Distance Limits**: Prevents over-computation for large areas
- **Resolution Control**: Adjustable sampling for quality/speed tradeoffs
- **Incremental Generation**: Processes large patterns in chunks

## Extension Points

### Custom Hatch Algorithms

New hatch algorithms can be registered:

```python
def custom_fill(settings, outlines, matrix, limit=None):
    # Implement custom filling logic
    return points

kernel.register("hatch/custom", custom_fill)
```

### Custom Wobble Patterns

New wobble patterns can be added:

```python
def custom_wobble(wobble, x0, y0, x1, y1):
    # Implement custom wobble logic
    for x, y in wobble.wobble(x0, y0, x1, y1):
        yield modified_x, modified_y

kernel.register("wobble/custom", custom_wobble)
```

### Pattern Extensions

The living hinge system supports custom patterns:

```python
def custom_pattern_generator(params):
    # Generate custom pattern geometry
    return geometry

# Register with pattern system
```

This fill module transforms basic vector paths into rich, laser-optimized toolpaths with advanced filling and decorative capabilities essential for professional laser processing.
