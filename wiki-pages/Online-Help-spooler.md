# Online Help: Spooler

## Overview

This help page covers the **Spooler** functionality in MeerK40t.

The Spooler panel provides comprehensive control over laser cutting job queues and execution. It serves as the central hub for managing, monitoring, and controlling all laser operations in MeerK40t.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\spoolerpanel.py`

## Category

**GUI**

## Description

The Spooler displays two main sections:
- **Active Job Queue** (top): Shows currently queued and running laser operations
- **Job History** (bottom): Displays completed jobs with detailed execution information

The spooler manages laser operations in a prioritized queue system, allowing multiple jobs to be prepared and executed in sequence. It provides real-time monitoring of job progress, multi-device support, and comprehensive job management capabilities.

## How to Use

### Available Controls

- **Device Selector** (Combo Box): Filters jobs by laser device
- **Pause/Resume** (Button): Temporarily halts or resumes laser operations
- **Abort** (Button): Immediately stops all laser operations
- **Silent Mode** (Checkbox): Disables audio feedback during processing
- **Job Queue List**: Displays active and queued jobs with detailed information
- **Job History List**: Shows completed jobs with execution details
- **Clear History** (Button): Removes all entries from job history

### Key Features

- Integrates with: `pause`, `spooler;completed`, `spooler;queue`, `spooler;idle`, `spooler;realtime`
- Real-time progress monitoring with step counts, time estimates, and loop information
- Multi-device support with filtering capabilities
- Right-click context menus for individual job management
- CSV export functionality for job history
- Timer-based automatic updates every 5 seconds

### Basic Usage

1. **Prepare Operations**: Create laser jobs through other MeerK40t panels (Design, Camera, etc.)
2. **Monitor Queue**: Review queued jobs in the spooler panel, check priorities and details
3. **Execute Jobs**: Monitor real-time progress as jobs execute, use pause/resume as needed
4. **Review History**: Check completed jobs in the history section for performance analysis

### Advanced Usage

#### Job Management
- Right-click jobs for context menu options (remove, stop, enable/disable)
- Use device selector to focus on specific laser devices
- Monitor multi-pass jobs with loop progress indicators

#### History Analysis
- Export job history to CSV for external analysis
- Clear old history entries to manage log size
- Filter history by device or job type

## Technical Details

Provides user interface controls for spooler functionality. Features button, label controls for user interaction. Integrates with pause, spooler;completed for enhanced functionality.

The spooler uses wxPython list controls to display job information with columns for device, job name, status, type, steps, passes, priority, runtime, and time estimates. It implements signal listeners for real-time updates and includes timer-based refresh mechanisms to ensure display accuracy.

Key technical components:
- **Signal Integration**: Listens to spooler signals for queue updates and completion notifications
- **Multi-threading**: Background updates prevent UI blocking during intensive operations
- **CSV Export**: Structured data export with device, timing, and performance metrics
- **Context Menus**: Dynamic right-click menus based on job state and capabilities

## Related Topics

- [[Online Help: Devices]] - Device configuration and management
- [[Online Help: Jog]] - Manual positioning controls
- [[Online Help: Move]] - Coordinate-based positioning
- [[Online Help: Transform]] - Object transformation operations
- [[Online Help: Tree]] - Element tree management

## Screenshots

*Screenshots showing the spooler panel with active jobs and history would be helpful here.*

---

*This help page provides comprehensive documentation for the spooler feature, covering job queue management, real-time monitoring, and execution control.*
