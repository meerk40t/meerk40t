# Online Help: Preferences

## Overview

This help page covers the **Preferences** functionality in MeerK40t.

The Preferences dialog provides comprehensive control over MeerK40t's behavior, appearance, and functionality through multiple organized tabs. This central configuration interface allows you to customize units, language, classification rules, GUI appearance, and many other aspects of the laser cutting software.

## General
<img width="212" alt="image" src="https://github.com/meerk40t/meerk40t/assets/2670784/d80e2433-014a-4322-9362-82097fb390cb">

### Units Settings
- **Units**: Define the standard measurement units for MeerK40t to use
  - **mm**: Millimeters (metric system, default)
  - **cm**: Centimeters (metric system)
  - **inch**: Inches (imperial system)
  - **mil**: Thousandths of an inch (imperial system)
- Affects all measurements, coordinates, and display values throughout the application

### Language Settings
- **Language**: Sets the user interface language
- Requires application restart to take effect
- Supports multiple languages for international users
- Automatically updates all menus, dialogs, and messages

### General Preferences
- Various application-wide settings and behaviors
- Configuration options for general MeerK40t operation
- User experience customization settings

### Settings Management
- **Save**: Immediately save current settings to disk
- **Export**: Export settings to a backup file for safekeeping
- **Import**: Import previously saved settings (with safety warnings)
- Right-click menu provides advanced clearing options:
  - Clear pane/window positions
  - Clear color settings
  - Clear recent file names
  - Clear camera settings
  - Clear all user settings (developer mode only)

## Input/Output
### SVG Pixel Settings
- **SVG Pixel Per Inch**: Select the Pixels Per Inch to use when loading SVG files
  - **96 px/in Inkscape**: Standard web/SVG resolution
  - **72 px/in Illustrator**: Adobe Illustrator default
  - **90 px/in Old Inkscape**: Legacy Inkscape version
  - **Custom**: User-defined PPI value
- Critical for accurate scaling of vector graphics

### File Processing Options
- **SVG Viewport is bed**: Use SVG viewport dimensions to scale elements
- **Image DPI Scaling**: Control how raster images are scaled
  - **Unset**: Treat images as 1000 pixels per inch
  - **Set**: Use embedded DPI information for accurate sizing
- **Create file-node for imported image**: Control image organization in project tree

### CAD File Support
- **DXF Center and Fit**: Automatically scale and center DXF files to fit the laser bed
- **Inkscape-path**: Path to Inkscape executable for advanced SVG processing
- **Unsupported elements**: Handle complex SVG features (gradients, clips, text effects)
  - **Ask at load time**: Prompt user for conversion decisions
  - **Convert automatically**: Let Inkscape handle conversions silently

![image](https://github.com/meerk40t/meerk40t/assets/2670784/741b4d31-2169-4dc7-93cc-818ed55e3eba)

## Classification
See: [Classification](Online-Help-classification)

### Classification Presets
- **Automatic**: Optimized settings for automatic element-to-operation assignment
- **Manual**: Complete manual control over classification process
- Preset buttons quickly configure multiple related settings

### Classification Rules
- **Classify on color**: Automatic assignment based on element colors
- **Classify new elements**: Auto-classify newly added elements
- **Fuzzy classification**: Approximate color matching
- **Black as raster**: Treat black elements as raster operations
- **Default operations**: Fallback assignment rules

## Operations
### Operation-Specific Settings
- Speed and power parameters for different operation types
- Device-specific configuration options
- Safety thresholds and warnings
- Default parameter values

## GUI
This section allows you to influence the look and feel of the user interface.

![image](https://github.com/meerk40t/meerk40t/assets/2670784/39f6a942-6bd3-4864-8ace-34434dbbd8fe)

### Appearance Settings
- **Icon size**: Control the size of toolbar and menu icons
- **Mini icon in tree**: Display small icons in the elements tree
- **Color entries in tree**:
  - **Active**: Display elements in their actual colors in the tree
  - **Inactive**: Use standard tree colors
- **Show ribbon labels**: Display text labels on ribbon bar buttons

### General GUI Options
- Window behavior and layout preferences
- Dialog display options
- User interface responsiveness settings

### Miscellaneous Settings
- Various UI customization options
- Performance and display tweaks
- Accessibility preferences

### Zoom and Navigation
- Default zoom levels and behavior
- Mouse wheel zoom sensitivity
- Pan and scroll preferences

## Scene
### Canvas Display Options
- Grid and guide settings
- Background colors and patterns
- Element rendering preferences
- Scene boundary and margin settings

## Colors
### Color Scheme Customization
- Comprehensive color picker interface
- Organized by functional categories (Scene, Operations, GUI elements)
- Real-time preview of color changes
- **Reset Colors**: Restore default color scheme
- **Reset to brighter defaults**: Use high-contrast color scheme (dark themes)

### Special Colors
- **Object-Label**: Color for element labels and annotations
- **Scene elements**: Background, grid, selection colors
- **Operation colors**: Cut, engrave, raster operation colors

## Ribbon
### Toolbar Customization
- Interactive ribbon editor for toolbar layout
- Add, remove, and rearrange toolbar buttons
- Create custom tool groups and sections
- Save and load ribbon configurations

## Developer Mode (Advanced)
### Coordinate Space Settings
- Advanced coordinate system configuration
- Debug and development options
- Extended preference categories

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\preferences.py`

## Category

**Configuration**

## Description

The Preferences dialog is MeerK40t's central configuration hub, providing organized access to all application settings through a tabbed interface. Each tab focuses on a specific aspect of the software, from basic units and language to advanced classification rules and GUI customization. The system supports presets, import/export functionality, and real-time updates.

## How to Use

### Key Features

- Integrates with: `restart`
- Integrates with: `theme`
- Integrates with: `preferences`
- Multi-tab configuration interface
- Preset configurations for common workflows
- Settings backup and restore capabilities

### Basic Usage

1. **Access Preferences**: Use menu `Edit → Preferences` or keyboard shortcut `Ctrl-,`
2. **Navigate Tabs**: Click on tab headers to access different preference categories
3. **Modify Settings**: Change values using dropdowns, checkboxes, text fields, and color pickers
4. **Apply Changes**: Most changes take effect immediately; some require restart
5. **Save Configuration**: Use Save button or let MeerK40t auto-save on exit

## Technical Details

The Preferences system uses a modular architecture with specialized panels for different configuration categories. Each panel extends wx.Panel and integrates with MeerK40t's signal system for real-time updates.

**Key Technical Components**:
- **Tab-based Interface**: wx.aui.AuiNotebook for organized configuration access
- **ChoicePropertyPanel**: Dynamic preference panel generation from settings definitions
- **Signal Integration**: Real-time updates through signal listeners
- **Settings Persistence**: Automatic saving and loading of user preferences
- **Import/Export System**: Configuration backup and restore functionality

**Configuration Management**:
- **Persistent Storage**: Settings saved in kernel configuration system
- **Validation**: Input validation and range checking
- **Signals**: Event-driven updates for preference changes
- **Presets**: Predefined configuration sets for common use cases

## Usage Guidelines

### Configuration Strategy

**Start with Basics**:
- Set units and language first
- Configure classification presets (Automatic vs Manual)
- Adjust GUI appearance to your preferences

**Workflow Optimization**:
- Use presets for initial setup
- Fine-tune individual settings as needed
- Create backups before major changes
- Test configurations with sample projects

### Safety Considerations

**Backup Important Settings**:
- Regularly export your configuration
- Test imported settings before relying on them
- Be cautious with developer mode options
- Keep multiple backup versions

### Performance Tuning

**GUI Optimization**:
- Adjust icon sizes for your display
- Configure zoom sensitivity for comfortable navigation
- Set appropriate update frequencies
- Balance visual quality with performance

## Troubleshooting

### Settings Not Applying

**Restart Requirements**:
- Some changes (language, major GUI settings) require restart
- Check for restart notifications in the interface
- Save settings before restarting

### Import/Export Issues

**File Compatibility**:
- Ensure configuration files are from compatible MeerK40t versions
- Check file permissions for import/export directories
- Verify file integrity before importing

### Color Scheme Problems

**Theme Conflicts**:
- Reset colors if display issues occur
- Try brighter defaults for dark themes
- Check for theme signal conflicts
- Restart application after major color changes

### Performance Issues

**Configuration Overhead**:
- Reduce real-time updates for better performance
- Adjust GUI refresh rates
- Disable unnecessary visual features
- Monitor memory usage with complex configurations

## Advanced Features

### Preset System

**Workflow Presets**:
- **Automatic Classification**: Optimized for new users and standard workflows
- **Manual Classification**: Complete control for advanced users
- **Custom Presets**: User-defined configuration sets

### Configuration Scripting

**Command Line Access**:
- All preferences accessible via console commands
- Batch configuration changes
- Automated setup scripts
- Integration with external tools

### Developer Extensions

**Advanced Options**:
- Coordinate space debugging
- Extended preference categories
- Development mode features
- API access to configuration system

## Related Topics

*Link to related help topics:*

- [Online Help: Classification](Online-Help-classification)
- [Online Help: Devices](Online-Help-devices)
- [Online Help: Operations](Online-Help-operations)
- [Online Help: GUI](Online-Help-gui)

## Screenshots

### General Tab - Basic Settings
The General tab displaying fundamental application settings:
- **Units Dropdown**: Measurement system selection (mm, cm, inch, mil)
- **Language Dropdown**: User interface language selection
- **General Preferences**: Various application-wide behavior settings
- **Settings Management**: Save, Export, and Import buttons for configuration backup

### Input/Output Tab - File Processing
The Input/Output tab showing file handling configuration:
- **SVG Pixel Settings**: PPI selection (96/Inkscape, 72/Illustrator, 90/Old Inkscape, Custom)
- **File Processing Options**: SVG viewport, image DPI scaling, file-node creation
- **CAD File Support**: DXF centering, Inkscape path, unsupported element handling
- **Conversion Options**: Ask at load time vs automatic conversion

### Classification Tab - Element Assignment
The Classification tab displaying automatic operation assignment settings:
- **Preset Buttons**: Automatic and Manual classification preset options
- **Classification Rules**: Color-based assignment, fuzzy matching, black as raster
- **New Element Handling**: Auto-classify newly added elements
- **Default Operations**: Fallback assignment rules for unclassified elements

### GUI Tab - Interface Appearance
The GUI tab showing user interface customization options:
- **Icon Size Control**: Toolbar and menu icon size adjustment
- **Tree Display Options**: Mini icons, color entries in tree, ribbon labels
- **General GUI Options**: Window behavior and layout preferences
- **Zoom and Navigation**: Mouse wheel sensitivity and pan/scroll settings

### Colors Tab - Color Scheme Customization
The Colors tab displaying comprehensive color management:
- **Color Categories**: Organized sections for Scene, Operations, GUI elements
- **Color Pickers**: Individual color selection for each interface element
- **Real-time Preview**: Live preview of color changes
- **Reset Options**: Reset to defaults or brighter defaults for dark themes

### Scene Tab - Canvas Display Options
The Scene tab showing canvas and display configuration:
- **Grid and Guide Settings**: Grid visibility, snap behavior, guide lines
- **Background Options**: Canvas background color and pattern selection
- **Element Rendering**: How elements are displayed on the scene
- **Boundary Settings**: Scene margins and boundary display options

### Operations Tab - Laser Operation Defaults
The Operations tab displaying operation-specific parameter configuration:
- **Operation Categories**: Separate sections for Cut, Engrave, Raster, Image operations
- **Parameter Controls**: Speed, power, frequency settings for each type
- **Safety Thresholds**: Warning levels and danger limits
- **Device-Specific Options**: Hardware-dependent parameter ranges

### Ribbon Tab - Toolbar Customization
The Ribbon tab showing interactive toolbar configuration:
- **Ribbon Editor Interface**: Drag-and-drop toolbar button arrangement
- **Button Management**: Add, remove, and rearrange toolbar elements
- **Custom Groups**: Create user-defined tool sections and categories
- **Configuration Save/Load**: Save and restore custom ribbon layouts

### Developer Mode Tab - Advanced Options
The Developer Mode tab displaying advanced configuration options:
- **Coordinate Space Settings**: Advanced coordinate system debugging
- **Extended Preferences**: Additional configuration categories
- **Debug Options**: Development and troubleshooting features
- **API Access**: Advanced configuration system integration

---

*This help page provides comprehensive documentation for the Preferences system in MeerK40t.*
