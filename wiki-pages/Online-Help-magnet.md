# Online Help: Magnet

## Overview

This help page covers the **Magnet** functionality in MeerK40t.

The Magnet system provides interactive guide lines that help you align and position objects precisely during editing operations. Magnet lines act like invisible rulers that objects "snap" to when moved or resized, making it easy to create perfectly aligned designs.

The magnet system consists of two main panels:
- **Actions Panel**: Interactive controls for creating and managing magnet guide lines
- **Options Panel**: Configuration controls for magnet snapping behavior and settings

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\magnetoptions.py` - Main magnet panel implementation
- `meerk40t\gui\wxmscene.py` - Scene pane magnet functionality and console commands

## Category

**GUI**

## Description

The Magnet system provides visual guide lines that objects automatically snap to during editing operations. This helps you:

- Align objects precisely to specific positions
- Create evenly spaced layouts
- Maintain consistent spacing between design elements
- Quickly position objects at edges, centers, or custom divisions

Magnet lines are persistent and can be saved/loaded as named configurations for different types of work.

## How to Use

### Accessing Magnet Controls

The Magnet panel is located in the right docking pane under the "Editing" submenu. It contains two tabs:

### Actions Tab - Creating Magnet Lines

#### Manual Line Creation
- **Position field**: Enter a coordinate value (supports units like mm, inches, etc.)
- **X button**: Creates a vertical magnet line at the entered position
- **Y button**: Creates a horizontal magnet line at the entered position

#### Automatic Line Creation Around Selection
When objects are selected, you can automatically create guide lines:

**Horizontal Lines:**
- **Left**: Creates a vertical line at the left edge of selection
- **Center**: Creates a vertical line at the horizontal center of selection
- **Right**: Creates a vertical line at the right edge of selection
- **3, 4, 5**: Divides the selection into 3rds, 4ths, or 5ths with vertical lines

**Vertical Lines:**
- **Top**: Creates a horizontal line at the top edge of selection
- **Center**: Creates a horizontal line at the vertical center of selection
- **Bottom**: Creates a horizontal line at the bottom edge of selection
- **3, 4, 5**: Divides the selection into 3rds, 4ths, or 5ths with horizontal lines

#### Clearing Magnet Lines
- **Clear All**: Removes all magnet lines from both axes
- **Clear X**: Removes only vertical (X-axis) magnet lines
- **Clear Y**: Removes only horizontal (Y-axis) magnet lines

### Options Tab - Configuring Magnet Behavior

#### Attraction Areas
Choose which parts of objects will snap to magnet lines:
- **Left/Right Side**: Object edges snap to vertical magnet lines
- **Top/Bottom Side**: Object edges snap to horizontal magnet lines
- **Center**: Object centers snap to any magnet line

#### Attraction Strength
Controls how close objects need to be to magnet lines before snapping:
- **Off**: No magnetic attraction
- **Weak**: Very close attraction range
- **Normal**: Standard attraction range
- **Strong**: Extended attraction range
- **Very Strong**: Much larger attraction range
- **Enormous**: Maximum attraction range

#### Save/Load Configurations
- **Template dropdown**: Lists saved magnet configurations
- **Load button**: Applies the selected configuration
- **Save button**: Saves current settings as a new configuration

### Basic Usage Workflow

1. **Set up guides**: Create magnet lines using the Actions tab
2. **Configure snapping**: In Options tab, choose what snaps and how strongly
3. **Edit objects**: Move, resize, or create objects - they'll snap to guides
4. **Save configuration**: Save your guide setup for reuse

### Advanced Usage

#### Precision Layout
1. Select objects to align
2. Use the numbered buttons (3, 4, 5) to create evenly spaced guides
3. Objects will snap to these divisions when moved

#### Template Workflows
1. Set up guides for a specific job type (business cards, signs, etc.)
2. Save the configuration with a descriptive name
3. Load it quickly for similar jobs

## Technical Details

### Magnet Line Storage
Magnet lines are stored in a text file (`magnet_lines.txt`) in the user's MeerK40t configuration directory. The file format includes:
- Attraction strength setting
- X-axis magnet line positions
- Y-axis magnet line positions

### Signal Integration
The magnet system integrates with several signals:
- `refresh_scene`: Updates scene display when magnets change
- `emphasized`: Enables/disables selection-based actions
- `magnet_options`: Updates UI when settings change externally

### Console Commands
Magnet lines can also be managed via console commands:

```
magnet clear x          # Clear all vertical magnet lines
magnet clear y          # Clear all horizontal magnet lines
magnet set x <position> # Add vertical line at position
magnet set y <position> # Add horizontal line at position
magnet delete x <position> # Remove vertical line at position
magnet delete y <position> # Remove horizontal line at position
magnet split x <count>  # Create <count> vertical lines across selection
magnet split y <count>  # Create <count> horizontal lines across selection
```

### Performance Considerations
- Magnet attraction calculations are performed during object manipulation
- Large numbers of magnet lines may impact editing performance
- Attraction strength affects calculation frequency

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]
- [[Online Help: Scene]]

## Screenshots

### Magnet Actions Tab
The Actions tab displays the main magnet line creation controls:
- **Manual Creation**: Position input field with X and Y buttons for creating individual guide lines
- **Selection-Based Guides**: Left/Center/Right buttons for vertical lines, Top/Center/Bottom buttons for horizontal lines
- **Division Controls**: Numbered buttons (3, 4, 5) for creating evenly spaced divisions across the selection
- **Clear Options**: Clear All, Clear X, and Clear Y buttons for removing magnet lines

### Magnet Options Tab
The Options tab shows configuration settings:
- **Attraction Areas**: Checkboxes for Left/Right Side, Top/Bottom Side, and Center snapping options
- **Attraction Strength**: Radio button selection from Off to Enormous strength levels
- **Configuration Management**: Template dropdown with Load and Save buttons for storing magnet setups

### Magnet Lines in Scene View
The main scene view displays active magnet lines as visual guides:
- **Vertical Lines**: Blue vertical lines at specified X positions
- **Horizontal Lines**: Blue horizontal lines at specified Y positions
- **Object Snapping**: Shows objects automatically aligning to nearby magnet lines during movement
- **Selection Highlighting**: Selected objects with visible snap points (corners, centers, edges)

### Advanced Magnet Configurations
- **Precision Layout**: Shows numbered division lines (3rds, 4ths, 5ths) across a selected area
- **Template Application**: Demonstrates loading a saved magnet configuration for consistent layouts
- **Multi-Object Alignment**: Illustrates how multiple objects snap to the same guide lines simultaneously
