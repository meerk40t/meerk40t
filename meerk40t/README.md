# Meerk40t structure

This ReadMe page describes how the Meerk40t python code is structured and provides a very brief description of each of the major subdirectories.

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

## Devices

Device modules are specific to laser cutting and the lower level interactions with laser cutter drivers.

## DXF

DXF modules deal with Digital Exchange Format files.

## Extra

Extra modules provide non-core functionality.

## Gui

The Gui modules require wxPython and deal with the graphical interactions between the user and the software.

## Image

Image modules are tools dealing with Pillow (Python Image Library).

## Tools

Tools are simple stand-alone datastructure/algorithms that perform non-kernel operations
which may be considerably useful to many modules, or which simply do not require any ecosystem functionality.

## Kernel Server
The Server governs interactions within TCP and UDP sockets.

## Main.py
The main file deals with the CLI for Meerk40t as well as loading and processing of different plugins, both internal and external.

## svgelements
The svgelements file is a directly included version of the svgelements project
[https://github.com/meerk40t/svgelements](https://github.com/meerk40t/svgelements)
which deals with the high fidelity parsing of SVG data and geometric rendering.
It implements the core parts of SVG v1.1 and SVG 2.0  and provides a number of robust objects like `Angle`, `Length`, `Color`, `Point` and `Matrix` which are used throughout MeerK40t.

The Paths are used as the elements for vector shapes.

Many commands accept Angles and Lengths as real values. Though the Length is now preferred used within core/units.py.

The Viewbox functions is used to do things like center the camera image in the window.

Many of these are fundamental objects within MeerK40t. 
