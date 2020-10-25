# MeerK40t
Laser software for the Stock-LIHUIYU laserboard. This is the stock board for most K40 Laser Cutters. M2 Nano, et al.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software. It's a replacement for LaserDrw, Corel Laser, and K40 Whisperer. With the dual driver support it can run aside any of these programs, without needing any special. It's written in python and has precompiled versions for Windows, Mac OSX, and Raspberry Pi. Available: https://github.com/meerk40t/meerk40t/releases


# Installing

Windows, OSX, Raspberry Pi, and Linux Versions.
Everything is prebundled. You can just run the file.
https://github.com/meerk40t/meerk40t/releases

Download the version you need and run.

If you need want something more complex or need to run from Python directly: https://github.com/meerk40t/meerk40t/wiki/Alternative-Installs

# Features

* Built in Raster Preprocessing, RasterWizard.
* Dual drivers, use either the Whisperer method or LaserDrw method. 
* Grid/Guides, Zoom and Pan scene Navigation (use middle mouse button, mouse wheel).
* Easy Object Manipulation.
* PPI Power modulation (Yes, power modulation for the M2 Nano)
* Multi-K40 support.
* Drag-and-Drop support for SVGs/Images.
* On-the-fly job Processing
* Multi-language support.
* Modular/Hackable Add-On and Kernel API.
* Pixel perfect curve cutting.
* Command Line Interface

# GUI

The wxMeerK40t is the GUI and is written in wxPython.

# CLI

MeerK40t has a highly robust command line interface. It should be able to execute many projects without needing or having a gui

# Features

## Pulse Modulation

The stock controller is not known for having power control, MeerK40t gives it power control. How is this possible? MeerK40t pulses the laser in software. See the Wiki for additional details: https://github.com/meerk40t/meerk40t/wiki/How-does-MeerK40t's-pulse-modulation-works

This does not mean you should overpower your laser with the knob? NO. Leave that knob alone.

Most power modulation is done through hardware because most boards have the ability to process things and execute stuff. The Lhystudios (M2 Nano, etc) boards are different in that they are incredibly dumb. They execute very basic command directly on a micro-controller and do no planning or work directly on the device. This leaves everything to the software running the laser to constantly feed it new set of commands.

## Driver

The MeerK40t driver interface uses either the LibUsb driver or the CH341DLL default windows driver. This means the driver used is whatever you have, so you don't need to mess with drivers and it can run along side whatever other software you use.

## SVG Paths.

MeerK40t has a custom SVG library implementing the SVG standard. It is, in part, derived from code from `regebro/svg.path` library and the `mathandy/svgpathtools` library. It's one of the most expansive and full implementations of SVG in python. And has been spun off into it's own project.

## Curve Plotting

MeerK40t uses a special class of algorithms to perfectly plot shapes. If your SVG has a bezier curve, it will be plotted perfectly to within the nearest pixel. These shapes are not subdivided into lines at any point. Giving you perfect native resolution.

See: https://github.com/meerk40t/meerk40t/wiki/Zingl-Bresenham-Curve-Plotting

# Translations

MeerK40t is built with translations in mind. Providing a translation into your native language is fast and easy. https://github.com/meerk40t/meerk40t/wiki/Providing-a-Translation. 
