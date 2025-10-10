# Online Help: Templates

## Overview

This help page covers the **Templates** functionality in MeerK40t.

This panel provides controls for lasertool functionality. Key controls include "A" (label), "Use position" (button), "<empty>" (label).

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\lasertoolpanel.py`

## Category

**GUI**

## Description

The Templates panel provides precision laser positioning tools for creating geometric shapes and frames. This advanced feature allows users to define shapes by physically positioning the laser head at key points on the workbed, then automatically generating the corresponding geometric elements.

Users would use this feature when:
- **Creating precise circular elements**: When you need to find the exact center of a circular object or mark on a bed
- **Defining rectangular boundaries**: When creating frames or boundaries using physical measurements
- **Placing square elements**: When working with square objects that need precise positioning and orientation
- **Reverse-engineering existing objects**: When you have physical objects and need to create digital representations
- **Quality control and measurement**: When verifying alignments or taking precise measurements

The system uses mathematical algorithms to calculate geometric properties from laser position measurements, providing professional-grade precision for laser cutting and engraving workflows.

## How to Use

### Available Controls

#### Find Center Tab
- **A, B, C Point Labels**: Labels for the three circumference points
- **Use Position Buttons**: Capture current laser position for each point
- **Position Displays**: Show captured coordinates for each point
- **Make Reference Checkbox**: Create a reference mark at the center point
- **Mark Center Checkbox**: Place a visible mark at the calculated center
- **Move to Center Button**: Move laser head to the calculated center position
- **Create Circle Button**: Generate a circle element using the calculated center and radius

#### Place Frame Tab
- **Corner 1, Corner 2 Labels**: Labels for the two rectangle corners
- **Use Position Buttons**: Capture current laser position for each corner
- **Position Displays**: Show captured coordinates for each corner
- **Make Reference Checkbox**: Create reference marks at the corners
- **Create Frame Button**: Generate a rectangular element from the two corner points

#### Place Square Tab
- **Side A 1, Side A 2, Side B Labels**: Labels for the three square definition points
- **Use Position Buttons**: Capture current laser position for each point
- **Position Displays**: Show captured coordinates for each point
- **Dimension Field**: Specify the size/extension of the square to create
- **Make Reference Checkbox**: Create reference marks at the corners
- **Mark Corner Checkbox**: Place visible marks at the calculated corner positions
- **Create Square Button**: Generate a square element using the calculated geometry

### Key Features

- **Real-time Position Capture**: Uses current laser head position for precise measurements
- **Mathematical Accuracy**: Employs geometric algorithms for center finding and shape calculation
- **Visual Feedback**: Shows captured positions and provides instructional graphics
- **Safety Checks**: Warns when calculated positions are outside safe workbed boundaries
- **Integration Options**: Can create reference marks and automatically classify new elements

### Basic Usage

1. **Select Template Type**: Choose the appropriate tab (Find Center, Place Frame, or Place Square)
2. **Position Laser**: Manually move the laser head to the first reference point on your physical object
3. **Capture Position**: Click "Use Position" to record the current laser coordinates
4. **Repeat for Additional Points**: Move to and capture each required reference point
5. **Configure Options**: Set checkboxes for reference marks or center marking as needed
6. **Generate Element**: Click the creation button to add the calculated shape to your design
7. **Optional Movement**: For circles, you can choose to move the laser to the calculated center

## Technical Details

The Templates system implements sophisticated geometric algorithms to create shapes from physical measurements:

**Find Center Algorithm:**
Uses the three-point circle equation to calculate center coordinates and radius. The system solves the general circle equation `x² + y² + 2ax + 2by + c = 0` using three known points to determine the center coordinates (h, k) and radius `r = √(h² + k² - c)`.

**Place Frame Algorithm:**
Creates rectangles using two diagonally opposite corner points. Calculates width and height as absolute differences between coordinates, then positions the rectangle at the minimum x,y coordinates.

**Place Square Algorithm:**
Determines square geometry using three points: two on one side and one on an adjacent side. Calculates the center point, rotation angle, and proper orientation using trigonometric relationships and coordinate geometry.

**Position Integration:**
- Monitors `driver;position`, `emulator;position`, and `status;position` signals
- Captures real-time laser head coordinates in device units
- Converts between internal units and display units for user feedback
- Validates positions against workbed boundaries for safety

**Safety Features:**
- Boundary checking prevents laser movement outside safe workbed limits
- User confirmation dialogs for potentially dangerous operations
- Visual warnings when calculated positions exceed device constraints

**Element Creation:**
- Generates SVG-compatible circle and rectangle elements
- Supports automatic classification and reference mark creation
- Integrates with MeerK40t's element tree and operation system

## Related Topics

- [[Online Help: Jog]] - Manual laser positioning and movement controls
- [[Online Help: Move]] - Basic movement operations and positioning
- [[Online Help: Transform]] - Element transformation and geometric operations
- [[Online Help: Circle]] - Creating and working with circular elements
- [[Online Help: Rectangle]] - Creating and working with rectangular elements
- [[Online Help: Reference]] - Working with reference marks and alignment points

## Screenshots

The Templates panel interface includes three main tabs:

1. **Find Center Tab**: Shows three point capture controls (A, B, C) with position displays, checkboxes for reference marks, and buttons for center movement and circle creation
2. **Place Frame Tab**: Displays two corner point controls with position displays and frame creation options
3. **Place Square Tab**: Shows three point capture controls, dimension input field, and square creation options with orientation controls
4. **Instruction Graphics**: Each tab includes visual diagrams showing how to position points on physical objects
5. **Position Feedback**: Real-time display of captured coordinates in user-selected units
6. **Safety Dialogs**: Warning messages when calculated positions exceed workbed boundaries

The interface uses a tabbed notebook layout with instructional tooltips and visual aids to guide users through the geometric measurement process.

---

*This help page is automatically generated. Please update with specific information about the templates feature.*
