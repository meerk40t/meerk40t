# Online Help: Hatches

## Overview

This help page covers the **Hatches** functionality in MeerK40t.

HatchPropertyPanel - Advanced hatch pattern configuration and editing interface.

This panel provides comprehensive control over hatch effect operations including pattern generation,
spacing, angle control, and fill style selection. It enables precise configuration of hatch patterns
for laser engraving and cutting operations with real-time preview capabilities.

Technical Purpose:
- Manages hatch effect node parameters for pattern generation
- Controls hatch distance, angle, and angle delta for pattern variation
- Implements loop count controls for multi-pass hatching
- Provides algorithm selection (Scanbeam, Direct Grid, Auto-Select)
- Supports unidirectional and bidirectional hatch patterns
- Handles stroke color configuration with auto-classification
- Generates real-time hatch pattern previews

Signal Listeners:
- None directly (relies on callback mechanisms for property updates)

User Interface:
- Element ID: Identification and naming controls
- Stroke Color: Color selection with classification callbacks
- Loops: Hatch pass count with slider control
- Hatch Distance: Spacing between hatch lines with length validation
- Angle: Primary hatch angle with slider control
- Angle Delta: Secondary angle variation for complex patterns
- Fill Style: Algorithm selection (Auto-Select, Scanbeam, Direct Grid)
- Unidirectional: Toggle for single-direction hatching
- Auto-classify: Immediate classification after color changes
- Preview: Real-time hatch pattern visualization

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\hatchproperty.py`

## Category

**GUI**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Unidirectional** (Checkbox)
- **Algorithm:** (Label)

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

*This help page is automatically generated. Please update with specific information about the hatches feature.*
