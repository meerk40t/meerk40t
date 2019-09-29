# meerk40t
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t "MeerK" (provisional name) is a built-from-the-ground-up MIT licensed open-source laser cutting software.


# Philosophy

The goal is simple. Provide a working, effective, stock K40 laser program that is easy to hack on. There are a number of highly creative, dedicated, and determined people out there. And a lot of people have want to help with the software aspects as well. Creating a highly functional and highly modular program should help people do that.

There is little chance of success for projects of lofty goals and no actions so I am creating a viable product that should work for most use cases. This combined with the good bones of the modular design, and design choices can provide easily hackable modular software package.

# Current State
The usb driver uses `pyusb` so it requires the same driver install as Whisperer.

* Grid/Guides, Zoom and Pan scene Navigation (use middle mouse button, mouse wheel).
* PPI Power modulation (Yes, power modulation for the M2 Nano)
* Multi-K40 support.
* Independent path speeds.
* Drag and Drop support for SVGs/Images.
* Processes job as it executes. Starts instantly.

If you have any bug reports or feature requests raise an issue. They might not be added right away (unless they are awesome) but I do need a running log of things people think of, and things needed and discussions about those things.


# Phases:
Phase 0. Building. - Done.

Phase 1. Testing.
* Make sure the program is stable and there should be no known major bugs
* Make sure it runs consistently and allow all the stuff it should need to be viable.
* Document everything and add test suites.
* Add instructions to how to install for savvy people to use it and try to get some feedback on bugs or issues. 

Phase 2. Bundle.
* More success requires easier installing and utilizing.
* Bundle program in an installable form with libusb driver so that it can just be installed and work.

Phase 3. Collaborate and Listen.
* Try to get stronger collaboration and feedback
* Improve things with more of a team group effort.

---

Currently at Phase 1-2. You can use it, there are no know giant gaps in functionality. It is not perfect, but it should be hooked up and working. It has some killer features and some elements that are great.

---

# Installing / Testing

## Easy Windows

Download MeerK40t.exe
https://github.com/meerk40t/meerk40t/releases

Run: MeerK40t.exe

This might work out of the gate for you. It doesn't need to install or do anything weird. Chrome may say it's dangerous given that not enough people have downloaded it. If that makes you worry you can run it from the python source code or read the source code etc, using the methods below.

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
  * Type: `sudo apt-get libpng`


# Pulse Modulation

The stock firmware is not known for having power control, MeerK40t gives it power control. Some have asked how this is possible. Basically I use software to pulse the laser. See the Wiki for additional details: https://github.com/meerk40t/meerk40t/wiki/How-does-MeerK40t's-pulse-modulation-works%3F

This does not mean you should overpower your laser. Leave that knob alone.

Most power modulation is done through hardware because most boards have the ability to process things and excute stuff in their firmware. The Lhystudios (M2 Nano, etc) boards are different in that they are incredibly dumb. They basically execute machine code of the most basic variety. Leaving everything software running the laser to constantly feed it the next set of commands. This means a setting like power modulations can only be done in software. And, now is.


# GUI

The GUI is written in wxPython. It's pretty easy to hack on and quite easy to improve. Being modular though, the gui aspects should be kept apart from the functional aspects, so that a different GUI could be used without losing any core functionality.

# Driver

The USB driver currently uses the same methodology that Whisperer, name to use pyusb. So using the same bundled driver is the easiest method. Until phase 2 when this project will basically bundle the same driver. Using the USB-EPP/I2C... CH341A. However in the prebuilt .exe the libusb0.dll is included in the .exe. I'm not sure what impact this will have. But, so far people haven't had many problems. 

# Controller

The main interfacing with K40 is done through the `K40Controller` this should properly synch with the device in an asynchronized manner both giving consistent state updates, and robust control over the device. USB connectivity is done through `pyemb`. This code is written from the ground up. And includes a couple additional custom commands like '\n' and '-' which do not appear in the LHMicro-GL codeset. 

These extra code elements perform metacontrol actions like pad the packet the rest of the way and cause the controller to wait for the FINISHED signal. This means that all functionality on the board can be executed with just an ascii string. And multiple jobs can simply be appended to the controllers buffere without any issues.

# Spooler

Most jobs are spooled like a printer spooler where the jobs are performed in sequence. You can add additional jobs to the spooler while it's still running the first job. And use the interface as needed. (Though with some cautions).

# Geometry

## SVG Paths.

The SVG parser is from code I wrote for `mathandy/svgpathtools`, which is a tools expansions of `regebro/svg.path` library. The path.py used for the shapes is part of a proposed improvement to regebro's library there. `svgpathtools` includes other functions like offset curves that are very important for things like kerf compensation. The geometry in those is good enough and easy enough that it should allow a lot of solid extensions and modifications.

## Curve Plotting

The LIHUIYU series of boards are connected to two stepper motors these can step one step in either direction, or trigger both at the same time. So everything in the K40 are made of dots at 1000dpi. Every movement is a step either orthogonally or diagonally, this means there are no actual curves only a series of very tiny steps in 1 of 8 possible directions. This is where the Zingl Plotter comes in. The Beauty of Bresenham's Algorithm ( http://members.chello.at/easyfilter/bresenham.html ) author, Zingl came up with a series of algorithms based on Bresenham's insights, which natively allows these operations to be performed with regard to the native shapes themselves. This means there is no need to deal with more primative or subdivied elements. We can natively use the curves.

MeerK40t will draw pixel perfect curves (except for Arc which might be off a couple pixels currently). Which means if your design contains a Cubic Bezier curve, the program will draw it flawlessly.

## Working Together

This combination of high level understanding of curves and low level rapid production of the curves to within 1 dot of correctness gives MeerK the ability to perform vector curves natively. These are not subdivided into suitibly small line segments, curves are simply executed on the fly. And the project internally stores these as the curves they are, permitting high level manipulations, and low level flawless and fast rendering.


# Parsers

The ability to drag and drop and display and modify job elements is critical to any good laser cutting application. Currently MeerK uses Pillow to load images. `svg_parser` to load the SVG files. `EgvParser`  is from software written for K40Tools to load EGV files. Requests for dealing with additional file formats should be quite modular, so after they are written they should be quite easy to integrate. 

# Rasterization

The project includes a variant of RasterBuilder (MIT Licensed by author) that was originally for Visicut after adding the Stock K40 driver to the project. It uses a highly debuggable methodology to build rasters. This gives MeerK the ability to overscan, perform bottom-to-top rasters, start from any corner, skip blank edge pixels, skip blank edge lines and makes the entire process extremely easy to troubleshoot or extend. If you wanted to, for example, break the image space into different regions and raster those areas independently, the ability to modify a robust debuggable rasterizer would be essential.

**Note:** Rasters do not scale in a traditional manner. You can make them bigger with step size but you need to understand generally what that means. The program will not perform these operations for you automatically because they can potentially be lossy.

See notes on Rastering (https://github.com/meerk40t/meerk40t/wiki/Notes-on-Rastering) in the wiki.


# Lhymicro-gl Writer

Beyond connecting to the correct USB, the other essential component is the ability to accurately write Lhymicro-gl code, which the stock firmware uses. This is done with the LhymicroWriter. It uses a middle-level to low level on the fly writer, that constantly track the writing location natively, and the machine state.

We can also adapt for edge conditions and alterations without any trouble. So writing an extension that changes the speed speed the laser moves at while it's moving would trivial. Different code instructions can be used since the writer knows its current state and can simply perform all the things it needs to change to the correct state, and write that in the Lhymicro-gl being sent to the controller.

## LaserSpeed

For the speedcodes I use LaserSpeed which I wrote for K40Nano and Whisperer and is now included in that code base, and published under MIT license. 

## LaserCommands

One of the design elements is the use of a middle language. These are yielded various LaserElement classes and sent to the writer. In theory these could eventually serve as the backbone for switching out the backend to other methods to control other lasers.

# LaserProject

The LaserProject consist of LaserElements these can call a `generate()` generator which creates a series of LaserCommands which are used to produce itself. Nothing is generated before hand and no giant memory structures need to be created to process the projects this way. Additional objects and structures can easily used through the same API. These LaserElements also contain instructions as to how to draw themselves.
