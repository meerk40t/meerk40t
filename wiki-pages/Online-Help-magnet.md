# Online Help: Magnet

## Overview

This help page covers the **Magnet** functionality in MeerK40t.

MagnetOptionPanel - Magnet snapping configuration interface.

Technical Purpose:
Provides configuration controls for magnet snapping behavior in the MeerK40t scene.
Manages attraction strength settings, target area selection (left/right, top/bottom, center),
and persistence of magnet configurations. Integrates with the scene pane's magnet system
to control object snapping during editing operations.

Signal Listeners:
- magnet_options: Updates UI when magnet options change externally

Signal Emissions:
- refresh_scene: Emitted when magnet settings change to update scene display

End-User Perspective:
This panel lets you customize how objects snap to guide lines in the scene. You can choose
which parts of objects get attracted to magnet lines (edges or centers), set how strong the
attraction is (from weak to enormous), and save/load different magnet configurations for
different types of work. The "Left/Right Side" option makes object edges snap to vertical
lines, "Top/Bottom Side" makes edges snap to horizontal lines, and "Center" makes object
centers snap to any magnet line.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\magnetoptions.py`
- `meerk40t\gui\magnetoptions.py`
- `meerk40t\gui\magnetoptions.py`

## Category

**GUI**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Left/Right Side** (Checkbox)
- **Top/Bottom Side** (Checkbox)
- **Center** (Checkbox)
- **Load** (Button)
- **Save** (Button)
- **Position:** (Label)
- **Horizontal** (Label)
- **Left** (Button)

### Key Features

- Integrates with: `emphasized`
- Integrates with: `refresh_scene`
- Integrates with: `magnet_options`

### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

## Technical Details

*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the magnet feature.*
