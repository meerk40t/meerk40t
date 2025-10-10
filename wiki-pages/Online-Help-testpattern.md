# Online Help: Testpattern

## Overview

This help page covers the **Testpattern** functionality in MeerK40t.

This panel provides controls for template functionality. Key controls include "Template-Name" (label), "Save" (button), "Load" (button).

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\materialtest.py`

## Category

**GUI**

## Description

The Testpattern panel is a sophisticated material testing and parameter optimization tool that generates systematic grids of laser operations to help users find optimal settings for their specific materials and lasers. This feature creates test patterns that vary two different parameters simultaneously, allowing for scientific optimization of laser cutting and engraving processes.

Users would use this feature when:
- **Material Optimization**: Finding the best speed/power combinations for new materials
- **Laser Calibration**: Determining optimal settings for different laser types or configurations
- **Quality Control**: Establishing baseline parameters for consistent results
- **Process Development**: Testing parameter interactions and finding sweet spots
- **Troubleshooting**: Diagnosing issues with cutting depth, burn marks, or engraving quality

The system generates a grid where each cell represents a unique combination of two parameters (like speed vs power), with optional labels and color coding to make results easy to interpret and compare.

## How to Use

### Available Controls

#### Operation Selection
- **Operation Dropdown**: Choose the type of laser operation to test (Cut, Engrave, Raster, Image, Hatch, Wobble)
- **Image Selection**: When Image operation is selected, choose from existing images in the design

#### Parameter Configuration (X-Axis)
- **Parameter Dropdown**: Select the first parameter to vary (Speed, Power, Passes, DPI, etc.)
- **Count Spinner**: Number of test values for the first parameter
- **Minimum/Maximum Fields**: Value range for the first parameter
- **Width Field**: Size of each test pattern element
- **Delta Field**: Horizontal spacing between test patterns
- **Color Dropdown**: Color aspect for visual coding (Red, Green, Blue)
- **Growing Checkbox**: Direction of color gradient for first parameter

#### Parameter Configuration (Y-Axis)
- **Parameter Dropdown**: Select the second parameter to vary
- **Count Spinner**: Number of test values for the second parameter
- **Minimum/Maximum Fields**: Value range for the second parameter
- **Height Field**: Size of each test pattern element
- **Delta Field**: Vertical spacing between test patterns
- **Color Dropdown**: Color aspect for visual coding
- **Growing Checkbox**: Direction of color gradient for second parameter

#### Display Options
- **Labels Checkbox**: Add descriptive text labels to the grid
- **Values Checkbox**: Show parameter values on the grid axes
- **Create Boundary Shape**: Add duplicate shapes around effects for testing

#### Template Management
- **Template Name Field**: Name for saving/loading parameter sets
- **Save Button**: Store current settings as a named template
- **Load Button**: Restore previously saved settings
- **Delete Button**: Remove saved templates

### Key Features

- **Multi-Parameter Testing**: Simultaneously test two parameters in a grid layout
- **Operation Type Support**: Test Cut, Engrave, Raster, Image, Hatch, and Wobble operations
- **Color Coding**: Visual differentiation using RGB color gradients
- **Template System**: Save and reuse parameter configurations
- **Flexible Parameters**: Support for speed, power, passes, DPI, hatch settings, and wobble parameters
- **Smart Layout**: Automatic centering and spacing calculations
- **Safety Warnings**: Confirmation dialogs before clearing existing work

### Basic Usage

1. **Select Operation Type**: Choose the laser operation you want to optimize from the dropdown
2. **Choose Parameters**: Select two different parameters to test (e.g., Speed vs Power)
3. **Set Parameter Ranges**: Define minimum/maximum values and number of test points for each parameter
4. **Configure Layout**: Set element sizes and spacing for the test grid
5. **Set Display Options**: Enable labels and values for easy result interpretation
6. **Choose Colors**: Select color coding scheme for visual differentiation
7. **Generate Pattern**: Click "Create Pattern" to generate the test grid
8. **Run Test**: Execute the laser job and evaluate the results
9. **Save Template**: Save successful parameter combinations for future use

## Technical Details

The Testpattern system implements systematic parameter variation using a grid-based approach:

**Grid Generation Algorithm:**
- Creates a 2D matrix where each cell represents a unique parameter combination
- Calculates parameter values using linear interpolation between min/max ranges
- Supports both continuous ranges and discrete value selections
- Automatically centers the entire grid on the workbed

**Parameter Types Supported:**
- **Speed**: Cutting/engraving speed (mm/s or mm/min depending on settings)
- **Power**: Laser power (percentage or PPI depending on display settings)
- **Passes**: Number of operation repetitions
- **DPI**: Dots per inch for raster operations
- **Overscan**: Additional travel distance for raster operations
- **Hatch Distance/Angle**: Spacing and orientation for hatch patterns
- **Wobble Parameters**: Radius, interval, speed multiplier, and type for wobble effects

**Color Coding System:**
- RGB color space with independent control for each parameter axis
- Gradient direction control (growing vs shrinking intensity)
- Combined colors when both parameters affect the same color channel
- Visual differentiation for easy result interpretation

**Template Persistence:**
- Settings stored in `templates.cfg` configuration file
- Persistent storage using Settings framework
- Template naming and management through SaveLoadPanel interface
- Automatic restoration of parameter ranges and display options

**Integration Points:**
- Monitors `service/device/active` for device changes
- Responds to `speed_min` and `power_percent` display setting changes
- Uses device-specific parameter defaults and validation
- Integrates with operation property panels for parameter editing

**Safety and Validation:**
- Input validation for parameter ranges and types
- Workbed boundary checking for grid placement
- Confirmation dialogs before clearing existing work
- Automatic parameter type conversion and unit handling

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the testpattern feature.*
