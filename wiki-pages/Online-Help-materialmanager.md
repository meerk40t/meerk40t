# Online Help: Material Manager

## Overview

This help page covers the **Material Manager** functionality in MeerK40t.

The Material Manager is a comprehensive library system for managing material-specific laser cutting and engraving settings. It allows you to create, import, export, and organize material profiles that contain optimized laser parameters for different materials, thicknesses, and laser types.

The system stores material settings in persistent configuration files and provides tools for importing from popular laser software like LightBurn and EZCAD.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\materialmanager.py` - Main material manager implementation
- `meerk40t\core\elements\element_types.py` - Operation type definitions
- Configuration stored in `operations.cfg` in the MeerK40t working directory

## Category

**GUI**

## Description

The Material Manager serves as a centralized repository for laser material settings, enabling users to:

- **Store Material Profiles**: Save optimized settings for different materials and thicknesses
- **Import from Other Software**: Load material libraries from LightBurn (.clb), EZCAD (.lib/.ini), and MeerK40t (.cfg) files
- **Organize by Categories**: Filter and sort materials by name, thickness, or laser type
- **Apply Settings**: Load material profiles into the operations tree or status bar
- **Share with Community**: Contribute material settings to the MeerK40t community
- **Compensate for Hardware**: Adjust settings for different lens sizes and laser power levels

Each material profile contains a complete set of laser operations (cut, engrave, raster, image) with optimized parameters like power, speed, frequency, and passes.

## How to Use

### Accessing Material Manager

The Material Manager can be opened from:
- **Menu**: Configuration → Material Library
- **Console**: `window toggle MatManager`
- **Button**: Material Library button in the configuration section

The interface consists of three main sections:
- **Library Tree**: Hierarchical view of available material profiles
- **Operation Preview**: Detailed view of operations in the selected material
- **Material Details**: Editable properties of the selected material

### Filtering Materials

Use the filter controls at the top to narrow down the material library:

#### Material Filter
- Enter material names (e.g., "Plywood", "Acrylic", "Leather")
- Supports partial matching and multiple materials

#### Thickness Filter
- Enter thickness values (e.g., "3mm", "1/8")
- Filters materials by their specified thickness

#### Laser Type Filter
- Select from available laser types in your system
- Shows only materials compatible with the selected laser

#### Reset Filter
- Clears all filters to show the complete library

### Browsing Material Library

The library tree organizes materials hierarchically:

#### Categorization Options
- **By Material**: Groups by material type (Plywood, Acrylic, etc.)
- **By Laser**: Groups by laser device type
- **By Thickness**: Groups by material thickness

#### Tree Structure
- **Top Level**: Category groups (Material/Laser/Thickness)
- **Middle Level**: Subcategories within the grouping
- **Bottom Level**: Individual material entries with operation counts

### Viewing Material Details

When a material is selected, the details panel shows:

#### Basic Information
- **Title**: Display name of the material profile
- **Material**: Material type (Plywood, Acrylic, etc.)
- **Thickness**: Material thickness specification
- **Laser**: Compatible laser device type

#### Technical Details
- **Power**: Laser power rating (typically in Watts)
- **Lens Size**: Focal lens diameter (typically in mm)

#### Notes
- Additional information and usage notes
- Import conversion details
- Special handling instructions

### Managing Operations

The operation preview table shows all laser operations in the selected material:

#### Operation Columns
- **#**: Operation sequence number
- **Operation**: Operation type (Cut, Engrave, Raster, Image)
- **Id**: Unique operation identifier
- **Label**: Descriptive operation name
- **Power [ppi]**: Laser power setting (0-1000)
- **Speed [mm/s]**: Cutting/engraving speed
- **Frequency [kHz]**: Pulse frequency (for fiber lasers)
- **Passes**: Number of operation repetitions
- **Effects**: Applied effects (hatches, wobbles)

#### Editing Operations
- **Inline Editing**: Click on values to edit directly
- **Right-Click Menu**: Access advanced operations
- **Color Coding**: Visual distinction between operation types

### Creating New Materials

#### From Current Operations
1. Set up operations in the main operations tree
2. Click **"Get current"** to capture current settings
3. Enter material details (name, thickness, laser type)
4. Click **"Set"** to save the material profile

#### Create Empty Material
1. Click **"Add new"** to create a blank material profile
2. Configure material properties
3. Add operations using the right-click menu in the preview table

### Importing Material Libraries

#### Supported Formats
- **LightBurn (.clb)**: LightBurn material library files
- **EZCAD (.lib/.ini)**: EZCAD material database files
- **MeerK40t (.cfg)**: MeerK40t operations configuration

#### Import Process
1. Click **"Import"** button
2. Select the library file to import
3. Configure compensation settings if needed:
   - **Compensate Lens-Sizes**: Adjust for different focal lens sizes
   - **Compensate Power-Levels**: Adjust for different laser power ratings
   - **Consolidate same thickness**: Group similar materials together

#### Compensation Settings
When importing from different systems, you can compensate for hardware differences:

- **Lens Size Compensation**: Adjusts power/speed for different focal lengths
- **Power Level Compensation**: Scales settings for different laser power ratings
- **Automatic Optimization**: Prevents power settings from exceeding safe limits

### Applying Material Settings

#### Load into Operations Tree
1. Select a material from the library
2. Click **"Load into Tree"**
3. Choose whether to clear existing operations or merge
4. Material operations are added to the operations branch

#### Use for Status Bar
1. Select a material from the library
2. Click **"Use for statusbar"**
3. Material operations become available in the status bar icons
4. Quick access to frequently used material settings

### Managing Material Library

#### Right-Click Operations (Library Tree)
- **Add new**: Create a new material profile
- **Get current**: Capture current operations tree
- **Load into Tree**: Apply material to operations
- **Use for statusbar**: Set as status bar defaults
- **Duplicate**: Copy an existing material profile
- **Delete**: Remove a material profile
- **Delete all**: Clear the entire library
- **Sort by...**: Change categorization method
- **Expand/Collapse**: Control tree display

#### Right-Click Operations (Operations Table)
- **Add Raster/Image/Engrave/Cut**: Insert new operation types
- **Duplicate**: Copy an existing operation
- **Delete**: Remove an operation
- **Load into Tree**: Apply single operation to tree
- **Use for statusbar**: Add to status bar defaults
- **Color all [type]**: Apply color coding to operation type
- **Add/Remove effects**: Apply hatches, wobbles, etc.
- **Fill missing ids/labels**: Auto-generate missing identifiers

### Sharing Materials

#### Community Contribution
1. Select a material profile
2. Click **"Share"** button
3. Enter your name for attribution
4. Material is uploaded to the MeerK40t community server
5. Helps other users with similar materials

#### Automatic Processing
- Settings are packaged into a configuration file
- Includes all operation parameters and metadata
- Anonymized for privacy (no personal information included)

## Technical Details

### Storage Format
Material settings are stored in the `operations.cfg` file using a hierarchical structure:
```
[material_name info]
title=Display Name
material=Material Type
thickness=3mm
laser=0
power=50W
lens=2.0mm
note=Additional information

[material_name 000001]
type=op cut
id=C1
label=Cut (100%, 5mm/s)
power=1000
speed=5
passes=1
color=#FF0000
```

### Signal Integration
The Material Manager integrates with several system signals:
- `rebuild_tree`: Updates operations tree after changes
- `default_operations`: Updates status bar operation icons

### Import Processing
- **LightBurn Import**: Parses XML structure, converts parameters
- **EZCAD Import**: Reads INI-style format, maps to MeerK40t operations
- **MeerK40t Import**: Direct configuration file import with validation

### Compensation Algorithms
- **Lens Compensation**: Power scales with lens area ratio (D₁²/D₂²)
- **Power Compensation**: Linear scaling of power settings
- **Safety Limits**: Prevents power settings exceeding 100% (1000 ppi)

### Performance Considerations
- Large libraries may impact loading performance
- Import operations process files sequentially
- Settings validation occurs during save operations

## Related Topics

*Link to related help topics:*

- [[Online Help: Operations]]
- [[Online Help: Laser Panel]]
- [[Online Help: Configuration]]
- [[Online Help: Tree]]

## Screenshots

*Add screenshots showing the material manager interface, library tree, operation preview, and import dialog.*
