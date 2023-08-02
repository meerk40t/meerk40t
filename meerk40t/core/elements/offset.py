"""
This adds console commands that deal with the creation of an offset
"""
from copy import copy
from math import atan2, tau
from time import perf_counter

from meerk40t.core.node.node import Linejoin
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.tools.geomstr import Geomstr
import pyclipr

"""
The following routines deal with the offset of an SVG path at a given distance D.
An offset or parallel curve can easily be established:
    - for a line segment by another line parallel and in distance D:
        Establish the two normals with length D on the end points and
        create the two new endpoints
    - for an arc segment: elongate rx and ry by D
To establish an offset for a quadratic or cubic bezier by another cubic bezier
is not possible so this requires approximation.
An acceptable approximation is proposed by Tiller and Hanson:
    P1 start point
    P2 end point
    C1 control point 1
    C2 control point 2
    You create the offset version of these 3 lines and look for their intersections:
        - offset to (P1 C1)  -> helper 1
        - offset to (C1 C2)  -> helper 2
        - offset to (P2 C2)  -> helper 3
        we establish P1-new
        the intersections between helper 1 and helper 2 is our new control point C1-new
        the intersections between helper 2 and helper 3 is our new control point C2-new



A good visual representation can be seen here:
https://feirell.github.io/offset-bezier/

The algorithm deals with the challenge as follows:
a) It walks through the subpaths of a given path so that we have a continuous curve
b) It looks at the different segment typs and deals with them,
generating a new offseted segement
c) Finally it stitches those segments together, treating for the simplifaction
"""

def offset_path(
    path, offset_value=0, radial_connector=False, linearize=True, interpolation=500
):

    time_start = perf_counter()
    results = []
    time_end = perf_counter()
    print (f"Done, execution time: {time_end - time_start:.2f}s")
    return results


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    @self.console_argument(
        "offset",
        type=str,
        help=_(
            "offset to line mm (positive values to left/outside, negative values to right/inside)"
        ),
    )
    @self.console_option(
        "radial", "r", action="store_true", type=bool, help=_("radial connector")
    )
    @self.console_option(
        "native",
        "n",
        action="store_true",
        type=bool,
        help=_("native path offset (use at you own risk)"),
    )
    @self.console_option(
        "interpolation", "i", type=int, help=_("interpolation points per segment")
    )
    @self.console_command(
        "offset",
        help=_("create an offset path for any of the given elements"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_offset_path(
        command,
        channel,
        _,
        offset=None,
        radial=None,
        native=False,
        interpolation=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        if native:
            linearize = False
        else:
            linearize = True
        if interpolation is None:
            interpolation = 500
        if offset is None:
            offset = 0
        else:
            try:
                ll = Length(offset)
                # Invert for right behaviour
                offset = -1.0 * float(ll)
            except ValueError:
                offset = 0
        if radial is None:
            radial = False
        data_out = list()
        for node in data:
            if hasattr(node, "as_path"):
                p = abs(node.as_path())
            else:
                bb = node.bounds
                if bb is None:
                    # Node has no bounds or space, therefore no offset outline.
                    return "elements", data_out
                p = Geomstr.rect(
                    x=bb[0], y=bb[1], width=bb[2] - bb[0], height=bb[3] - bb[1]
                ).as_path()

            node_path = offset_path(
                p,
                offset,
                radial_connector=radial,
                linearize=linearize,
                interpolation=interpolation,
            )
            node_path.validate_connections()
            newnode = self.elem_branch.add(
                path=node_path, type="elem path", stroke=node.stroke
            )
            newnode.stroke_width = UNITS_PER_PIXEL
            newnode.linejoin = Linejoin.JOIN_ROUND
            newnode.label = f"Offset of {node.id if node.label is None else node.label}"
            data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
