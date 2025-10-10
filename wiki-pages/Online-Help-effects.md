# Online Help: Effects

## Overview

This help page covers the **Effects** functionality in MeerK40t.

The Effects panel provides configuration settings for default parameters used by laser cutting effects such as hatching and wobbling patterns. These settings establish the baseline values that will be applied when creating new effect operations.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\device\gui\effectspanel.py`

## Category

**GUI**

## Description

The Effects panel serves as a central configuration hub for laser effect parameters in MeerK40t. It allows users to set default values for various effect types that will be automatically applied when creating new operations. This ensures consistency across projects and saves time by eliminating the need to manually configure common settings for each new effect.

The panel is organized into two main effect categories:

### Hatch Effects
Hatch effects create fill patterns by drawing parallel lines across shapes. The panel configures:
- **Hatch Distance**: Default spacing between hatch lines
- **Hatch Angle**: Default angle for hatch line orientation
- **Hatch Angle Delta**: Default angle variation for multi-pass hatching

### Wobble Effects
Wobble effects apply oscillating distortions along cut paths to create textured or decorative patterns. The panel configures:
- **Wobble Type**: Default pattern style (circle, sine wave, etc.)
- **Wobble Speed**: Default rotation speed of the wobble pattern
- **Wobble Radius**: Default amplitude/size of the wobble distortion
- **Wobble Interval**: Default spacing between wobble pattern repetitions

Users would access this panel when they want to customize the default behavior of laser effects across their projects, ensuring that newly created effects start with their preferred settings rather than generic defaults.

## How to Use

### Basic Usage

1. **Access the Panel**: Open the Effects panel from the device configuration area
2. **Configure Hatch Defaults**: Set your preferred hatch distance, angle, and angle delta values
3. **Configure Wobble Defaults**: Choose your default wobble type, speed, radius, and interval
4. **Apply Settings**: The new defaults will be used for all subsequently created effects

### Available Controls

- **Hatch Distance**: Text field for setting default spacing between hatch lines (accepts length units like mm, inches)
- **Hatch Angle**: Text field for default hatch line angle (accepts angle units like deg, rad)
- **Hatch Angle Delta**: Text field for default angle variation between hatch passes
- **Wobble Type**: Dropdown selection for default wobble pattern type
- **Wobble Speed**: Numeric field for default wobble rotation speed
- **Wobble Radius**: Text field for default wobble distortion amplitude
- **Wobble Interval**: Text field for default spacing between wobble repetitions

## Technical Details

The Effects panel uses MeerK40t's settings system to store default values that are applied when creating new effect nodes. The settings are stored with keys like:

- `effect_hatch_default_distance`
- `effect_hatch_default_angle`
- `effect_hatch_default_angle_delta`
- `effect_wobble_default_type`
- `effect_wobble_default_speed`
- `effect_wobble_default_radius`
- `effect_wobble_default_interval`

These settings integrate with the ChoicePropertyPanel system, which provides validation and user-friendly input controls for different data types (lengths, angles, numeric values, etc.). The panel dynamically loads available wobble types by querying the plugin system with `context.match("wobble", suffix=True)`.

When users create new hatch or wobble effects through other panels (like the Hatch Property Panel or Wobble Property Panel), these default values serve as the initial configuration, which users can then modify for specific operations.

## Related Topics

*Link to related help topics:*

- [[Online Help: Hatches]] - Detailed hatch pattern configuration
- [[Online Help: Wobbles]] - Detailed wobble effect configuration
- [[Online Help: Defaultactions]] - Other default operation settings
- [[Online Help: Formatter]] - Output formatting options

## Screenshots

*Add screenshots showing the Effects panel with hatch and wobble default settings.*

---

*This help page is automatically generated. Please update with specific information about the effects feature.*
