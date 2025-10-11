# Online Help: Arrangement

## Overview

The **Arrangement** panel is MeerK40t's grid-based element organization tool. It automatically arranges selected design elements into structured grids with customizable spacing, alignment, and sizing options. This tool is essential for creating professional layouts like button arrays, component grids, or organized collections of design elements.

Arrangement transforms chaotic selections into orderly, evenly-spaced grids with precise control over positioning and spacing.

## What is Element Arrangement?

Element arrangement is the process of automatically organizing design elements into structured grid layouts. Unlike manual positioning or basic alignment, arrangement provides:

- **Grid-based organization**: Automatic placement into rows and columns
- **Flexible spacing**: Adjacent placement or custom gap distances
- **Size normalization**: Optional equal width/height across rows and columns
- **Alignment control**: Nine-point alignment within each grid cell
- **Batch processing**: Handle multiple elements simultaneously

### When to Use Arrangement

Use arrangement when you need:
- **Grid layouts**: Create ordered arrays of buttons, icons, or components
- **Consistent spacing**: Ensure equal gaps between elements
- **Size uniformity**: Make elements consistent in width or height
- **Professional organization**: Transform scattered elements into structured layouts
- **Batch positioning**: Position many elements with minimal manual work

## Location in MeerK40t

The Arrangement functionality is part of the Alignment dialog:
- **Menu**: `Edit` → `Element Alignment` → `Expert Mode`
- **Dialog Tab**: Third tab labeled "Arrange"
- **Source code**: `meerk40t\gui\alignment.py` (ArrangementPanel class)

## Category

**GUI**

## Description

The Arrangement tool organizes selected elements into customizable grid layouts. It calculates optimal positioning based on your specifications and automatically places elements with precise spacing and alignment.

### Key Capabilities

- **Grid Configuration**: Set number of columns and rows for your layout
- **Spacing Control**: Choose between adjacent placement or custom gap distances
- **Size Options**: Make all columns same width or all rows same height
- **Alignment Choices**: Position elements within grid cells (left/center/right, top/center/bottom)
- **Processing Order**: Control which elements go where based on selection sequence
- **Real-time Preview**: See arrangement results before applying

The tool analyzes your selected elements and creates a centered grid layout on the laser bed, making it perfect for creating professional, organized designs.

## How to Use

### Basic Arrangement Workflow

1. **Select Elements**: Choose the design elements you want to arrange (2+ elements required)
2. **Open Arrangement**: Go to `Edit` → `Element Alignment` → `Expert Mode`, then click the "Arrange" tab
3. **Set Grid Dimensions**:
   - **X-Axis**: Number of columns in your grid
   - **Y-Axis**: Number of rows in your grid
4. **Configure Alignment**: Choose how elements position within each grid cell:
   - **X-Axis**: Left, Center, or Right alignment
   - **Y-Axis**: Top, Center, or Bottom alignment
5. **Set Spacing Method**:
   - **Adjacent**: Elements touch each other with no gaps
   - **Set distances**: Specify custom gaps between elements
6. **Configure Gaps** (if using set distances):
   - **X Gap**: Horizontal spacing between columns
   - **Y Gap**: Vertical spacing between rows
7. **Set Size Options**:
   - **Same width**: Make all columns the same width (uses maximum element width)
   - **Same height**: Make all rows the same height (uses maximum element height)
8. **Choose Processing Order**:
   - **Selection**: Arrange in current selection order
   - **First Selected**: Process oldest selections first
   - **Last Selected**: Process newest selections first
9. **Click Arrange**: Apply the grid layout to your elements

### Arrangement Examples

#### Button Grid Layout
- **Use case**: Creating a calculator or control panel interface
- **Settings**: 4 columns, 5 rows, center alignment, 2mm gaps, same width/height
- **Result**: Professional button array with consistent spacing

#### Icon Organization
- **Use case**: Arranging decorative elements or logos
- **Settings**: 3 columns, auto rows, left/top alignment, adjacent spacing
- **Result**: Clean, organized layout without gaps

#### Component Layout
- **Use case**: Positioning circuit board components or mechanical parts
- **Settings**: Custom columns/rows, center alignment, 5mm gaps, same width
- **Result**: Precisely spaced components ready for manufacturing

### Advanced Techniques

#### Size Normalization
- **Same Width**: Useful for text elements or buttons to create visual consistency
- **Same Height**: Good for icons or logos to maintain proportional appearance
- **Combined**: Both options create uniform grid cells for maximum consistency

#### Spacing Strategies
- **Adjacent**: Maximum space efficiency, elements touch each other
- **Fixed Gaps**: Predictable spacing for professional appearance
- **Mixed Approach**: Use adjacent for one axis, gaps for the other

#### Processing Order Control
- **Selection Order**: Maintains your intended element sequence
- **Time-based**: First/Last selected can help organize complex selections
- **Visual Flow**: Arrange elements to create reading flow (left-to-right, top-to-bottom)

## Technical Details

The Arrangement system uses sophisticated grid calculation algorithms:

### Core Components
- **Grid Calculator**: Determines optimal positioning for each element
- **Size Analyzer**: Measures element dimensions for spacing calculations
- **Alignment Engine**: Applies nine-point alignment within grid cells
- **Spacing Logic**: Handles both adjacent and fixed-gap arrangements

### Key Technologies
- **Bounding Box Analysis**: Precise measurement of element dimensions
- **Grid Mathematics**: Calculates positions for uniform spacing and alignment
- **Transformation Matrices**: Applies positioning changes efficiently
- **Size Normalization**: Equalizes dimensions across rows and columns

### Algorithm Details

#### Grid Calculation
1. **Measure Elements**: Calculate bounding boxes for all selected elements
2. **Determine Grid Size**: Use specified columns/rows or calculate optimal layout
3. **Calculate Cell Dimensions**:
   - **Variable**: Each cell sized to fit its element
   - **Same Width**: All columns use maximum element width
   - **Same Height**: All rows use maximum element height
4. **Position Grid**: Center the entire grid on the laser bed

#### Spacing Logic
- **Adjacent**: Elements positioned so edges touch (gap = 0)
- **Fixed Distance**: User-specified gaps between element edges
- **Boundary Handling**: Ensures elements stay within laser bed limits

#### Alignment Options
- **Nine-point system**: Left/Center/Right × Top/Center/Bottom combinations
- **Element centering**: Positions based on element bounding boxes
- **Consistent application**: Same alignment logic for all grid cells

## Related Topics

- [Online Help: Alignment](Online-Help-alignment)
- [Online Help: Distribute](Online-Help-distribute)
- [Online Help: Transform](Online-Help-transform)
- [Online Help: Selection](Online-Help-selection)

## Screenshots

*Arrangement tab showing grid configuration controls*

*Grid dimension settings with column and row controls*

*Alignment options for positioning within grid cells*

*Spacing configuration with adjacent vs. fixed distance options*

*Size normalization controls for consistent appearance*

*Completed grid layout with evenly spaced elements*

---

*This help page provides comprehensive documentation for MeerK40t's element arrangement functionality.*
