# Online Help: Keyhole

## Overview

The **Keyhole** feature creates keyhole operations for layered designs, allowing complex multi-element images to be engraved with precise registration between layers. This technique uses a reference element to create alignment features that ensure perfect positioning of subsequent layers.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t/gui/imagesplitter.py`

## Category

**GUI**

## Description

Keyhole operations are essential for creating multi-layered designs where precise alignment between layers is critical. The keyhole technique creates a reference "keyhole" pattern from one element that serves as an alignment guide for subsequent engraving passes.

This feature is particularly useful for:
- **Multi-layered designs**: Ensuring perfect registration between design layers
- **Complex compositions**: Maintaining alignment in detailed artwork
- **Precision engraving**: Creating alignment features for high-accuracy work
- **Layered effects**: Building up complex images through multiple engraving passes

The keyhole system works by:
1. **Selecting a reference element** (first or last selected)
2. **Generating a keyhole mask** from the reference shape
3. **Creating alignment features** for subsequent layers
4. **Ensuring precise registration** between engraving passes

## How to Use

### Accessing Keyhole Operations

1. **Select Elements**: Choose the elements you want to use for keyhole operations
2. **Open Image Operations**: Click the "Image ops" button or navigate to `Editing → Image Splitting`
3. **Switch to Keyhole Tab**: Select the "Keyhole operation" tab
4. **Configure Settings**: Set DPI, reference element, and options
5. **Generate Keyhole**: Click "Create keyhole image"

### Available Controls

#### Reference Element Selection
- **First Selected**: Uses the first selected element as the keyhole reference
- **Last Selected**: Uses the last selected element as the keyhole reference

#### Image Resolution
- **DPI Setting**: Controls the resolution of the generated keyhole image
- **Typical Values**: 500-1000 DPI depending on detail requirements

#### Keyhole Options
- **Invert Mask**: Inverts the keyhole mask (cuts vs. preserves reference shape)
- **Trace Keyhole**: Adds outline tracing to the keyhole for better visibility

### Basic Usage Workflow

#### Creating a Keyhole Reference

1. **Prepare Design**: Create your multi-layered design with distinct elements
2. **Select Reference**: Choose which element will serve as the alignment reference
3. **Set Parameters**:
   ```
   Reference: First Selected (or Last Selected)
   DPI: 500 (adjust based on detail needs)
   Invert Mask: Unchecked (preserve reference shape)
   Trace Keyhole: Checked (add outline for visibility)
   ```
4. **Generate Keyhole**: Click "Create keyhole image"
5. **Review Output**: Check the generated keyhole pattern in the scene

#### Multi-Layer Engraving Process

1. **Layer 1 (Reference)**: Engrave the keyhole reference element
2. **Registration**: Use the keyhole features to align subsequent layers
3. **Layer 2-N**: Engrave additional layers using keyhole for alignment
4. **Verification**: Check alignment accuracy between layers

### Advanced Usage

#### Optimizing for Different Materials

**Wood/Materials with Texture**:
```
DPI: 300-500
Trace Keyhole: Enabled (better visibility on textured surfaces)
Invert Mask: As needed for contrast
```

**Metal/Reflective Surfaces**:
```
DPI: 500-1000
Trace Keyhole: Enabled (depth perception on smooth surfaces)
Invert Mask: Consider for better contrast
```

#### Complex Multi-Element Designs

For designs with multiple distinct elements:
- Use the **most distinctive shape** as the keyhole reference
- Ensure the reference element has **clear, recognizable features**
- Consider **symmetry** for easier alignment
- Test keyhole generation on **scrap material** first

## Technical Details

### Keyhole Generation Algorithm

The keyhole system creates alignment features by:

1. **Reference Extraction**: Isolates the selected reference element
2. **Mask Generation**: Creates a binary mask from the reference shape
3. **Feature Enhancement**: Adds alignment features and registration marks
4. **Image Processing**: Applies DPI scaling and mask operations

### Mask Operations

#### Normal Mask (Invert Disabled)
- **Reference Shape**: Preserved as engraved area
- **Background**: Not engraved (transparent)
- **Use Case**: Direct engraving of reference element

#### Inverted Mask (Invert Enabled)
- **Reference Shape**: Not engraved (masked out)
- **Background**: Engraved
- **Use Case**: Creating negative space or contrast effects

### Trace Keyhole Feature

When enabled, adds outline tracing:
- **Outline Generation**: Creates vector outline of reference shape
- **Depth Enhancement**: Provides visual depth cues
- **Alignment Aids**: Improves registration accuracy

### Integration with Image Processing

The keyhole system integrates with MeerK40t's image processing pipeline:
- **DPI Scaling**: Maintains resolution consistency
- **Color Management**: Preserves element colors and properties
- **Operation Assignment**: Automatically creates appropriate engraving operations

## Safety Considerations

- **Test First**: Always test keyhole patterns on scrap material
- **Material Compatibility**: Different materials may require different settings
- **Alignment Verification**: Double-check registration between layers
- **Depth Control**: Ensure appropriate engraving depth for visibility

## Troubleshooting

### Keyhole Not Visible

#### Problem: Generated keyhole pattern is too faint
**Solutions**:
- Increase DPI setting for finer detail
- Enable "Trace Keyhole" for better visibility
- Adjust engraving power/depth
- Check material surface preparation

#### Problem: Keyhole features are distorted
**Solutions**:
- Reduce DPI if pixelation occurs
- Check for interference from other design elements
- Verify reference element selection
- Clean material surface

### Alignment Issues

#### Problem: Subsequent layers don't align properly
**Solutions**:
- Use higher contrast keyhole settings
- Ensure consistent material positioning
- Check for material warping during engraving
- Verify laser calibration and focus

#### Problem: Keyhole reference is ambiguous
**Solutions**:
- Choose a more distinctive reference element
- Enable trace outlining for better definition
- Consider using multiple reference points
- Test different invert mask settings

### Performance Issues

#### Problem: Keyhole generation is slow
**Solutions**:
- Reduce DPI setting for faster processing
- Limit selection to essential reference elements
- Close other applications during processing
- Consider system memory limitations

## Related Topics

- [[Online Help: Imagesplit]] - Image splitting for large format engraving
- [[Online Help: Alignment]] - Element alignment and positioning tools
- [[Online Help: Distribute]] - Element distribution and spacing
- [[Online Help: Arrangement]] - Advanced element arrangement options
- [[Online Help: Imageproperty]] - Image processing and property controls

## Screenshots

*Screenshots would show:*
- *Keyhole panel interface with reference element selection*
- *Generated keyhole pattern with trace outlining*
- *Multi-layer design with keyhole alignment features*
- *Before/after comparison of aligned vs. misaligned layers*

---

*This help page is automatically generated. Please update with specific information about the keyhole feature.*
