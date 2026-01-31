# Tools

Tools are stand-alone utilities that help with various processes and may be shared among different functions. These are
unrelated to the functionality of the kernel ecosystem.

These can largely be removed and used whole-cloth without requiring any additional code scaffolding.

## Architecture

The tools module provides a comprehensive collection of specialized utility libraries for geometric computation, font rendering, image processing, and algorithmic operations. These utilities are designed as standalone components that can be used independently of the SefroCut kernel system.

### Module Categories
- **Geometric Algorithms**: Path optimization, boolean operations, spatial indexing
- **Font Processing**: Vector font parsing and rendering (Hershey, SHX, TrueType)
- **Image Processing**: Raster plotting algorithms and pixel manipulation
- **Mathematical Utilities**: Matrix operations, geometric primitives
- **Algorithmic Tools**: Graph traversal, spatial queries, optimization routines

## Dual Algorithm Strategy

Advanced path optimization system that implements multiple algorithmic approaches for laser cutting path planning.

### Features
- **Strategy Pattern**: Pluggable algorithm implementations
- **Performance Comparison**: Benchmarking different optimization strategies
- **Path Optimization**: Minimizing laser head movement and processing time
- **Configurable Parameters**: Adjustable optimization criteria

### Usage
```python
strategy = DualAlgorithmStrategy()
optimized_path = strategy.optimize(input_path, parameters)
```

## Driver to Path

Utility for converting device-specific driver commands into geometric path representations.

### Features
- **Driver Translation**: Convert hardware commands to vector paths
- **Device Abstraction**: Unified interface for different laser controllers
- **Path Reconstruction**: Rebuild geometric paths from command sequences
- **Debug Visualization**: Visual representation of driver command execution

## Geomstr

High-performance geometric data structure for storing and manipulating complex geometric primitives. **Note: As of recent refactoring, Geomstr has been moved to `sefrocut.core.geomstr` to reflect its central importance to the SefroCut solution.**

### Architecture
Geomstr uses aligned numpy arrays to store geometric primitives (lines, quads, cubics, arcs, points) in a memory-efficient format. The structure supports efficient operations like reversing, transforming, and path traversal.

### Features
- **Primitive Types**: Lines, quadratic/cubic Bezier curves, arcs, points
- **Memory Efficient**: Aligned array storage with complex number representation
- **Path Operations**: Run-based geometry with implicit connections
- **Transformation Support**: Affine transformations and matrix operations
- **Vertex System**: Graph-based topology with indexed vertices
- **Performance Optimized**: Numba JIT compilation for critical operations

### Geometric Primitives
```python
# Structure: [start, control1, center, control2, end]
# Center stores type information and settings reference
line = [start_point, None, "line", None, end_point]
quad = [start, control, "quad", control, end]  # control1 == control2
cubic = [start, control1, "cubic", control2, end]
arc = [start, control, "arc", control, end]  # Three-point arc representation
```

### Operations
- **Path Traversal**: Efficient iteration through connected geometry
- **Reversing**: Fast geometry reversal using numpy flip operations
- **Transformation**: Matrix-based geometric transformations
- **Intersection**: Geometric intersection and collision detection
- **Simplification**: Path optimization and curve approximation

## JhfParser

Parser for Hershey Font (.jhf) files, implementing the classic vector font system developed by Dr. Allen Vincent Hershey.

### Features
- **Hershey Font Support**: Complete implementation of Hershey vector fonts
- **Glyph Parsing**: Automatic parsing of glyph definitions from .jhf files
- **Character Mapping**: Full ASCII character set support
- **Font Metrics**: Automatic calculation of font bounds and spacing
- **Rendering Engine**: Vector path generation for text rendering

### Font Format
Hershey fonts use a coordinate system where:
- Origin (0,0) is at the center of each glyph
- X increases to the right, Y increases downward
- Coordinates are relative to ASCII value of 'R' (82)
- Pen-up commands indicated by " R" in coordinate data

### Usage
```python
font = JhfFont("hershey.jhf")
font.render(path_object, "HELLO", font_size=12.0)
```

## Kerftest

Calibration and testing utilities for laser kerf (cutting width) compensation.

### Features
- **Kerf Measurement**: Automated measurement of laser cutting kerf
- **Calibration Patterns**: Generate test patterns for kerf analysis
- **Compensation Algorithms**: Apply kerf compensation to cutting paths
- **Material Profiles**: Store kerf data for different materials and power settings

## Living Hinges

Pattern generation system for creating flexible living hinges in laser-cut materials.

### Features
- **Rectangular Patterns**: Generate hinge patterns within defined areas
- **Cell-Based Design**: Configurable cell size and spacing
- **Material Optimization**: Patterns optimized for material flexibility
- **Rotation Support**: Pattern rotation for different cutting orientations
- **Padding Control**: Adjustable spacing between hinge elements

### Pattern Types
- **Line Patterns**: Simple parallel cut lines
- **Geometric Patterns**: Circles, custom shapes for hinge flexibility
- **Material-Specific**: Optimized patterns for different material thicknesses

## Living Hinge Optimizer

Advanced optimization algorithms for living hinge design and material efficiency.

### Features
- **Stress Analysis**: Calculate stress distribution in hinge patterns
- **Material Efficiency**: Optimize hinge patterns for minimal material waste
- **Flexibility Modeling**: Predict hinge flexibility based on pattern parameters
- **Automated Design**: Generate optimal hinge patterns for specific requirements

## Pathtools

Core geometric algorithms implementing the Eulerian Fill optimization for laser cutting.

### Eulerian Fill Algorithm

The Eulerian Fill creates an optimized traversal path for hatch patterns by:

1. **Graph Construction**: Convert outline shapes into graph nodes and edges
2. **Rung Generation**: Add horizontal "rungs" connecting outline segments
3. **Eulerian Path Finding**: Solve for a path that visits all rungs with minimal retrace
4. **Optimization**: Minimize total laser head movement

### Key Classes

#### Graph
Spatial data structure for managing geometric relationships:
```python
class Graph:
    def add_shape(self, outline, closed=True):  # Add closed shape to graph
    def monotone_fill(self, ...):  # Generate fill pattern
    def walk(self, path):  # Traverse optimized path
```

#### Segment
Graph edges representing line segments with intersection capabilities:
```python
class Segment:
    def intersect(self, other):  # Calculate line intersections
    def get_intercept(self, y):  # Y-axis intercept calculation
```

#### VectorMontonizer
Monotonic vector processing for efficient scanline operations:
- **Event Management**: Handle edge events during scanline processing
- **Active Edge Tracking**: Maintain active edge list during scanning
- **Intersection Resolution**: Handle edge crossings and ordering

### Performance Characteristics
- **Time Complexity**: O(n log n) for graph construction and optimization
- **Space Complexity**: O(n) for geometric storage
- **Optimization**: Significant reduction in unnecessary laser movement

## Point Finder (Acceleration Structure)

Spatial indexing system for efficient nearest-point queries and collision detection.

### Features
- **Spatial Indexing**: Fast lookup of points within regions
- **AABB Hierarchy**: Axis-aligned bounding box tree structure
- **Layer Support**: Multi-layer spatial organization
- **Reference System**: Efficient storage of point and segment references

### Architecture
- **Area-Based Storage**: Hierarchical bounding box system
- **Sorted Axis Lists**: Maintain sorted X and Y coordinates
- **Reference Encoding**: Compact storage of geometric references
- **Merge Operations**: Efficient area combination and splitting

### Performance
- **Query Time**: O(log n) for point location queries
- **Memory Usage**: O(n) storage with hierarchical overhead
- **Update Operations**: Efficient insertion and deletion

## Polybool

Polygon boolean operations library implementing constructive solid geometry for 2D shapes.

### Supported Operations
- **Union**: Combine multiple polygons into one
- **Intersection**: Find overlapping regions
- **Difference**: Subtract one polygon from another
- **XOR**: Exclusive OR operation between polygons

### Features
- **Robust Computation**: Handle edge cases and degenerate geometry
- **Numerical Stability**: Tolerance-based floating point operations
- **Performance Optimized**: Numba JIT compilation for critical paths
- **Memory Efficient**: Optimized data structures and algorithms

### Algorithm Components
- **Point Classification**: Determine point-in-polygon relationships
- **Edge Intersection**: Calculate intersection points between edges
- **Winding Rules**: Handle polygon orientation and hole detection
- **Topology Reconstruction**: Build result polygons from intersection data

### Usage
```python
from sefrocut.tools.polybool import Polygon

poly1 = Polygon(points1)
poly2 = Polygon(points2)
result = poly1.union(poly2)
```

## Pmatrix

Perspective matrix class for 3D transformations in geometric operations.

### Features
- **3x3 Matrix Operations**: Full 3x3 matrix mathematics
- **Numpy Integration**: High-performance numpy-based computations
- **Transformation Support**: Scale, rotate, translate, skew operations
- **Matrix Concatenation**: Efficient matrix multiplication and composition

### Operations
```python
# Create transformation matrices
scale_matrix = PMatrix.scale(sx=2.0, sy=1.5)
rotate_matrix = PMatrix.rotate(angle=math.pi/4)
translate_matrix = PMatrix.translate(tx=10, ty=20)

# Combine transformations
combined = translate_matrix @ rotate_matrix @ scale_matrix
```

### Performance
- **Vectorized Operations**: Numpy-based matrix operations
- **Memory Efficient**: Minimal object overhead
- **Type Safety**: Proper matrix dimension handling

## RasterPlotter

Comprehensive raster plotting system for converting pixel data to laser movement commands.

### Supported Raster Methods
- **Standard Rastering**: Top-to-bottom, bottom-to-top, left-to-right, right-to-left
- **Diagonal Scanning**: Corner-based diagonal traversal patterns
- **Greedy Algorithms**: Neighbor-based path optimization
- **Crossover Processing**: Alternating row/column processing
- **Spiral Patterns**: Center-outward spiral traversal

### Key Features
- **Pixel Filtering**: Intelligent skip-pixel logic for blank areas
- **Overlap Compensation**: Adjust for laser spot diameter
- **Bidirectional Scanning**: Forward and reverse pass options
- **Distance Tracking**: Calculate travel vs. burn distances
- **Performance Monitoring**: Debug output and timing information

### Algorithm Architecture
```python
class RasterPlotter:
    def plot(self, image_data, method=RASTER_T2B):
        # Convert pixel data to optimized laser paths
        # Handle different scanning patterns
        # Apply filtering and optimization
        return laser_commands
```

### Configuration Options
- **Starting Corners**: Top-left, top-right, bottom-left, bottom-right
- **Scan Direction**: Unidirectional or bidirectional
- **Pixel Threshold**: Brightness thresholds for laser activation
- **Speed Optimization**: Minimize non-burning travel time

## ShxParser

Parser for AutoCAD SHX (Shape) font files, supporting technical and architectural font rendering.

### Features
- **SHX Font Support**: Parse compiled AutoCAD shape fonts
- **Shape Definitions**: Decode binary shape definitions
- **Character Rendering**: Convert shapes to vector paths
- **Font Metrics**: Calculate character spacing and bounds

### SHX Format
SHX files contain:
- **Shape Definitions**: Binary-encoded vector shapes
- **Character Mapping**: ASCII to shape index mapping
- **Metric Information**: Character width and spacing data
- **Compiled Format**: Optimized binary representation

### Usage
```python
font = ShxFont("technical.shx")
font.render_shape(character_code, scale_factor)
```

## TTFParser

Pure Python TrueType font parser for vectorizing TTF/OTF fonts.

### Features
- **TrueType Support**: Parse TTF font files without external libraries
- **OpenType Support**: Handle OTF font variations
- **Glyph Extraction**: Convert font glyphs to vector paths
- **Kerning Support**: Character spacing and positioning
- **Unicode Support**: Full Unicode character set handling

### Font Tables Parsed
- **head**: Font header with global metrics
- **hhea/hmtx**: Horizontal metrics and advances
- **loca/glyf**: Glyph location and outline data
- **cmap**: Character to glyph mapping
- **name**: Font naming information

### Glyph Rendering
- **Bezier Curves**: Convert quadratic Bezier curves to cubic
- **Composite Glyphs**: Handle compound character construction
- **Hinting**: Optional font hinting support
- **Scaling**: Arbitrary size rendering

### Usage
```python
font = TrueTypeFont("arial.ttf")
glyph_path = font.get_glyph_path('A')
scaled_path = font.render_glyph('A', font_size=12)
```

## ZinglPlotter

Pixel-perfect vector plotting using Zingl-Bresenham algorithms.

### Algorithm Basis
Based on Alois Zingl's Bresenham algorithm implementations for:
- **Line Drawing**: Integer-only line rasterization
- **Circle Drawing**: Perfect circle pixel coverage
- **Ellipse Drawing**: Elliptical shape rendering
- **Bezier Curves**: Cubic and quadratic Bezier curve plotting

### Features
- **Pixel Perfect**: Exact pixel coverage for geometric primitives
- **Integer Mathematics**: No floating point errors
- **Performance Optimized**: Fast integer-only calculations
- **Complete Coverage**: All pixels on geometric paths are hit

### Supported Primitives
```python
# Line plotting
for x, y in ZinglPlotter.plot_line(x0, y0, x1, y1):
    # Process each pixel

# Circle plotting  
for x, y in ZinglPlotter.plot_circle(xc, yc, radius):
    # Process circle pixels

# Bezier curve plotting
for x, y in ZinglPlotter.plot_cubic_bezier(x0, y0, x1, y1, x2, y2, x3, y3):
    # Process curve pixels
```

### Performance Characteristics
- **Time Complexity**: O(length) for lines, O(radius) for circles
- **Memory Usage**: Minimal, iterator-based processing
- **Accuracy**: Perfect pixel coverage with no gaps or overlaps

## Integration Notes

### Standalone Usage
Most tools modules can be used independently:
```python
# Use without SefroCut kernel
from sefrocut.tools.zinglplotter import ZinglPlotter
from sefrocut.tools.ttfparser import TrueTypeFont
```

### Kernel Integration
Tools register with the kernel for SefroCut integration:
```python
kernel.register("tool/rasterplotter", RasterPlotter)
kernel.register("tool/font_ttf", TrueTypeFont)
```

### Dependencies
- **Numba**: JIT compilation for performance (optional)
- **NumPy**: Array operations and mathematical functions
- **Pillow**: Image processing for raster operations
- **FontTools**: Additional font parsing capabilities

### Performance Optimization
- **JIT Compilation**: Numba acceleration where available
- **Vectorization**: NumPy array operations for bulk processing
- **Memory Pooling**: Efficient memory reuse in geometric operations
- **Algorithm Selection**: Automatic choice of optimal algorithms

### Error Handling
- **Graceful Degradation**: Fallback implementations when dependencies unavailable
- **Input Validation**: Comprehensive checking of geometric data
- **Numerical Stability**: Tolerance-based floating point operations
- **Exception Safety**: Proper cleanup on error conditions

This tools collection provides the mathematical and algorithmic foundation for SefroCut's advanced laser processing capabilities, enabling precise geometric operations, font rendering, and optimization algorithms essential for professional laser cutting and engraving systems.
