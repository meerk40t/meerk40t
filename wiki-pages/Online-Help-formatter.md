# Online Help: Formatter

## Overview

This help page covers the **Formatter** functionality in MeerK40t.

The Formatter panel provides advanced customization options for how different types of elements and operations are displayed in MeerK40t's tree view. It allows users to create custom display formats using placeholder variables to show relevant information for each node type.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\device\gui\formatterpanel.py`

## Category

**GUI**

## Description

The Formatter panel gives users fine-grained control over how information is presented in the MeerK40t interface. By default, MeerK40t displays elements and operations with standard formatting, but the Formatter allows customization of these displays using format strings with placeholders.

This feature is particularly useful for:

- **Power Users**: Who want to see specific technical details prominently displayed
- **Workflow Optimization**: Customizing displays to highlight important parameters for specific job types
- **Information Density**: Controlling how much information is shown for different element types
- **Consistency**: Ensuring that similar operations display information in the same format

The panel organizes formatters by category:
- **Elements**: Basic shapes and graphics (rectangles, ellipses, paths, images, text)
- **Grouping + Files**: File nodes and group containers
- **Operations**: Laser operations (cut, engrave, raster, image, dots)
- **Elements (Effects)**: Special effects (hatch, wobble, warp)
- **Operations (Special)**: Utility operations (wait, home, goto, console commands)
- **Placements**: Position markers and placement points

Each node type can have a custom formatter string that uses placeholders like {speed}, {power}, {passes}, etc. to display relevant parameters.

## How to Use

### Basic Usage

1. **Access the Panel**: Open the Formatter panel from the device configuration area
2. **Choose Display Units**: Configure whether power shows as percentage or PPI, and speed as mm/min or mm/s
3. **Enable Custom Formatting**: Check the box next to any node type you want to customize
4. **Create Format String**: Enter a custom format string using available placeholders
5. **Apply Changes**: The tree view will immediately update to show your custom formatting

### Available Controls

- **Show power as %**: Toggle between percentage (100%) and PPI (1000) power display
- **Show speed in mm/min**: Toggle between mm/min and mm/s speed display
- **Node Type Checkboxes**: Enable custom formatting for specific element/operation types
- **Format String Fields**: Text fields for entering custom format strings with placeholders

### Key Features

- **Dynamic Placeholders**: Each node type shows available placeholders in the tooltip
- **Conditional Display**: Format fields only appear when the corresponding checkbox is enabled
- **Real-time Updates**: Changes apply immediately to the tree view
- **Category Organization**: Formatters are grouped by functionality for easy navigation

### Format String Examples

For a cut operation, you might use:
```
Cut: {speed}mm/s, {power}%, {passes} passes
```

For an image operation:
```
Image: {speed}mm/min, {power}ppi, {raster_direction}
```

## Technical Details

The Formatter panel uses MeerK40t's settings system to store custom format strings for each node type. Settings are stored with keys like `formatter_op_cut`, `formatter_elem_rect`, etc.

The system works by:
1. **Node Type Detection**: Identifying the type of each node in the tree
2. **Format String Lookup**: Retrieving the custom format string for that node type
3. **Placeholder Replacement**: Substituting placeholders with actual node parameter values
4. **Display Rendering**: Showing the formatted string in the tree view

Available placeholders vary by node type and are determined by each node's `default_map()` method, which returns a dictionary of available parameters. Common placeholders include:
- `{speed}` - Operation speed
- `{power}` - Laser power setting
- `{passes}` - Number of operation passes
- `{dpi}` - Dots per inch for raster operations
- `{width}`, `{height}` - Dimensions for elements
- `{name}` - Element or operation name

The panel integrates with the ChoicePropertyPanel system for consistent UI behavior and includes icons for each node type to make identification easier.

## Related Topics

*Link to related help topics:*

- [[Online Help: Tree]] - Understanding the tree view structure
- [[Online Help: Defaultactions]] - Other display and behavior settings
- [[Online Help: Effects]] - Effect-related formatting options
- [[Online Help: Operationproperty]] - Operation parameter configuration

## Screenshots

*Add screenshots showing the Formatter panel with custom format strings and the resulting tree view display.*

---

*This help page is automatically generated. Please update with specific information about the formatter feature.*
