# Online Help: Laserpanel

## Overview

This help page covers the **Laserpanel** functionality in MeerK40t.

- Device selection dropdown with configuration access button for multi-device management
- Primary execution controls (Start/Pause/Stop) with safety arm/disarm system to prevent accidental firing
- Secondary operation buttons (Outline/Simulate) for job preview and testing with background processing options
- Real-time power and speed adjustment sliders with override controls for running jobs
- Optimization toggle with dynamic enable/disable based on device capabilities
- Rotary active status indicator for rotary engraving operations
- Comprehensive tooltip system explaining all control functions and safety warnings
- Settings persistence for control states and user preferences across sessions
- Dynamic UI adaptation based on device capabilities and current job state

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/7a77ad01-48c9-48d6-9194-9d88e317ba61)

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\laserpanel.py`

## Category

**GUI**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Outline** (Button)
- **Simulate** (Button)
- **Optimize** (Checkbox)
- **Override** (Checkbox)
- **Power** (Label)
- **Speed** (Label)
- **Clear** (Button)
- **Update** (Button)

### Key Features

- Integrates with: `device;connected`
- Integrates with: `service/device/active`
- Integrates with: `pause`

### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

## Technical Details

- Purpose: Central control panel for laser operations including device selection, job execution, safety arming, parameter adjustment, and optimization controls with real-time device state synchronization
- Signals: Multiple listeners including "optimize", "pwm_mode_changed", "device;modified", "device;renamed", "device;connected", "pause", "laser_armed", "laserpane_arm", "plan" for comprehensive device and job state management
- Help Section: laserpanel

*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the laserpanel feature.*
