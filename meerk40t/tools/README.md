

# Tools

Tools are stand-alone utilities that help with various processes and may be shared among different functions. These are unrelated to the functionality of the kernel ecosystem.

## Pathtools
Contains some graph creating code, vector monotone code that can determine the insideness of various shapes.


### VectorMonotonizer

The vector monotonizer takes a series of segments and sorts them according to their y-coordinate. This sorted list of allows for a scanline operation that finds, for a particular y-coordinate all the segments that are currently being intersected with. This allows functions like creating horizontal lines through a shape and determining if a point is inside a given shape.

### Eulerian Fill

The Eulerian Fill performs creates a graph made out of edges and a series of horizontal rungs. It then solves for an optimal walk that visits all of the horizontal rungs and as many of the edge nodes as needed to perform this walk. This should at most walk the entire edge plus 50% for scaffolding.
