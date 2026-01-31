# Kernel

The Kernel is the central nervous system of SefroCut, providing a sophisticated plugin architecture, service management, and communication infrastructure. It serves as the foundation that enables modular development and extensibility across the entire application.

## Architecture Overview

The Kernel implements a hierarchical plugin system with lifecycle management, enabling different components to be loaded, initialized, and managed in a coordinated manner. It provides core services like threading, scheduling, settings persistence, and inter-module communication.

### Core Components

#### Kernel Class
The main Kernel class (`kernel.py`) serves as the central hub, managing:
- **Plugin System**: Dynamic loading and lifecycle management of plugins
- **Service Architecture**: Domain-based service registration and activation
- **Context System**: Path-based configuration and settings management
- **Threading**: Safe multi-threading with job scheduling
- **Communication**: Signal/channel system for inter-module messaging
- **Console System**: Command-line interface and scripting capabilities

#### Service System
Services (`service.py`) are specialized contexts that provide domain-specific functionality:
- **Domain Registration**: Services register under specific domains (e.g., "device", "gui")
- **Lifecycle Management**: Services follow attachment/detachment lifecycles
- **Context Extension**: Services extend kernel contexts with domain-specific attributes
- **Multiple Instances**: Multiple services can exist per domain with activation switching

#### Context System
Contexts (`context.py`) provide path-based configuration management:
- **Hierarchical Paths**: Settings organized in path-based hierarchies
- **Persistent Storage**: Automatic saving/loading of configuration data
- **Attribute Access**: Direct attribute access to settings with fallback mechanisms
- **Derivation**: Sub-contexts can be created for specific path scopes

## Plugin Lifecycle System

The Kernel implements a comprehensive lifecycle system (`lifecycles.py`) that manages the initialization, operation, and shutdown of plugins and services.

### Kernel Lifecycle Phases

```python
# Initialization Phase
LIFECYCLE_KERNEL_INIT = 0           # Initial state
LIFECYCLE_KERNEL_PRECLI = 20        # Pre-command line interface
LIFECYCLE_KERNEL_CLI = 25           # Command line interface setup

# Registration Phase  
LIFECYCLE_KERNEL_INVALIDATE = 50    # Plugin invalidation
LIFECYCLE_KERNEL_PREREGISTER = 100  # Pre-registration
LIFECYCLE_KERNEL_REGISTER = 101     # Plugin registration
LIFECYCLE_KERNEL_CONFIGURE = 102    # Configuration setup

# Boot Phase
LIFECYCLE_KERNEL_PREBOOT = 200      # Pre-boot preparation
LIFECYCLE_KERNEL_BOOT = 201         # Core system boot
LIFECYCLE_KERNEL_POSTBOOT = 202     # Post-boot initialization

# Runtime Phase
LIFECYCLE_KERNEL_PRESTART = 300     # Pre-start preparation
LIFECYCLE_KERNEL_START = 301        # System start
LIFECYCLE_KERNEL_POSTSTART = 302    # Post-start setup
LIFECYCLE_KERNEL_READY = 303        # System ready for operation
LIFECYCLE_KERNEL_FINISHED = 304     # Runtime completion

# Main Loop Phase
LIFECYCLE_KERNEL_PREMAIN = 400      # Pre-main loop
LIFECYCLE_KERNEL_MAINLOOP = 401     # Main application loop
LIFECYCLE_KERNEL_POSTMAIN = 402     # Post-main loop

# Shutdown Phase
LIFECYCLE_KERNEL_PRESHUTDOWN = 900  # Pre-shutdown cleanup
LIFECYCLE_KERNEL_SHUTDOWN = 1000    # Final shutdown
```

### Service Lifecycle Phases

```python
LIFECYCLE_SERVICE_INIT = 0          # Initial state
LIFECYCLE_SERVICE_ADDED = 50        # Service added to kernel
LIFECYCLE_SERVICE_ATTACHED = 100    # Service attached to context
LIFECYCLE_SERVICE_ASSIGNED = 101    # Service assigned as active
LIFECYCLE_SERVICE_DETACHED = 200    # Service detached from context
LIFECYCLE_SERVICE_SHUTDOWN = 1000   # Service shutdown
```

### Module Lifecycle Phases

```python
LIFECYCLE_MODULE_OPENED = 100       # Module opened in context
LIFECYCLE_MODULE_CLOSED = 200       # Module closed
```

## Communication Systems

### Channel System

Channels (`channel.py`) provide a publish-subscribe messaging system for inter-module communication:

```python
# Create a channel
console_channel = kernel.channel("console", timestamp=True, ansi=True)

# Send messages
console_channel("System initialized")

# Watch for messages
def message_handler(message):
    print(f"Received: {message}")

console_channel.watch(message_handler)
```

**Channel Features:**
- **Buffering**: Configurable message buffers with size limits
- **Formatting**: ANSI color codes and BBCode support
- **Threading**: Thread-safe message handling
- **Watching**: Multiple subscribers can watch channels
- **Timestamps**: Automatic timestamping of messages

### Signal System

The signal system enables event-driven communication between components:

```python
# Send a signal
kernel.signal("device_connected", "/device/laser", device_info)

# Listen for signals
@kernel.signal_listener("device_connected")
def on_device_connected(device_info):
    print(f"Device connected: {device_info}")
```

**Signal Processing:**
- **Queued Processing**: Signals processed asynchronously
- **Thread Safety**: Safe signal handling across threads
- **Path-based Routing**: Signals can be scoped to specific paths
- **Listener Management**: Dynamic addition/removal of listeners

## Threading and Scheduling

### Job Scheduler

The Kernel provides a sophisticated job scheduling system (`jobs.py`):

```python
# Schedule a recurring job
job = kernel.add_job(
    run=my_function,
    name="my_job",
    interval=1.0,  # Run every second
    times=None,    # Run indefinitely
    run_main=True  # Run in main thread
)

# Remove a job
kernel.remove_job(job)
```

**Scheduler Features:**
- **Thread Separation**: Jobs can run in main thread or background threads
- **Conditional Execution**: Jobs can have conditional execution requirements
- **Interval Control**: Configurable execution intervals
- **Limited Runs**: Jobs can be limited to specific number of executions
- **Timer Commands**: Console command timers for automation

### Thread Management

Safe multi-threading with automatic lifecycle management:

```python
# Create a managed thread
thread = kernel.threaded(
    my_function,
    arg1, arg2,
    thread_name="worker_thread",
    daemon=False
)

# Thread monitoring
messages = kernel.get_thread_messages()
for thread_name, status, user_type, info in messages:
    print(f"Thread {thread_name}: {status}")
```

## Settings and Persistence

### Settings System

The Settings class (`settings.py`) provides hierarchical configuration management:

```python
# Access settings
kernel.setting_name = "value"
value = kernel.setting_name

# Sectioned settings
kernel["section"]["key"] = "value"
value = kernel["section"]["key"]
```

**Settings Features:**
- **Hierarchical Storage**: Section/key organization
- **Automatic Persistence**: Settings saved to disk automatically
- **Type Safety**: Support for various data types
- **Backup Creation**: Automatic backup of configuration files
- **Safe Paths**: Secure file access with fallback mechanisms

### Context-Based Settings

Contexts provide path-specific settings management:

```python
# Get a context
device_context = kernel.get_context("/device/laser")

# Context-specific settings
device_context.power = 1000
device_context.speed = 500
```

## Console Command System

### Command Registration

The console system (`functions.py`) enables command-line interaction:

```python
@kernel.console_command("laser_power", help="Set laser power")
def set_power(channel, _, power: int = None, **kwargs):
    if power is None:
        channel(f"Current power: {kernel.power}")
    else:
        kernel.power = power
        channel(f"Power set to: {power}")
```

**Console Features:**
- **Argument Parsing**: Automatic argument parsing with type hints
- **Help System**: Built-in help generation
- **Command Completion**: Tab completion support
- **Scripting**: Batch command execution
- **Channel Output**: Structured output through channels

### Command Options and Arguments

```python
@kernel.console_argument("power", type=int, help="Laser power in watts")
@kernel.console_option("verbose", "-v", action="store_true", help="Verbose output")
@kernel.console_command("configure")
def configure_laser(channel, _, power: int, verbose: bool = False, **kwargs):
    # Implementation
    pass
```

## Registration and Lookup System

### Object Registration

The Kernel maintains a hierarchical registry of objects and services:

```python
# Register an object
kernel.register("device/laser/driver", laser_driver)

# Lookup registered objects
driver = kernel.lookup("device/laser/driver")

# Find objects by pattern
for obj, path, name in kernel.find("device/*/driver"):
    print(f"Found driver: {name} at {path}")
```

**Registration Features:**
- **Hierarchical Paths**: Path-based object organization
- **Pattern Matching**: Regex-based object discovery
- **Dynamic Updates**: Automatic lookup change notifications
- **Service Integration**: Active service lookup prioritization

### Lookup Listeners

Components can listen for registration changes:

```python
@kernel.lookup_listener("device/*/driver")
def on_driver_change(new_drivers, old_drivers):
    # Handle driver changes
    pass
```

## Service Management

### Service Domains

Services are organized by functional domains:

```python
# Available service domains
kernel.services("device")        # Get available device services
kernel.services("device", True)  # Get active device service

# Service lifecycle
kernel.add_service("device", laser_service)
kernel.activate("device", laser_service)
kernel.deactivate("device")
```

**Service Features:**
- **Domain Organization**: Services grouped by functionality
- **Activation Management**: Single active service per domain
- **Lifecycle Events**: Automatic lifecycle event triggering
- **Context Integration**: Services automatically available in contexts

### Service Plugins

Services can have associated plugins:

```python
def laser_plugin(service, lifecycle):
    if lifecycle == "attached":
        # Service attached logic
        pass
    elif lifecycle == "detached":
        # Service detached logic
        pass

kernel.add_plugin(laser_plugin)
```

## Context Management

### Context Hierarchy

Contexts provide scoped configuration and access:

```python
# Root context
root = kernel.root

# Derived contexts
device_context = root.derive("device")
laser_context = device_context.derive("laser")

# Context navigation
subcontexts = list(root.subpaths())
```

**Context Features:**
- **Path-based Access**: Hierarchical context organization
- **Settings Inheritance**: Automatic settings inheritance
- **Module Management**: Context-scoped module opening/closing
- **Service Access**: Direct access to active services

## Plugin Architecture

### Plugin Types

The Kernel supports multiple plugin types:

```python
# Kernel plugins - affect entire system
def kernel_plugin(kernel, lifecycle):
    if lifecycle == "boot":
        # System boot logic
        pass

# Service plugins - affect specific services
def service_plugin(service, lifecycle):
    if lifecycle == "attached":
        # Service attachment logic
        pass

# Module plugins - affect specific modules
def module_plugin(module, lifecycle):
    if lifecycle == "opened":
        # Module opening logic
        pass

kernel.add_plugin(kernel_plugin)
```

### Plugin Registration

Plugins can register additional functionality:

```python
def my_plugin(kernel, lifecycle):
    if lifecycle == "register":
        # Register custom functionality
        kernel.register("my_feature", MyFeature())
        kernel.add_service("my_domain", MyService())

kernel.add_plugin(my_plugin)
```

## Error Handling and Safety

### Safe Evaluation

The Kernel provides safe expression evaluation:

```python
# Safe arithmetic evaluation
result = kernel.safe_eval("power * 2", "power", 500)  # Returns 1000
```

### File Access Safety

Secure file operations with automatic fallback:

```python
# Safe file opening
with kernel.open_safe("config.txt", "r") as f:
    data = f.read()
```

### Inhibitor System

The inhibitor system (`inhibitor.py`) manages system state control:

```python
# Check system state
if kernel.inhibitor.allow_operation("laser_fire"):
    # Perform operation
    pass
```

## Integration Patterns

### Kernel Integration

Modules integrate with the Kernel through standardized patterns:

```python
class LaserModule:
    def __init__(self, context):
        self.context = context
        self.kernel = context.kernel

    def module_open(self):
        # Module initialization
        self.kernel.signal("laser_module_opened", self.context.path)

    def module_close(self):
        # Module cleanup
        self.kernel.signal("laser_module_closed", self.context.path)
```

### Service Integration

Services extend the Kernel's capabilities:

```python
class LaserService(Service):
    def __init__(self, kernel, path):
        super().__init__(kernel, path)
        self.power = 1000

    def service_attach(self):
        # Service attachment
        self.kernel.laser = self  # Make service available

    def service_detach(self):
        # Service detachment
        self.kernel.laser = None
```

## Performance and Threading

### Thread Safety

The Kernel ensures thread-safe operations:
- **Lock Management**: Internal locking for critical sections
- **Thread Local Storage**: Per-thread data isolation
- **Atomic Operations**: Safe concurrent data access
- **Queue Processing**: Asynchronous message processing

### Performance Optimization

- **Lazy Loading**: Components loaded on demand
- **Efficient Lookups**: Optimized registration system
- **Minimal Overhead**: Lightweight context and service management
- **Background Processing**: Non-blocking operations where possible

## Configuration and Environment

### Environment Information

The Kernel provides system environment details:

```python
env = kernel.os_information
print(f"OS: {env['OS_NAME']}")
print(f"Temp Directory: {env['OS_TEMPDIR']}")
print(f"Working Directory: {env['WORKDIR']}")
```

### Configuration Management

Automatic configuration handling:
- **File-based Storage**: Persistent settings in config files
- **Backup Creation**: Automatic configuration backups
- **Migration Support**: Configuration version handling
- **Safe Writing**: Atomic configuration file updates

## Debugging and Monitoring

### Debug Mode

Comprehensive debugging capabilities:

```python
# Enable debugging
kernel._start_debugging()

# Monitor system state
kernel.channel("kernel-lifecycle").watch(print)
kernel.channel("service-lifecycle").watch(print)
```

### Channel Monitoring

Real-time system monitoring through channels:

```python
# Monitor console output
kernel.channel("console").watch(lambda msg: print(f"Console: {msg}"))

# Monitor signals
kernel.channel("signals").watch(lambda msg: print(f"Signal: {msg}"))
```

## Shutdown and Cleanup

### Graceful Shutdown

The Kernel manages orderly system shutdown:

```python
# Initiate shutdown
kernel.shutdown()

# Check shutdown status
if kernel.is_shutdown:
    # System is shutting down
    pass
```

**Shutdown Process:**
1. **Pre-shutdown**: Signal preparation and cleanup
2. **Module Closure**: Close all opened modules
3. **Service Shutdown**: Shutdown all active services
4. **Context Flush**: Save all context settings
5. **Thread Termination**: Stop all managed threads
6. **Final Cleanup**: Release all resources

This Kernel architecture provides the foundation for SefroCut's modular, extensible design, enabling complex laser control systems to be built from composable, reusable components.