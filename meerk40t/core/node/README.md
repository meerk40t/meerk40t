# Nodes

The primary method of storing tree data for the elements object are within nodes. These tend to store all the required
data for operations, elements, or other data objects within a project. There are three primary node types. And many
minor operation types.

## RootNode

The root node is a structural node at the root, it allows node modification listeners and deals with various events
that occur within the tree as a whole. It also serves to hold and create the primary branches.

## Branches

There are currently three primary branches, operations, elements, and registration marks. These are structural and
should always be present.

### Operation Branch

The operations branch stores an ordered list of operations to be performed on the laser when `start` is executed.
This does not necessarily have a 1:1 with operations, but has a roughly similar relationship. Some types like
placements have an effect on the overall execution. The operations branch also stores info about the number of passes
or continuous passes, that should be conveyed to the LaserJob that is built during CutPlanning.

### Elements Branch

Elements branch stores elements which typically are displayed within the scene. These are usually raster images or
geometric shapes.

### Regmarks Branch

This branch stores Registration Marks. These are usually things seen within the scene but are not manipulated in the
ways the element branch is manipulated. This is intended to outline and highlight particular elements like the positions
within a jig without being sent to the laser.

## Node

Generic Abstract Class, this is usually the base for all class types. And includes functions that should be present for
all nodes. This provides bootstrapping from the `bootstrap.py` of all available node classes.

## ReferenceNode

The reference node is fundamental and referenced in the `._references` value of the nodes. These are simple pointers to
other real nodes that occur within the tree. All reference nodes should have a `.node` attribute. These are not copies
of particular nodes but pointers back to nodes that exist.

# General Concepts

The operations nodes types all start with `op`, the util types all start with `util`, the element types all start
with `elem`, effect nodes types start with `effect` and the branch types all start with `branch`. Some structural nodes
like filenode and groupnode don't have such prefixes. But, the general rule for prefixes is that if it's useful to know
these types of nodes are similar, they can use one of the given prefixes.



