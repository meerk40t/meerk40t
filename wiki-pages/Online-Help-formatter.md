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

- [[Online Help: Tree]] - Understanding the tree view structure and navigation
- [[Online Help: Defaultactions]] - Other display and behavior customization settings
- [[Online Help: Effects]] - Effect-related formatting options and parameters
- [[Online Help: Operationproperty]] - Operation parameter configuration and properties
- [[Online Help: Devices]] - Device-specific configuration panels

## Screenshots

### Formatter Panel - General Settings
The top section of the Formatter panel showing global display options:
- **Show power as % Checkbox**: Toggle between percentage (100%) and PPI (1000) power display modes
- **Show speed in mm/min Checkbox**: Toggle between mm/min and mm/s speed display formats
- **Unit Configuration**: Controls how numeric values are presented throughout the interface
- **Global Settings**: Options that affect all formatter displays

### Element Formatters Section
The Elements category showing basic shape formatting controls:
- **Element Type Checkboxes**: Individual toggles for rectangles, ellipses, paths, images, and text elements
- **Format String Fields**: Text input areas for custom display formats (only visible when enabled)
- **Node Type Icons**: Visual indicators next to each element type for easy identification
- **Conditional Display**: Format fields appear/disappear based on checkbox state

### Operation Formatters Section
The Operations category for laser operation display customization:
- **Operation Type Checkboxes**: Toggles for cut, engrave, raster, image, and dots operations
- **Parameter Placeholders**: Access to {speed}, {power}, {passes} and other operation-specific variables
- **Custom Format Strings**: Text fields for creating personalized operation labels
- **Real-time Preview**: Immediate updates to tree view when formats are changed

### Special Operations Formatters
The Operations (Special) category for utility operation formatting:
- **Special Operation Types**: Checkboxes for wait, home, goto, and console command operations
- **Utility Formatting**: Custom display options for non-laser operations
- **Command Parameters**: Access to operation-specific variables and settings
- **Workflow Integration**: Consistent formatting for all operation types

### Effects and Grouping Formatters
The Elements (Effects) and Grouping + Files categories:
- **Effect Types**: Checkboxes for hatch, wobble, and warp effect formatting
- **Grouping Options**: Format controls for file nodes and group containers
- **Effect Parameters**: Access to effect-specific variables like radius, speed, angle
- **Hierarchical Display**: Custom formatting for nested element structures

### Placements Formatters
The Placements category for position marker customization:
- **Placement Types**: Checkboxes for different placement operation variants
- **Position Variables**: Access to X/Y coordinates, rotation, and loop parameters
- **Grid Parameters**: Variables for repeats, gaps, and spacing in placement arrays
- **Location Formatting**: Custom display of placement positioning information

### Tree View with Custom Formatting
The MeerK40t tree view showing formatted node labels:
- **Custom Operation Labels**: Operations displaying with user-defined format strings
- **Element Information**: Shapes and graphics showing custom parameter displays
- **Visual Hierarchy**: Formatted labels maintaining clear tree structure
- **Parameter Visibility**: Important settings prominently displayed in node labels

### Format String Editor
Close-up of a format string input field with placeholder hints:
- **Tooltip Display**: Hover information showing available placeholders for the node type
- **Syntax Highlighting**: Visual cues for valid placeholder usage
- **Validation Feedback**: Real-time checking of format string syntax
- **Example Templates**: Suggested format strings for common use cases

### Before/After Formatting Comparison
Side-by-side comparison showing standard vs custom formatting:
- **Default Labels**: Standard MeerK40t node labels with basic information
- **Custom Labels**: User-formatted labels showing specific parameters and details
- **Information Density**: Comparison of how much information is displayed
- **Workflow Efficiency**: How custom formatting improves user productivity
