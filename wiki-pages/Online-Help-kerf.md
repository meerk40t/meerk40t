# Online Help: Kerf

## Overview

The **Kerf** tool generates test patterns to help determine the correct kerf compensation value for your laser cutter. Kerf compensation accounts for the width of material removed by the laser beam, ensuring that cut parts have precise dimensions.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t/tools/kerftest.py`

## Category

**Tools**

## Description

Kerf compensation is essential for precision laser cutting. When a laser cuts through material, it removes a small width of material (the kerf). Without compensation, cut parts will be smaller than intended.

The Kerf tool creates test patterns that allow you to:
- **Measure actual kerf width** of your laser setup
- **Determine compensation values** for different materials
- **Create calibration patterns** for quality control
- **Test different laser settings** (speed, power, focus)

Three pattern types are available:
- **Rectangular (Box Joints)**: Traditional kerf measurement with interlocking pieces
- **Circular (Inlays)**: Concentric circle patterns for precise measurement
- **Slider**: Linear sliding scale for easy kerf determination

## How to Use

### Accessing the Kerf Tool

1. **Open Kerf Tool**: Navigate to `Laser-Tools → Kerf-Test` in the menu
2. **Configure Settings**: Set laser parameters and test range
3. **Generate Pattern**: Click "Create Pattern" to generate test shapes
4. **Cut Test Pieces**: Burn the pattern on your material
5. **Measure Results**: Determine the correct kerf compensation value

### Available Controls

#### Laser Operation Settings
- **Speed**: Cutting speed (mm/s or mm/min based on display preference)
- **Power**: Laser power (percentage or PPI based on display preference)

#### Pattern Parameters
- **Pattern Type**: Rectangular, Circular, or Slider pattern selection
- **Count**: Number of test pieces to generate (1-100)
- **Minimum**: Starting kerf value for testing
- **Maximum**: Ending kerf value for testing
- **Size**: Dimensions of each test pattern
- **Delta**: Spacing between test patterns

### Basic Usage Workflow

#### Step 1: Configure Laser Settings
```
Speed: Set your typical cutting speed
Power: Set appropriate power for clean cuts
```

#### Step 2: Define Test Range
```
Minimum: 0.05mm (typical starting point)
Maximum: 0.25mm (typical ending range)
Count: 5-10 test pieces
Size: 20mm (comfortable working size)
Delta: 5mm (adequate spacing)
```

#### Step 3: Generate and Cut Pattern
1. Click **"Create Pattern"**
2. Confirm clearing existing elements (if any)
3. Execute the job on your laser
4. Carefully cut out all test pieces

#### Step 4: Determine Kerf Value

##### For Rectangular/Circular Patterns:
1. Test-fit pieces with matching labels together
2. Find the pair that fits perfectly (no gaps, no overlap)
3. Use the kerf value from that pair's label

##### For Slider Pattern:
1. Burn and cut out the entire slider assembly
2. Push all cut pieces firmly to the left
3. Read the kerf compensation value where the right edge of the last piece aligns with the scale

### Advanced Usage

#### Material-Specific Testing
Different materials require different kerf compensation:
- **Wood**: 0.1-0.2mm typical range
- **Acrylic**: 0.05-0.15mm typical range
- **Cardboard**: 0.15-0.3mm typical range

#### Speed and Power Optimization
Test kerf at different settings to find optimal combinations:
- **Higher speed**: May increase kerf width
- **Lower power**: May decrease kerf width
- **Focus adjustment**: Affects kerf consistency

#### Precision Measurement
For critical applications:
- Use digital calipers for precise measurement
- Test multiple times for consistency
- Consider environmental factors (humidity, temperature)

## Technical Details

### Kerf Compensation Theory
When laser cutting, the beam removes material in a path of finite width. Without compensation, the resulting part is smaller than the design by half the kerf width on each side.

**Formula**: Actual dimension = Design dimension - Kerf width

### Pattern Generation Algorithm

#### Rectangular Patterns
Creates pairs of interlocking box joint pieces with progressively increasing kerf compensation values. Each pair consists of:
- **Outer piece**: Positive kerf compensation (+kerf/2 on each side)
- **Inner piece**: Negative kerf compensation (-kerf/2 on each side)

#### Circular Patterns
Generates concentric circles where:
- **Outer circle**: Cut with positive kerf compensation
- **Inner circle**: Cut with negative kerf compensation
- Perfect fit indicates correct kerf value

#### Slider Pattern
Creates a linear sliding scale with:
- **Marked scale**: Engraved measurement markings
- **Cut pieces**: Progressive kerf compensation values
- **Sliding mechanism**: Allows direct reading of compensation value

### Color Coding
Test patterns use color coding for easy identification:
- **Red operations**: Outer cuts (positive kerf)
- **Green operations**: Inner cuts (negative kerf)
- **Blue operations**: Measurement engravings
- **Black operations**: Text labels

### Validation and Safety
The tool includes input validation:
- **Range checking**: Ensures valid parameter ranges
- **Unit conversion**: Handles different measurement units
- **Safety confirmation**: Warns before clearing existing work

## Safety Considerations

- **Material Selection**: Use scrap material for testing
- **Ventilation**: Ensure proper ventilation when cutting
- **Eye Protection**: Wear appropriate laser safety glasses
- **Fire Prevention**: Have fire extinguishing equipment ready
- **Test Multiple Times**: Verify kerf values are consistent

## Troubleshooting

### Patterns Don't Fit Properly

#### Too Loose (Undercut)
**Problem**: Test pieces fit too loosely
**Solutions**:
- Increase kerf compensation values
- Check for material warping during cutting
- Verify laser focus and alignment

#### Too Tight (Overcut)
**Problem**: Test pieces won't fit together
**Solutions**:
- Decrease kerf compensation values
- Check for material thickness variations
- Verify cutting speed and power settings

### Inconsistent Results

#### Variable Kerf Width
**Problem**: Different kerf values across test range
**Solutions**:
- Check laser beam consistency
- Verify material uniformity
- Test different speed/power combinations
- Check for lens contamination

#### Measurement Errors
**Problem**: Difficulty determining correct fit
**Solutions**:
- Use magnification for precise fitting
- Clean cut edges before testing
- Use digital measurement tools
- Test with multiple material samples

### Pattern Generation Issues

#### Invalid Parameters
**Problem**: "Create Pattern" button disabled
**Solutions**:
- Check all parameter fields are filled
- Verify numeric values are within valid ranges
- Ensure minimum < maximum for multi-piece patterns

#### Display Issues
**Problem**: Patterns don't display correctly
**Solutions**:
- Check scene refresh after pattern generation
- Verify sufficient workspace area
- Clear existing elements if needed

## Related Topics

- [Online Help: Hinges](Online-Help-hinges) - Related precision cutting tools
- [Online Help: K40Controller](Online-Help-k40controller) - Laser controller configuration
- [Online Help: K40Operation](Online-Help-k40operation) - Operation-specific settings
- [Online Help: Operationproperty](Online-Help-operationproperty) - Operation parameter configuration
- [Online Help: Speed and Power](Online-Help-speedandpower) - Basic speed and power settings

## Screenshots

*Screenshots would show:*
- *Kerf tool interface with parameter controls*
- *Generated rectangular test pattern with labeled pieces*
- *Circular inlay test pattern*
- *Slider pattern with measurement scale*
- *Example of fitted test pieces showing correct kerf compensation*

---

*This help page is automatically generated. Please update with specific information about the kerf feature.*
