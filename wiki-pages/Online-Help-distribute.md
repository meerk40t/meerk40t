# Online Help: Distribute

## Overview

This help page covers the **Distribute** functionality in MeerK40t.

The Distribute panel provides advanced controls for evenly spacing and positioning selected design elements along various paths, shapes, or boundaries. This feature is essential for creating precise layouts, evenly spaced patterns, and complex arrangements where elements need to follow specific geometric constraints.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\alignment.py`

## Category

**GUI**

## Description

The Distribute feature allows you to automatically position selected elements along different types of paths or within defined boundaries. Unlike simple alignment, distribution creates evenly spaced arrangements where elements follow geometric patterns or shapes.

**When to use Distribute:**
- Creating evenly spaced elements along a curved path
- Distributing objects around the perimeter of another shape
- Placing elements at specific points on a complex path
- Creating precise grid-like arrangements with custom spacing
- Arranging elements along the laser bed boundaries
- Following the outline of a reference object

## How to Use

### Available Controls

- **Position of element relative to X-Axis:** Choose how elements align horizontally (Left, Center, Right, Space)
- **Position of element relative to Y-Axis:** Choose how elements align vertically (Top, Center, Bottom, Space)
- **Keep first + last inside:** When enabled, ensures the first and last elements stay within the target area boundaries
- **Rotate:** When distributing along shapes, rotates elements to follow the path direction
- **Work-Sequence:** Determines processing order (Position, First Selected, Last Selected)
- **Treatment:** Defines the distribution area/shape:
  - **Position:** Along the boundaries of the selection's bounding rectangle
  - **Shape:** Along the outline of the first selected element
  - **Points:** At the defined points of the first selected element
  - **Laserbed:** Along the laser bed boundaries
  - **Ref-Object:** Along the boundaries of a reference object
- **Distribute** (Button): Applies the distribution settings

### Key Features

- Integrates with: `emphasized` (selected elements)
- Integrates with: `reference` (reference objects for boundary-based distribution)
- Integrates with: `refresh_scene` (updates the display after changes)

### Basic Usage

1. **Select Elements:** Choose 2 or more design elements you want to distribute
2. **Choose Distribution Method:** Select a Treatment option (Position, Shape, Points, Laserbed, or Ref-Object)
3. **Set Positioning:** Choose X and Y axis alignment (Left/Center/Right, Top/Center/Bottom, or Space for even distribution)
4. **Configure Options:** Enable "Keep first + last inside" and/or "Rotate" as needed
5. **Apply Distribution:** Click the "Distribute" button to reposition your elements

## Technical Details

The distribution system uses sophisticated geometric algorithms to calculate element positions:

**Distribution Algorithms:**
- **Position Mode:** Creates evenly spaced points along the bounding rectangle of selected elements
- **Shape Mode:** Converts the first selected element to a path and distributes remaining elements along its outline
- **Points Mode:** Uses individual points from the first element's path as distribution targets
- **Laserbed/Ref-Object Mode:** Distributes elements along rectangular boundaries

**Spacing Calculations:**
- **Equidistant:** Creates equal distances between element centers
- **Space Mode:** Distributes elements with equal gaps between their edges
- **Boundary Respect:** "Keep first + last inside" ensures edge elements stay within target boundaries

**Rotation Integration:** When distributing along shapes, elements can be automatically rotated to follow the path's tangent direction, creating natural-looking curved arrangements.

The system preserves element aspect ratios and handles complex path types including Bezier curves, arcs, and polylines through interpolation algorithms.

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Arrangement]]
- [[Online Help: Autoexec]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the distribute feature.*
