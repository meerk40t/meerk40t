# Online Help: Operationinfo

## Overview

This help page covers the **Operationinfo** functionality in MeerK40t.

The Operation Information panel provides a comprehensive overview of all laser operations in your project, showing operation details, element assignments, and time estimates. It serves as a central hub for managing and monitoring your laser cutting/engraving workflow.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\operation_info.py`

## Category

**GUI**

## Description

The Operation Information panel displays a detailed list of all operations in your project, including their types, assigned elements, and estimated execution times. It helps you understand your job structure, identify unassigned elements, and optimize your workflow. This panel is essential for project planning, time estimation, and quality control in laser operations.

## How to Use

### Available Controls

- **Get Time Estimates** (Button): Calculates and displays estimated runtime for each operation
- **Operations List**: Shows all operations with details and right-click context menus

### Key Features

- Integrates with: `tree_changed`
- Integrates with: `rebuild_tree`
- Integrates with: `element_property_reload`
- Real-time operation monitoring
- Time estimation capabilities
- Unassigned element detection
- Right-click context menus for operations

### Basic Usage

1. **Open Panel**: Access from Operations → Operation Information menu
2. **Review Operations**: Examine the list of all operations in your project
3. **Get Estimates**: Click "Get Time Estimates" to calculate runtimes
4. **Manage Elements**: Use right-click menus to handle unassigned elements or reclassify operations

## Operations List Display

### Column Information

**# (Index)**:
- Sequential numbering of operations
- Unique identifier for each operation in the list

**Type**:
- Operation type with icon (Cut, Raster, Image, Engrave, Dots)
- Visual indicators for different operation categories
- Icons help quickly identify operation purposes

**Name**:
- Display label of the operation
- Custom names or default type labels
- Helps identify specific operations in complex projects

**Items**:
- Number of elements assigned to each operation
- Shows operation utilization and element distribution
- Zero items indicate empty operations

**Runtime**:
- Estimated execution time for the operation
- Initially shows "---" until estimates are calculated
- Displays actual time estimates after calculation

### Special Entries

**Unassigned Elements**:
- Marked with "!" in the index column
- Shows elements not assigned to any operation
- Displays element type and count
- Helps identify elements that need classification

## Time Estimation

### How It Works

**Calculation Process**:
1. Click "Get Time Estimates" button
2. System calculates runtime for each operation
3. Estimates appear in the Runtime column
4. Based on operation settings and assigned elements

**Estimation Factors**:
- Operation speed and power settings
- Number and complexity of assigned elements
- Laser movement calculations
- Acceleration and deceleration times

### Accuracy Considerations

**Estimate Quality**:
- Provides reasonable approximations
- Actual times may vary based on hardware performance
- Useful for job planning and scheduling
- Helps compare different operation configurations

## Right-Click Context Menus

### For Operations

**Remove All Items**:
- Clears all elements from the selected operation
- Useful for resetting operations or reassigning elements
- Maintains operation settings while removing assignments

**Re-Classify**:
- Re-evaluates all elements against operation criteria
- Automatically reassigns elements based on current classification rules
- Useful after changing operation parameters or element properties

### For Unassigned Elements

**Emphasize Elements**:
- Highlights specific unassigned element types in the design
- Helps visualize which elements need assignment
- Supports both specific types and all unassigned elements

## Workflow Applications

### Project Planning

**Job Overview**:
- See complete operation structure at a glance
- Identify bottlenecks and long-running operations
- Plan job execution order and timing
- Estimate total project completion time

**Resource Management**:
- Monitor operation distribution across job
- Identify underutilized or empty operations
- Balance workload across different operation types
- Optimize for material usage and time efficiency

### Quality Control

**Element Assignment Verification**:
- Ensure all design elements are properly assigned
- Identify orphaned elements that won't be processed
- Verify operation coverage for complex designs
- Prevent incomplete job execution

**Operation Validation**:
- Check that operations have appropriate settings
- Verify time estimates are reasonable
- Identify operations that may need parameter adjustments
- Ensure job feasibility before execution

### Troubleshooting

**Problem Identification**:
- Locate operations with zero assigned elements
- Find unassigned elements that may be missed
- Identify operations with unusually long or short estimates
- Detect classification or assignment issues

## Technical Details

The OpInfoPanel class extends ScrolledPanel and provides a wxListCtrl-based interface for operation management.

**Key Technical Components**:
- **List Control**: wxListCtrl with custom columns and icons
- **Image List**: Operation type icons for visual identification
- **Signal Integration**: Responds to tree changes and element updates
- **Time Estimation**: Calculates operation runtimes based on parameters
- **Context Menus**: Dynamic right-click menus for operations and elements

**Data Management**:
- **Operation Enumeration**: Lists all operations from elements.ops()
- **Element Classification**: Identifies unassigned elements by type
- **Icon Assignment**: Maps operation types to appropriate icons
- **Data Persistence**: Column widths saved between sessions

**Signal Handling**:
- **Tree Changes**: Updates list when operations are added/modified/removed
- **Property Updates**: Refreshes data when operation properties change
- **Element Updates**: Monitors for new or changed elements

## Usage Guidelines

### Regular Monitoring

**During Design**:
- Check operation assignments as you build designs
- Monitor time estimates for realistic planning
- Identify and assign unassigned elements promptly
- Verify operation settings and parameters

**Before Execution**:
- Review complete operation list
- Calculate final time estimates
- Ensure all elements are assigned
- Verify operation order and settings

### Performance Optimization

**Time Management**:
- Use estimates to identify time-consuming operations
- Consider breaking long operations into smaller parts
- Optimize speed and power settings based on estimates
- Plan job execution during appropriate time slots

**Element Organization**:
- Group similar elements into appropriate operations
- Avoid leaving elements unassigned
- Use re-classify to optimize element distribution
- Consider operation-specific settings for different element types

## Troubleshooting

### Time Estimates Not Showing

**Calculation Issues**:
- Ensure operations have valid settings
- Check that elements are properly assigned
- Verify operation parameters are complete
- Try refreshing the panel or restarting MeerK40t

**Display Problems**:
- Click "Get Time Estimates" button again
- Check for error messages in console
- Verify operation types are supported
- Ensure sufficient system resources

### Unassigned Elements Not Appearing

**Detection Problems**:
- Refresh the panel using tree change signals
- Check that elements exist in the design
- Verify element types are recognized
- Look for classification rule conflicts

### Operations Not Listed

**Visibility Issues**:
- Ensure operations exist in the elements tree
- Check operation types are supported
- Verify operations are not hidden or disabled
- Try rebuilding the tree structure

### Context Menu Problems

**Menu Not Appearing**:
- Ensure right-click is on a valid list item
- Check that operations/elements exist
- Verify panel has proper focus
- Try clicking on different parts of the item

## Advanced Features

### Icon-Based Operation Types

**Visual Identification**:
- Cut operations: Laser beam icon
- Raster operations: Direction arrow icon
- Image operations: Image icon
- Engrave operations: Weak laser beam icon
- Dots operations: Points icon

### Dynamic Updates

**Real-time Synchronization**:
- Panel updates automatically when operations change
- Element assignments reflected immediately
- Time estimates recalculated on demand
- Context menus adapt to current state

### Element Classification Integration

**Smart Assignment**:
- Works with automatic element classification
- Supports fuzzy classification for complex elements
- Integrates with operation-specific rules
- Maintains assignment history and preferences

## Related Topics

*Link to related help topics:*

- [[Online Help: Operationproperty]]
- [[Online Help: Opbranchproperty]]
- [[Online Help: Pathproperty]]
- [[Online Help: Tree]]

## Screenshots

*Add screenshots showing the operation information panel with sample operations and time estimates.*

---

*This help page provides comprehensive documentation for the Operation Information panel in MeerK40t.*
