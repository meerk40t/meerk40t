# Online Help: Pathproperty

## Overview

This help page covers the **Pathproperty** functionality in MeerK40t.

The Path Properties panel provides comprehensive control over vector path elements, including geometric properties, visual attributes, positioning, and path statistics. This panel is the central interface for editing and analyzing vector graphics elements in your laser cutting/engraving projects.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\pathproperty.py`

## Category

**Path Properties**

## Description

The Path Properties panel is a multi-section configuration interface that allows you to modify all aspects of vector path elements. It includes controls for element identification, geometric properties, visual styling (stroke and fill), positioning, and detailed path analysis. The panel adapts its interface based on the selected element type, showing relevant properties for each geometry type.

## How to Use

### Key Features

- Comprehensive path element editing
- Real-time visual attribute modification
- Path statistics and analysis
- Automatic classification integration
- Multi-panel property organization

### Basic Usage

1. **Select Path Element**: Choose a vector element (line, curve, shape, text path, etc.) in the elements tree or canvas
2. **Modify Visual Properties**: Adjust stroke color, fill color, and stroke width
3. **Set Geometric Properties**: Configure position, size, and shape-specific parameters
4. **Analyze Path**: Click "Retrieve" to calculate path statistics (segments, points, length, area)
5. **Apply Changes**: Changes are applied immediately and reflected on the canvas

## Property Panels

### ID Panel

**Element Identification**:
- Unique element identifier
- Custom naming and labeling
- Hierarchical organization support

### Rounded Rectangle Panel (Rounded Rect Elements)

**Corner Radius Control**:
- **RX**: Horizontal corner radius
- **RY**: Vertical corner radius
- Independent control of corner curvature
- Real-time preview of corner changes

### Dynamic Path Attributes

**Plugin-Based Properties**:
- Extensible attribute system through plugins
- Element-type-specific properties loaded dynamically
- Custom controls for specialized path types

### Stroke and Fill Panels

**Color Management**:
- **Stroke Color**: Outline color selection with color picker
- **Fill Color**: Interior fill color selection with color picker
- **Color Transparency**: Alpha channel support
- **Color Classification**: Automatic operation assignment based on colors

**Visual Effects**:
- Solid colors, gradients, and patterns
- Color swatch management
- Real-time color preview

### Stroke Width Panel

**Line Thickness Control**:
- **Stroke Width**: Line thickness in various units (px, mm, pt)
- **Unit Conversion**: Automatic conversion between measurement systems
- **Minimum/Maximum Limits**: Device-capability-aware constraints

### Line Properties Panel

**Line Style Configuration**:
- **Line Cap**: End cap styles (butt, round, square)
- **Line Join**: Corner join styles (miter, round, bevel)
- **Miter Limit**: Maximum miter length for sharp corners
- **Dash Patterns**: Custom dash and gap sequences

### Prevent Change Panel

**Element Protection**:
- **Lock Element**: Prevent accidental modification
- **Protect Properties**: Selective property locking
- **Change Prevention**: Safeguard critical design elements

### Position Size Panel

**Geometric Positioning**:
- **X/Y Position**: Coordinate positioning
- **Width/Height**: Dimension control
- **Rotation**: Angular orientation
- **Scale**: Proportional resizing
- **Transform Origin**: Pivot point for transformations

## Path Information Display

### Statistics Controls

**Path Analysis**:
- **Retrieve Button**: Calculate and display path statistics
- **Segments**: Number of path segments (lines, curves, moves)
- **Points**: Total number of control points
- **Length**: Total path length in millimeters
- **Area**: Covered area with and without stroke width

### Automatic Classification

**Smart Element Assignment**:
- **Auto-Classify Checkbox**: Automatically reclassify elements after color changes
- **Color-Based Operations**: Assign elements to operations based on stroke/fill colors
- **Real-time Updates**: Immediate classification when colors change

## Supported Element Types

### Vector Shapes

**Geometric Elements**:
- Lines and polylines
- Rectangles and rounded rectangles
- Circles and ellipses
- Polygons and complex shapes
- Custom paths and curves

### Text Elements

**Text Path Properties**:
- Font-based path generation
- Character spacing and kerning
- Text transformation properties
- Path outline generation

### Effect Elements

**Specialized Paths**:
- Hatch patterns and fills
- Image trace results
- Effect-generated geometry
- Plugin-created elements

## Technical Details

The PathPropertyPanel class extends ScrolledPanel and orchestrates multiple specialized sub-panels for comprehensive path editing.

**Key Technical Components**:
- **Modular Panel System**: Individual panels for different property categories
- **Dynamic Panel Loading**: Plugin-based attribute panels loaded at runtime
- **Path Analysis Engine**: Complex geometric calculations for statistics
- **Color Management**: Integrated color picker and classification system
- **Real-time Updates**: Immediate visual feedback for property changes

**Path Analysis Algorithm**:
- **Segment Counting**: Identifies distinct path segments (Move, Line, Curve, Close)
- **Point Extraction**: Collects all control points from path elements
- **Length Calculation**: Precise path length using numerical integration
- **Area Computation**: Raster-based area calculation with stroke consideration

**Color Classification Integration**:
- **Signal-Based Updates**: Responds to color changes with automatic classification
- **Operation Assignment**: Matches element colors to operation color rules
- **Tree Synchronization**: Updates element tree and canvas display

## Usage Guidelines

### Path Editing Workflow

**Property Modification**:
- Select element first, then modify properties
- Use "Retrieve" to analyze complex paths before laser processing
- Check area calculations for material usage estimation
- Verify path length for time and power calculations

### Color Management

**Classification Strategy**:
- Use consistent color schemes for automatic operation assignment
- Enable auto-classify for streamlined workflow
- Test color changes on scrap material first
- Consider material absorption characteristics

### Geometric Precision

**Measurement Accuracy**:
- Use appropriate units for your workflow (mm for precision work)
- Check path statistics before final output
- Verify area calculations for material cost estimation
- Consider stroke width in total material coverage

## Troubleshooting

### Panel Not Displaying

**Element Selection**:
- Ensure a valid path element is selected
- Check that element type is supported (elem* or effect*)
- Text elements are not supported (use text properties instead)
- Try refreshing the elements tree

### Statistics Not Calculating

**Path Complexity**:
- Complex paths may take time to analyze
- Check console for calculation errors
- Ensure element has valid geometry
- Try selecting individual path segments

### Color Changes Not Applying

**Classification Issues**:
- Verify auto-classify is enabled if needed
- Check that operations exist for the selected colors
- Ensure element is not locked or protected
- Try manual classification after color changes

### Property Changes Not Visible

**Update Problems**:
- Click outside controls to trigger updates
- Check for element locking or protection
- Verify element is not hidden or disabled
- Try refreshing the canvas view

## Advanced Features

### Plugin-Based Attributes

**Extensible Properties**:
- Custom panels loaded through plugin system
- Specialized controls for custom element types
- Third-party property extensions
- Dynamic interface adaptation

### Path Statistics Analysis

**Detailed Metrics**:
- **Segment Analysis**: Break down complex paths into components
- **Point Optimization**: Identify redundant control points
- **Length Optimization**: Calculate efficient travel paths
- **Area Estimation**: Material usage and cost calculation

### Color Classification Automation

**Smart Assignment**:
- **Rule-Based Classification**: Automatic operation assignment
- **Color Matching**: Fuzzy color matching for similar shades
- **Batch Processing**: Apply classification rules to multiple elements
- **Template Support**: Save and load classification templates

## Related Topics

*Link to related help topics:*

- [[Online Help: Operationproperty]]
- [[Online Help: Textproperty]]
- [[Online Help: Imageproperty]]
- [[Online Help: Transform]]

## Screenshots

*Add screenshots showing the path properties panel with different element types and property configurations.*

---

*This help page provides comprehensive documentation for the Path Properties panel in MeerK40t.*
