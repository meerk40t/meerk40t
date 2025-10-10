# Online Help: Imagesplit

## Overview

This help page covers the **Imagesplit** functionality in MeerK40t.

The Image Split tool provides advanced image processing capabilities for handling large raster images in laser engraving operations. It allows users to split oversized images into smaller, manageable tiles and create keyhole operations for complex multi-element designs.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\imagesplitter.py`

## Category

**GUI**

## Description

The Image Split functionality is essential for laser engraving workflows involving large images that exceed the physical working area of the laser device. It provides two main capabilities:

### Image Splitting
**Render + Split** mode allows dividing large images into a grid of smaller tiles that can be engraved separately and reassembled. This is crucial for:
- **Large Format Engraving**: Breaking down oversized designs into manageable pieces
- **Device Limitations**: Working around maximum travel distances of laser systems
- **Material Constraints**: Adapting to workpiece size limitations
- **Quality Control**: Managing engraving precision across large areas

### Keyhole Operations
**Keyhole operation** mode creates specialized engraving patterns where one element acts as a "keyhole" or mask for another. This enables:
- **Layered Designs**: Complex multi-element compositions with cutouts and overlays
- **Stencil Effects**: Creating masks and templates for selective engraving
- **Registration Marks**: Precise alignment features for multi-piece assemblies
- **Special Effects**: Artistic compositions with depth and layering

Users would access this tool when working with images larger than their laser's working area, or when creating complex multi-element designs requiring precise registration and layering.

## How to Use

### Available Controls

- **X-Axis/Y-Axis**: Spin controls for setting grid dimensions (1-25 tiles per axis)
- **Order to process**: Radio buttons for selection processing order (Selection, First Selected, Last Selected)
- **DPI**: Text field for output image resolution
- **Create split images**: Button to generate tiled image set
- **Create keyhole image**: Button to generate keyhole composition
- **Invert Mask**: Checkbox to invert the keyhole mask
- **Trace Keyhole**: Checkbox to add outline tracing to keyhole

### Key Features

- **Grid-Based Splitting**: Configurable X/Y tile counts for flexible layout
- **Processing Order Control**: Different selection handling for complex designs
- **Resolution Management**: Independent DPI control for split outputs
- **Keyhole Masking**: Advanced compositing with inversion and tracing options
- **Real-time Validation**: Dynamic button enabling based on selection state
- **Settings Persistence**: Automatic saving/restoration of user preferences

### Basic Usage

1. **Select Image Elements**: Choose the image(s) to be split or used in keyhole operation
2. **Choose Operation Mode**: Select either "Render + Split" or "Keyhole operation" tab
3. **Configure Parameters**: Set grid dimensions, processing order, and resolution
4. **Apply Operation**: Click the appropriate button to generate the split images or keyhole composition
5. **Process Results**: The generated images will appear in the element tree for further processing

### Advanced Techniques

- **Optimal Grid Sizing**: Balance tile count with engraving time and registration accuracy
- **Resolution Matching**: Use consistent DPI across split operations for uniform quality
- **Keyhole Layering**: Combine multiple keyhole operations for complex stencil effects
- **Registration Planning**: Design split layouts to minimize alignment challenges

## Technical Details

The Image Split tool implements sophisticated image processing algorithms:

- **Grid Division**: Mathematical subdivision of source images into rectangular tiles
- **Coordinate Mapping**: Precise pixel-to-physical unit conversion for accurate splitting
- **Keyhole Compositing**: Boolean operations between mask and target images
- **Resolution Scaling**: Independent DPI handling for output optimization

**Command Integration:**
- `render_split <cols> <rows> <dpi> --order <selection>` - Core splitting operation
- `render_keyhole <dpi> --order <selection> [--invert] [--outline]` - Keyhole generation

The tool integrates with MeerK40t's element selection system and maintains settings persistence across sessions. It uses wxPython for the user interface and PIL (Python Imaging Library) for image processing operations.

## Related Topics

*Link to related help topics:*

- [[Online Help: Imageproperty]] - Image processing and enhancement controls
- [[Online Help: Crop]] - Image cropping and boundary management
- [[Online Help: Placement]] - Element positioning and alignment
- [[Online Help: Raster]] - Raster engraving operations

## Screenshots

### Image Split Dialog - Render + Split Tab
The main dialog shows the "Render + Split" tab with grid configuration controls:
- **Grid Controls**: X-Axis and Y-Axis spin controls (1-25) for setting the number of tiles
- **Processing Order**: Radio button selection between "Selection", "First Selected", and "Last Selected"
- **Resolution**: DPI text field for output image resolution
- **Action Button**: "Create split images" button (enabled when images are selected)
- **Status Display**: Shows current selection count and operation readiness

### Image Split Dialog - Keyhole Operation Tab
The "Keyhole operation" tab displays advanced compositing options:
- **Keyhole Controls**: "Create keyhole image" button for mask-based operations
- **Mask Options**: "Invert Mask" checkbox to reverse the keyhole masking effect
- **Outline Feature**: "Trace Keyhole" checkbox to add outline tracing to the keyhole
- **Same Order Controls**: Processing order radio buttons (Selection/First Selected/Last Selected)
- **Resolution Field**: DPI setting for keyhole output resolution

### Before/After Examples
- **Original Large Image**: Shows an oversized image that exceeds laser working area
- **Split Result**: Displays the grid of smaller tiled images created by the split operation
- **Keyhole Composition**: Illustrates a keyhole operation with one image acting as a mask for another
- **Registration Marks**: Shows how split images include alignment features for reassembly

---

*This help page is automatically generated. Please update with specific information about the imagesplit feature.*
