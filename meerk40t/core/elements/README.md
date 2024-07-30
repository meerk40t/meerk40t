## Elements

The elements modules governs all the interactions with the various nodes, as well as dealing with tree information.
This serves effectively as the datastructure that stores all information about any active project. This includes
several smaller functional pieces like Penbox and Wordlists.

The tree and all data in it are parts of elements.

Most submodules in Elements deal with registering console commands dealing with some particular smaller aspect.

### Align

Alignment based commands for elements

### Branches

Commands concerning elements, operations, and regmark branches and their interactions.

### Clipboard

Manipulation of the clipboard in element which can temporarily store some elements.

### Tree Ops

The Tree ops are the manipulations of the tree nodes with various right-click selection commands that are discovered
through filtering the node type and finding the relevant and valid registered tree operations. These can be accessed
through the console with the `tree` commands.

### Elements

Primary element service that stores all the related data.

### Grid

Gridlike commands and some advanced duplication routines.

### Material

Materials database information to load and save different operations.

### Notes

Notes are stored information about a project. These are usually viewed on loading of a file and can contain whatever
relevant data is required.

### Offset

The offset logic deals with the shape offset implementation for how particular elements make an offset path.

### Penbox

Penboxes are special operations in a list. These are expected to be useful for per-loop command changes.

### Placements

Placements deals with command logic for adding placements to a scene.

### Render

Render and vectorize commands which usually use the rendering engine in wxPython and/or the various vectorization
routines.

### Shapes

Shapes are within the element branch and usually concerned with making or manipulating different shape elements.

### Trace

Operations concerned with running job, and various measurements of the would-be job.

### Tree Commands

There are several very useful operations that can be done with tree manipulation and specific functions called on the
specific nodes themselves. These console commands gives you access to those functions via the console, so they are
available in pure CLI.

### Undo/Redo

The undo/redo commands are primarily concerned with the undo stack commands and restoring and saving the tree state

### Wordlist

The wordlist commands concern various text replace wordlist items.
