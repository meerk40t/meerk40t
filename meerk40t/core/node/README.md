# Nodes

The primary method of storing tree data for the elements object are within nodes. These tend to store all the required data for operations, elements, or other data objects within a project. There are three primary node types.

## RootNode

The Root is responsible for bootstrapping nodes into the required node form. If you are adding a new node type, you must place the relationship between node type and the node's class within the bootstrap so that these node types can be instanced through various methods. One instance of this class is usually persisted throughout the program's lifecycle.

## Node

Generic Abstract Class, this is usually the base for all class types. And includes functions that should be present for all nodes.

## ReferenceNode

The reference node is fundamental and referenced in the `._references` value of the nodes. These are simple pointers to other real nodes that occur within the tree. All reference nodes should have a `.node` attribute. 

# General Concepts

The operations nodes types all start with `op`, the util types all start with `util`, the element types all start with `elem`, and the branch types all start with `branch`. Some structural nodes like filenode and groupnode do don't have such prefixes. But, the general rule for prefixes is that if it's useful to know these types of nodes are similar, they can use one of the given prefixes.

