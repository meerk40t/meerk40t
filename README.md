# MeerK40t
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software.


# Philosophy

The goal is simple. Provide a working, effective, stock K40 laser program that is easy to hack on. There are a number of highly creative, dedicated, and determined people out there. And a lot of people have want to help with the software aspects as well. Creating a highly functional and highly modular program should help people do that.

There is little chance of success for projects of lofty goals and no actions so I am creating a viable product that should work for most use cases. This combined with the good bones of the modular design, and solid design choices can provide easily hackable modular software package.

# Current State

The usb driver uses either `pyusb` making it compatible with K40Whisperer or the default windows driver making it also compatible with LaserDrw. So long as it has either availible, they will happily coexist.

* Dual drivers, use either the Whisperer method or LaserDrw method. 
* Grid/Guides, Zoom and Pan scene Navigation (use middle mouse button, mouse wheel).
* PPI Power modulation (Yes, power modulation for the M2 Nano)
* Independent path speeds.
* Multi-K40 support.
* Drag-and-Drop support for SVGs/Images.
* Processes job as on the fly, they start instantly.
* Multi-language support.
* Module Add-On and Kernel API.

If you have any bug reports or feature requests raise an issue. They might not be added right away (unless they are awesome) but I do need a running log of things people think of, and things needed and discussions about those things.

There are prebundled precomiled releases for Windows, Mac OSX, Raspberry Pi. 

# Phases:
Phase 0. Building. - Done.

Phase 1. Expected Features.
* Make sure the program is stable and there should be no known major bugs.
* Document everything and add test suites.
* Make sure all the expected features people have are included. So that typical the established workflows people have continue to work.
* If Meerk40t's lack of something makes the way you do things harder than it needs to be, that's an issue for Phase 1.

Phase 2. Bundle.
* Phase 2 involved bundling and driver work, but with precomiled bundles this is less needed. And the libusb driver install method is not mission criticial with the advent of Dual Drivering. This is mostly solved.


Phase 3. Collaborate and Listen.
* Try to get stronger collaboration and feedback
* Improve things with more of a team group effort.

---

# Installing / Testing

## Easy Windows

Download MeerK40t.exe
https://github.com/meerk40t/meerk40t/releases

Run: MeerK40t.exe

This should work out of the gate for you. It doesn't need to install or do anything. Chrome may say it's dangerous given that not enough people have downloaded it. If that makes you worry you can run it from the python source code or read the source code etc, using the methods below.

## Run Batch File to Python.

Download the source and run `MeerK40t.py` with python. 

* Download click: "Clone or Download".
* Click "Download Zip"
* Unzip on your desktop, this should be the meerk40t-master directory.
* Find `install_run.bat` in the `meerk40t-master` directory and run it.


The batch file checks the checks and installs requirements and runs MeerK40t.py

```
pip install -r requirements.txt
python MeerK40t.py
pause
```

The batch file only avoids the command prompt.


## Command Prompt Fallback

You need to use `python` and the python requirements of `wxPython` `pyusb` and `Pillow` to run `MeerK40t.py`.

Windows Instructions:
You will need python:
* Download and install from: https://www.python.org/

You will need Meerk40t:
* Download click: "Clone or Download".
* Click "Download Zip"
* Unzip on your desktop, this should be the meerk40t-master directory.
* Press Windows + R (to load run).
* Type "cmd" 
  * This should be a dos prompt at `C:\Users\(Name)>` location.
* Type "cd Desktop"
* Type "cd meerk40t-master
* Type "python MeerK40t.py"
  * At this point it could fail in a couple ways. It could lack: `wxPython`. `pyusb`. `Pillow`. See Troubleshooting:

## Troubleshooting Install

### Windows:
* `ModuleNotFoundError: No module named 'wx'` means you need wxPython.
  * Type: `pip install wxPython`
* `ModuleNotFoundError: No module named 'usb'` means you need pyusb.
  * Type: `pip install pyusb`
* `ModuleNotFoundError: No module named 'PIL'` means you need Pillow.
  * Type: `pip install Pillow`

### Linux:
* `ImportError: libpng12.so.0: cannot open shared object file: No such file or directory .` libpng is not installed.
  * Type: `sudo apt-get install libpng`


# Pulse Modulation

The stock firmware is not known for having power control, MeerK40t gives it power control. Some have asked how this is possible. Basically I use software to pulse the laser. See the Wiki for additional details: https://github.com/meerk40t/meerk40t/wiki/How-does-MeerK40t's-pulse-modulation-works%3F

This does not mean you should overpower your laser. Leave that knob alone.

Most power modulation is done through hardware because most boards have the ability to process things and excute stuff in their firmware. The Lhystudios (M2 Nano, etc) boards are different in that they are incredibly dumb. They execute very basic command directly on a micro-controller and do no planning or work directly on the device. This leaves everything to the software running the laser to constantly feed it the next set of commands. This means a setting like power modulations can only be done in software. And, now is.


# GUI

The GUI is written in wxPython. It's pretty easy to hack on and quite easy to improve. Being modular though, the gui aspects should be kept apart from the functional aspects, so that a different GUI could be used without losing any core functionality.

# Driver

The USB driver uses either the LibUsb driver or the CH341DLL.dll.

# Backend

There are three main parts for any backend system within MeerK40t, these are the Spooler, the Interpreter, and the Pipe.

## Spooler

Jobs are spooled like a printer spooler, so that jobs are performed in sequence. You can add additional jobs to a spooler while it's still running the first job.

## Interpreter

The main interpreter is the LhymicroInterpreter which converts LaserCommands into low level Lhymicro-GL code Any Interpreter is tasked with coverting such commands usable sets of bytes.

## Pipe

The system is agnostic with regard to where the data is going and should end up. Which the K40Controller is most used and default pipe. It doesn't have to be, and what to do with the code when we have it, is not a question with just one answer.

# Controller

The main interfacing with K40 is done through the `K40Controller` this should properly synch with the controller device, in an asynchronized, manner both giving consistent state updates, and robust control over the device. USB connectivity is done through `pyemb` or accessing the Windows driver. This code is written from the ground up, and includes a couple additional custom commands like '\n' and '-' which do not appear in the Lhymicro-GL codeset. 

These extra code elements perform metacontrol actions like pad the packet the rest of the way and cause the controller to wait for the FINISHED signal. This means that all functionality on the board can be executed with just an ascii string. And multiple jobs can simply be appended to the controller's buffer without any issues.

# Geometry

## SVG Paths.

The SVG library is a seperate project based in `svgelements` which can be retrived `pip install svgelements`. It is, in part, derived fromcode I wrote for `mathandy/svgpathtools`, which is a tools expansions of `regebro/svg.path` library. It's one of the most expansive and full implementations of SVG in python. It allows for curve level manipulations without requiring any linearization.

## Curve Plotting

The LIHUIYU series of boards are connected to two stepper motors, these can step one step in either direction, or trigger both at the same time. So everything in the K40 are made of positions at 1000dpi. Every movement is a step either orthogonally or diagonally, this means there are no actual curves only a series of very tiny steps in 1 of 8 possible directions. This is where the Zingl Plotter comes in. The Beauty of Bresenham's Algorithm ( http://members.chello.at/easyfilter/bresenham.html ) author, Zingl came up with a series of algorithms based on Bresenham's insights, which natively allows these curve plotting operations to be performed directly with the native shapes themselves. This means there is no need to deal with more primative or subdivied elements. If we have a large curve or small curve it will always have perfect precision because we can natively use the curves themselves.

MeerK40t will draw pixel perfect curves (except for Arc which might be off a couple pixels currently). Which means if your design contains a Cubic Bezier curve, the program will draw it flawlessly.

## Working Together

This combination of high level understanding of curves and ease of manipulating these and the low level rapid production of the curves to within 1 dot of correctness gives MeerK40t the ability to execute native vector curves which are very easy to manipulate. These are never subdivided into good-enough small line segments, and the curves are executed on the fly. And since no linearization is needed, the project internally stores everything as the curves they are, giving you access to high-level manipulations, and low-level extremely fast.

# Parsers

The ability to drag and drop and display and modify job elements is critical to any good laser cutting application. Currently MeerK40t uses Pillow to load images. `svgelements` to load the SVG files. There an `EgvParser` from K40Tools to load EGV files. These loaders are registered in the kernel api and can be augmented with your own formats quite easily. Requests for dealing with additional file formats can be easily addressed and integrated.

# Rasterization

The project includes a variant of RasterBuilder (MIT Licensed by author) that was originally built for Visicut after adding the Stock K40 driver to the project. It uses a highly debuggable methodology to build rasters. This gives MeerK40t the ability to overscan, perform bottom-to-top rasters, start from any corner, skip blank edge pixels, skip blank edge lines and makes the entire process extremely easy to troubleshoot or extend. If you wanted to, for example, break the image space into different regions and raster those areas independently, the ability to modifyy, a robust debuggable rasterizer, would be essential.

**Note:** Rasters do not scale in a traditional manner. You can make them bigger with step_size/scan_gap but you need to understand generally what that means.

See notes on Rastering (https://github.com/meerk40t/meerk40t/wiki/Notes-on-Rastering) in the wiki.


# Lhymicro-GL Interpreter

The Lhymicro-GL interpreter writes Lhymicro-GL code to be used in the stock firmware. This is done with the LhymicroInterpreter. It uses middle-level to low level on the fly writer, which tracks the local state of the device.

We can also adapt for edge conditions and alterations on the fly without any trouble. So writing an extension that changes the speed speed, while the laser is moving moving would trivial. Since the interpreter knows its current state and can perform the actions needed for state changes, it permits on the fly alteration and can write that in the Lhymicro-GL being sent to the controller.

## LaserSpeed

For the speedcodes, I use LaserSpeed which I wrote for K40Nano and is now included in the Whisperer source code published under MIT license.

## LaserCommands

The core of MeerK40t uses a language agnostic coding, which conveys spoolable commands. These are yielded various LaserNode classes and sent to the interpreter.


