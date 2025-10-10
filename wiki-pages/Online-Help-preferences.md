# Online Help: Preferences

## Overview

This help page covers the **Preferences** functionality in MeerK40t.

This panel provides controls for preferencesmain functionality. Key controls include "Save" (button), "Export" (button), "Import" (button).

## General
<img width="212" alt="image" src="https://github.com/meerk40t/meerk40t/assets/2670784/d80e2433-014a-4322-9362-82097fb390cb">

- Units: Define the standard units for MeerK40t to use (imperial/metric)
- Language: Sets the user interface language
### Input/Output
- SVG Pixel: Select the Pixels Per Inch to use when loading an SVG file
- SVG Viewport is bed: SVG files can be saved without real physical units. This setting uses the SVG viewport dimensions to scale the rest of the elements in the file.
- Image DPI Scaling:
  - Unset: Use the image as if it were 1000 pixels per inch.
  - Set: Use the DPI setting saved in the image to scale the image to the correct size.
- Create a file-node for imported image:
  - Unset: Attach the image directly to elements.
  - Set: Put the image under a file-node created for it.
- DXF Center and Fit: Fit (scale down if necessary) and center a DXF file within the bed
- Inkscape-path: Path to inkscape-executable. Leave empty to let Meerk40t establish standard locations.
- Unsupported elements: MeerK40ts standard to load / save data is the svg-Format (supported by many tools like [Inkscape](https://inkscape.org/)). While it is supporting most of SVG functionalities, there are still some unsupported features (most notably advanced text effect, clips and gradients).
To overcome that limitation MeerK40t can automatically convert these features with the help of inkscape:
if you set the 'Unsupported feature' option you can either ask at load time how to proceed or let inkscape perform the conversion automatically. Please note that this conversion might not really needed most of the times, so the recommendation is to use the 'Ask at load time' option.

![image](https://github.com/meerk40t/meerk40t/assets/2670784/741b4d31-2169-4dc7-93cc-818ed55e3eba)
- Save: MeerK40t will save the settings at the end of the session when shutting down, you can immediately save the settings to disk with this button
- Export: Export the current settings to a different location (create a backup of your config) - highly recommended
- Import: Import a previously saved setting file

## Classification
see: [Classification](https://github.com/meerk40t/meerk40t/wiki/Online-Help:-CLASSIFICATION)

## GUI
This section allows to influence the look and feel of the user interface.

![image](https://github.com/meerk40t/meerk40t/assets/2670784/39f6a942-6bd3-4864-8ace-34434dbbd8fe)

### Appearance
- Icon size:
- Mini icon in tree:
- Color entries in tree:
  - Active: the complete node in the tree will be displayed according to the elements color: <img height="30" src="https://github.com/meerk40t/meerk40t/assets/2670784/e0a6ce7e-4f93-4867-8349-7ff2ad0fc2a2">
  - Inactive: Standard colors are used: <img height="30" src="https://github.com/meerk40t/meerk40t/assets/2670784/1f889f04-a6c2-4a5c-bfad-f481af2e5f7d">


- Show the ribbon labels:
  - Active: Show the labels for ribbonbar.
  - Inactive: Hide the ribbon labels.

### General

### Misc

### Zoom

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\preferences.py`
- `meerk40t\gui\preferences.py`

## Category

**GUI**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Save** (Button)
- **Export** (Button)
- **Import** (Button)
- **Save** (Button)
- **Export** (Button)
- **Import** (Button)

### Key Features

- Integrates with: `restart`
- Integrates with: `theme`
- Integrates with: `preferences`

### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

## Technical Details

Provides user interface controls for preferencesmain functionality. Features button controls for user interaction. Integrates with restart, theme for enhanced functionality.

*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the preferences feature.*
