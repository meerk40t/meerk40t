# Online Help: Alignment

## Overview

The **Alignment** panel is MeerK40t's comprehensive element positioning and organization tool. It provides three powerful functions - **Align**, **Distribute**, and **Arrange** - to help you create professional, well-organized designs with precise element positioning.

The Alignment dialog combines three distinct but related tools:
- **Align**: Position elements relative to each other or reference points
- **Distribute**: Space elements evenly along paths or boundaries
- **Arrange**: Organize elements into structured grids

## What is Element Alignment?

Element alignment is the process of positioning design elements relative to each other or reference points to create organized, professional layouts. Unlike manual positioning, alignment tools provide:

- **Precision positioning**: Exact alignment to edges, centers, or custom points
- **Batch operations**: Align multiple elements simultaneously
- **Reference-based positioning**: Align relative to selection bounds, first/last selected, laser bed, or reference objects
- **Visual feedback**: Real-time preview of alignment results

### When to Use Alignment

Use alignment tools when you need:
- **Professional layouts**: Create evenly spaced, well-organized designs
- **Precise positioning**: Align elements to exact coordinates or relative positions
- **Batch operations**: Position multiple elements consistently
- **Reference alignment**: Align elements to specific points or objects on your design

## Location in MeerK40t

The Alignment dialog is accessed through:
- **Menu**: `Edit` → `Element Alignment` → `Expert Mode`
- **Toolbar**: Alignment button (when elements are selected)
- **Shortcut**: Configurable via keybindings
- **Source code**: `meerk40t\gui\alignment.py`

## Category

**GUI**

## Description

The Alignment panel provides three specialized tools for element positioning and organization:

### Align Tab
Positions selected elements relative to reference points or boundaries. Choose alignment along X and Y axes independently, with options for left/center/right and top/center/bottom positioning.

### Distribute Tab
Spaces elements evenly along paths, boundaries, or custom shapes. Elements can be distributed along rectangular boundaries, complex shapes, or specific point sequences.

### Arrange Tab
Organizes elements into structured grids with customizable spacing, alignment, and sizing options. Perfect for creating ordered layouts like button arrays or component grids.

All tools work with selected elements and provide real-time visual feedback through an information panel showing selection details and previews.

## How to Use

### Align Tab

#### Basic Alignment Workflow

1. **Select Elements**: Choose the elements you want to align (2+ elements required)
2. **Choose Reference**: Select what to align relative to:
   - **Selection**: Align within the bounds of all selected elements
   - **First Selected**: Align relative to the first element you selected
   - **Last Selected**: Align relative to the last element you selected
   - **Laserbed**: Align relative to the entire laser bed area
   - **Reference-Object**: Align relative to a designated reference object
3. **Set X/Y Alignment**: Choose positioning for horizontal and vertical axes:
   - **Leave**: Don't change this axis
   - **Left/Center/Right** (X-axis): Position relative to left edge, center, or right edge
   - **Top/Center/Bottom** (Y-axis): Position relative to top edge, center, or bottom edge
4. **Choose Treatment**: Select how to handle the alignment:
   - **Individually**: Each element aligns independently
   - **As Group**: Elements maintain relative positions while group aligns
5. **Click Align**: Apply the alignment settings

#### Alignment Examples

- **Center on bed**: Set both X and Y to "Center", Reference to "Laserbed"
- **Left-align column**: Set X to "Left", Y to "Leave", Reference to "Selection"
- **Bottom row**: Set X to "Leave", Y to "Bottom", Reference to "Selection"

### Distribute Tab

#### Basic Distribution Workflow

1. **Select Elements**: Choose elements to distribute (3+ elements typically needed)
2. **Choose Treatment**: Select the distribution area:
   - **Position**: Distribute along rectangular boundaries of selection
   - **Shape**: Distribute along the outline of the first selected element
   - **Points**: Distribute along specific points of the first selected element
   - **Laserbed**: Distribute across the entire laser bed
   - **Ref-Object**: Distribute along a reference object boundary
3. **Set Positioning**: Choose how elements position relative to distribution points:
   - **Left/Center/Right/Top/Center/Bottom**: Standard alignment options
   - **Space**: Evenly distribute elements with equal spacing between them
4. **Configure Options**:
   - **Keep first + last inside**: Ensure first and last elements stay within boundaries
   - **Rotate**: Rotate elements to follow curved distribution paths
   - **Work-Sequence**: Process elements in selection order, first-selected, or last-selected order
5. **Click Distribute**: Apply the distribution

#### Distribution Examples

- **Even spacing**: Set both X and Y to "Space" for equal gaps between elements
- **Circular pattern**: Use "Shape" treatment with a circle as the first element
- **Path following**: Use "Points" treatment with a path element for custom distributions

### Arrange Tab

#### Basic Arrangement Workflow

1. **Select Elements**: Choose elements to arrange in a grid
2. **Set Grid Dimensions**: Specify number of columns and rows
3. **Configure Alignment**: Choose how elements align within each grid cell:
   - **Left/Center/Right** for horizontal positioning
   - **Top/Center/Bottom** for vertical positioning
4. **Set Spacing Options**:
   - **Adjacent**: Elements touch each other
   - **Set distances**: Specify custom gaps between elements
   - **X/Y Gaps**: Define horizontal and vertical spacing
5. **Configure Sizing**:
   - **Same width**: Make all columns the same width (maximum of elements)
   - **Same height**: Make all rows the same height (maximum of elements)
   - **Order to process**: Selection order, first-selected, or last-selected
6. **Click Arrange**: Create the grid layout

#### Arrangement Examples

- **Button grid**: 3x4 grid with center alignment and equal spacing
- **Component layout**: Custom gaps with same-width columns for consistent appearance
- **Icon arrangement**: Adjacent layout with left/top alignment

## Technical Details

The Alignment system uses sophisticated geometric algorithms:

### Core Components
- **InfoPanel**: Displays selection information and element previews
- **AlignmentPanel**: Handles basic alignment operations
- **DistributionPanel**: Manages complex distribution algorithms
- **ArrangementPanel**: Creates structured grid layouts

### Key Technologies
- **Geometric Calculations**: Precise positioning using bounding boxes and transformation matrices
- **Path Processing**: Complex shape analysis for distribution along curves and paths
- **Grid Algorithms**: Efficient arrangement calculations for various grid configurations
- **Real-time Updates**: Live preview and validation of alignment operations

### Algorithm Details

#### Alignment Algorithm
- Calculates reference points based on selected mode (selection bounds, first/last element, bed, reference)
- Applies X/Y transformations independently
- Supports both individual and group transformations
- Preserves element relationships in group mode

#### Distribution Algorithm
- **Boundary Distribution**: Even spacing along rectangular boundaries
- **Shape Distribution**: Path interpolation along complex shapes
- **Point Distribution**: Positioning at specific path vertices
- **Rotation Support**: Automatic element rotation to follow curved paths

#### Arrangement Algorithm
- **Grid Calculation**: Dynamic grid sizing based on element dimensions
- **Spacing Logic**: Adjacent vs. fixed-gap arrangements
- **Alignment Options**: Nine-point alignment within each grid cell
- **Size Normalization**: Optional width/height equalization across rows/columns

## Related Topics

- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]
- [[Online Help: Transform]]
- [[Online Help: Selection]]

## Screenshots

*Alignment dialog showing the three tabs: Align, Distribute, and Arrange*

*Align tab with X/Y axis controls and reference selection*

*Distribute tab showing shape-based distribution options*

*Arrange tab with grid configuration and spacing controls*

*Information panel displaying selected elements and previews*

---

*This help page provides comprehensive documentation for MeerK40t's alignment, distribution, and arrangement functionality.*
