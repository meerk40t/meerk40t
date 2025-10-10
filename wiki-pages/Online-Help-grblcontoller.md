# Online Help: Grblcontoller

## Overview

This help page covers the **Grblcontoller** functionality in MeerK40t.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\grbl\gui\grblcontroller.py`

## Category

**GRBL**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Clear** (Button)

### Key Features

- Integrates with: `grbl;status`
- Integrates with: `grbl_controller_update`
- Integrates with: `update_interface`

### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

## Technical Details

Provides a comprehensive wxPython-based control interface for GRBL-compatible laser devices,
enabling real-time communication, command execution, and device monitoring. This panel serves
as the primary user interface for device interaction, handling connection management, G-code
command transmission, macro execution, and communication logging. It integrates with the
MeerK40t kernel's signal system to maintain synchronized device state and user interface updates.

**Signal Integration:**
- `update_interface`: Updates GUI button states and connection status indicators
- `grbl_controller_update`: Refreshes the communication log display with new data
- Control and monitor your GRBL laser device in real-time. Connect or disconnect from the device,
- send individual G-code commands or execute stored macros, and view all communication in the log window.
- Use predefined buttons for common operations like homing, status queries, and alarm clearing.

*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Grblconfig]]
- [[Online Help: Grblhwconfig]]
- [[Online Help: Grbloperation]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the grblcontoller feature.*
