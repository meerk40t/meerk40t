# SefroCut Cylinder Correction Module

## Overview

The Cylinder Correction Module provides specialized functionality for engraving cylindrical objects using galvo laser systems. When engraving on curved surfaces, the laser beam must be mathematically corrected to account for the cylinder's curvature, ensuring that straight lines remain straight and circles remain circular on the final engraved result.

## Physics and Mathematics

### The Problem
When engraving flat designs onto cylindrical surfaces, the laser beam follows straight lines in 3D space, but the surface curves. This causes:

- **Straight lines to appear curved** on the cylinder
- **Circles to become distorted ellipses**
- **Parallel lines to converge or diverge**
- **Text to appear stretched or compressed**

### The Solution
Cylinder correction mathematically transforms the engraving pattern to compensate for the surface curvature:

```
Flat Design → Cylinder Correction → Corrected Pattern → Laser Engraving → Straight Result
```

### Mathematical Principles

#### Coordinate Transformation
For a cylinder along the Y-axis with radius R:

```
Input coordinates: (x, y) on flat plane
Cylinder coordinates: (θ, z) on cylinder surface

Transformation:
θ = x / R          (angle around cylinder)
z = y              (height along cylinder)
```

#### Laser Path Correction
The laser must follow a helical path that appears straight on the cylinder:

```
Laser position: (R × cos(θ), z, R × sin(θ))
Where θ varies with x-coordinate and z varies with y-coordinate
```

## Architecture

```
sefrocut/cylinder/
├── cylinder.py              # Core cylinder correction service
├── gui/
│   ├── gui.py              # GUI plugin registration
│   ├── cylindersettings.py # Settings panel implementation
│   └── __init__.py         # GUI module initialization
├── __init__.py             # Module initialization
└── README.md               # This documentation
```

### Core Components

- **CylinderCorrection Service**: Main correction logic and parameter management
- **CylinderSettings GUI**: wxPython-based configuration interface
- **Device Integration**: Hooks into galvo device drivers for coordinate transformation

## Key Features

### Axis Selection
- **X-Axis Cylinder**: Cylinder rotates along the X-axis (height varies with Y)
- **Y-Axis Cylinder**: Cylinder rotates along the Y-axis (height varies with X)
- **Independent Control**: Each axis can be configured separately

### Parameter Configuration
- **Mirror Distance**: Distance from laser mirror to cylinder surface
- **Cylinder Diameter**: Diameter of the object being engraved
- **Active/Inactive**: Enable/disable correction for specific jobs

### Real-time Updates
- **Dynamic Recalculation**: Parameters update engraving paths in real-time
- **Device Synchronization**: Automatic driver validation on parameter changes
- **Signal Integration**: Responds to device and view changes

## Configuration Parameters

### Basic Settings
```python
cylinder_active: bool = False          # Enable/disable cylinder correction
cylinder_mirror_distance: Length = "100mm"  # Mirror to cylinder distance
```

### X-Axis Configuration
```python
cylinder_x_axis: bool = False          # Enable X-axis cylinder mode
cylinder_x_diameter: Length = "50mm"   # Cylinder diameter for X-axis
cylinder_x_concave: bool = False       # Concave vs convex (reserved for future)
```

### Y-Axis Configuration
```python
cylinder_y_axis: bool = False          # Enable Y-axis cylinder mode
cylinder_y_diameter: Length = "50mm"   # Cylinder diameter for Y-axis
cylinder_y_concave: bool = False       # Concave vs convex (reserved for future)
```

## Console Commands

### Basic Commands
```bash
# Check cylinder status
cylinder

# Enable cylinder correction
cylinder on

# Disable cylinder correction
cylinder off
```

### Configuration Commands
```bash
# Set mirror distance
cylinder distance 150mm

# Configure X-axis cylinder
cylinder axis X 75mm

# Configure Y-axis cylinder
cylinder axis Y 100mm
```

### Status Output
```
Cylinder mode is not active, use 'cylinder on' or 'cylinder axis X <object diameter>' to activate it

Distance from mirror to object: 100.0
Cylinder Mode X: on, object diameter: 50.0, concave: off.
Cylinder Mode Y: off, object diameter: 50.0, concave: off.
Notabene: Updates occur only when toggled off and on. Concave is unused.
```

## GUI Interface

### Cylinder Settings Window
The module provides a dedicated settings window accessible via:
- **Device Menu**: Device Settings → Cylinder-Correction
- **Toolbar Button**: Cylinder button with barrel distortion icon
- **Console Command**: `window toggle Cylinder`

### Settings Panel Features
- **Organized Sections**: Parameters grouped by axis (X/Y) and distances
- **Conditional Display**: Settings appear/disappear based on selections
- **Real-time Updates**: Changes reflected immediately in device driver
- **Validation**: Input validation with unit conversion

### Visual Indicators
- **Barrel Distortion Icon**: Represents the correction transformation
- **Status Integration**: Settings panel updates with device signals
- **Tabbed Interface**: Integrated into SefroCut's window management

## Integration with Device Drivers

### Galvo Device Support
Cylinder correction specifically targets galvo laser systems:
- **Balor Devices**: Primary target with full correction support
- **Galvo Systems**: Any galvo device with coordinate transformation capability

### Driver Interface
```python
class GalvoDriver:
    def cylinder_validate(self):
        """Validate and apply cylinder correction parameters"""
        # Transform coordinates based on cylinder settings
        # Update internal correction matrices
        # Apply to subsequent engraving operations
```

### Signal Integration
The module responds to device signals:
- **cylinder_active**: Enable/disable correction mode
- **cylinder_update**: Trigger parameter validation
- **view;realized**: Apply correction on view realization

## Usage Examples

### Basic Cylinder Engraving
```bash
# Configure for a 50mm diameter cylinder along X-axis
cylinder axis X 50mm

# Set mirror distance
cylinder distance 120mm

# Enable correction
cylinder on

# Engrave design - correction automatically applied
engrave mydesign.svg
```

### Complex Multi-Axis Setup
```bash
# Configure both axes for complex cylindrical object
cylinder axis X 60mm
cylinder axis Y 40mm
cylinder distance 100mm
cylinder on

# The system will apply appropriate corrections for each axis
```

### Batch Processing
```bash
# Enable cylinder correction for batch jobs
cylinder axis X 75mm
cylinder on

# Process multiple files with consistent correction
engrave batch1.svg
engrave batch2.svg
engrave batch3.svg
```

## Technical Implementation

### Coordinate Transformation Algorithm
```python
def cylinder_transform(x, y, diameter, mirror_distance):
    """
    Transform flat coordinates to cylinder-corrected coordinates

    Args:
        x, y: Flat design coordinates
        diameter: Cylinder diameter
        mirror_distance: Mirror to cylinder distance

    Returns:
        corrected_x, corrected_y: Transformed coordinates
    """
    radius = diameter / 2.0
    angle = x / radius  # Convert linear to angular

    # Apply cylinder correction
    corrected_x = mirror_distance * math.tan(angle)
    corrected_y = y

    return corrected_x, corrected_y
```

### Real-time Parameter Updates
```python
@signal_listener("cylinder_x_diameter")
def on_diameter_change(self, origin, *args):
    """Update correction when diameter changes"""
    self.validate_cylinder_parameters()
    self.update_device_driver()
    self.signal_update_to_gui()
```

### Memory Management
- **Lightweight Service**: Minimal memory footprint
- **Parameter Caching**: Settings cached for performance
- **Lazy Validation**: Corrections calculated only when needed
- **Reference Management**: Proper cleanup on service detachment

## Limitations and Considerations

### Hardware Requirements
- **Galvo Systems Only**: Designed specifically for galvo lasers
- **Coordinate Transformation**: Requires driver support for coordinate mapping
- **Real-time Capability**: Needs sufficient processing power for real-time correction

### Current Limitations
- **Concave Support**: Reserved for future implementation
- **Complex Geometries**: Limited to simple cylindrical shapes
- **Multi-cylinder**: Single cylinder configuration per device

### Performance Impact
- **Minimal Overhead**: Correction calculations are lightweight
- **Real-time Processing**: Applied during engraving without significant delay
- **Memory Efficient**: Small parameter set with efficient storage

## Troubleshooting

### Common Issues

#### Correction Not Applying
```bash
# Check if cylinder mode is active
cylinder

# Ensure proper axis configuration
cylinder axis X 50mm

# Verify device driver support
device list
```

#### Unexpected Results
```bash
# Check mirror distance setting
cylinder distance

# Validate diameter measurements
cylinder axis X <measured_diameter>

# Toggle correction off/on to refresh
cylinder off
cylinder on
```

#### GUI Not Updating
- **Signal Issues**: Restart SefroCut to refresh signal connections
- **Driver Problems**: Check device driver cylinder support
- **Parameter Validation**: Ensure all required parameters are set

### Diagnostic Commands
```bash
# Full status check
cylinder

# Device driver validation
device driver cylinder_validate

# Signal debugging
signal list | grep cylinder
```

## Future Enhancements

### Planned Features
- **Concave Cylinder Support**: Full implementation of concave surface correction
- **Complex Geometries**: Support for conical, spherical, and custom shapes
- **Multi-cylinder**: Multiple cylinders in single setup
- **Automatic Calibration**: Laser-based measurement of cylinder parameters
- **3D Preview**: Visual preview of corrected engraving patterns

### Advanced Corrections
- **Material Compensation**: Adjust for material thickness variations
- **Thermal Expansion**: Account for heat-induced dimensional changes
- **Surface Finish**: Optimize for different material surface characteristics
- **Speed Optimization**: Adjust engraving speed based on cylinder geometry

## Integration with SefroCut Ecosystem

### Device Compatibility
- **Balor Series**: Full native support with hardware acceleration
- **Generic Galvo**: Works with any galvo driver supporting coordinate transformation
- **Future Devices**: Extensible architecture for new galvo systems

### Workflow Integration
- **Design Phase**: Correction parameters set during design preparation
- **Execution Phase**: Automatic application during engraving
- **Quality Control**: Real-time validation and adjustment

### Plugin Architecture
```python
def plugin(service, lifecycle=None):
    if lifecycle == "service":
        # Register for galvo devices
        return ("provider/device/balor",)
    elif lifecycle == "added":
        # Attach cylinder correction service
        service.add_service_delegate(CylinderCorrection(service))
```

## Contributing

When contributing to the cylinder correction module:

1. **Mathematical Accuracy**: Ensure all coordinate transformations are mathematically correct
2. **Performance**: Keep correction calculations efficient for real-time use
3. **Device Compatibility**: Test with multiple galvo device types
4. **User Experience**: Provide clear feedback and error messages
5. **Documentation**: Update examples and troubleshooting guides

## Related Modules

- **device/balor**: Primary target device with cylinder correction support
- **core/space**: Coordinate system management
- **core/view**: Viewport transformation matrices
- **gui**: User interface components and window management

The cylinder correction module enables precise engraving on cylindrical objects, transforming what would otherwise be distorted patterns into clean, accurate results on curved surfaces.
