# DXF Module

The DXF (Drawing Exchange Format) module provides comprehensive support for importing AutoCAD DXF files into SefroCut. This module enables laser cutting software to work with industry-standard CAD file formats, converting DXF geometric entities into SefroCut's element system for laser processing.

## Architecture

The DXF module follows SefroCut's plugin architecture pattern with a clean separation of concerns:

```
sefrocut/dxf/
├── __init__.py          # Module initialization
├── plugin.py            # Plugin lifecycle and configuration
└── dxf_io.py           # Core DXF parsing and conversion logic
```

### Core Components

- **DxfLoader**: Main loader class registered with the kernel's load system
- **DXFProcessor**: Core processing engine that converts DXF entities to SefroCut elements
- **Plugin Integration**: Lifecycle hooks for dependency checking and settings registration

## Features

### File Format Support
- **DXF Versions**: Compatible with various DXF versions through ezdxf library
- **File Recovery**: Automatic recovery of corrupted or low-quality DXF files
- **Unit Conversion**: Automatic scaling based on DXF unit specifications
- **Coordinate System**: Proper transformation from DXF coordinate system (+Y up) to SefroCut (+Y down)

### Geometric Entity Support
The module supports comprehensive DXF entity conversion:

- **Basic Shapes**: Lines, circles, arcs, ellipses, points
- **Polylines**: Both 2D and 3D polylines with arc segments
- **Complex Geometry**: Splines, hatches, solids, traces
- **Text Elements**: MTEXT and TEXT entities with font scaling
- **Images**: Embedded raster images with proper positioning
- **Blocks**: INSERT entities for grouped geometry

### Smart Processing Features
- **Auto-Centering**: Optional centering and scaling to fit laser bed dimensions
- **Layer Assignment**: Automatic operation assignment based on layer names
- **Color Mapping**: DXF color conversion to SefroCut stroke colors
- **3D Polyline Support**: Configurable support for 3D polylines (can be disabled for mesh data)

### Integration Features
- **Element Classification**: Automatic classification of imported elements
- **Operation Assignment**: Smart assignment to cut/engrave operations based on layer names
- **Matrix Transformations**: Proper scaling, translation, and coordinate system conversion

## Usage

### Basic Import
```python
# DXF files are automatically loaded through SefroCut's file loading system
# Simply open a .dxf file in SefroCut
```

### Console Commands
The DXF module integrates with SefroCut's console system but doesn't provide additional commands beyond standard file loading.

### Programmatic Usage
```python
from sefrocut.dxf.dxf_io import DxfLoader

# Load DXF file programmatically
loader = DxfLoader()
success = loader.load(kernel, elements_service, "path/to/file.dxf")
```

## Configuration

### Settings
The DXF module provides two main configuration options:

- **DXF Center and Fit** (`dxf_center`): When enabled, automatically scales and centers DXF content to fit within the laser bed dimensions
- **DXF: Try to read 3D-polylines** (`dxf_try_unsupported`): Enables processing of 3D polylines (disable if file contains mesh data)

### Preferences Panel
Settings are accessible through:
- **Menu**: File → Preferences → Input/Output section
- **Configuration**: Both options appear under the "Input" section

## Supported DXF Entities

| Entity Type | Support Level | Description |
|-------------|---------------|-------------|
| `CIRCLE` | Full | Converted to ellipse elements |
| `ARC` | Full | Converted to path elements with arc geometry |
| `ELLIPSE` | Full | Full ellipse support with rotation |
| `LINE` | Full | Direct conversion to line elements |
| `POINT` | Full | Converted to point elements |
| `POLYLINE` | Full | Support for 2D/3D polylines with arc segments |
| `LWPOLYLINE` | Full | Lightweight polyline support |
| `HATCH` | Full | Complex hatch patterns converted to paths |
| `IMAGE` | Full | Embedded images with proper positioning |
| `MTEXT` | Full | Multi-line text with font scaling |
| `TEXT` | Full | Single-line text elements |
| `SOLID` | Full | Solid fills converted to filled paths |
| `TRACE` | Full | Trace entities as filled quadrilaterals |
| `SPLINE` | Full | B-spline conversion to cubic/quadratic paths |
| `INSERT` | Full | Block insertions as grouped elements |

## Technical Details

### Coordinate System Transformation
DXF uses a bottom-left origin with +Y upward, while SefroCut uses top-left with +Y downward. The module applies:

```python
# Scale and flip Y-axis, then translate to SefroCut coordinate system
matrix.post_scale(scale, -scale)
matrix.post_translate_y(device.view.unit_height)
```

### Unit Handling
- **Default Units**: Assumes millimeters if no units specified in DXF header
- **Unit Conversion**: Uses ezdxf's unit conversion system for proper scaling
- **Scaling Factor**: Calculated from DXF `$INSUNITS` header variable

### Color Mapping
- **RGB Colors**: Direct conversion from entity.rgb if available
- **Indexed Colors**: DXF color index mapped through ezdxf's color table
- **Layer Colors**: Falls back to layer color if entity color is "ByLayer" (256)

### Layer-Based Operation Assignment
Automatic operation assignment based on layer names:
- **ENGRAVE** layers → Assign to engrave operations
- **CUT** layers → Assign to cut operations
- **Color Matching**: Attempts to match existing operations by color/label

### Error Handling
- **File Recovery**: Uses ezdxf's recovery module for corrupted files
- **Unsupported Entities**: Gracefully skips unknown entity types
- **Version Compatibility**: Handles different ezdxf library versions

### Performance Considerations
- **Memory Usage**: Large DXF files with complex geometry may require significant memory
- **Processing Time**: Hatch patterns and splines involve computational geometry
- **File Size Limits**: Limited by available system memory and ezdxf library constraints

## Dependencies

### Required Dependencies
- **ezdxf**: Core DXF parsing library (https://ezdxf.readthedocs.io/)
  - Minimum version: Compatible with recovery features
  - Tested with versions supporting cubic bezier decomposition

### Optional Dependencies
- **PIL/Pillow**: Required for image entity processing and EXIF handling

### Version Compatibility
The module includes compatibility code for different ezdxf versions:
- **v0.6.14+**: Uses updated color handling
- **v0.15+**: Uses flattening API for splines
- **Pre-v0.13**: Fallback spline processing methods

## Examples

### Basic DXF Import
1. Open SefroCut
2. File → Open
3. Select a .dxf file
4. Content automatically imports and centers on bed

### Configuration Example
```python
# Enable auto-centering
kernel.elements.setting(bool, "dxf_center", True)

# Enable 3D polyline support
kernel.elements.setting(bool, "dxf_try_unsupported", True)
```

### Layer-Based Operations
Create layers in CAD software named:
- `CUT_OUTER` → Automatically assigned to cut operations
- `ENGRAVE_DETAIL` → Automatically assigned to engrave operations

### Troubleshooting

#### Common Issues
- **Import Fails**: Check ezdxf installation and DXF file corruption
- **Wrong Scale**: Verify units in CAD software match SefroCut expectations
- **Missing Colors**: Check DXF color settings and layer assignments
- **Performance Issues**: Simplify complex hatch patterns or splines

#### Debug Information
Enable console logging to see detailed import information:
```python
# Console command to check loaded elements
elements list
```

#### File Compatibility
- **Recommended**: DXF versions R12-R2018
- **Best Results**: Files from AutoCAD, LibreCAD, DraftSight
- **Known Issues**: Some proprietary CAD software may export non-standard DXF

## Integration with SefroCut Core

The DXF module integrates deeply with SefroCut's core systems:

- **Element Tree**: Imported entities become nodes in the element hierarchy
- **Operation System**: Automatic assignment to laser operations
- **View System**: Proper scaling and positioning on the virtual bed
- **Classification**: Post-import element classification for optimization

This module transforms industry-standard CAD files into laser-ready toolpaths, bridging the gap between design software and laser cutting hardware.
