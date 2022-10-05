# Tools

Tools are stand-alone utilities that help with various processes and may be shared among different functions. These are unrelated to the functionality of the kernel ecosystem.

These can largely be removed and used whole-cloth without requiring any additional code scaffolding.

## Pathtools
Contains some graph creating code, vector monotone code that can determine the insideness of various shapes.

### VectorMonotonizer

The vector monotonizer takes a series of segments and sorts them according to their y-coordinate. This sorted list of allows for a scanline operation that finds, for a particular y-coordinate all the segments that are currently being intersected with. This allows functions like creating horizontal lines through a shape and determining if a point is inside a given shape.

### Eulerian Fill

The Eulerian Fill performs creates a graph made out of edges and a series of horizontal rungs. It then solves for an optimal walk that visits all the horizontal rungs and as many of the edge nodes as needed to perform this walk. This should at most walk the entire edge plus 50% for scaffolding.

## Point Finder

Point Finder is intended as an acceleration structure for solving the nearest point algorithm.

## RasterPlotter

Rasterplotter deals with the conversion of pixels into discrete laser commands, performing a `Raster` operation.

## ZinglPlotter

ZinglPlotter deals with the plotting of vector shapes and their conversion into pixel perfect laser movements. Based on the Zingl-Bresenham Algorithms.
See: http://members.chello.at/easyfilter/bresenham.html
