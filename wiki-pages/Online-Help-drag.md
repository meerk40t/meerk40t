# Online Help: Drag

## Overview

This help page covers the **Drag** functionality in MeerK40t.

The Drag panel provides sophisticated laser positioning and alignment controls, allowing you to precisely position the laser head relative to your design elements. It features intelligent alignment tools and a locking system that maintains relative positioning during element manipulation.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Drag panel enables precise laser positioning through multiple alignment methods and provides a unique locking system for maintaining alignment relationships. It combines direct positioning controls with intelligent trace operations for complex alignment tasks.

The panel consists of a 3x3 grid of buttons providing:
- **Corner Alignment**: Position laser at selection corners
- **Center Alignment**: Position laser at selection center
- **Directional Movement**: Move selection and laser together
- **Trace Operations**: Create alignment patterns
- **Locking System**: Maintain relative positioning during element manipulation

## How to Use

### Available Controls

- **Corner Buttons (TL/TR/BL/BR)**: Align laser with selection corners (right-click to lock/unlock)
- **Center Button**: Align laser with selection center (right-click to lock/unlock)
- **Directional Arrows**: Move selection and laser together (left/right/up/down)
- **First Position Button**: Jump to first point of selected element
- **Trace Hull Button**: Perform convex hull trace of selection
- **Trace Quick Button**: Perform simple trace of selection (right-click for circle trace)

### Key Features

- Integrates with: `wxpane/Navigation`, `refresh_scene`, `emphasized`, `modified`, `driver;position`, `emulator;position`
- Real-time position synchronization with lock mode
- Boundary checking to prevent movement outside bed dimensions
- Timer-based continuous movement with acceleration
- Visual feedback for lock mode status (green highlighting)

### Basic Usage

1. **Select Elements**: Choose design elements in the main scene
2. **Position Laser**: Use corner or center buttons to align laser with selection
3. **Lock if Needed**: Right-click alignment buttons to lock laser position relative to selection
4. **Move Together**: Use directional arrows to move both selection and laser as a unit
5. **Create Traces**: Use trace buttons for alignment pattern creation

### Advanced Usage

#### Lock Mode Operation
- Right-click any alignment button (corners or center) to lock laser position
- Locked buttons show green background highlighting
- When locked, laser automatically follows element movements
- Click locked button again to unlock
- Only one lock mode active at a time

#### Trace Operations
- **Trace Hull**: Creates convex hull outline around selection for alignment
- **Trace Quick**: Performs simple boundary trace (left-click) or circle trace (right-click)
- Useful for creating alignment marks or test patterns

#### Boundary Management
- Panel respects bed dimension limits when "confined" mode is active
- Shows warning dialog if attempting to move outside boundaries
- Automatically adjusts position to stay within limits

## Technical Details

Provides interactive controls for positioning the laser head and aligning it with design elements. Features label controls for user interaction. Integrates with wxpane/Navigation, refresh_scene for enhanced functionality.

The Drag panel implements sophisticated positioning logic using bounding box calculations and maintains alignment relationships through a locking system. It supports real-time position synchronization and includes boundary checking for safe operation.

Key technical components:
- **Bounding Box Calculations**: Uses element bounds for alignment positioning
- **Lock Mode System**: Maintains relative positioning during element transformations
- **Signal Integration**: Real-time updates via driver and emulator position signals
- **Boundary Validation**: Prevents movement outside configured bed dimensions
- **Timer Controls**: Implements continuous movement with configurable acceleration

### Alignment Algorithms
The panel calculates alignment positions based on element bounding boxes:
- **Corner Alignment**: Uses bbox coordinates [x0,y0,x1,y1] for corner positioning
- **Center Alignment**: Calculates center point as ((x0+x1)/2, (y0+y1)/2)
- **Lock Mode**: Tracks position deltas and applies transformations to maintain relationships

### Trace Operations
- **Convex Hull**: Creates minimal convex polygon containing all selection points
- **Quick Trace**: Performs boundary following algorithm
- **Circle Trace**: Generates circular alignment pattern around selection center

## Safety Considerations

- **Boundary Checking**: Prevents laser movement outside bed dimensions
- **Lock Mode Awareness**: Be aware of active locks when moving elements
- **Selection Requirements**: Most operations require element selection
- **Real-time Updates**: Position changes are applied immediately

## Troubleshooting

### Controls Not Responding
- Ensure elements are selected in the main scene
- Check that Navigation panel is active
- Verify device connection for position updates

### Lock Mode Not Working
- Confirm elements are selected before locking
- Check for active lock mode (only one can be active)
- Verify position signals are being received

### Boundary Warnings
- Check bed dimension settings in device configuration
- Ensure "confined" mode is appropriate for your setup
- Review position coordinates for validity

### Trace Operations Failing
- Verify selection contains valid geometry
- Check for complex or self-intersecting shapes
- Ensure sufficient space for trace patterns

## Related Topics

- [Online Help: Jog](Online-Help-jog) - Manual laser positioning controls
- [Online Help: Move](Online-Help-move) - Coordinate-based positioning
- [Online Help: Transform](Online-Help-transform) - Element transformation operations
- [Online Help: Navigation](Online-Help-navigation) - Complete navigation control suite

## Screenshots

*Screenshots showing the drag panel with alignment buttons, lock mode indicators, and trace operation examples would be helpful here, demonstrating the 3x3 button layout and lock mode visual feedback.*

---

*This help page provides comprehensive documentation for the drag functionality, covering laser positioning, alignment operations, and the unique locking system for maintaining relative positioning during element manipulation.*
