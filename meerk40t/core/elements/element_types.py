"""
Helper list to define node types according to some criteria. For example, you'd likely want to delete
to only show up for the non-structural nodes. However, there's not a simple method for specifying that
and listing all the nodes a tree-op would apply to can result in a very long list.
These are those long list.
"""


non_structural_nodes = (
    "op cut",
    "op raster",
    "op image",
    "op engrave",
    "op dots",
    "op hatch",
    "effect hatch",
    "util console",
    "util wait",
    "util home",
    "util goto",
    "util output",
    "util input",
    "place point",
    "place current",
    "reference",
    "lasercode",
    "cutcode",
    "blob",
    "elem ellipse",
    "elem image",
    "elem path",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "file",
    "group",
)
op_parent_nodes = (
    "op cut",
    "op raster",
    "op image",
    "op engrave",
    "op dots",
    "op hatch",
    "effect hatch",
)
op_nodes = (
    "op cut",
    "op raster",
    "op image",
    "op engrave",
    "op dots",
    "op hatch",
    "util console",
    "util wait",
    "util home",
    "util goto",
    "util output",
    "util input",
    "place point",
    "place current",
)
place_nodes = (
    "place point",
    "place current",
)
elem_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
)
elem_group_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "effect hatch",
    "group",
    "file",
)
elem_ref_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "reference",
)
