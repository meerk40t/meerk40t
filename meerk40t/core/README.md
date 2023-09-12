# Core

Core modules are classes that define Meerk40t-specific ecosystem within the kernel.

## Bind/Alias

Controls the Bind and Alias routines within the kernel-console controls their loading and saving.

## Cutcode

Cutcode is a hybrid datatype of shapes combined with speeds, power, and other laser specific settings.

## Planning

The planning module defines a number of `plan` commands and helps define the job being run. The conversion from the
operations with referenced elements to cutcode, optimization of cutcode, and arrangement of things to be added to a
LaserJob. The LaserJob is then added to the Spooler which is then passed the driver.

### LaserJob

Planning is effectively a method of making a LaserJob which is a type of SpoolerJob. This is simply a list of cutcode
and utility objects which when the job is spooled, are given a driver to control. This abstraction permits complex code
to also serve as SpoolerJob, even if infinite, dynamic, or driver-specific.

## PlotPlanner

The plot planner module define algorithms and functions that plan the pulse plotting of the laser. These do things like
convert orthogonal and diagonal moves into single step moves, control PPI, perform pulse grouping, etc. This class
controls any modifications or algorithms needed to modify the laser independent laser movements. Plotplanning deals with
the arrangement of the individual laser pulses either controlling the interactions of ppi power modulation, dashes,
ordering modifications, grouping and other changes to the dynamic firing of the laser. This is *mostly* for the lihuiyu
device which doesn't have a direct line function.

## Space

The space service controls the conversion of scene positions to user space positions. Devices likewise control the
conversion from scene to device space.

## Spoolers

Spoolers contain a list of SpoolerJob objects, which can be cleared, stopped, added and removed. The spooler calls
`execute(driver)` on the SpoolerJob and the job will optionally call functions on the provided driver (provided that the
driver supports that particular command).

### SpoolerJob

SpoolerJobs provide an execution functionality and some basic spooler-required bits of information like priority,
run-state, and time-estimate.

## SVG IO

The SVG_IO module defines the saving and loading of svg files.

## Treeop

The tree operations provides decorators for implementing tree-ops. These functions are largely node specific functions
specifically intended for the popupmenu associated with particular types.

## Undos

The undo provides for undo and redo methods for copying and recreating the node tree. This permits earlier versions of
the tree state to be restored and unrestored to help with editing.

## Units

The units files provides core units to be used throughout the program. This is done for things like Length and Angle
which need meerk40t specific forms of these different unit-types for various amounts of support and conversion.

## View

View provides functionality for a 4 point -> 4 point conversion matrix. This allows manipulations for the space service
and for the devices to convert from one coordinate system to a different coordinate system.

## Webhelp

The Webhelp module defines simple URIs within registered kernel address `webhelp/*` these are URIs that may need to be
launched to help the user. These are opened with console command `webhelp <help>`

## Wordlist

Wordlist provides basic data structure and functions for define sets of words which may need to be changed dynamically
during the execution of some jobs. This provides the datastructure of the `.wordlist` object found in the `elements`
service
