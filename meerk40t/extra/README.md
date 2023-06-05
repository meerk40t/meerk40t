# Extra

Extra modules are largely tools and plugins that serve minor mostly standalone purposes. These are not dependent on other things and are not required. They are functional but not essential, usually adding interesting but ultimately unneeded functionality to the kernel ecosystem.

Some code is removed from a more prominent role elsewhere, others perform functions like making system calls to "Inkscape" to permit those given functions.

Many of these resemble addons that are built-in to meerk40t.

## CAG (Computer Additive Geometry)
The cag operations provide access to Clipper which is located in the tools section, this allows for clipping of shapes by other shapes.

## Embroider

Embroider permits console calls to "embroider" which performs an Eulerian Fill operation on selected closed shapes.

## Inkscape

Inkscape permits and refers to calls to Inkscape. Some operations with the Commandline of Inkscape are useful operations and calling them to perform those functions can be helpful in some automated contexts.

## PathOptimize

Path Optimize are the older path-based optimizations routines from 0.6.x that worked on Path objects themselves. With the switch to `CutCode` this is less needed, but still provided.

## Updater

Updater was/is intended to provide program update capabilities checking the GitHub for later version of the MeerK40t.


## Vectrace

Vectrace performs simple black/white image decomposition. Converting an image into a vector elements. This should allow for some tracing of image objects.
This can be invoked with `vectrace` in console.

## Winsleep

Winsleep is a windows only plugin that prevents Microsoft Windows OSes from entering sleepmode while projects are actively sending a laser project.