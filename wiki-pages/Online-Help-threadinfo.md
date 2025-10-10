# Online Help: Threadinfo

## Overview

This help page covers the **Threadinfo** functionality in MeerK40t.

The ThreadInfo panel provides real-time monitoring and management of background tasks and threaded operations in MeerK40t. It displays active background jobs, their status, runtime, and allows users to track the progress of preparatory operations like burn preparation, file processing, and other system tasks.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\thread_info.py`

## Category

**GUI**

## Description

The ThreadInfo panel is a critical monitoring tool that displays all active background tasks in MeerK40t. Background tasks are preparatory jobs issued with the 'threaded' command, such as:

- Burn preparation operations
- File processing and conversion
- Rasterization tasks
- Optimization calculations
- Device communication tasks
- System maintenance operations

The panel provides real-time visibility into these operations, showing task names, current status, and elapsed runtime. This helps users understand what the system is doing in the background and when operations are complete.

## How to Use

### Accessing the ThreadInfo Panel

The ThreadInfo panel can be accessed in two ways:

1. **As a docked panel**: Available in the bottom pane area as "Tasks"
2. **As a standalone window**: Through the Window menu or via the `wxpane/ThreadInfo` command

### Available Controls

- **Task List**: A table showing all active background tasks with columns for:
  - **#**: Sequential task number
  - **Task**: Description of the background operation
  - **Status**: Current state of the task (Running, Completed, etc.)
  - **Runtime**: Elapsed time in HH:MM:SS format

- **Auto-show on new task** (Checkbox): When enabled, the panel will automatically appear whenever a new background task starts

- **Right-click Context Menu**:
  - **Show System Tasks**: Toggle to display/hide internal system threads (normally hidden)

### Key Features

- **Real-time Updates**: Automatically refreshes every 2 seconds when visible, or every 5 seconds when hidden
- **Signal Integration**: Responds to `thread_update` signals for immediate status changes
- **Thread Safety**: Uses proper locking mechanisms to safely access thread information
- **Column Resizing**: Remembers column widths between sessions
- **System Task Filtering**: Option to hide/show internal system threads

### Basic Usage

1. **Monitor Active Tasks**: Open the ThreadInfo panel to see what background operations are currently running
2. **Track Progress**: Watch the Runtime column to see how long tasks have been executing
3. **Identify Bottlenecks**: Use the Status column to identify tasks that may be stuck or taking too long
4. **Auto-show Setup**: Enable "Auto-show on new task" to be notified when new background work begins
5. **System Monitoring**: Right-click and enable "Show System Tasks" for advanced troubleshooting

### Advanced Usage

- **Performance Monitoring**: Use runtime information to identify slow operations
- **Debugging**: Enable system tasks view to see internal thread activity
- **Resource Management**: Monitor multiple concurrent tasks and their impact on system performance

## Technical Details

The ThreadInfo panel integrates deeply with MeerK40t's threading architecture:

- **Thread Management**: Monitors the kernel's thread registry (`kernel.threads`)
- **Signal System**: Listens for `thread_update` signals to refresh the display
- **Timer Jobs**: Uses scheduled jobs for periodic updates when the panel is hidden
- **Locking**: Implements thread-safe access using `kernel.thread_lock`
- **Persistence**: Saves column widths and auto-show preferences

Each thread entry contains:
- Thread object reference
- Status message
- User type flag (user vs system task)
- Task information string
- Start timestamp

The panel calculates runtime by comparing current time against the thread's start time, formatting it as hours:minutes:seconds.

## Troubleshooting

### Common Issues

- **Panel not updating**: Check if the panel is visible (updates are throttled when hidden)
- **Missing tasks**: Ensure "Show System Tasks" is enabled if looking for internal operations
- **Performance impact**: The panel itself has minimal overhead but monitoring many threads may affect system performance

### Performance Considerations

- Updates are throttled to every 2 seconds when visible to prevent excessive CPU usage
- Column resizing and persistence operations are optimized
- Thread enumeration uses proper locking to prevent race conditions

## Related Topics

*Link to related help topics:*

- [[Online Help: Console]] - Command-line interface for thread operations
- [[Online Help: Spooler]] - Job queue management
- [[Online Help: Simulation]] - Preview operations that may spawn background tasks

## Screenshots

### ThreadInfo Panel - Active Tasks View
The main ThreadInfo panel displaying current background operations:
- **Task List Table**: Columns showing # (sequential number), Task description, Status, and Runtime
- **Active Tasks**: Currently running background operations with their descriptions
- **Status Indicators**: Current state of each task (Running, Completed, etc.)
- **Runtime Display**: Elapsed time in HH:MM:SS format for each task

### Auto-Show Configuration
The panel with auto-show settings enabled:
- **Auto-show Checkbox**: Checked to automatically display panel when new tasks start
- **New Task Notification**: Panel appearing automatically when background work begins
- **Task Details**: Information about newly started background operations
- **User Notification**: Visual cue when the panel opens due to new activity

### System Tasks Monitoring
The panel showing internal system threads:
- **Right-Click Menu**: Context menu with "Show System Tasks" option selected
- **System Threads**: Internal MeerK40t threads (normally hidden) now visible
- **Thread Details**: Technical information about system-level operations
- **Advanced Monitoring**: Complete view of all active threads in the system

### Task Completion Status
The panel showing completed and running tasks:
- **Mixed Status**: Combination of Running and Completed task states
- **Completion Times**: Final runtime for finished operations
- **Active Operations**: Currently executing tasks with ongoing time counters
- **Progress Tracking**: Visual indication of task lifecycle stages

### Performance Monitoring View
The panel during intensive operations:
- **Multiple Concurrent Tasks**: Several background operations running simultaneously
- **Resource Usage**: Runtime information for performance analysis
- **Task Identification**: Clear task names for identifying bottlenecks
- **System Load**: Overview of computational workload distribution

### Empty State Display
The panel when no background tasks are active:
- **No Tasks Message**: Clear indication when no background operations are running
- **Ready State**: Panel prepared to display new tasks as they start
- **Auto-show Ready**: Checkbox visible and ready for configuration
- **Clean Interface**: Minimal display when system is idle

### Long-Running Task Monitoring
The panel tracking extended background operations:
- **Extended Runtime**: Tasks running for significant periods (minutes/hours)
- **Status Persistence**: Continuous monitoring of long-duration operations
- **Progress Indication**: Ongoing status updates for lengthy processes
- **Resource Tracking**: Time-based analysis of system resource utilization

---

*This help page provides comprehensive documentation for the ThreadInfo background task monitoring system.*
