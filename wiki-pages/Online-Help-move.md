# Online Help: Move

## Overview

The Move panel provides precise coordinate-based laser positioning controls. It allows you to send the laser head to specific X/Y coordinates or save and recall frequently used positions using a numbered button grid.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Move panel is designed for precision laser positioning when you need exact coordinate control. Unlike the Jog panel's relative movements, the Move panel works with absolute coordinates, making it ideal for:

- **Precise positioning**: Move to exact coordinates for alignment and calibration
- **Saved positions**: Store and recall frequently used locations
- **Measurement-based placement**: Position based on specific measurements
- **Reproducible setups**: Return to the same positions consistently
- **Template workflows**: Use saved positions for repeated operations

The panel combines direct coordinate input with a 3x3 grid of position memory buttons, allowing you to build a library of important locations on your laser bed.

## How to Use

### Accessing the Move Panel

The Move panel is available in two ways:

1. **As a pane**: Window → Panes → Navigation (includes Move panel)
2. **As a window**: Window → Navigation → Navigation

### Direct Coordinate Movement

- **X/Y Input Fields**: Enter target coordinates directly
  - Supports various units (mm, inches, etc.)
  - Auto-converts based on your current unit settings
  - Press Enter or click "Move To" button to execute

- **Move To Button**:
  - **Left-click**: Move laser to entered coordinates
  - **Right-click**: Activate mouse-click mode to set position by clicking on the scene

- **Current Position Display**: Shows real-time laser head coordinates
  - **Double-click**: Copy current position to input fields

### Position Memory System

The 3x3 grid of numbered buttons (1-9) provides position memory:

- **Left-click a button**: Move laser to saved coordinates
- **Right-click a button**: Save current laser position to that button
- **Button tooltips**: Show saved coordinates and usage instructions

**Default Button Positions:**
- **1, 2, 3**: Bottom row (0%, 50%, 100% of bed width)
- **4, 5, 6**: Middle row (0%, 50%, 100% of bed width)
- **7, 8, 9**: Top row (0%, 50%, 100% of bed width)

### Key Features

- Integrates with: `wxpane/Navigation`
- Integrates with: `refresh_scene`
- Integrates with: `jog_amount`

### Basic Usage

1. **Direct positioning**: Enter coordinates in X/Y fields and click "Move To"
2. **Save positions**: Move to desired location, right-click a number button to save
3. **Recall positions**: Left-click saved buttons to return to those locations
4. **Current position**: Double-click position display to copy coordinates to input fields
5. **Mouse positioning**: Right-click "Move To" button, then click on scene to set position

## Technical Details

The Move panel implements sophisticated coordinate management with unit conversion and boundary validation:

**Coordinate System:**
- **Absolute positioning**: Works with bed coordinate system (0,0 is bottom-left)
- **Unit conversion**: Automatic conversion between display units and internal coordinates
- **Boundary checking**: Prevents movement outside laser bed dimensions
- **Relative length support**: Coordinates can be relative to display dimensions

**Position Memory:**
- **Persistent storage**: Saved positions survive application restarts
- **Unit preservation**: Coordinates stored in millimeters for precision
- **Grid layout**: 3x3 button array mapped to bed corners, edges, and center
- **Tooltip feedback**: Real-time display of saved coordinates

**Integration Points:**
- **Device validation**: Checks if target position is within bed boundaries
- **Position tracking**: Updates current position display in real-time
- **Signal system**: Responds to device position changes and scene updates

**Safety Features:**
- **Boundary enforcement**: Blocks moves outside safe work area
- **Error handling**: Graceful handling of invalid coordinate input
- **Device verification**: Confirms device is ready before movement commands

## Safety Considerations

- **Boundary awareness**: Always ensure target coordinates are within your laser bed
- **Unit verification**: Double-check units when entering coordinates manually
- **Position confirmation**: Verify laser reaches intended position before proceeding
- **Saved position validation**: Test saved positions after bed size changes
- **Emergency access**: Use Jog panel for quick repositioning if needed

## Troubleshooting

### Coordinates Not Accepted

**Problem**: Entering coordinates doesn't work
- **Check units**: Ensure coordinates use valid unit abbreviations (mm, in, etc.)
- **Verify format**: Use proper number format (e.g., "100.5mm", not "100.5 mm")
- **Boundary check**: Confirm coordinates are within bed dimensions
- **Device status**: Ensure laser device is connected and ready

### Buttons Don't Save Positions

**Problem**: Right-clicking buttons doesn't save coordinates
- **Position validity**: Ensure laser is at a valid position before saving
- **Device connection**: Verify device is properly connected
- **Permission check**: Ensure MeerK40t can write to its configuration directory

### Position Display Not Updating

**Problem**: Current position doesn't show correctly
- **Device compatibility**: Check if your device reports position correctly
- **Connection status**: Ensure device communication is active
- **Driver issues**: Restart device connection if position updates fail

### Mouse-Click Mode Not Working

**Problem**: Right-clicking Move To button doesn't activate mouse mode
- **Scene access**: Ensure scene window is visible and active
- **Tool conflicts**: Check if other tools are interfering with mouse input
- **Mode activation**: Try clicking on scene after activating mouse mode

### Saved Positions Lost

**Problem**: Saved button positions disappear after restart
- **Write permissions**: Ensure MeerK40t has write access to configuration files
- **Configuration corruption**: Try resetting device configuration
- **File location**: Check if configuration files are being stored correctly

## Advanced Usage

### Workflow Optimization

**Setup Routines:**
1. Define key positions (material corners, alignment points, test areas)
2. Save them to numbered buttons for quick access
3. Create standard operating positions for different job types

**Quality Control:**
- **Alignment checks**: Use saved positions for consistent alignment verification
- **Test patterns**: Position laser for repeatable test cuts
- **Calibration points**: Store calibration reference positions

**Production Workflows:**
- **Batch processing**: Use position memory for multi-part jobs
- **Quality assurance**: Return to inspection positions consistently
- **Maintenance access**: Store positions for cleaning and maintenance

### Coordinate System Understanding

**Bed Coordinate System:**
- **Origin (0,0)**: Bottom-left corner of laser bed
- **X-axis**: Increases from left to right
- **Y-axis**: Increases from bottom to top
- **Units**: Internal storage in millimeters, display in preferred units

**Relative Positioning:**
- **Display-relative**: Coordinates can be relative to display dimensions
- **Bed-relative**: Absolute positioning within laser bed boundaries
- **Element-relative**: Can be combined with element selection for relative moves

### Integration with Other Tools

**Combined Workflows:**
- **With Jog**: Use Move for precision positioning, Jog for fine adjustments
- **With Camera**: Position for camera alignment, save reference points
- **With Operations**: Store setup positions for different cutting operations
- **With Spooler**: Save positions for job staging and material handling

---

*This help page provides comprehensive documentation for the Move panel functionality in MeerK40t.*
