# Online Help: Ribboneditor

## Overview

This help page covers the **Ribboneditor** functionality in MeerK40t.

The Ribbon Editor is a powerful customization tool that allows users to modify the appearance and organization of MeerK40t's ribbon interface. It provides comprehensive controls for managing ribbon bars, pages, panels, and user-defined buttons, enabling users to create a personalized workspace that matches their workflow preferences.

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/a6e8c2db-7c48-488a-8fa6-cd13bb559b8d)

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\wxmribbon.py`

## Category

**GUI**

## Description

The Ribbon Editor serves as the central hub for customizing MeerK40t's dynamic ribbon interface. MeerK40t uses a sophisticated ribbon system that organizes commands into categorized panels and pages, providing quick access to frequently used tools and operations.

The ribbon system consists of multiple ribbon bars (Primary, Tools, Edit Tools) that can be independently configured. Each ribbon bar contains pages (like "Project", "Modify", "Config") which in turn contain panels (like "Control", "Device", "Align") with related buttons and controls.

The Ribbon Editor allows users to:
- Add, remove, and reorder ribbon pages
- Customize panel layouts within pages
- Create custom user-defined buttons with flexible actions
- Control label display preferences
- Reset configurations to factory defaults
- Manage multiple ribbon bar configurations

This customization capability is particularly valuable for users who work with specific device types or have established workflows, as it allows them to optimize their interface for maximum efficiency.

## How to Use

### Available Controls

#### Ribbon Selection
- **Ribbon Dropdown**: Selects which ribbon bar to customize (Primary, Tools, Edit Tools)
- **Show the Ribbon Labels** (Checkbox): Controls whether text labels are displayed beneath ribbon icons

#### Page Management
- **Pages List**: Displays all pages in the selected ribbon
- **Page Label Text Field**: Edit the display name of the selected page
- **Add Page Button (+)**: Creates a new page in the ribbon
- **Delete Page Button (trash icon)**: Removes the selected page
- **Move Page Up/Down Buttons**: Changes the order of pages in the ribbon

#### Panel Management
- **Panels List**: Shows all panels within the selected page
- **Add to Page Button**: Adds available panels to the selected page
- **Delete Panel Button (trash icon)**: Removes panels from the page
- **Move Panel Up/Down Buttons**: Reorders panels within the page

#### Available Panels
- **Available Panels List**: Shows panels that can be added to pages
- **Panel Tooltip**: Hover over panels to see which buttons they contain

#### User-Defined Buttons
- **User Buttons List**: Displays custom buttons created by the user
- **Add Button (+)**: Creates a new custom button
- **Delete Button (trash icon)**: Removes custom buttons
- **Edit Button (pencil icon)**: Modifies button properties
- **Move Button Up/Down**: Changes button order

#### Action Controls
- **Apply Button**: Saves all changes to the ribbon configuration
- **Reset to Default Button**: Restores the ribbon to its original factory configuration

### Key Features

The Ribbon Editor integrates with MeerK40t's dynamic button registration system:
- **button/control**: Device control panels (Red Dot, Frame, etc.)
- **button/device**: Device configuration panels
- **button/project**: Project management operations
- **button/basicediting**: Basic editing tools
- **button/modify**: Element modification tools
- **button/geometry**: Geometric transformation tools
- **button/preparation**: Job preparation operations
- **button/jobstart**: Job execution controls
- **button/control**: Device control operations
- **button/config**: Application configuration
- **button/align**: Alignment operations
- **button/select**: Selection tools
- **button/tools**: Creation tools
- **button/lasercontrol**: Laser power controls
- **button/extended_tools**: Advanced creation tools
- **button/group**: Grouping operations
- **button/user**: User-defined custom buttons

### Basic Usage

#### Customizing Ribbon Layout

1. **Select Ribbon Bar**: Choose which ribbon to customize from the dropdown (Primary, Tools, or Edit Tools)
2. **Add/Remove Pages**: Use the page controls to create new pages or remove unwanted ones
3. **Organize Panels**: Add panels to pages by selecting them from "Available Panels" and clicking "Add to page"
4. **Reorder Elements**: Use the up/down arrow buttons to arrange pages and panels in your preferred order
5. **Apply Changes**: Click "Apply" to save your custom layout

#### Creating Custom Buttons

1. **Add New Button**: Click the "+" button in the "User-defined buttons" section
2. **Configure Button Properties**:
   - **Label**: Display name for the button
   - **Tooltip**: Help text shown when hovering
   - **Action left click**: Command executed on left-click (e.g., "element* delete", "window open Camera")
   - **Action right click**: Command executed on right-click (optional)
   - **Rule to enable**: When the button should be active (Always, When elements selected, When 2+ elements selected)
   - **Rule to display**: When the button should be visible
   - **Icon**: Select from available MeerK40t icons
3. **Apply Configuration**: Click "Apply" to save the custom button

#### Managing Label Display

1. **Toggle Labels**: Check/uncheck "Show the Ribbon Labels" to control text display beneath icons
2. **Apply Setting**: Click "Apply" to save the label preference

#### Resetting Configuration

1. **Reset to Default**: Click "Reset to Default" to restore the original ribbon layout
2. **Apply Reset**: Click "Apply" to confirm the reset operation

## Technical Details

The Ribbon Editor manages a hierarchical configuration system stored in `ribbon_[identifier].cfg` files:

```
Ribbon Configuration Structure:
├── Ribbon (metadata)
│   ├── identifier: ribbon type (primary/tools/edittools)
│   └── show_labels: boolean for label display
├── Page_1, Page_2, ... (page definitions)
│   ├── id: unique page identifier
│   ├── label: display name
│   ├── seq: display order
│   └── Panel_1, Panel_2, ... (panel definitions)
│       ├── id: panel identifier
│       ├── seq: panel order
│       └── label: panel display name
└── Button_1, Button_2, ... (user-defined buttons)
    ├── id: button identifier
    ├── label: button text
    ├── tip: tooltip text
    ├── action_left/right: click commands
    ├── enable/visible: activation rules
    ├── icon: icon identifier
    └── seq: button order
```

The system uses persistent storage to maintain customizations across sessions. Button enable/disable rules are dynamically evaluated based on element selection state, and the ribbon automatically updates when new buttons are registered by device drivers or plugins.

## Related Topics

*Link to related help topics:*

- [[Online Help: Preferences]] - General application preferences including ribbon settings
- [[Online Help: Devices]] - Device-specific ribbon panels and controls
- [[Online Help: Operation Property]] - Operation-specific ribbon controls

## Screenshots

### Ribbon Editor Main Interface
The main Ribbon Editor window displaying customization controls:
- **Ribbon Dropdown**: Selection between Primary, Tools, and Edit Tools ribbons
- **Show Labels Checkbox**: Toggle for displaying text labels beneath ribbon icons
- **Pages List**: Hierarchical view of ribbon pages and their panels
- **Available Panels List**: Panels that can be added to the selected page

### Page Management Controls
The page management section showing page organization:
- **Pages List**: Current pages in the selected ribbon with expand/collapse
- **Page Label Field**: Text input for editing the selected page name
- **Add Page Button**: Plus icon for creating new ribbon pages
- **Delete/Move Buttons**: Trash icon and up/down arrows for page management

### Panel Customization Interface
The panel management area for organizing page contents:
- **Panels in Page List**: Current panels within the selected page
- **Add to Page Button**: Adds selected available panel to the current page
- **Delete Panel Button**: Trash icon for removing panels from pages
- **Move Panel Buttons**: Up/down arrows for reordering panels within pages

### User-Defined Buttons Section
The custom buttons management area:
- **User Buttons List**: Custom buttons created by the user
- **Add Button**: Plus icon for creating new custom buttons
- **Edit Button**: Pencil icon for modifying button properties
- **Delete/Move Buttons**: Trash and arrow icons for button management

### Button Configuration Dialog
The custom button properties dialog:
- **Label Field**: Display name for the custom button
- **Tooltip Field**: Help text shown on hover
- **Action Fields**: Left-click and right-click command inputs
- **Enable/Visible Rules**: Dropdowns for when button is active/visible
- **Icon Selection**: Dropdown for choosing button icon

### Ribbon Layout Preview
The interface showing a customized ribbon layout:
- **Modified Pages List**: Shows added/removed/reordered pages
- **Panel Organization**: Custom arrangement of panels within pages
- **User Buttons Integration**: Custom buttons appearing in appropriate panels
- **Apply Pending**: Visual indication of unsaved changes

### Before/After Customization Comparison
Side-by-side view showing ribbon changes:
- **Original Layout**: Default ribbon configuration
- **Customized Layout**: User-modified page and panel arrangement
- **Added Elements**: New pages or panels visible in the customized version
- **Removed Elements**: Missing pages or panels from the original layout

### Reset to Default Confirmation
The reset functionality interface:
- **Reset Button**: "Reset to Default" button for restoring original layout
- **Confirmation Dialog**: Warning about losing customizations
- **Factory Configuration**: Preview of the default ribbon structure
- **Apply Reset**: Confirmation to proceed with the reset operation

---

*This help page provides comprehensive documentation for the Ribbon Editor customization system.*
