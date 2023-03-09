# Core

Core modules are classes that define Meerk40t specific ecosystem requirements within the kernel.

## Bind/Alias

Controls the Bind and Alias routines within the kernel-console controls their loading and saving.

## Elements
Elements are shape, path, image, and path-text interactions. The Tree structure for storing most of the data and defines a lot of commands as tree-operations.
This includes nodes like LaserOperations are broad laser operations like `Engrave`, `Cut`, `Raster`, and `Image`. These operations combined with Elements become `CutCode` which is used by the devices to control the operations.

## Cutcode
Cutcode is a hybrid datatype of shapes combined with `LaserSettings` of speeds, power, and other laser specific settings.

## Planning
The planning module is defines a number of `plan` commands and does help define the job being run. The conversion from the Operations to Cutcode, optimization of cutcode, and arrangement of things to be added to the spooler. This includes optimizations of the cutcode.

## PlotPlanner
The plot planner module define algorithms and functions that plan the pulse plotting of the laser. These do things like convert orthogonal and diagonal moves into single step moves, control PPI, perform pulse grouping, etc. This class controls any modifications or algorithms needed to modify the laser independent laser movements. Plotplanning deals with the arrangement of the individual laser pulses either controlling the interactions of ppi power modulation, dashes, ordering modifications, grouping and other changes to the dynamic firing of the laser.

## Spoolers
Spoolers are context agnostic data to be sent to devices. This is the initial step within a device and serves as the destination for laser commands and controls.

## SVG IO
The SVG_IO module defines the saving and loading of svg files.

## Webhelp
The Webhelp module defines simple URIs within registered kernel address `webhelp/*` these are URIs that may need to be launched to help the user. These are opened with console command `webhelp <help>`
