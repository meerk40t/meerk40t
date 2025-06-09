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
    "effect hatch",
    "effect wobble",
    "effect warp",
    "util console",
    "util wait",
    "util home",
    "util goto",
    "util output",
    "util input",
    "place point",
    "place current",
    "reference",
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
    "image raster",
    "file",
    "group",
)
op_parent_nodes = (
    "op cut",
    "op raster",
    "op image",
    "op engrave",
    "op dots",
)
op_image_nodes = (
    "op raster",
    "op image",
)
op_vector_nodes = (
    "op cut",
    "op engrave",
)
op_burnable_nodes =(
    "op cut",
    "op engrave",
    "op dots",
    "op raster",
    "op image",
)
op_nodes = (
    "op cut",
    "op raster",
    "op image",
    "op engrave",
    "op dots",
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
effect_nodes = ("effect hatch", "effect wobble", "effect warp")
image_nodes = ("image raster", "image processed", "elem image")
elem_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "image raster",
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
    "image raster",
    "effect hatch",
    "effect wobble",
    "effect warp",
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
    "image raster",
    "effect hatch",
    "effect wobble",
    "effect warp",
    "reference",
)
