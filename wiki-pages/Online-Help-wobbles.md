# Online Help: Wobbles

## Overview

This help page covers the **Wobbles** functionality in MeerK40t.

The Wobble effect applies oscillating distortions along vector paths, creating dynamic movement patterns that add visual interest and texture to laser-cut designs. This effect transforms straight or curved paths into wavy, oscillating patterns that can simulate natural movement, create decorative borders, or add artistic flair to designs.

- Element ID management and identification
- Auto-hide controls for visibility management
- Stroke color selection with classification callbacks
- Wobble radius control for distortion amplitude
- Wobble interval setting for pattern spacing along path
- Wobble speed control for rotation rate around path
- Fill style selection from available wobble pattern plugins
- Auto-classification toggle for color changes

## Location in MeerK40t

This help section is accessed from:
- `meerk40t/gui/propertypanels/wobbleproperty.py`
- `meerk40t/core/node/effect_wobble.py`
- `meerk40t/fill/fills.py`

## Category

**Effects**

## Description

The Wobble effect creates oscillating distortions along vector paths by applying mathematical transformations that displace points perpendicular to the path direction. This creates dynamic, wavy patterns that can range from subtle ripples to dramatic oscillations.

**Key Features:**
- **Multiple Pattern Types**: Choose from 12 different wobble patterns including circles, sine waves, sawtooth waves, gears, and meanders
- **Configurable Parameters**: Control distortion amplitude (radius), pattern spacing (interval), and rotation speed
- **Real-time Preview**: See effects immediately in the design view
- **Path-based Processing**: Works on any vector geometry including lines, curves, and complex shapes
- **Color Integration**: Automatically inherits stroke colors from parent operations

**Common Use Cases:**

- Creating decorative borders and frames
- Adding texture to text and logos
- Simulating natural movement (water, wind, fabric)
- Artistic effects for invitations and decorative pieces
- Adding visual interest to geometric patterns

## How to Use

### Basic Usage

1. **Select Elements**: Choose the vector elements you want to apply the wobble effect to
2. **Apply Wobble Effect**: Right-click on the selected elements and choose "Effects" → "Wobble" from the context menu, or use the toolbar button
3. **Configure Parameters**:
   - Set the **Wobble Radius** to control distortion amplitude (e.g., "1.5mm")
   - Adjust the **Wobble Interval** for pattern spacing along the path (e.g., "0.1mm")
   - Set the **Wobble Speed** to control how quickly the pattern rotates (default: 50)
   - Choose a **Fill Style** from the available wobble patterns
4. **Preview and Adjust**: Use the preview function to see the effect before finalizing
5. **Apply to Operations**: The wobble effect will be processed during laser cutting

### Advanced Configuration

**Parameter Details:**
- **Radius**: Controls the amplitude of the wobble distortion. Larger values create more dramatic oscillations
- **Interval**: Determines how frequently the wobble pattern repeats along the path. Smaller intervals create denser patterns
- **Speed**: Controls the rotational speed of circular patterns. Higher values create tighter spirals
- **Pattern Types**: Each pattern creates different visual effects:
  - `circle`: Smooth circular oscillations
  - `circle_left`/`circle_right`: Directional circular patterns
  - `sinewave`: Smooth sinusoidal waves
  - `sawtooth`: Sharp, angular oscillations
  - `jigsaw`: Interlocking puzzle-piece pattern
  - `gear`: Mechanical gear-tooth pattern
  - `slowtooth`: Gradual angular transitions
  - `meander_1/2/3`: Complex wandering patterns
  - `dash`: Dashed line effect
  - `tabs`: Tabbed connection pattern

### Tips and Best Practices

- Start with small radius values (0.5-1.5mm) and gradually increase for dramatic effects
- Use interval values that are 1/10th to 1/5th of your radius for smooth patterns
- Test patterns on scrap material before cutting final designs
- Combine wobble effects with other effects like warps for complex distortions
- Use slower speeds for detailed work, faster speeds for bold patterns

## Technical Details

The wobble effect works by sampling points along the original path at regular intervals and displacing them perpendicular to the path direction using mathematical functions. The displacement follows the selected pattern type and is modulated by the speed parameter.

**Algorithm Overview:**
1. **Path Sampling**: The original geometry is converted to a sequence of line segments
2. **Point Generation**: Points are generated along the path at intervals specified by the wobble_interval parameter
3. **Displacement Calculation**: Each point is displaced by the wobble_radius amount using the selected pattern function
4. **Pattern Application**: The displacement follows mathematical functions (sine waves, circles, etc.) modulated by the speed parameter
5. **Geometry Reconstruction**: The displaced points are connected to form the final wobble path

**Supported Pattern Types:**
- `circle`: Standard circular oscillation using cos/sin functions
- `circle_left`/`circle_right`: Directional circular patterns with phase offsets
- `sinewave`: Pure sinusoidal displacement
- `sawtooth`: Linear ramp functions creating sharp transitions
- `jigsaw`: Alternating positive/negative displacements
- `gear`: Square wave patterns simulating gear teeth
- `slowtooth`: Gradual transitions between displacement states
- `meander_1/2/3`: Complex multi-frequency patterns
- `dash`: Binary on/off displacement patterns
- `tabs`: Alternating displacement for connection features

**Performance Considerations:**
- Smaller interval values increase processing time and file size
- Complex patterns (meanders) require more computational resources
- Effects are calculated once and cached until parameters change

**Signal Integration:**
- None directly (relies on callback mechanisms for property updates)
- Integrates with the element tree notification system for real-time updates
- Supports auto-hide functionality for effect management

**File Format Integration:**
- Effects are stored as part of the project file
- Parameters are preserved in effect descriptors for sharing and reuse
- Compatible with all supported vector formats (SVG, DXF, etc.)

## Related Topics

*Link to related help topics:*

- [[Online Help: Effects]] - Overview of all effect types
- [[Online Help: Warp]] - Perspective distortion effects
- [[Online Help: Hatches]] - Fill pattern effects
- [[Online Help: Path Property]] - Path manipulation tools
- [[Online Help: Operation Property]] - Operation configuration

## Screenshots

*Add screenshots showing the wobble property panel and example effects.*

---

*This help page provides comprehensive documentation for the wobble effect system in MeerK40t.*
