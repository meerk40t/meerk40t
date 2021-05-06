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

