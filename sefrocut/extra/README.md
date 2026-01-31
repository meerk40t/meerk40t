# Extra Modules

Extra modules are largely tools and plugins that serve minor mostly standalone purposes. These are not dependent on
other things and are not required. They are functional but not essential, usually adding interesting but ultimately
unneeded functionality to the kernel ecosystem.

Some code is removed from a more prominent role elsewhere, others perform functions like making system calls to
Inkscape to permit those given functions.

Many of these resemble addons that are built-in to sefrocut.

## Architecture

The extra modules directory contains a collection of specialized plugins and utilities that extend SefroCut's functionality without being core dependencies. Each module follows the standard SefroCut plugin pattern with lifecycle hooks (`invalidate`, `register`, `boot`, etc.) and integrates through the kernel service system.

### Module Categories
- **File Format Support**: Parsers for proprietary CAD/CAM file formats
- **Image Processing**: Vectorization and image manipulation tools
- **External Integration**: Interfaces to external applications and systems
- **Hardware Control**: Auxiliary device control and monitoring
- **Utility Functions**: Helper tools and parametric operations

## CAG (Constructive Additive Geometry)

The CAG operations provide access to polygon boolean operations using the `polybool` library, enabling clipping of shapes by other shapes.

### Features
- **Boolean Operations**: Union, intersection, XOR, and difference operations on vector shapes
- **Automatic Classification**: Post-operation element classification
- **Stroke/Fill Preservation**: Maintains original styling attributes
- **Undo Support**: Operations wrapped in undo scopes

### Usage
```python
# Select multiple elements and run boolean operations
union selected_elements
intersection selected_elements
xor selected_elements
difference selected_elements
```

### Dependencies
- `numpy`: Required for polygon operations
- `polybool`: Core boolean geometry library

## Coolant

Provides interfaces for coolants and auxiliary systems like air assist. External modules can register coolant methods that devices can claim and control.

### Features
- **Method Registration**: Plugin system for different coolant implementations
- **Device Integration**: Devices can claim ownership of coolant methods
- **Built-in Methods**:
  - `popup`: User instruction dialogs
  - `gcode_m7/m8`: GRBL-compatible M-codes
- **Constraint System**: Device-specific compatibility checking

### Usage
```python
# Register a custom coolant method
coolants.register_coolant_method("my_coolant", control_function, config_function)

# Device claims coolant ownership
device.claim_coolant("my_coolant")
```

## Encode Detect

Text file encoding detection utility that identifies common encoding patterns in files.

### Supported Encodings
- ASCII
- UTF-8
- UTF-16BE
- UTF-16LE
- CP1252 (Windows-1252)

### Features
- **BOM Detection**: Identifies byte order marks for UTF variants
- **Statistical Analysis**: Uses null byte patterns to detect UTF-16
- **File Stream Processing**: Efficient detection from file handles

## EZD (EZCad2 Parser)

Parser for EZCad2 .ezd files, a proprietary format used by EZCad2 laser software.

### Features
- **Complete Object Support**: Parses all EZCad2 object types including vectors, images, and modifications
- **Pen System**: Imports pen settings and layer assignments
- **Coordinate System**: Handles EZCad2's center-based coordinate system
- **Hatch/Spiral Support**: Complex grouped objects with cached path data
- **Unit Conversion**: Automatic mm/inch conversions

### Supported Elements
- Vector shapes (lines, curves, polygons)
- Bitmap images
- Hatch patterns
- Spiral modifications
- Text objects

## Hershey Fonts

Advanced font rendering system supporting multiple font formats for laser engraving.

### Supported Formats
- **JHF (Hershey Fonts)**: Classic vector fonts
- **SHX (AutoCAD)**: Shape fonts used in CAD software
- **TrueType**: Standard TTF/OTF fonts with vectorization

### Features
- **Font Caching**: LRU caching for performance
- **Path Optimization**: Welds and optimizes font outlines
- **Character Mapping**: Full Unicode support where available
- **Beam Table Operations**: Advanced geometry processing for font paths

### Usage
```python
# Load and render text with Hershey fonts
font = HersheyFont("hershey.jhf")
paths = font.render_text("HELLO", size=100)
```

## Image Actions

Image manipulation and rasterization utilities for converting vector elements to raster images.

### Features
- **Raster Generation**: Convert vector elements to high-DPI images
- **Bounds Calculation**: Automatic viewport calculation
- **DPI Control**: Configurable dots-per-inch for output quality
- **Aspect Ratio**: Optional ratio preservation
- **Multi-Element Support**: Batch processing of element collections

### Usage
```python
# Create raster image from selected elements
image = create_image(raster_function, elements, bounds, dpi=1000)
```

## Inkscape Integration

Comprehensive integration with Inkscape for file format conversion and vector processing.

### Features
- **Multi-Format Support**: Converts numerous vector formats to SVG
  - PDF, EPS, CDR, CMX, CCX, CDT, WMF, VSD, AI files
- **Command Line Operations**: Direct Inkscape CLI integration
- **SVG Preprocessing**: Automatic conversion of unsupported SVG features
- **Version Compatibility**: Handles different Inkscape versions (0.92, 1.x)
- **Console Commands**:
  - `inkscape simplify`: Convert to plain SVG
  - `inkscape text2path`: Convert text to paths
  - `inkscape makepng`: Generate PNG previews

### Configuration
- **Path Setting**: Configure Inkscape executable location
- **Feature Detection**: Automatic preprocessing of complex SVG features
- **Conversion Preferences**: User choice for handling unsupported elements

### Dependencies
- **Inkscape**: External application installation required

## LBRN (LightBurn Parser)

Parser for LightBurn .lbrn and .lbrn2 files, supporting both standard and optimized formats.

### Features
- **XML Parsing**: Efficient parsing of LightBurn's XML structure
- **Layer Support**: Imports layer settings and assignments
- **Material Profiles**: Material-specific settings preservation
- **Image Support**: Embedded bitmap handling
- **Optimization**: .lbrn2 format for faster loading

### Supported Elements
- Vector paths and shapes
- Bitmap images
- Layer hierarchies
- Material settings
- Cut/engrave operations

## MK Potrace

Custom implementation of the Potrace algorithm for high-quality bitmap vectorization.

### Features
- **Turn Policies**: Multiple path connection strategies
  - BLACK/WHITE: Color preference
  - LEFT/RIGHT: Directional bias
  - MINORITY/MAJORITY: Frequency-based
  - RANDOM: Stochastic approach
- **Corner Detection**: Configurable corner threshold (`alphamax`)
- **Curve Optimization**: Automatic Bezier curve simplification
- **Despeckling**: Remove small artifacts with `turdsize` parameter

### Parameters
- `turdsize`: Minimum feature size (default: 2)
- `turnpolicy`: Path connection policy (default: MINORITY)
- `alphamax`: Corner detection threshold (default: 1.0)
- `opticurve`: Enable curve optimization (default: True)
- `opttolerance`: Optimization error tolerance (default: 0.2)

## Outerworld

External system integration utilities for web services and network communication.

### Features
- **URL Calling**: Direct HTTP requests to external services
- **REST Integration**: Support for RESTful APIs
- **File Loading**: Remote file loading capabilities
- **Position Control**: Coordinate-based element placement
- **HTTP Server**: Built-in web server for remote access

### Console Commands
```bash
call_url <url>          # Call external web service
load_remote <url>       # Load file from remote location
http_server            # Start/stop built-in HTTP server
```

## Param Functions

Parametric shape creation and manipulation functions for dynamic geometry generation.

### Features
- **Grid Generation**: Create copied grids of elements
- **Parametric Shapes**: Shapes with editable parameters
- **Copy Operations**: Intelligent element duplication
- **Geometric Calculations**: Advanced positioning and sizing

### Usage
```python
# Create parametric grid
create_copied_grid(start_point, element, cols=5, rows=3, spacing_x=10, spacing_y=10)
```

## Potrace

Vectorization using the Potrace library for bitmap-to-vector conversion.

### Features
- **Library Integration**: Uses official Potrace library
- **Advanced Options**: Full parameter control for vectorization quality
- **Backend Compatibility**: Fallback implementations for missing library
- **Numba Optimization**: JIT compilation for performance

### Dependencies
- `potracer`: Python port of Potrace (optional)
- `numpy`: Required for array operations

## Serial Exchange

Serial communication utilities for auxiliary device control.

### Features
- **Blocking Operations**: Synchronous serial exchanges for spooler integration
- **Timeout Control**: Configurable operation timeouts
- **Success/Failure Detection**: Pattern-based response validation
- **Command Execution**: Trigger commands based on serial responses

### Usage
```bash
serial_exchange -p COM4 -b 9600 -s "OK" -f "ERROR" "COMMAND"
```

### Dependencies
- `pyserial`: Serial communication library

## Updater

Automatic version checking and update notification system for SefroCut.

### Features
- **GitHub Integration**: Checks releases on GitHub repository
- **Version Comparison**: Compares current version with available releases
- **Beta Support**: Optional checking for pre-release versions
- **Platform Detection**: Automatic platform-specific asset detection
- **Frequency Control**: Configurable check intervals (startup, daily, weekly)

### Supported Platforms
- Windows (exe installers)
- Linux (tar archives)
- macOS (dmg packages)
- Raspberry Pi (specialized builds)
- Source distributions

### Configuration
- **Check Frequency**: At startup, daily, or weekly
- **Beta Inclusion**: Include/exclude pre-release versions
- **Auto-Notification**: GUI prompts for available updates

## Vectrace

Simple polygon-based bitmap vectorization using boundary tracing.

### Features
- **Boundary Tracing**: Follows black pixel boundaries
- **Polygon Generation**: Converts outlines to polygon shapes
- **Direction Optimization**: Smart turn policies for clean paths
- **Performance**: Lightweight implementation without external dependencies

### Algorithm
- **Scanline Processing**: Horizontal line scanning for shape detection
- **Boundary Following**: Clockwise/counter-clockwise path tracing
- **Polygon Assembly**: Combines traced segments into complete shapes

## Winsleep

Windows-specific plugin that prevents system sleep during laser operations.

### Features
- **Sleep Prevention**: Uses Windows API to disable sleep modes
- **Automatic Activation**: Monitors pipe running signals
- **Multi-Process Support**: Handles multiple concurrent operations
- **Thread Execution State**: Sets ES_SYSTEM_REQUIRED flag

### Operation
- **Activation**: Automatically enables when laser jobs start
- **Deactivation**: Disables when all operations complete
- **Platform Specific**: Windows-only functionality

## XCS (XTool Creative Space Parser)

Parser for XTool Creative Space .xcs files, supporting version 2.x formats.

### Features
- **JSON Structure**: Parses XTool's JSON-based file format
- **Canvas Support**: Full canvas geometry and settings
- **Device Integration**: Device-specific parameter preservation
- **Material Profiles**: Material settings and configurations
- **Preview Images**: Embedded thumbnail extraction

### Supported Elements
- Vector paths and shapes
- Material settings
- Device configurations
- Canvas layouts
- Preview images

## Integration Notes

### Plugin Lifecycle
All extra modules follow SefroCut's plugin lifecycle:
- `invalidate`: Check dependencies and platform compatibility
- `register`: Register commands, loaders, and services
- `boot`: Initialize runtime components
- `shutdown`: Cleanup resources

### Dependencies
Many modules have optional dependencies that enable additional functionality when installed. Missing dependencies typically disable the module gracefully rather than causing errors.

### Performance Considerations
- **Heavy Processing**: Image processing and vectorization modules may be CPU-intensive
- **Memory Usage**: Large file parsing can require significant memory
- **External Calls**: Inkscape integration involves process spawning and file I/O

### Error Handling
Modules implement robust error handling:
- **Dependency Checks**: Graceful degradation when libraries unavailable
- **File Validation**: Comprehensive error checking for malformed files
- **User Feedback**: Clear error messages through kernel channels

This collection of extra modules significantly extends SefroCut's capabilities while maintaining the core system's modularity and optional nature.