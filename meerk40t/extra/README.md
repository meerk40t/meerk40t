

# Extra

Extra modules are largely tools and plugins that serve minor mostly standalone purposes. These are not dependent on other things and are not required. They are functional but not essential, usually adding interesting but ultimately unneeded functionality to the kernel ecosystem.

Some code is removed from a more prominent role elsewhere, others perform functions like making system calls to "Inkscape" to permit those given functions.

Many of these resemble addons that are built-in to meerk40t.

## Embroider

Embroider permits console calls to "embroider" which performs an Eulerian Fill operation on selected closed shapes.

## Inkscape

Inkscape permits and refers to calls to Inkscape. Some operations with the Commandline of Inkscape are useful operations and calling them to perform those functions can be helpful in some automated contexts.

## PathOptimize

Path Optimize are the older path-based optimizations routines from 0.6.x that worked on Path objects themselves. With the switch to `CutCode` this is less needed, but still provided.

## Vectrace

Vectrace performs simple black/white image decomposition. Converting an image into a vector elements. This should allow for some tracing of image objects.
This can be invoked with `vectrace` in console.