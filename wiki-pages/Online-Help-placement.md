# Online Help: Placement

## Overview

This help page covers the **Placement** functionality in MeerK40t.

The Placement Properties panel provides comprehensive control over job start positions and grid-based element placement. Placements define where laser operations will execute on the laser bed, allowing you to create multiple copies of your design at different positions.

Placements are MeerK40ts terms for a job start position. Normally MeerK40t burns your design exactly on the laserbed as it is displayed on the scene. Your job start is at the top left corner or (0, 0).

<img src="https://github.com/meerk40t/meerk40t/assets/2670784/173785bd-b175-45c6-81c9-40264f72a861" width="450">

You can define arbitrary job start positions by putting a so called placement (
<img src="https://github.com/meerk40t/meerk40t/assets/2670784/62591c7c-a412-4bc3-af86-f998222cc2b8" width="30">
) on the scene: you select the icon in the toolbar and click on the scene to define a new jobstart.

<img src="https://github.com/meerk40t/meerk40t/assets/2670784/e3a611c4-b04b-4600-ab17-a0bbd3fc9a76">

In this example we have 6 of them:

<img src="https://github.com/meerk40t/meerk40t/assets/2670784/729b02cc-38c7-4e63-980e-686198df75ca" width="200">

This will use the defined layout and place it at every defined jobstart:

<img src="https://github.com/meerk40t/meerk40t/assets/2670784/bfe68969-071a-4aed-8ece-37a97b058868" >

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\placementproperty.py`

## Category

**Placement Properties**

## Description

The Placement Properties panel is a sophisticated interface for managing job start positions and creating complex grid patterns. It supports two main placement types: single point placements and grid-based array placements with advanced positioning, rotation, and pattern generation capabilities.

## How to Use

### Key Features

- Integrates with: `element_property_reload`
- Single point and grid-based placements
- Advanced positioning and rotation controls
- Pattern generation for tiling operations
- Visual grid preview and validation

### Basic Usage

1. **Create Placement**: Select the placement tool from the toolbar and click on the scene to create a placement point
2. **Configure Position**: Set X/Y coordinates for the placement origin
3. **Set Grid Parameters**: Define repetitions and gaps for array placements
4. **Configure Rotation**: Apply rotation to the entire placement grid
5. **Generate Patterns**: Use the grid helper to automatically create common patterns (quadratic, hexagonal, etc.)
6. **Preview and Execute**: Review the placement grid and execute the job

## Placement Types

### Place Current

**Single Position Placement**:
- Places the design at a single specified position
- Simple X/Y coordinate positioning
- Optional rotation around the placement point
- Loop count for repeated execution at the same position

### Place Point

**Grid-Based Array Placement**:
- Creates multiple copies in a grid pattern
- Configurable repetitions in X and Y directions
- Adjustable gaps between placements
- Advanced alternating displacements for complex patterns

## Property Controls

### Basic Controls

**Enable/Disable**:
- **Enable**: Include/exclude placement from job execution
- Controls whether this placement contributes to the final job

**Position Settings**:
- **X/Y Coordinates**: Starting position for the placement grid
- **Rotation**: Angular rotation applied to all elements in the placement
- **Loops**: Number of times to repeat the entire placement

### Grid Configuration

**X-Direction Repetitions**:
- **Repeats**: Number of placements in horizontal direction (0 = fill available space)
- **Gap**: Spacing between placements in X-direction

**Y-Direction Repetitions**:
- **Repeats**: Number of placements in vertical direction (0 = fill available space)
- **Gap**: Spacing between placements in Y-direction

### Advanced Positioning

**Alternating Displacements**:
- **X-Displacement**: Percentage-based offset for alternating rows/columns
- **Y-Displacement**: Percentage-based offset for alternating rows/columns
- **Rotate Alternating**: Rotate elements in alternating positions

**Corner Positioning**:
- **Corner**: Reference point for placement (Top-Left, Top-Right, Bottom-Right, Bottom-Left, Center)
- Determines how the placement grid is positioned relative to the X/Y coordinates

**Orientation**:
- **L2R (unidirectional)**: Left to right, top to bottom
- **L2R (bidirectional)**: Left to right then right to left (snake pattern)
- **T2B (bidirectional)**: Top to bottom, bidirectional columns

### Selection Controls

**Grid Subset Selection**:
- **Start-Index**: First placement position to use (0-based)
- **Count**: Number of placements to execute (0 = all remaining)

### Grid Helper (Tiling)

**Automatic Pattern Generation**:
- **Shape Selection**: Choose from predefined patterns:
  - **Quadratic**: Square grid pattern
  - **Hexagon**: Hexagonal honeycomb pattern
  - **Circular**: Circular packing pattern
  - **Triangular**: Triangular grid pattern

**Pattern Parameters**:
- **Dimension**: Size parameter for the selected shape
- **Define Button**: Generate placement parameters for the selected pattern
- **Create Template**: Optionally create a visual template element

## Visual Grid Preview

**Placement Visualization**:
- Real-time preview of which grid positions will be used
- X marks active placements, - marks inactive positions
- Updates automatically when parameters change
- Helps validate complex grid configurations

## Technical Details

The PlacementPanel class manages two distinct placement operation types with comprehensive grid mathematics and pattern generation algorithms.

**Key Technical Components**:
- **Grid Mathematics**: Complex algorithms for calculating placement positions based on orientation and alternating displacements
- **Pattern Generators**: Built-in functions for common tiling patterns (hexagonal, triangular, circular)
- **Visual Preview**: Real-time grid visualization with selection highlighting
- **Parameter Validation**: Range checking and automatic limit enforcement

**Placement Algorithms**:
- **Orientation Processing**: Different traversal patterns (unidirectional, bidirectional, vertical priority)
- **Alternating Logic**: Percentage-based displacements for irregular patterns
- **Boundary Calculation**: Automatic fitting to available workspace
- **Subset Selection**: Index-based selection of placement positions

**Pattern Generation**:
- **Geometric Calculations**: Mathematical generation of regular patterns
- **Workspace Fitting**: Automatic calculation of maximum repetitions
- **Template Creation**: Optional visual elements for pattern verification

## Usage Guidelines

### Basic Placement

**Single Position Jobs**:
- Set X/Y coordinates to desired position
- Use corner setting to control alignment
- Apply rotation if needed
- Set loops for repeated execution

### Grid Operations

**Array Creation**:
- Define base position and gap spacing
- Set repetitions (0 for auto-fill)
- Choose orientation pattern
- Use alternating displacements for special patterns

### Pattern Generation

**Tiling Operations**:
- Select appropriate shape for your needs
- Enter dimension parameter
- Click "Define" to generate placement parameters
- Optionally create template for visualization
- Adjust parameters as needed

### Advanced Techniques

**Complex Arrangements**:
- Combine multiple placements for irregular layouts
- Use subset selection for partial grid execution
- Apply alternating rotations for varied orientations
- Create overlapping patterns with negative gaps

## Troubleshooting

### Grid Not Displaying

**Parameter Validation**:
- Ensure X/Y coordinates are within workspace bounds
- Check that repetitions are valid (≥ 0)
- Verify gap values are reasonable
- Enable the placement operation

### Pattern Generation Issues

**Shape Parameters**:
- Ensure dimension value is positive and reasonable
- Check workspace size compatibility
- Verify shape selection is valid
- Try different dimension values

### Preview Problems

**Visualization Issues**:
- Parameters may be outside display range
- Try reducing repetitions or adjusting gaps
- Check for extremely large coordinate values
- Refresh the panel display

### Execution Problems

**Job Issues**:
- Verify placement is enabled
- Check that elements are assigned to operations
- Ensure coordinates are within laser bed limits
- Test with single placement first

## Advanced Features

### Mathematical Grid Generation

**Algorithmic Patterns**:
- Precise geometric calculations for regular patterns
- Support for complex polygonal arrangements
- Automatic workspace boundary detection
- Mathematical optimization for packing efficiency

### Dynamic Parameter Updates

**Real-time Feedback**:
- Immediate visual updates when parameters change
- Automatic validation and range checking
- Preview updates for parameter validation
- Signal-based synchronization with scene display

### Integration with Operations

**Job Execution**:
- Seamless integration with laser operations
- Support for all operation types (cut, engrave, raster)
- Preservation of operation-specific parameters
- Batch execution across multiple placements

## Related Topics

*Link to related help topics:*

- [[Online Help: Operationproperty]]
- [[Online Help: Transform]]
- [[Online Help: Alignment]]
- [[Online Help: Distribute]]

## Screenshots

*Add screenshots showing placement creation, grid configuration, and pattern generation.*

---

*This help page provides comprehensive documentation for the Placement Properties panel in MeerK40t.*
