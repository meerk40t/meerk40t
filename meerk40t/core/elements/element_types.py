"""
Helper list to define node types according to some criteria. For example, you'd likely want to delete
to only show up for the non-structural nodes. However, there's not a simple method for specifying that
and listing all the nodes a tree-op would apply to can result in a very long list.
These are those long list.
"""

from meerk40t.svgelements import (
    Circle,
    Ellipse,
    Path,
    Point,
    Polygon,
    Polyline,
    Rect,
    SimpleLine,
    SVGImage,
)


def get_type_from_element(element):
    if isinstance(element, Path):
        return "elem path"
    elif isinstance(element, SVGImage):
        return "elem image"
    elif isinstance(element, Rect):
        return "elem rect"
    elif isinstance(element, SimpleLine):
        return "elem line"
    elif isinstance(element, (Ellipse, Circle)):
        return "elem ellipse"
    elif isinstance(element, (Polygon, Polyline)):
        return "elem polyline"
    elif isinstance(element, Point):
        return "elem point"


non_structural_nodes = (
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
    "util origin",
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
    "util origin",
    "util output",
    "util input",
    "place point",
    "place current",
)
elem_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem geomstr",
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
    "elem geomstr",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "group",
    "file",
)
elem_ref_nodes = (
    "elem ellipse",
    "elem image",
    "elem path",
    "elem geomstr",
    "elem point",
    "elem polyline",
    "elem rect",
    "elem line",
    "elem text",
    "reference",
)
