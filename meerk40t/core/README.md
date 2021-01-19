

# Core

Core modules are largely tools and classes that define Meerk40t specific ecosystem requirements within the kernel.

* Bind/Alias controls the Bind and Alias routines within the kernel-console and their loading and saving.

* Elements is shape, path, image, and path-text interactions.
* Laser Operations are broad laser operations like `Engrave`, `Cut`, `Raster`, and `Image`. These operations combined with Elements become `Cutcode` which is used by the devices to control the operations.
* Cutcode is a hybrid datatype of shapes combined with lasersettings of speeds, power, and other laser specific settings.
* Cutplanning is a set of methods for dealing with the arrangements of cutcode to optimize or modify the order of the cuts.
* Plotplanning deals with the arrangement of the individual laser pulses either controlling the interactions of ppi power modulation, dashes, ordering modifications, grouping and other changes to the dynamic firing of the laser.
* Rasterplotter deals with the conversion of pixels into discrete laser commands, performing a `Raster` operation.
* ZinglPlotter deals with the plotting of vector shapes and their conversion into pixel perfect laser movements. Based on the Zingl-Bresenham Algorithms. See: http://members.chello.at/easyfilter/bresenham.html