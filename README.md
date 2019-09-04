# meerk40t
Laser software for the Stock-LIHUIYU laserboard.


MeerK40t "Meer" (provisional name) is a built from the ground up open source laser cutting software.

# Current State

The driver works the same way as with Whisperer so installing the bundled driver there is reasonable.

The bones are largely established. And well built.

Most of the aspects of a functional stock k40 laser cutter work, it will cut some things.

It has some highly serious bugs and issues that aren't fixed and need to be.

---

# Philosophy

The goal is simple. Provide a working, effective, stock K40 laser program that is easy to hack on. There are a number of highly creative, dedicated, and determined people out there. And a lot of people have wanted to help with the software aspects as well. The primary subgoal of this project is to create an outlit for hacking the software aspect of the K40.

Obviously there is little success for projects of lofty goals and no actions so I've written a (not quite fully) working application. The goal is to make sure it has good bones.

## GUI
The primary GUI is written in wxPython. It's pretty easy to hack on and quite easy to improve. This is MeerK40t, Navigation, Preferences, Controller, and LaserSceneView. This includes a grid and guides I wrote for this project and a ZoomerPanel I wrote for EmbroidePy (an embrodiery project).

## Backend
The USB driver will use the same methodology of Whisperer for now. So the same bundled driver is the easiest method.

The main interfacing with K40 is done through the `K40Controller` this should properly synch with the device in an asynchronized manner both giving consistent state updates, but also robust control over the device. USB connectivity is done through `pyemb`. This is written from the ground up. And includes a couple additional custom commands like '\n' and '-' which do not appear in the LHMicro-GL codeset. 

These perform metacontrol actions like pad the packet the rest of the way and, cause the controller to wait for the FINISHED signal. This means that all functionality of the board can be executed with just an ascii string. And multiple jobs can simply be added to the queue without any issues 

## Geometry

The SVG parser is code I wrote for mathandy/svgpathtools, which is a major tools expansions of regebro/svg.path library. The path.py used for the shapes is part of a proposed improvement to regebro's library there. svgpathtools includes other functions like offset curves that are very important for things like kerf compensation.

The LIHUIYU series of boards are connected to two stepper motors these can step one step in either direction, or trigger both at the same time. So everything in the K40 are made of dots at 1000dpi. Every movement is a step either orthogonally or diagonally, this means there are no actual curves only a series of very tiny steps in 1 of 8 possible directions. This is where the Zingl Plotter comes in. The Beauty of Bresenham's Algorithm ( http://members.chello.at/easyfilter/bresenham.html ) author, Zingl came up with a series of algorithms based on Bresenham's insights, which natively allows the performing these steps, with regard to the native shapes themselves.

This combination of high level understanding of curves and low level rapid production of the curves to within 1 dot of correctness gives Meer the ability to perform vector curves natively. These are not subdivided into suitibly small line segments, curves are simply executed. (TODO: there is actually no arc ability in Zingl yet, and some functions arn't ported correctly yet).


## Parsers

The ability to drag and drop and display and modify job elements is critical to any good laser cutting application. Currently Meer uses Pillow to load images. EgvParser which I wrote for K40Tools to load EGV files. And `svgparser` to load the SVG files.

## Rasterization

The project includes a variant of RasterBuilder, I wrote for Visicut after adding a Stock K40 driver to the project, which provides methods for a highly debuggable methodology to build rasters based on a state machine. This gives Meer the ability to overscan, perform bottom-to-top rasters, start from any corner, provide right-to-left or left-to-right rasters, skip blank edge pixels, skip blank edge lines and make the entire process extremely easy to troubleshoot or extend. If you wanted to, for example, break the image space into different regions and raster those areas independently, the ability to modify a robust debuggable rasterizer would be essential. Or if you wanted to perform passes based on value of the pixel (like first pass does 66% black, and second pass does 33% black). The good bones are essential.

## Lhymicro-gl Writer

Beyond connecting to the correct USB the other essential component is the ability to accurately write Lhymicro-gl code. This is done with the LhymicroWriter. It uses a similar methodology to the one I used in the K40Nano's NanoPlotter class but rewritten, to be simple enough to work, and only complex enough to cover all possibilities.

### LaserSpeed

For the speedcodes I use LaserSpeed which I wrote for K40Nano and Whisperer and is now included in that code base, and published under MIT license.

## LaserCommands

The LaserProject consist of LaserElements these can call a `generate()` generator which creates a series of LaserCommands which are used to produce itself. Nothing is generated before hand and no giant memory structures need to be created to process the projects this way. Additional objects and structures can easily used through the same API. 

