# meerk40t
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t "MeerK" (provisional name) is a built-from-the-ground-up MIT licensed open-source laser cutting software.


# Current State

The usb driver uses `pyusb` so it requires the same driver install as Whisperer.

Verifying functionality and bug finding.

# Phases:
Phase 0. Building. - Done.

Phase 1. Testing.
* Make sure the program is stable and there should be no known major bugs
* Make sure it runs consistently and allow all the stuff it should need to be viable.
* Add instructions to how to install for savvy people to use it and try to get some feedback on bugs or issues. 

Phase 2. Bundle.
* More success requires easier installing and utilizing.
* Bundle program in an installable form with libusb driver so that it can just be installed and work.

Phase 3. Collaborate and Listen.
* Try to get stronger collaboration and feedback
* Improve things with more of a team group effort.
* Take feature suggestions.
* Take code assistence.
* Improve.

---

Currently we are at Phase 1. You can use it, there are no know giant gaps in functionality. It is not perfect, but it should be hooked up and working.

---

# Installing / Testing

I compiled the project into a binary at the end of Phase 0. So the releases should have a working .exe file.
https://github.com/meerk40t/meerk40t/releases

This might work out of the gate for you.

---

You can also download the source and run `MeerK40t.py` with python. The icons are included so it should run out of the gate.

---

Fallback instructions.

These are not definitive instructions they are some that should work. Basically you need to use python to run `MeerK40t.py`.

Windows Instructions:
You will need python:
* Download and install from: https://www.python.org/

You will need meerk40t:
* Download click: "Clone or Download".
* Click "Download Zip"
* Unzip on your desktop, this should be the meerk40t-master directory.
* Press Windows + R (to load run).
* Type "cmd" 
  * This should be a dos prompt at `C:\Users\(Name)>` location.
* Type "cd Desktop"
* Type "cd meerk40t-master
* Type "python MeerK40t.py"
  * At this point it could fail in a couple ways. It could lack: `wxPython`. `pyusb`. `Pillow`.
  * `ModuleNotFoundError: No module named 'wx'` means you need wxPython.
    * Type: `pip install wxPython`
  * `ModuleNotFoundError: No module named 'usb'` means you need pyusb.
    * Type: `pip install pyusb`
  * `ModuleNotFoundError: No module named 'PIL'` means you need Pillow.
    * Type: `pip install Pillow`


# Philosophy

The goal is simple. Provide a working, effective, stock K40 laser program that is easy to hack on. There are a number of highly creative, dedicated, and determined people out there. And a lot of people have want to help with the software aspects as well. Creating a highly functional and highly modular program should help people do that.

There is little chance of success for projects of lofty goals and no actions the early phases of this project are working out a good enough version that satisfies 'minimum viable product' functionality. This combined with the good bones of the modular design and design choices can provide easily hackable modular software package.

## GUI
The primary GUI is written in wxPython. It's pretty easy to hack on and quite easy to improve. Being modular though, the gui aspects should be kept apart from the functional aspects, so that a different GUI could be used without losing any core functionality.

## Driver
The USB driver currently uses the same methodology that Whisperer, name to use pyusb. So using the same bundled driver is the easiest method. Until phase 2 when this project will basically bundle the same driver. Using the USB-EPP/I2C... CH341A

## Controller

The main interfacing with K40 is done through the `K40Controller` this should properly synch with the device in an asynchronized manner both giving consistent state updates, but also robust control over the device. USB connectivity is done through `pyemb`. This is written from the ground up. And includes a couple additional custom commands like '\n' and '-' which do not appear in the LHMicro-GL codeset. 

These perform metacontrol actions like pad the packet the rest of the way and, cause the controller to wait for the FINISHED signal. This means that all functionality on the board can be executed with just an ascii string. And multiple jobs can simply be added to the queue without any issues.

## Geometry

The SVG parser is from code I wrote for `mathandy/svgpathtools`, which is a major tools expansions of `regebro/svg.path` library. The path.py used for the shapes is part of a proposed improvement to regebro's library there. `svgpathtools` includes other functions like offset curves that are very important for things like kerf compensation. The geometry in those is good enough and easy enough that it should allow a lot of solid extensions and modifications.

The LIHUIYU series of boards are connected to two stepper motors these can step one step in either direction, or trigger both at the same time. So everything in the K40 are made of dots at 1000dpi. Every movement is a step either orthogonally or diagonally, this means there are no actual curves only a series of very tiny steps in 1 of 8 possible directions. This is where the Zingl Plotter comes in. The Beauty of Bresenham's Algorithm ( http://members.chello.at/easyfilter/bresenham.html ) author, Zingl came up with a series of algorithms based on Bresenham's insights, which natively allows these operations to be performed with regard to the native shapes themselves. This means there is no need to deal with more primative or subdivied elements. We can natively use the curves.

This combination of high level understanding of curves and low level rapid production of the curves to within 1 dot of correctness gives MeerK the ability to perform vector curves natively. These are not subdivided into suitibly small line segments, curves are simply executed on the fly.


## Parsers

The ability to drag and drop and display and modify job elements is critical to any good laser cutting application. Currently MeerK uses Pillow to load images. 'EgvParser' which I wrote for K40Tools to load EGV files. And `svgparser` to load the SVG files.

## Rasterization

The project includes a variant of RasterBuilder, I wrote for Visicut after adding a Stock K40 driver to the project, which provides methods for a highly debuggable methodology to build rasters based on a state machine. This gives MeerK the ability to overscan, perform bottom-to-top rasters, start from any corner, provide right-to-left or left-to-right rasters, skip blank edge pixels, skip blank edge lines and makes the entire process extremely easy to troubleshoot or extend. If you wanted to, for example, break the image space into different regions and raster those areas independently, the ability to modify a robust debuggable rasterizer would be essential. Or if you wanted to perform passes based on value of the pixel (like first pass does 66% black, and second pass does 33% black). The good bones are essential.

## Lhymicro-gl Writer

Beyond just connecting to the correct USB the other essential component is the ability to accurately write Lhymicro-gl code, which the stock firmware uses. This is done with the LhymicroWriter. With a middle-level to low level on the fly writer, we can track our location natively. We can also adapt for edge conditions and alterations without any trouble. So writing an extension that changes the speed speed the laser moves at while it's moving and running a different set of code instructions is possible. Since the writer knows its current state and can simply perform all the things it needs to perform these state changes, and write that in the Lhymicro-gl.

### LaserSpeed

For the speedcodes I use LaserSpeed which I wrote for K40Nano and Whisperer and is now included in that code base, and published under MIT license.

## LaserCommands

One of the core design elements is the use of a middle language which can be used to issue high level commands but do so in a consistent fashion. So if loading an SVG gives us a bezier curve, we can simply yield that command on the generate method of the LaserElement subclass and cause it to produce a Bezier curve. Or if we add in a different parser we can simply issue a series of high level commands which will then be given to the writer which will turn those into low level commands.

## LaserProject

The LaserProject consist of LaserElements these can call a `generate()` generator which creates a series of LaserCommands which are used to produce itself. Nothing is generated before hand and no giant memory structures need to be created to process the projects this way. Additional objects and structures can easily used through the same API. These LaserElements also contain instructions as to how to draw themselves.

