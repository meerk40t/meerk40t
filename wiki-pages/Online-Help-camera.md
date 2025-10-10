# Online Help: Camera

## Overview

This help page covers the **Camera** functionality in MeerK40t.

MeerK40t provides comprehensive camera integration for laser cutting operations, supporting up to 5 USB cameras simultaneously. Cameras serve two primary purposes: **job supervision** during laser operations and **material positioning** to accurately place workpieces on the laser bed.

The camera system includes advanced features like fisheye lens correction, perspective calibration, and real-time background integration. This allows precise alignment of designs with physical materials and monitoring of laser operations.

The camera button in the toolbar will auto-detect cameras and let you choose from up to 5 cameras.

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/8920eafb-8c99-4553-b779-0b14fe41f494)

You can calibrate your picture within the camera panel by setting the 4 corner circles to the outer corners of your laserbed:

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/03af4992-d38d-4a39-b05a-b121235de132)

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\camera\gui\camerapanel.py`

## Category

**GUI**

## Description

The Camera panel provides a complete interface for managing USB cameras in MeerK40t. Users would use this feature when they need to:

- **Position materials accurately** on the laser bed before cutting
- **Monitor laser operations** in real-time during job execution
- **Calibrate camera perspective** to match the physical laser bed dimensions
- **Correct lens distortions** for wide-angle or fisheye camera lenses
- **Capture snapshots** of workpieces for design reference
- **Set up automated background updates** during long cutting jobs

The system supports multiple camera sources including USB cameras (auto-detected) and custom URI-based camera feeds.

## How to Use

### Available Controls

#### Main Control Buttons
- **Update Image** - Captures a single frame from the camera and displays it
- **Export Snapshot** - Saves the current camera frame as an image element in the scene
- **Reconnect Camera** - Restarts the camera connection (useful if camera becomes unresponsive)
- **Detect Distortions** - Initiates fisheye correction calibration using a checkerboard pattern

#### Correction Options
- **Correct Fisheye** (Checkbox) - Enables/disables fisheye lens distortion correction
- **Correct Perspective** (Checkbox) - Enables/disables perspective correction using four-point calibration

#### Performance Controls
- **FPS Slider** - Adjusts camera frame rate from 0-120 FPS (0 = 1 frame every 5 seconds)

### Key Features

- **Multi-Camera Support**: Up to 5 cameras can be configured simultaneously
- **URI Management**: Custom camera sources via URI Manager window
- **Real-time Background**: Camera feed can be set as scene background with automatic updates
- **Device Linking**: Cameras can be linked to specific laser devices for coordinated operations
- **Aspect Ratio Control**: Multiple aspect ratio preservation modes (meet, slice, none)
- **Resolution Management**: Camera resolution can be changed from available options

### Basic Usage

1. **Open Camera Panel**: Click the camera button in the toolbar or use `camwin <index>` command
2. **Select Camera Source**: Right-click in camera view → "Manage URIs" to choose USB camera or custom URI
3. **Adjust Settings**: Set desired FPS and enable corrections as needed
4. **Calibrate Perspective** (if needed):
   - Disable "Correct Perspective" to show calibration markers
   - Drag the four corner circles to match your laser bed corners
   - Re-enable "Correct Perspective"
5. **Calibrate Fisheye** (if needed):
   - Print a 6x9 checkerboard pattern and place it flat in camera view
   - Click "Detect Distortions" button
   - Ensure the pattern is clearly visible for accurate calibration
6. **Use for Positioning**: Click "Update Image" to capture current view, or set as live background

### Advanced Usage

#### Live Background Updates
- Right-click in camera view → "refresh" submenu
- Choose update rate (e.g., "2x / 1sec" for 2 frames per second)
- Camera will automatically update scene background at selected interval
- Useful for monitoring long cutting jobs

#### Device-Specific Operation
- Link camera to specific device via right-click → "refresh" → device selection
- Camera updates will be coordinated with selected laser device operations

#### URI Management
- Open URI Manager via right-click → "Manage URIs"
- Add custom camera sources (IP cameras, RTSP streams, etc.)
- Remove or edit existing URI entries

## Technical Details

The camera system is built around OpenCV for camera access and image processing. Each camera runs as a separate service context (`camera/{index}`) with its own settings and state.

**Core Components:**
- **CameraPanel**: Main wxPython interface with scene display and controls
- **Scene Widgets**: Handle camera display, perspective markers, and image rendering
- **URI Management**: Stores camera sources in persistent settings
- **Correction Algorithms**: OpenCV-based fisheye and perspective transformations

**Key Technical Features:**
- **Fisheye Correction**: Uses OpenCV's camera calibration with checkerboard detection
- **Perspective Correction**: Four-point homography transformation
- **Frame Processing**: Real-time bitmap conversion for wxPython display
- **Multi-threading**: Camera capture runs in background job for smooth UI

**Integration Points:**
- Signals: `camera_uri_changed`, `refresh_scene`, `camera;fps`, `camera;stopped`
- Windows: `window/CameraURI` for URI management
- Commands: `camwin`, `camdetect`, `camera{index}` service commands

## Related Topics

- [[Online Help: Devices]] - Managing laser cutting devices
- [[Online Help: K40Controller]] - K40 laser controller operations
- [[Online Help: K40Operation]] - Basic laser cutting operations
- [[Online Help: K40Tcp]] - Network-based laser control

## Screenshots

*Camera panel showing live feed with perspective calibration markers:*

![Camera Panel](https://github.com/meerk40t/meerk40t/assets/2670784/03af4992-d38d-4a39-b05a-b121235de132)

*URI Manager for configuring camera sources:*

*Right-click context menu with camera options:*

---

This documentation covers the complete camera functionality in MeerK40t, including setup, calibration, and advanced usage scenarios for both material positioning and job supervision.
