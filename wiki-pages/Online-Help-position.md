# Online Help: Position

## Overview

This help page covers the **Position** functionality in MeerK40t.

The Position panel provides comprehensive control over the location, size, and dimensions of selected elements in your laser cutting/engraving projects. This panel allows precise positioning and scaling with multiple reference points and unit systems.

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/36086961-2c7b-44ab-ae83-701cd09ebe8e)

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\position.py`

## Category

**Position and Dimensions**

## Description

The Position panel is a sophisticated interface for editing the geometric properties of vector elements and images. It provides precise control over position coordinates, dimensions, and scaling with real-time visual feedback. The panel supports multiple unit systems, aspect ratio locking, and different editing modes for individual elements or grouped selections.

## How to Use

### Key Features

- Integrates with: `refresh_scene`
- Integrates with: `modified_by_tool`
- Integrates with: `lock_active`
- Real-time position and dimension editing
- Multiple unit systems and conversions
- Reference point positioning system
- Individual vs. group editing modes

### Basic Usage

1. **Select Elements**: Choose one or more elements in the scene that you want to reposition or resize
2. **Set Reference Point**: Click the reference point button to choose which part of the selection (corner, edge, center) should be positioned
3. **Enter Coordinates**: Type X and Y values to move the selection to the desired position
4. **Adjust Dimensions**: Modify width and height values to scale the selection
5. **Apply Changes**: Click the execute button or press Enter to apply the changes

## Position Controls

### Coordinate System

**X/Y Position**:
- **X**: Horizontal position coordinate
- **Y**: Vertical position coordinate
- Values displayed in selected units
- Real-time input validation and conversion

**Reference Point System**:
- **9-Point Grid**: Choose from 9 reference positions:
  - Top-Left, Top-Center, Top-Right
  - Middle-Left, Center, Middle-Right
  - Bottom-Left, Bottom-Center, Bottom-Right
- Visual grid selector button
- Determines which point of the selection is positioned at the X/Y coordinates

### Dimension Controls

**Width and Height**:
- **Width (W)**: Horizontal dimension of the selection
- **Height (H)**: Vertical dimension of the selection
- Independent or linked scaling based on aspect ratio lock

**Aspect Ratio Control**:
- **Keep Ratio**: Maintains width/height proportions when scaling
- Automatic adjustment of complementary dimension
- Preserves element shapes during resizing

## Editing Modes

### Individual Element Mode

**Individual Editing**:
- **Individually Checkbox**: When checked, changes apply to each selected element separately
- Each element gets the same new dimensions
- Useful for standardizing multiple elements to the same size
- Maintains relative positions between elements

### Group Selection Mode

**Unified Editing**:
- **Group Mode**: When unchecked, changes apply to the selection as a whole
- Scales and moves the entire selection together
- Maintains spatial relationships between elements
- Bounding box operations

## Unit System

### Available Units

**Measurement Systems**:
- **mm**: Millimeters (default metric)
- **cm**: Centimeters
- **inch**: Inches (imperial)
- **mil**: Thousandths of an inch
- **%**: Percentage (relative to scene size)

**Unit Conversion**:
- Automatic conversion between unit systems
- Context-aware display based on workspace settings
- Real-time updates when units change

## Advanced Features

### Real-time Updates

**Live Preview**:
- Immediate visual feedback as values change
- Non-destructive editing (changes not applied until executed)
- Preview of reference point positioning
- Dynamic unit conversion display

### Signal Integration

**Event Handling**:
- **refresh_scene**: Updates when scene changes
- **modified_by_tool**: Responds to tool modifications
- **lock_active**: Synchronizes aspect ratio lock state
- Automatic panel updates for selection changes

### Precision Input

**Value Validation**:
- Numeric input validation with error handling
- Length parsing with unit recognition
- Zero-dimension protection for lines and points
- Range checking and automatic correction

## Usage Guidelines

### Positioning Elements

**Coordinate Entry**:
- Enter absolute coordinates for precise placement
- Use reference points to control alignment (center for centering, corners for alignment)
- Consider workspace origin and coordinate system
- Check units match your design requirements

### Scaling Operations

**Dimension Changes**:
- Use aspect ratio lock for proportional scaling
- Individual mode for standardizing multiple elements
- Group mode for maintaining design relationships
- Preview changes before applying

### Unit Selection

**Appropriate Units**:
- Choose units that match your design scale
- Metric units (mm/cm) for precision work
- Imperial units (inch/mil) for compatibility
- Percentage for relative positioning

## Troubleshooting

### Panel Not Updating

**Selection Issues**:
- Ensure elements are properly selected and emphasized
- Check that elements have valid bounds
- Try refreshing the scene or reselecting elements
- Verify panel is visible and enabled

### Changes Not Applying

**Execution Problems**:
- Click the execute button or press Enter in text fields
- Check for invalid numeric values
- Ensure sufficient workspace bounds
- Verify element types support the requested changes

### Unit Conversion Issues

**Display Problems**:
- Check unit selection matches expected values
- Verify workspace unit settings
- Try switching units and back
- Refresh the panel display

### Reference Point Confusion

**Positioning Issues**:
- Click the reference point button to see the 9-point grid
- Select the appropriate corner/edge/center for your positioning needs
- Preview the position before applying changes
- Use center point for relative positioning

## Technical Details

The PositionPanel class provides sophisticated geometric transformation capabilities with real-time visual feedback and multi-unit support.

**Key Technical Components**:
- **Coordinate Transformation**: Unit-aware position and dimension calculations
- **Reference Point System**: 9-point positioning grid with visual indicators
- **Aspect Ratio Management**: Proportional scaling with automatic dimension adjustment
- **Signal Integration**: Real-time updates through event-driven architecture
- **Validation Engine**: Input validation and error handling for numeric fields

**Geometric Operations**:
- **Translation**: Matrix-based position changes with bounds tracking
- **Scaling**: Proportional and independent dimension modifications
- **Reference Point Logic**: Offset calculations for different anchor positions
- **Unit Conversion**: Dynamic conversion between measurement systems

**Performance Optimizations**:
- **Lazy Updates**: Deferred calculations until changes are applied
- **Bounds Caching**: Efficient bounding box calculations
- **Signal Debouncing**: Prevents excessive update cycles
- **Memory Management**: Proper cleanup of graphical resources

## Related Topics

*Link to related help topics:*

- [[Online Help: Transform]]
- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Placement]]

## Screenshots

*Add screenshots showing the position panel with different reference points and unit selections.*

---

*This help page provides comprehensive documentation for the Position panel in MeerK40t.*
