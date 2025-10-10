# Online Help: Jog

## Overview

The Jog panel provides manual control over laser head movement around the work area. It features directional buttons for precise positioning, home positioning, rail locking/unlocking, and movement confinement controls.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Jog panel is essential for manual laser positioning and setup operations. It provides intuitive directional controls that allow you to move the laser head around your work area for:

- **Setup and alignment**: Position the laser for job setup and material alignment
- **Testing and calibration**: Move the laser to test positions and verify calibration
- **Manual operations**: Direct control when automated positioning isn't suitable
- **Emergency positioning**: Quick access to home position or safe locations

The panel includes both 2D movement controls (X/Y axes) and Z-axis controls for devices that support vertical movement. All movements respect configurable distance settings and can be confined to the laser bed boundaries.

## How to Use

### Accessing the Jog Panel

The Jog panel is available in two ways:

1. **As a pane**: Window → Panes → Jog (docks to the right side of interface)
2. **As a window**: Window → Navigation → Jog

### Directional Movement Controls

The main control area features a 3x3 grid of directional buttons:

- **Center button (Home)**: Returns laser to home position (0,0 coordinates)
  - **Left-click**: Move to logical home position
  - **Middle-click**: Jump to first job start position (if defined)
  - **Right-click**: Move to physical home (if endstops available)

- **Arrow buttons**: Move laser in cardinal directions (up, down, left, right)
  - **Left-click**: Move by 1x jog distance
  - **Hold**: Continuous movement with acceleration
  - **Right-click**: Move by 10x jog distance

- **Diagonal buttons**: Move laser diagonally (up-left, up-right, down-left, down-right)
  - Same click/hold behavior as arrow buttons

### Movement Configuration

- **Lock/Unlock buttons**: Control laser rail locking (bottom row, left/right positions)
  - **Lock**: Prevents accidental movement during operation
  - **Unlock**: Allows free movement for positioning

- **Confinement toggle**: Fence icon button (bottom row, center)
  - **Open fence**: Allow movement outside bed boundaries (caution mode)
  - **Closed fence**: Restrict movement to within bed dimensions

### Z-Axis Controls (when supported)

For devices with Z-axis capability, additional controls appear on the right:

- **Z-Up/Z-Down buttons**: Move laser vertically
- **Z-Home button**: Return to defined Z-home position
- **Z-Focus button**: Move to focus position (right-click on Z-Home)

### Key Features

- Integrates with: `wxpane/Navigation`
- Integrates with: `refresh_scene`
- Integrates with: `jog_amount`

### Basic Usage

1. **Access the panel**: Open Jog panel from Window menu
2. **Set jog distance**: Configure movement distance in Jog Distance panel
3. **Position laser**: Use directional buttons to move laser head
4. **Home when needed**: Use center home button to return to origin
5. **Lock for safety**: Use lock button during cutting operations

## Technical Details

The Jog panel implements sophisticated movement controls with acceleration and boundary checking:

**Movement System:**
- **Timer-based acceleration**: Buttons accelerate after 5/10 seconds of continuous hold
- **Boundary confinement**: Optional restriction to laser bed dimensions
- **Relative positioning**: All movements are relative to current position
- **Unit conversion**: Automatic conversion between display units and internal coordinates

**Safety Features:**
- **Rail locking**: Physical prevention of movement during cutting
- **Boundary checking**: Prevents movement outside safe work area
- **Emergency homing**: Multiple home position options for safety

**Integration Points:**
- **Device drivers**: Communicates with specific laser controller protocols
- **Position tracking**: Updates current position displays in real-time
- **Signal system**: Responds to device status and position change signals

**Z-Axis Support:**
- **Automatic detection**: Panel shows Z controls only for capable devices
- **Endstop integration**: Physical home detection for precise positioning
- **Focus positioning**: Specialized Z positioning for optimal focus

## Safety Considerations

- **Movement awareness**: Always verify laser position before starting jobs
- **Lock during operation**: Use rail lock to prevent accidental movement during cutting
- **Boundary respect**: Keep confinement enabled to avoid hardware damage
- **Power awareness**: Ensure laser is powered and connected before movement
- **Emergency access**: Know emergency stop procedures and home positioning

## Troubleshooting

### Laser Won't Move

**Problem**: Directional buttons don't respond
- **Check device connection**: Ensure laser is powered and connected
- **Verify device activation**: Confirm correct device is active in Device Manager
- **Check rail lock**: Unlock rails if locked during positioning
- **Test small movements**: Try minimal jog distance first

### Movement Jerky or Inaccurate

**Problem**: Laser movement is not smooth
- **Check jog distance**: Very small distances may cause stepper motor issues
- **Verify calibration**: Ensure laser calibration is current
- **Check power supply**: Inadequate power can cause movement problems
- **Update firmware**: Ensure laser controller firmware is up to date

### Buttons Don't Accelerate

**Problem**: Hold acceleration doesn't work
- **Check timer settings**: Verify button repeat settings in preferences
- **Restart MeerK40t**: Timer system may need refresh
- **Check system resources**: Low CPU/memory may affect timing

### Z-Axis Controls Missing

**Problem**: Z controls don't appear
- **Check device support**: Verify device has Z-axis capability
- **Update device config**: Refresh device settings in Device Manager
- **Check firmware**: Ensure device firmware supports Z movement

### Confinement Not Working

**Problem**: Laser moves outside bed boundaries
- **Check confinement setting**: Ensure fence icon shows closed state
- **Verify bed dimensions**: Confirm correct bed size in device settings
- **Check device calibration**: Boundary calculation depends on proper calibration

## Related Topics

- [[Online Help: Move]] - Coordinate-based positioning
- [[Online Help: Transform]] - Element transformation controls
- [[Online Help: Pulse]] - Laser pulse testing
- [[Online Help: Devices]] - Device management and configuration
- [[Online Help: Navigation]] - Complete navigation control suite

## Advanced Usage

### Custom Jog Distances

Set precise movement increments:
1. Open Jog Distance panel
2. Enter desired distance (e.g., "0.1mm", "0.01in")
3. All directional movements use this distance
4. Save frequently used distances for quick access

### Multi-Axis Coordination

For complex positioning:
- **X/Y first**: Position horizontally using directional buttons
- **Z adjustment**: Fine-tune focus with Z-axis controls
- **Verification**: Use Move panel to verify exact coordinates
- **Save positions**: Store important locations for quick recall

### Emergency Procedures

Quick safety actions:
- **Immediate home**: Center home button for instant return to origin
- **Physical home**: Right-click home for endstop-based positioning
- **Rail lock**: Lock rails to prevent any movement during issues
- **Power cycle**: Emergency shutdown if movement becomes unresponsive

### Integration with Workflows

Professional laser operation workflows:
- **Setup phase**: Use jog controls for initial material positioning
- **Test phase**: Move laser to verify alignment and focus
- **Production phase**: Lock rails and use automated positioning
- **Maintenance phase**: Unlock for cleaning and calibration procedures

---

*This help page provides comprehensive documentation for the Jog panel functionality in MeerK40t.*
