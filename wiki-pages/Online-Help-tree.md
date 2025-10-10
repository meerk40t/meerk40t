# Online Help: Tree

## Overview

The **Tree** panel is MeerK40t's central workspace management interface, providing a hierarchical view of all project elements, operations, and regmarks. It serves as the primary tool for organizing, managing, and controlling laser cutting/engraving jobs.

The tree displays three main branches:
- **Operations**: Laser processing instructions (cut, engrave, raster, etc.)
- **Elements**: Design objects to be processed (shapes, text, images)
- **Regmarks**: Registration marks and templates (not burned)

## Operations

### The Operations-parent node
The top-level Operations node provides global control over all laser processing instructions. Right-clicking this node reveals a comprehensive context menu for managing the entire operation set.

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/275504e8-24a6-4d96-a8a7-74730f0a4c72)

#### Global Settings
Opens a dialog for configuring job-wide operation parameters:
- **Passes**: How many times the entire job should repeat (1-∞)
- **Infinite Loop**: Continuously repeat the job (useful for material testing)

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/75cf67db-d329-4fcc-9a5a-e9635d9aa4e1)

#### Operation Management
- **Clear all**: Removes all operations from the project
- **Clear unused**: Removes operations with no assigned elements
- **Scale speed settings**: Adjust speeds for all/selected operations by percentage
- **Scale power settings**: Adjust power levels for all/selected operations by percentage

#### Operation State Control
- **Enable all operations**: Activates all operations for burning
- **Disable all operations**: Deactivates all operations (prevents burning)
- **Toggle all operations**: Reverses enabled/disabled state of all operations

#### Classification
- **Refresh classification for all**: Reassigns elements to operations
  - **Create new operations**: Generates missing operation types as needed
  - **Use existing only**: Only reassigns to current operations

#### Operation Templates
- **Load operations**: Imports previously saved operation configurations
- **Save operations**: Exports current operation set for reuse

#### Adding Operations
- **Append operation**: Adds standard laser operations (Image, Raster, Engrave, Cut)
- **Append special operation**: Adds control operations (Console commands, Movement, I/O control)

### Individual Operation Management
Each operation node shows processing parameters and provides operation-specific controls:
- **Speed**: Movement speed during processing
- **Power**: Laser power level
- **Frequency**: Pulse frequency (for supported devices)
- **Passes**: How many times this specific operation repeats
- **Color**: Visual identifier and grouping color

Operations can be reordered by dragging, affecting processing sequence.

## Elements

The Elements branch contains all design objects that will be processed by laser operations. Elements are automatically classified into appropriate operations based on their properties.

### Element Types
- **Shapes**: Rectangles, circles, ellipses, polygons
- **Paths**: Complex vector paths and curves
- **Text**: Editable text objects with font properties
- **Images**: Raster images for engraving
- **Groups**: Collections of related elements

### Element Management
- **Drag and Drop**: Move elements between operations or groups
- **Selection**: Click to select, Ctrl+click for multi-select
- **Emphasis**: Visual highlighting of active elements
- **Grouping**: Organize related elements into folders
- **Hiding**: Temporarily hide elements from view

### Element Properties
Right-click elements to access:
- **Transform**: Move, rotate, scale, skew
- **Convert**: Change element types
- **Boolean operations**: Union, subtract, intersect
- **Path operations**: Simplify, reverse, break apart

## Regmarks

Regmarks are special elements that serve as visual guides and templates but are never burned by the laser. They provide reference points for design alignment and job setup.

### Regmark Features
- **Non-burnable**: Automatically excluded from laser processing
- **Background layer**: Displayed behind regular elements
- **Template function**: Use for alignment guides and job templates
- **Persistent storage**: Saved with project files

### Managing Regmarks
- **Drag elements**: Move elements in/out of regmarks section
- **Template usage**: Create reusable design frameworks
- **Alignment aids**: Position guides for multi-part jobs
- **Non-interactive**: Regmark elements cannot be selected on canvas

## Location in MeerK40t

The Tree panel is located in the right docking area by default. Access through:
- Main interface: Right panel (docked)
- Menu: `View` → `Panes` → `Tree`
- Keyboard: Configurable via keybindings

Source code: `meerk40t\gui\wxmtree.py`

## Category

**GUI**

## Description

The Tree panel is MeerK40t's hierarchical project browser and job management interface. It provides comprehensive control over the laser cutting/engraving workflow by organizing all project components into a clear, navigable structure.

Users interact with the tree through:
- **Visual hierarchy**: Clear organization of operations, elements, and regmarks
- **Drag and drop**: Intuitive element assignment and reorganization
- **Context menus**: Operation-specific and element-specific commands
- **Visual feedback**: Color coding, icons, and status indicators
- **Warning system**: Alerts for unassigned or disabled elements

The tree serves as the central hub for job preparation, allowing users to:
- Organize complex multi-operation jobs
- Fine-tune processing parameters
- Manage element assignments
- Monitor job readiness
- Access advanced features through context menus

## How to Use

### Basic Workflow

1. **Import/Load Design**: Add elements via File menu or drag-and-drop
2. **Review Classification**: Check automatic operation assignment in Tree
3. **Adjust Operations**: Modify speeds, powers, and other parameters
4. **Organize Elements**: Drag elements between operations as needed
5. **Configure Job**: Set passes, enable/disable operations
6. **Execute**: Send job to laser or simulate

### Key Features

- **Integrated with**: `freeze_tree`, `refresh_tree`, `updateelem_tree` signals
- **Supports**: Multi-selection, drag-and-drop, context menus
- **Provides**: Visual feedback, warnings, tooltips
- **Manages**: Operations, elements, regmarks, job parameters

### Advanced Usage

#### Operation Optimization
- Use speed/power scaling for material testing
- Enable/disable operations for partial job execution
- Reorder operations to optimize cutting sequence

#### Element Organization
- Group related elements for batch operations
- Use regmarks for complex multi-part assemblies
- Hide unused elements to reduce visual clutter

#### Job Templates
- Save/load operation configurations
- Create standardized processing setups
- Maintain consistency across projects

## Technical Details

The Tree panel implements a sophisticated node-based architecture:

### Core Components
- **ShadowTree**: Manages tree state and node relationships
- **Node System**: Hierarchical object management with parent/child relationships
- **Signal Integration**: Responds to kernel signals for real-time updates
- **Renderer Integration**: Provides visual feedback and icons

### Key Technologies
- **wxPython TreeCtrl**: Cross-platform tree widget
- **Signal-based Updates**: Real-time synchronization with kernel
- **Icon Management**: Dynamic icon generation and caching
- **Drag and Drop**: Advanced element manipulation
- **Color Coding**: Visual status indication

### Performance Features
- **Lazy Loading**: Icons generated on-demand
- **Caching**: Image and color cache for performance
- **Freeze/Thaw**: UI updates can be suspended during bulk operations
- **Background Processing**: Non-blocking updates for large projects

## Related Topics

- [[Online Help: Operations]]
- [[Online Help: Elements]]
- [[Online Help: Classification]]
- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Tree panel showing operations, elements, and regmarks branches*

*Context menu for operations management*

*Element properties and transformation options*

---

*This help page provides comprehensive documentation for the Tree panel functionality in MeerK40t.*
