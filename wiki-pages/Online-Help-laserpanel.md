# Online Help: Laserpanel

## Overview

The **Laserpanel** is MeerK40t's central laser control interface, providing comprehensive device management, job execution controls, safety systems, and real-time parameter adjustment capabilities. This panel serves as the primary command center for all laser engraving and cutting operations.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t/gui/laserpanel.py`

## Category

**GUI**

## Description

The Laserpanel is the heart of MeerK40t's laser control system, offering:

- **Device Management**: Multi-device selection and configuration access
- **Job Execution**: Start, pause, stop, and emergency stop controls
- **Safety Systems**: Arm/disarm mechanism to prevent accidental firing
- **Real-time Adjustment**: Live power and speed modification during jobs
- **Optimization Control**: Enable/disable cut plan optimization
- **Status Monitoring**: Rotary engraving indicators and device state
- **Preview Functions**: Outline tracing and simulation capabilities

The panel integrates deeply with MeerK40t's signal system, responding to device state changes, pause events, and optimization settings in real-time.

## How to Use

### Accessing the Laser Panel

The Laser panel is located in the right docking pane of the main MeerK40t window. It contains multiple tabs:

- **Laser**: Main control interface (primary controls)
- **Jog**: Manual positioning controls
- **Plan**: Job planning and management
- **Optimize**: Cut optimization settings
- **Move**: Coordinate-based movement

### Device Selection and Configuration

#### Device Dropdown
- **Purpose**: Switch between configured laser devices
- **Multi-device Support**: Only visible when multiple devices are available
- **Configuration Button**: Opens device-specific settings window

#### Device Configuration Access
```
Click the gear icon (⚙️) next to device dropdown
Opens: Device-specific configuration window
```

### Job Execution Controls

#### Primary Controls

**Start Button (Green)**
- **Function**: Execute the current job
- **Safety**: Only enabled when job is armed (if arming required)
- **Background**: Supports threaded execution for large jobs
- **Right-click**: Access arming preferences menu

**Pause/Resume Button**
- **Function**: Pause running jobs or resume paused jobs
- **Visual Feedback**: Changes color and label based on state
- **Background**: Yellow when paused, normal when running

**Stop Button (Red)**
- **Function**: Emergency stop - immediately halts laser operation
- **Safety**: Always available, bypasses normal shutdown procedures

#### Safety Arming System

**Arm/Disarm Toggle**
- **Purpose**: Two-stage safety system to prevent accidental firing
- **Armed State**: Green background, "Disarm" label, start button enabled
- **Disarmed State**: Gray background, "Arm" label, start button disabled
- **Configuration**: Can be enabled/disabled in preferences

#### Secondary Controls

**Outline Button**
- **Function**: Trace the outline of all elements without engraving
- **Purpose**: Preview job boundaries and positioning
- **Right-click**: Quick outline mode (faster but less accurate)

**Simulate Button**
- **Function**: Open simulation window to preview job execution
- **Purpose**: Test job without actual laser operation
- **Right-click**: Background simulation (non-blocking)

### Real-time Parameter Adjustment

#### Override Controls

**Override Checkbox**
- **Function**: Enable live adjustment of power and speed during job execution
- **Warning**: Affects running jobs - use with extreme caution
- **Device Support**: Only available on devices with adjustable parameters

#### Power Adjustment
- **Slider Range**: Device-dependent (relative or absolute scaling)
- **Display**: Percentage change from base settings
- **Modes**:
  - **Relative**: ± percentage adjustment
  - **Maximum**: Absolute power limit setting
- **Safety**: High power settings may damage laser tubes

#### Speed Adjustment
- **Slider Range**: ± percentage from base speed
- **Display**: Percentage change from programmed speed
- **Real-time**: Affects currently executing operations

### Optimization and Planning

#### Optimize Toggle
- **Function**: Enable/disable cut plan optimization
- **Default**: Follows global optimization setting
- **Real-time**: Can be changed during job preparation

#### Plan Management (Plan Tab)
- **Job Preservation**: "Hold" checkbox maintains job between runs
- **Plan List**: View prepared cut plans with status and content
- **Plan Operations**:
  - **Update**: Refresh plan with current elements
  - **Export**: Save plan to file
  - **Spool**: Send plan to device queue

### Status Indicators

#### Rotary Indicator
- **Display**: "Rotary active" banner when rotary engraving is enabled
- **Purpose**: Visual confirmation of rotary mode
- **Color**: Uses theme pause colors for visibility

#### Device Status
- **Connection State**: Reflected in control availability
- **Parameter Support**: Controls enabled based on device capabilities
- **Theme Integration**: Colors adapt to current theme settings

## Technical Details

### Signal Integration

The Laserpanel responds to multiple MeerK40t signals:

- `device;connected`: Updates device capability controls
- `device;modified/device;renamed`: Refreshes device list
- `pause`: Updates pause button state and colors
- `laser_armed`: Manages arm/disarm visual feedback
- `optimize`: Synchronizes optimization checkbox
- `pwm_mode_changed`: Updates power control modes
- `plan`: Refreshes plan list in Plan tab

### Job Execution Flow

1. **Preparation**: Plan creation with optional optimization
2. **Safety Check**: Arming verification (if enabled)
3. **Execution**: Threaded or direct job execution
4. **Monitoring**: Real-time parameter adjustment capability
5. **Completion**: Automatic disarm and status reset

### Threading Support

- **Background Execution**: Large jobs run in separate threads
- **Progress Monitoring**: Thread info window for long operations
- **UI Responsiveness**: Non-blocking operation during job execution

### Device Capability Detection

The panel dynamically adapts based on device features:

- **Adjustable Power**: Enables power override controls
- **Adjustable Speed**: Enables speed override controls
- **Rotary Support**: Shows rotary status indicator
- **Optimization**: Enables optimization toggle

### Safety Mechanisms

- **Keyboard Protection**: Start button ignores keyboard activation
- **Arming System**: Two-stage safety for accidental execution
- **Emergency Stop**: Always-available stop functionality
- **Parameter Limits**: Enforced bounds on power/speed adjustments

## Safety Considerations

### Laser Safety
- **Eye Protection**: Always wear appropriate laser safety glasses
- **Ventilation**: Ensure proper exhaust ventilation
- **Fire Prevention**: Keep fire extinguishing equipment ready
- **Material Safety**: Verify material compatibility before cutting

### Operational Safety
- **Test First**: Always test settings on scrap material
- **Parameter Limits**: Respect device manufacturer's specifications
- **Emergency Stop**: Know location and function of stop controls
- **Unattended Operation**: Never leave laser running unattended

### Software Safety
- **Arming Discipline**: Use arming system consistently
- **Parameter Changes**: Exercise caution when adjusting running jobs
- **Device Verification**: Confirm correct device selection before execution
- **Backup Plans**: Save work before executing large jobs

## Troubleshooting

### Start Button Disabled

#### Not Armed
**Problem**: Start button grayed out
**Solution**: Click "Arm" button to enable job execution

#### No Content
**Problem**: No elements selected for job
**Solution**: Select elements in design area

#### Device Issues
**Problem**: Device not connected or configured
**Solution**: Check device status and configuration

### Parameter Controls Unavailable

#### Device Limitations
**Problem**: Power/speed sliders disabled
**Solution**: Device doesn't support real-time adjustment

#### Override Disabled
**Problem**: Sliders grayed out
**Solution**: Check "Override" checkbox to enable controls

### Job Execution Issues

#### Job Doesn't Start
**Problem**: Job preparation fails
**Solutions**:
- Check console for error messages
- Verify element selection
- Clear and recreate job plan

#### Unexpected Behavior
**Problem**: Job behaves differently than expected
**Solutions**:
- Check optimization settings
- Verify device configuration
- Test with simulation first

### Performance Issues

#### Slow Job Preparation
**Problem**: Long delays before job starts
**Solutions**:
- Disable optimization for simple jobs
- Use background processing
- Check system resources

#### UI Unresponsive
**Problem**: Interface freezes during job execution
**Solutions**:
- Enable threaded execution
- Use background simulation
- Check system memory usage

## Related Topics

- [[Online Help: Devices]] - Device configuration and management
- [[Online Help: Simulation]] - Job preview and testing
- [[Online Help: Operationproperty]] - Operation parameter configuration
- [[Online Help: Spooler]] - Job queue management
- [[Online Help: Threadinfo]] - Background task monitoring

## Screenshots

*Screenshots would show:*
- *Complete laser panel interface with all controls visible*
- *Armed vs disarmed state differences*
- *Real-time parameter adjustment during job execution*
- *Plan management interface with job status*
- *Simulation preview window integration*

---

*This help page is automatically generated. Please update with specific information about the laserpanel feature.*
