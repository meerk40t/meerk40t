# MeerK40t Device Module

## Overview

The Device Module forms the foundation of MeerK40t's hardware abstraction layer, providing a unified interface for managing laser devices, their configurations, and user interactions. This module implements the core device service architecture that enables MeerK40t to support multiple laser hardware types through a consistent API.

## Architecture

```
meerk40t/device/
├── basedevice.py          # Core device management and service registration (323 lines)
├── devicechoices.py       # Device configuration system (135 lines)
├── dummydevice.py         # Mock device for testing (179 lines)
├── mixins.py              # Common device functionality (Status class)
├── gui/
│   ├── defaultactions.py  # Default action controls (720 lines)
│   ├── effectspanel.py    # Effect configuration panel
│   ├── formatterpanel.py  # Output formatting controls
│   └── warningpanel.py    # Warning and status display
├── __init__.py            # Module initialization
└── README.md              # This documentation
```

### Core Components

- **BaseDevice (basedevice.py)**: Device service management, activation, and console commands
- **DeviceChoices (devicechoices.py)**: Configuration system for device settings and effects
- **DummyDevice (dummydevice.py)**: Testing device implementation
- **Status Mixin (mixins.py)**: Common status tracking functionality
- **GUI Panels**: User interface components for device management

## Device Service Architecture

### Service Registration and Management

The device module implements a provider-based architecture where devices register themselves with the kernel:

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        # Register device providers
        kernel.register("provider/device/lhystudios", LhystudiosDevice)
        kernel.register("provider/device/balor", BalorDevice)
        kernel.register("provider/device/dummy", DummyDevice)
```

### Device Information System

Devices provide metadata through the `dev_info` registration:

```python
kernel.register(
    "dev_info/lhystudios_info",
    {
        "provider": "provider/device/lhystudios",
        "friendly_name": "LHYMicro-GL Laser",
        "extended_info": "USB-based laser cutter with Ruida controller",
        "priority": 10,  # Higher priority = preferred default
        "family": "ruida",
        "choices": [
            {
                "attr": "label",
                "default": "LHYMicro-GL",
            },
            # Additional configuration defaults
        ],
    },
)
```

### Device Lifecycle

Devices follow a structured lifecycle managed by the kernel:

1. **Registration**: Device providers register with kernel
2. **Instantiation**: Devices created with configuration choices
3. **Activation**: Device becomes the active service
4. **Operation**: Device processes jobs and commands
5. **Deactivation**: Device suspended when another becomes active
6. **Destruction**: Device cleaned up and removed

## Device Management Commands

### Device Listing and Information

```bash
# List all available devices
device

# Show detailed device information
device

# Display current device status
devinfo
```

**Sample Output:**
```
Defined Devices:
----------------
#	Label	Type	Family	Status
0 (*):	LHYMicro-GL	lhystudios	Ruida	idle
1:	Balor-Galaxy	balor	Balor	idle
2:	Dummy Device	dummy		paused
```

### Device Creation and Management

```bash
# Add a new device
device add lhystudios

# Add device with custom label
device add lhystudios -l "My Laser"

# Activate a device by name
device activate "LHYMicro-GL"

# Activate by index
device activate 0

# Duplicate an existing device
device duplicate "LHYMicro-GL" "Backup Laser"

# Delete a device
device delete "Old Laser"
```

### Device Status and Control

```bash
# Get current position (user and native coordinates)
devinfo
# Output: 100.0,50.0;32000,16000;

# Update coordinate system
viewport_update
```

## Device Configuration System

### Choice-Based Configuration

Devices use a declarative configuration system through "choices":

```python
choices = [
    {
        "attr": "bedwidth",           # Attribute name
        "object": self,              # Target object
        "default": "320mm",          # Default value
        "type": str,                 # Data type
        "label": _("Width"),         # Display label
        "tip": _("Width of the laser bed."),  # Help text
        "section": "bed_dim",        # Configuration section
    },
    {
        "attr": "scale_x",
        "object": self,
        "default": 1.000,
        "type": float,
        "label": _("X Scale Factor"),
        "tip": _("Scale factor for the X-axis."),
        "conditional": (self, "advanced_mode"),  # Show only if condition met
    },
]
self.register_choices("bed_dim", choices)
```

### Configuration Sections

The device module organizes settings into logical sections:

- **bed_dim**: Bed dimensions and scaling
- **effect_defaults**: Default settings for effects (hatch, wobble)
- **operation_defaults**: Default power/speed for operations
- **device_specific**: Hardware-specific parameters

### Effect Configuration

```python
def get_effect_choices(context):
    return [
        {
            "attr": "effect_hatch_default_distance",
            "object": context,
            "default": "1.0mm",
            "type": str,
            "label": _("Hatch Distance"),
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_type",
            "object": context,
            "default": "circle",
            "type": str,
            "style": "combo",
            "choices": get_wobble_options(),  # Dynamic choices
            "label": _("Wobble Type"),
        },
    ]
```

### Operation Defaults

```python
def get_operation_choices(context):
    operations = {
        "op_cut": (_("Cut"), 5),      # Default speed 5 mm/min
        "op_engrave": (_("Engrave"), 10),
        "op_raster": (_("Raster"), 200),
        "op_image": (_("Image"), 200),
    }

    for op_type, (label, default_speed) in operations.items():
        choices.append({
            "attr": f"default_speed_{op_type}",
            "object": context,
            "default": default_speed,
            "type": int,
            "label": f"{label} {_('Speed')}",
            "section": "Operation Defaults",
        })
```

## Status and State Management

### Status Mixin

All devices inherit common status functionality:

```python
class Status:
    def __init__(self):
        self._laser_status = "idle"

    @property
    def laser_status(self):
        return self._laser_status

    @laser_status.setter
    def laser_status(self, new_value):
        self._laser_status = new_value
        self.signal("pipe;running", bool(new_value == "active"))
```

### Status Values

- **idle**: Device ready but not active
- **active**: Device currently executing operations
- **paused**: Operations suspended
- **busy**: Device processing but not cutting
- **error**: Device in error state

### State Constants

```python
# Driver states
DRIVER_STATE_RAPID = 0      # Rapid movement
DRIVER_STATE_FINISH = 1     # Operation complete
DRIVER_STATE_PROGRAM = 2    # Program execution
DRIVER_STATE_RASTER = 3     # Raster operation
DRIVER_STATE_MODECHANGE = 4 # Changing modes

# Plot flags
PLOT_START = 2048           # Start of plot
PLOT_FINISH = 256           # End of plot
PLOT_RAPID = 4              # Rapid move
PLOT_JOG = 2                # Jog move
PLOT_SETTING = 128          # Setting change
PLOT_AXIS = 64              # Axis movement
PLOT_DIRECTION = 32         # Direction change
```

## Dummy Device for Testing

### Purpose and Usage

The DummyDevice provides a mock implementation for testing and development:

```python
class DummyDevice(Service, Status):
    """
    DummyDevice is a mock device service. It provides no actual device.
    This is mostly for testing.
    """

    def __init__(self, kernel, path, choices=None):
        self.name = "Dummy Device"
        self.spooler = Spooler(self, "default")
        self.viewbuffer = ""  # Mock output buffer
        # Register standard device choices
        self.register_choices("bed_dim", bed_dimension_choices)
        self.register_choices("dummy-effects", get_effect_choices(self))
```

### Testing Applications

```bash
# Add dummy device for testing
device add dummy -l "Test Device"

# Activate dummy device
device activate "Test Device"

# Test operations without hardware
engrave test.svg
# Output goes to viewbuffer instead of hardware
```

## GUI Components

### Default Actions Panel

Provides user interface controls for device operations:

```python
class DefaultActionPanel(wx.Panel):
    """User interface panel for laser cutting operations"""

    # Controls for:
    # - Job start/end actions
    # - Emergency stop
    # - Pause/resume
    # - Home position
    # - Air assist control
    # - Console access
```

### Effects Panel

Configuration interface for effect settings:

- Hatch patterns and parameters
- Wobble effects and modulation
- Speed and power adjustments
- Real-time preview

### Formatter Panel

Output formatting controls:

- File format selection
- Export options
- Post-processing settings
- Quality adjustments

### Warning Panel

Status and warning display:

- Device status indicators
- Error messages and alerts
- Maintenance reminders
- Connection status

## Device Provider Interface

### Required Methods

All device providers must implement:

```python
class LaserDevice(Service):
    def __init__(self, kernel, path, choices=None):
        """Initialize device with configuration"""

    def realize(self):
        """Update coordinate system and transformations"""

    def hold_work(self, priority):
        """Pause current operations"""

    def execute(self, job):
        """Execute a laser job"""

    # Device-specific methods
    def connect(self): pass
    def disconnect(self): pass
    def status(self): pass
```

### Optional Methods

```python
def viewport_update(self): pass      # Update view transformations
def signal_status(self): pass        # Emit status signals
def shutdown(self): pass             # Clean shutdown
def destroy(self): pass              # Complete cleanup
```

## Integration with MeerK40t Core

### Service Registration

Devices integrate with the core service system:

```python
# Register device service
kernel.add_service("device", device_instance, provider_path)

# Activate device
kernel.activate("device", device_instance, assigned=True)

# Device becomes accessible as kernel.device
active_device = kernel.device
```

### Channel Communication

Devices communicate through the channel system:

```python
# Device status updates
self.signal("device;status", "active")

# Coordinate updates
self.signal("device;position", (x, y))

# Error notifications
self.signal("device;error", "Connection lost")
```

### Settings Integration

Devices use the hierarchical settings system:

```python
# Device-specific settings
device.setting(str, "port", "/dev/ttyUSB0")

# Global overrides
kernel.setting(str, "preferred_device", "lhystudios")

# Persistent storage
kernel.write_persistent("activated_device", device.path)
```

## Boot and Initialization

### Automatic Device Activation

On startup, the device module:

1. **Reads last active device** from persistent storage
2. **Attempts to reactivate** the previous device
3. **Falls back to preferred device** if reactivation fails
4. **Creates default device** if no devices exist

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "boot":
        last_device = kernel.read_persistent(str, "/", "activated_device", None)
        if last_device:
            try:
                kernel.activate_service_path("device", last_device)
            except ValueError:
                pass

        if not hasattr(kernel, "device"):
            preferred_device = kernel.root.setting(str, "preferred_device", "lhystudios")
            kernel.root(f"service device start {preferred_device}\n")
```

### Shutdown Handling

On shutdown, the current device path is saved:

```python
if lifecycle == "preshutdown":
    setattr(kernel.root, "activated_device", kernel.device.path)
```

## Usage Examples

### Basic Device Setup

```bash
# List available device types
device

# Add a new LHYMicro-GL device
device add lhystudios -l "My Laser Cutter"

# Configure bed dimensions
# (through GUI or settings)

# Activate the device
device activate "My Laser Cutter"

# Verify activation
device
# Shows (*) next to active device
```

### Device Configuration

```bash
# Access device settings through GUI
window open Device-Settings

# Or configure through console
# (device-specific commands vary)
```

### Multi-Device Workflow

```bash
# Add multiple devices
device add lhystudios -l "Small Laser"
device add balor -l "Large Laser"

# Switch between devices
device activate "Small Laser"
# Work with small laser

device activate "Large Laser"
# Work with large laser
```

### Testing with Dummy Device

```bash
# Add dummy device for testing
device add dummy -l "Test Device"

# Activate dummy
device activate "Test Device"

# Test operations
engrave test_pattern.svg
cut test_outline.svg

# Check output in dummy device viewbuffer
# (for development/testing purposes)
```

## Troubleshooting

### Common Issues

#### Device Not Found
```bash
# Check available device types
device

# Verify device name spelling
device add lhystudios  # not "lhy" or "lhymicro"
```

#### Device Won't Activate
```bash
# Check if device exists
device list

# Try activating by index
device activate 0

# Check device status
devinfo
```

#### Configuration Problems
```bash
# Reset device settings
# (device-specific, check device documentation)

# Check configuration through GUI
window open Device-Settings
```

### Diagnostic Commands

```bash
# Full device information
device

# Current position and status
devinfo

# Update coordinate system
viewport_update

# Check service status
service list | grep device
```

## Extending Device Support

### Creating a New Device Provider

1. **Implement Device Class**
```python
from meerk40t.device.mixins import Status
from meerk40t.kernel import Service

class MyLaserDevice(Service, Status):
    def __init__(self, kernel, path, choices=None):
        Service.__init__(self, kernel, path)
        Status.__init__(self)
        # Initialize device-specific attributes
```

2. **Register Device Provider**
```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/mydevice", MyLaserDevice)
        kernel.register("dev_info/mydevice_info", {
            "provider": "provider/device/mydevice",
            "friendly_name": "My Laser Device",
            "extended_info": "Custom laser device implementation",
            "priority": 5,
            "choices": [
                {"attr": "label", "default": "My Device"},
                # Additional configuration
            ],
        })
```

3. **Implement Required Methods**
```python
def realize(self):
    """Update coordinate transformations"""

def execute(self, job):
    """Process laser job"""

def connect(self):
    """Establish hardware connection"""

def disconnect(self):
    """Close hardware connection"""
```

### GUI Integration

Add device-specific panels:

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "added":
        # Register device-specific windows
        kernel.register("window/MyDevice", MyDevicePanel)
        kernel.register("button/device/MyDevice", {
            "label": _("My Device Settings"),
            "action": lambda v: kernel.console("window toggle MyDevice\n"),
        })
```

## Performance Considerations

### Resource Management
- **Connection Pooling**: Reuse hardware connections
- **Lazy Initialization**: Initialize components on demand
- **Memory Efficient**: Stream processing for large jobs
- **Thread Safety**: Safe concurrent access

### Optimization Strategies
- **Batch Operations**: Group related commands
- **Caching**: Cache frequently used settings
- **Async Processing**: Non-blocking status updates
- **Smart Polling**: Efficient hardware status checking

## Future Enhancements

### Planned Features
- **Auto-Detection**: Automatic device discovery and configuration
- **Cloud Integration**: Remote device monitoring and control
- **Advanced Calibration**: Automated calibration routines
- **Device Groups**: Coordinated multi-device operations
- **Performance Analytics**: Device usage and efficiency metrics

### API Improvements
- **REST Interface**: HTTP API for device control
- **WebSocket Support**: Real-time device communication
- **Plugin Architecture**: Third-party device driver support
- **Configuration Import/Export**: Device profile management

This device module provides the essential infrastructure that enables MeerK40t to support a wide variety of laser hardware through a consistent, extensible interface.

