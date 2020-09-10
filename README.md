# MeerK40t
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed open-source laser cutting software. It's a replacement for LaserDrw, Corel Laser, and K40 Whisperer. With the dual driver support it can run aside any of these programs. It's written in python and has precompiled versions for Windows, Mac OSX, and Raspberry Pi. Available: https://github.com/meerk40t/meerk40t/releases

* Dual drivers, use either the Whisperer method or LaserDrw method. 
* Grid/Guides, Zoom and Pan scene Navigation (use middle mouse button, mouse wheel).
* PPI Power modulation (Yes, power modulation for the M2 Nano)
* Multi-K40 support.
* Drag-and-Drop support for SVGs/Images.
* On-the-fly job Processing
* Multi-language support.
* Modular/Hackable Add-On and Kernel API.
* Pixel perfect curve cutting.
* Command Line Interface

# Installing

## Easy Windows

Everything is prebundled. You can just run the file.

Download MeerK40t.exe
https://github.com/meerk40t/meerk40t/releases

Run: MeerK40t.exe

MeerK40t is compiled as a portable application. It doesn't need to install or do anything.


## Run Batch File to Python.

You will need python:
* Download and install from: https://www.python.org/

Download the source and run `MeerK40t.py` with python. 

* Download click: "Clone or Download".
* Click "Download Zip"
* Unzip on your desktop, this should be the meerk40t-master directory.
* Find `install_run.bat` in the `meerk40t-master` directory and run it.


The batch file checks and installs requirements and runs MeerK40t.py

```
pip install -r requirements.txt
python MeerK40t.py
pause
```

The batch file avoids the command prompt.

* Right click and "Run as Administrator" if you have permissions errors.

## Command Prompt Fallback

You will need python:
* Download and install from: https://www.python.org/

You need to use `python` and the requirements of `wxPython` `pyusb` and `Pillow` to run `MeerK40t.py`.

Windows Instructions:

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
* `PermissionError: [Errno 13] Permission denied:...`
  * Type: `sudo <previous command>`
* `ImportError: libpng12.so.0: cannot open shared object file: No such file or directory .` libpng is not installed.
  * Type: `sudo apt-get install libpng`


# GUI

The wxMeerK40t is the GUI and is written in wxPython.

# Features

## Pulse Modulation

The stock controller is not known for having power control, MeerK40t gives it power control. How is this possible? I use software to pulse the laser. See the Wiki for additional details: https://github.com/meerk40t/meerk40t/wiki/How-does-MeerK40t's-pulse-modulation-works

This does not mean you should overpower your laser with the knob? NO. Leave that knob alone.

Most power modulation is done through hardware because most boards have the ability to process things and execute stuff. The Lhystudios (M2 Nano, etc) boards are different in that they are incredibly dumb. They execute very basic command directly on a micro-controller and do no planning or work directly on the device. This leaves everything to the software running the laser to constantly feed it new set of commands.

## Driver

The MeerK40t driver interface uses either the LibUsb driver or the CH341DLL default windows driver.

## Backend

The backend in MeerK40t is highly modular. Lending towards permitting replacing the backend or replacing a part of the backend.

There are three main parts for any backend system within MeerK40t, these are the Spooler, the Interpreter, and the Pipe.

### Spooler

Jobs are spooled like a printer spooler, so that jobs are performed in sequence. You can add additional jobs to a spooler while it's still running the first job.

### Interpreter

The main interpreter is the LhymicroInterpreter which converts LaserCommands into low level Lhymicro-GL code Any Interpreter is tasked with converting such commands usable sets of bytes.

### Pipe

The system is agnostic with regard to where the data is going and should end up. Which the K40Controller is most used and default pipe. It doesn't have to be, and what to do with the code when we have it, is not a question with just one answer.


## Geometry

## SVG Paths.

The SVG library is a separate project based in `svgelements` which can be retrieved `pip install svgelements`. It is, in part, derived from code I wrote for `mathandy/svgpathtools`, which is a tools expansions of `regebro/svg.path` library. It's one of the most expansive and full implementations of SVG in python.

## Curve Plotting

The LIHUIYU series of boards are connected to two stepper motors, these can step one step in either direction, or trigger both at the same time. So everything in the K40 are made of positions at 1000dpi. Every movement is a step either orthogonality or diagonally, this means there are no actual curves only a series of very tiny steps in 1 of 8 possible directions. This is where the Zingl Plotter comes in. The Beauty of Bresenham's Algorithm ( http://members.chello.at/easyfilter/bresenham.html ) author, Zingl came up with a series of algorithms based on Bresenham's insights, which natively allows these curve plotting operations to be performed directly with the native shapes themselves. This means that there is no need to deal with more primitive or subdivided elements. If we have a large curve or small curve it will always have perfect precision because we can natively use the curves themselves.

MeerK40t will draw pixel perfect curves (except for Arc which could be off). Which means if your design contains a Cubic Bezier curve, the program will draw it flawlessly.

These are never subdivided into good-enough small line segments, and the curves are executed on the fly. And since no linearization is needed, the project internally stores everything as the curves they are, giving you access to high-level manipulations, and low-level extremely fast plotting.


# Parsers

The ability to drag and drop and display and modify job elements is critical to any good laser cutting application. Currently MeerK40t uses Pillow to load images. `svgelements` to load the SVG files. `RuidaDevice` to load .rd files. The `LhystudiosDevice` loads EGV files. These loaders are registered in the kernel api and can be augmented with other formats quite easily. Requests for dealing with additional file formats can be easily addressed and integrated.

# Rasterization

The project includes a RasterBuilder. It uses a highly debuggable methodology to build rasters. This gives MeerK40t the ability to overscan, perform bottom-to-top right-to-left rasters, start from any corner, skip blank edge pixels, skip blank edge lines and makes the entire process extremely easy to troubleshoot or extend.

See notes on Rastering (https://github.com/meerk40t/meerk40t/wiki/Notes-on-Rastering) in the wiki.


## LaserCommands

The core language internally used in MeerK40t is a backend-agnostic coding, which conveys spoolable commands. If you wish to write an add-on for MeerK40t that sends commands to the laser, or a backend for a different laser device, you will want to use these.

See notes on LaserCommands: https://github.com/meerk40t/meerk40t/wiki/LaserCommands

# Translations

MeerK40t is built with translations in mind. Providing a translation into your native language is fast and easy. https://github.com/meerk40t/meerk40t/wiki/Providing-a-Translation. 
