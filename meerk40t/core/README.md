

# Core

Core modules are largely tools and classes that define Meerk40t specific ecosystem requirements within the kernel.

## Bind/Alias

Controls the Bind and Alias routines within the kernel-console and their loading and saving.

## Elements
Elements is shape, path, image, and path-text interactions. The Tree structure for storing most of the data and defines a lot of commands as tree-operations.
This includes nodes like LaserOperations are broad laser operations like `Engrave`, `Cut`, `Raster`, and `Image`. These operations combined with Elements become `Cutcode` which is used by the devices to control the operations.

## Cutcode
Cutcode is a hybrid datatype of shapes combined with lasersettings of speeds, power, and other laser specific settings.

## Planning
The planning module is defines a number of `plan` commands and does helps define the job being run. The conversion from the Operations to Cutcode, optimization of cutcode, and arrangement of things to be added to the spooler.

## Optimizer
Optimizer is a set of methods for dealing with the arrangements of cutcode to optimize or modify the order of the cuts.

# PlotPlanner
Plotplanning deals with the arrangement of the individual laser pulses either controlling the interactions of ppi power modulation, dashes, ordering modifications, grouping and other changes to the dynamic firing of the laser.

## SVG IO
The SVG_IO module defines the saving and loading of svg files.

## Webhelp
The Webhelp module defines simple URIs within registered kernel address `webhelp/*` these are URIs that may need to be launched to help the user. These are opened with console command `webhelp <help>`

