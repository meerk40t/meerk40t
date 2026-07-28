# Meerk40t structure

This ReadMe page describes how the Meerk40t python code is structured and provides a very brief description of each of
the major subdirectories.

## Kernel

The Kernel serves as the central code that binds modules together within Meerk40t.
It is intended to be useful for other such ecosystems and agnostic with regard to the plugins used.
It provides several methods of interactions including signals, channels, persistent settings,
timers, schedulers, console commands, contexts, services and registered values.

The Kernel is responsible for booting / bootstrapping the application and providing core basic services
for use by plugins, including registering functionality, signalling events to other plugins, handling settings,
providing channels for information to be sent from plugins to the user or to other plugins, etc.

The kernel is intended to provide generalised functionality that could be used by any complex application.
Whilst the kernel has been written initially for Meerk40t, there is no reason why it should not be used as the core
of other applications.

Plugins are classified as follows:

## Core

Core modules are largely tools and classes that define Meerk40t specific ecosystem requirements within the kernel.

## Device Drivers

Device driver modules provide hardware-specific implementations for different laser controllers and cutting systems.

### balormk
JCZ controllers for galvo-based laser systems.

### grbl
GRBL-compatible devices including popular brands like Ortur, Atomstack, and Creality.

### lihuiyu
Lihuiyu M2/M3-Nano controllers (K40 laser systems).

### moshi
Moshiboard laser controllers.

### newly
NewlyDraw System 8.1 laser controllers.

### ruida
Ruida laser controllers and emulators.

## Hardware Abstraction

### camera
Camera integration and image capture functionality.

### ch341
CH341 USB interface chip support for hardware communication.

### device
Hardware abstraction layer providing unified interfaces for device management.

## Specialized Features

### cylinder
Galvo correction and coordinate transformation for cylindrical engraving.

### fill
Hatch fill patterns, wobble effects, and living hinge generation.

### rotary
Rotary engraving support for cylindrical objects.

## File Formats

### dxf
Digital Exchange Format (DXF) file processing and conversion.

## User Interface

### gui
Graphical user interface modules using wxPython and AUI framework for highly configurable UI.

## Image Processing

### image
Image processing tools using Pillow (Python Image Library) for laser engraving preparation.

## Network

Network modules handle TCP and UDP socket communications for remote access and control.

## Utilities

### extra
Additional non-core functionality and extended features.

### tools
Standalone data structures and algorithms for geometric operations, font processing, and optimization.

## Main

The main file handles the command line interface for Meerk40t as well as loading and processing of different plugins, both internal and external.

## svgelements

The svgelements file is a directly included version of the svgelements project
[https://github.com/meerk40t/svgelements](https://github.com/meerk40t/svgelements)
which deals with the high fidelity parsing of SVG data and geometric rendering.
It implements the core parts of SVG v1.1 and SVG 2.0 and provides a number of robust objects
like `Angle`, `Length`, `Color`, `Point` and `Matrix` which are used throughout MeerK40t.

The Paths are used as the elements for vector shapes.

Many commands accept Angles and Lengths as real values. Though the Length is now preferred used within core/units.py.

The Viewbox functions is used to do things like center the camera image in the window.

Many of these are fundamental objects within MeerK40t. 
