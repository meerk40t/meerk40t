#Meerk40t

These files relate directly to kernel operations and interactions between the kernel and general operations within the kernel space. 

Currently, this does the booting and bootstrapping which deals with loading of plugins including core, devices, and gui interactions. And deals with the kernel and other very general operations like servers connections and interactions.


# Core

Core modules are largely tools and classes that define Meerk40t specific ecosystem requirements within the kernel.

# Device

Device modules are specific to laser cutting and the lower level interactions with laser cutter drivers.


# DXF

DXF modules deal with Digital Exchange Format files.


# Extra

Extra modules are less plugin-like functions.

# Gui

The Gui modules all require wxPython and deal with the graphical interactions between the user and the software.

# Image

Image modules are tools dealing with Pillow (Python Image Library).

# Tools

Tools are simple stand-alone datastructure/algorithms that perform non-kernel operations which may be considerably useful to many different modules, or which simply do not require any ecosystem functionality. 

# Kernel
The Kernel serves as the central code that binds modules together within Meerk40t. It is intended to be useful for other such ecosystems and agnostic with regard to the plugins used. It provides several different methods of interactions including signals, channels, persistent settings, timers, schedulers, console commands, contexts, and registered values.

# Kernel Server
The Server governs interactions within TCP and UDP sockets.

# Main
The main file deals with the CLI for Meerk40t as well as loading and processing of different plugins, both internal and external.

# svgelements
The svgelements file is a directly included version of the svgelements project ( https://github.com/meerk40t/svgelements ) which deals with the high fidelity parsing of SVG data and geometric rendering. It provides a number of robust objects like `Angle`, `Length`, `Color`, `Point` and `Matrix` and these are used throughout MeerK40t. The Paths are used as the elements for vector shapes. Images are the regular values for the images within MeerK40t. Many commands accept Angles and Lengths as real values. The Viewbox functions is used to do things like center the camera image in the window. These are fundamental objects within MeerK40t.

