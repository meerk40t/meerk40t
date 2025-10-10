# Online Help: Simulate

## Overview

This help page covers the **Simulate** functionality in MeerK40t.

This panel shows you exactly what will happen when you run your laser job. Preview the cutting path, timing, and results before starting.

![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/3324df5a-3910-4f94-a54f-2aaae9e82881)

The simulation window allows you to preview the expected burn results: sequence of operations, durations etc.
It allows to fiddle with optimisation parameters and get an insight if and to what extent certain optimisation options would speed up the burn process.

If you are happy with what you are seeing then can you send the cutcode (the translation of elements and operations into laser commands) directly to the laser.

Optimisations: If you click on the button with the Arrow left indicator (<img src="https://github.com/meerk40t/meerk40t/assets/2670784/7da3759d-a85e-4d0d-8b3f-d62c27a24fa6" width="25">), then a panel with optimisation options appear. You can change them and click "Recalculate" to assess the impact these will have. You will find details about the optimisation options here: [Optimisation options](https://github.com/meerk40t/meerk40t/wiki/Online-Help:-OPTIMISATION)

### Tips:
- Change the Mode-Option at the bottom of the screen to change between
  - Step: jumps from one draw primitive (shape segment) to another - useful to see how mk has split the things into smaller parts. Images on the other hand are considered just one primitive.
  - Time (either in sec or min) - are more realistic view in terms what happens during a given interval.
- You can zoom in and move around the scene preview by using the mouse scrollwheel as you can do in the main scene.

### Expert Tips:
(I hope you know what you are doing :smirk: )
- Right click on the scene to get a context menu.
![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/e5070d2c-9bbf-4574-8619-8df0f306c348)
You can intentionally drop all lasercommands before / after the currently displayed execution step - this is helpful if you need to restart a job and don't want to do all the things until the point you needed to interrupt (intentionally stopped) again. Go to this point (or as close as you can get) and delete the cuts before.
- If you fold out the optimisation menu at the right hand side you have two more tabs, that could be interesting:
   - Operations: This a list of all the cutcode groups that MeerK40t creates under the hood. You can add additional instructions like a command to interrupt the burn and wait for a user command, and many more.
NB: Normally you would want to add special operations in the operation part of the tree (see [Operations](https://github.com/meerk40t/meerk40t/wiki/Online-Help:-OPERATIONS)), but this is an expert tool to change behaviour at a core level. <img src="https://github.com/meerk40t/meerk40t/assets/2670784/c17848e6-e6cb-4da9-be16-127fc6780d52" width="150">
   - Cutcode: if you select an operation in the previous tab, you can then see (and influence) the detailed laserinstructions. Again you can delete single segments, or split the laserjob at this point... <img src="https://github.com/meerk40t/meerk40t/assets/2670784/396f8312-2c34-4379-a529-027dcbfae750" width="150">

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\simulation.py`

## Category

**GUI**

## Description

The Simulate panel provides a comprehensive job preview and optimization environment that allows users to visualize exactly what will happen during laser execution before sending the job to the laser. This critical feature helps prevent costly mistakes by showing the cutting path sequence, timing estimates, and expected burn results.

Users would use this feature when:
- Previewing complex jobs before execution to verify cut order and timing
- Testing optimization settings to improve job efficiency
- Debugging job issues by examining individual cutcode segments
- Estimating job duration and resource requirements
- Validating that operations will execute as intended

The simulation integrates with MeerK40t's cutcode engine to provide accurate representations of laser movements, power settings, speed changes, and timing. It supports both step-by-step analysis and time-based playback, making it invaluable for both novice users learning laser operations and experts fine-tuning complex jobs.

## How to Use

### Available Controls

- **Optimize** (Checkbox)
- **Recalculate** (Button)
- **Steps** (Radio Button)
- **Time (sec.)** (Radio Button)
- **Time (min)** (Radio Button)
- **Send to Laser** (Button)
- **Playback Speed** (Label)
- **Mode** (Label)

### Key Features

- Integrates with: `background`
- Integrates with: `device;modified`
- Integrates with: `refresh_simulation`

### Basic Usage

1. **Open the Simulation Panel**: Access the simulation from the main MeerK40t interface to preview your current job
2. **Review Job Preview**: Examine the visual representation of your laser job in the scene preview area
3. **Adjust Playback Mode**: Choose between Step mode (jumps between draw primitives) or Time mode (shows progress over time intervals)
4. **Test Optimizations**: Click the optimization arrow button to access optimization settings and test different parameters
5. **Playback Control**: Use the playback controls to step through or continuously play the simulation
6. **Analyze Results**: Review timing estimates, operation sequence, and potential issues
7. **Send to Laser**: When satisfied with the preview, send the optimized cutcode directly to your laser device

## Technical Details

The simulation system works by processing the elements tree and operations through MeerK40t's cutcode generation engine. The cutcode represents the complete translation of design elements and laser operations into machine-executable commands.

**Core Components:**

- **Operations Panel**: Displays all cutcode groups created from the elements tree
- **Cutcode Panel**: Shows detailed laser instructions for selected operations
- **Scene Preview**: Real-time visualization of laser head movement and burn patterns
- **Statistics Engine**: Calculates job duration, travel distances, and optimization metrics

**Integration Points:**

- Connects to the `background` service for asynchronous processing
- Listens to `device;modified` signals for real-time updates
- Responds to `refresh_simulation` signals to update the preview
- Uses the cutplan optimization algorithms for travel path improvements

**Advanced Features:**

- Cutcode editing allows direct manipulation of laser commands
- Optimization testing provides before/after performance comparisons
- Context menu operations enable job interruption and restart capabilities
- Multi-mode playback supports both primitive-level and time-based analysis

## Related Topics

- [[Online Help: Operations]] - Creating and managing laser operations
- [[Online Help: OPTIMISATION]] - Detailed optimization options and algorithms
- [[Online Help: Spooler]] - Job execution and laser communication
- [[Online Help: Tree]] - Elements tree structure and management
- [[Online Help: Device Configuration]] - Laser device setup and configuration

## Screenshots

The simulation panel includes several key visual elements:

1. **Main Simulation View**: Shows the job preview with laser head movement visualization
2. **Operations Panel**: Lists all cutcode groups and allows adding special instructions
3. **Cutcode Panel**: Displays detailed laser commands for selected operations
4. **Optimization Panel**: Provides access to travel optimization settings
5. **Playback Controls**: Step-by-step or time-based simulation playback
6. **Context Menu**: Right-click options for job interruption and cutcode manipulation

See the images included in the Overview section above for visual examples of the simulation interface.

---

*This help page is automatically generated. Please update with specific information about the simulate feature.*
