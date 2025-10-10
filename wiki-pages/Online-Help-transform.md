# Online Help: Transform

## Overview

This help page covers the **Transform** functionality in MeerK40t.

The Transform panel provides comprehensive control over design element transformations, allowing you to scale, rotate, skew, and reposition selected elements using both interactive buttons and direct matrix editing.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Transform panel enables precise manipulation of selected design elements through affine transformations. It provides both intuitive button controls for common operations and direct matrix editing for advanced users. Transformations are applied to all currently emphasized (selected) elements in the scene.

The panel consists of two main sections:
- **Button Controls**: A 3x3 grid of buttons for quick scaling, rotation, translation, and reset operations
- **Matrix Editor**: Direct input fields for precise control over transformation matrix values

## How to Use

### Available Controls

- **Scale Down/Up Buttons**: Reduce or increase element size by 5% (left-click) or 50% (right-click)
- **Rotate CCW/CW Buttons**: Rotate elements counterclockwise/clockwise by 5° (left-click) or 90° (right-click)
- **Translate Arrows**: Move elements in cardinal directions by jog distance (left-click) or 10x jog distance (right-click)
- **Reset Button**: Restore elements to their original transformation matrix
- **Scale X/Y Fields**: Direct scaling factors for horizontal/vertical dimensions
- **Skew X/Y Fields**: Shear transformation values (entered as angles or tan values)
- **Translate X/Y Fields**: Direct position offsets in real distance units

### Key Features

- Integrates with: `wxpane/Navigation`, `refresh_scene`, `emphasized`, `modified`, `button-repeat`
- Real-time matrix value updates from selected elements
- Support for percentage, angle, and distance input formats
- Timer-based continuous operation with acceleration
- Only enabled when elements are selected

### Basic Usage

1. **Select Elements**: Choose the design elements you want to transform in the main scene
2. **Apply Quick Transformations**: Use the button grid for common operations like scaling or rotation
3. **Fine-tune with Matrix Editor**: Enter precise values in the matrix fields for exact control
4. **Reset if Needed**: Use the reset button to restore original transformations

### Advanced Usage

#### Direct Matrix Editing
The transformation matrix follows SVG standards with six parameters:
- **Scale X (a)**: Horizontal scaling factor (1.0 = 100%, 2.0 = 200%)
- **Skew Y (b)**: Vertical shear (entered as angle, converted to tan value)
- **Skew X (c)**: Horizontal shear (entered as angle, converted to tan value)
- **Scale Y (d)**: Vertical scaling factor (1.0 = 100%, 2.0 = 200%)
- **Translate X (e)**: Horizontal position offset in current units
- **Translate Y (f)**: Vertical position offset in current units

#### Input Format Flexibility
- **Scaling**: Enter as decimal (1.5) or percentage (150%)
- **Skew**: Enter as angle (15deg) or tangent value (0.2679)
- **Translation**: Enter in any supported distance unit (10mm, 0.5in, 2cm)

#### Continuous Operations
Left-click buttons for single operations, right-click for larger transformations. Buttons support continuous operation when held down, with acceleration based on button repeat settings.

## Technical Details

Provides transformation controls for scaling, rotating, and positioning design elements. Features label controls for user interaction. Integrates with wxpane/Navigation, refresh_scene for enhanced functionality.

The Transform panel implements SVG-compliant affine transformations using a 3x3 transformation matrix. All operations are applied relative to the element's current transformation state, allowing for cumulative transformations.

Key technical components:
- **Affine Transformations**: Full support for scale, rotate, skew, and translate operations
- **Matrix Validation**: Input validation with automatic unit conversion and error handling
- **Real-time Updates**: Live synchronization with scene selection and element modifications
- **Signal Integration**: Responds to emphasis changes, modifications, and scene refresh events
- **Timer Controls**: Implements continuous operation with configurable acceleration

### Transformation Matrix Format
The panel uses the standard SVG transformation matrix format:
```
[ a c e ]
[ b d f ]
[ 0 0 1 ]
```

Where:
- a = Scale X, c = Skew X, e = Translate X
- b = Skew Y, d = Scale Y, f = Translate Y

### Unit Conversion
Translation values are automatically converted between internal units (mils) and user-preferred units (mm, inches, etc.) for display and input.

## Safety Considerations

- **Selection Required**: Transform controls are disabled when no elements are selected
- **Cumulative Effects**: Transformations are applied on top of existing transformations
- **Precision Loss**: Multiple operations may introduce minor rounding errors
- **Reset Available**: Use the reset button to restore original state if needed

## Troubleshooting

### Controls Disabled
- Ensure elements are selected in the main scene
- Check that the Navigation panel is active and visible

### Unexpected Transformations
- Verify matrix values are entered correctly
- Check unit settings for translation values
- Use reset button to restore original state

### Performance Issues
- Large selections may cause slower updates
- Complex transformations can impact rendering performance
- Consider applying transformations in smaller batches

## Related Topics

- [[Online Help: Jog]] - Manual laser positioning controls
- [[Online Help: Move]] - Coordinate-based positioning
- [[Online Help: Navigation]] - Complete navigation control suite
- [[Online Help: Tree]] - Element hierarchy management

## Screenshots

*Screenshots showing the transform panel with button controls and matrix editor would be helpful here, demonstrating both basic button operations and advanced matrix editing.*

---

*This help page provides comprehensive documentation for the transform functionality, covering both intuitive button controls and advanced matrix manipulation for precise element transformations.*
