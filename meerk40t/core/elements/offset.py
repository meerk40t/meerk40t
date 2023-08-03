"""
This adds console commands that deal with the creation of an offset
"""
from copy import copy
from math import atan2, tau
from time import perf_counter

import numpy as np
import pyclipr

from meerk40t.core.node.node import Linejoin, Node
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.tools.geomstr import Geomstr

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
    print(f"Done, execution time: {time_end - time_start:.2f}s")
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
        interpolation=None,
        data=None,
        post=None,
        **kwargs,
    ):

        # def testroutine():
        #     # Tuple definition of a path
        #     path = [(0.0, 0.), (100, 0), (100, 100), (0, 100), (0, 0)]
        #     # Create an offsetting object
        #     po = pyclipr.ClipperOffset()
        #     # Set the scale factor to convert to internal integer representation
        #     po.scaleFactor = int(1000)
        #     # add the path - ensuring to use Polygon for the endType argument
        #     npp = np.array(path)
        #     po.addPath(npp, pyclipr.Miter, pyclipr.Polygon)
        #     # Apply the offsetting operation using a delta.
        #     offsetSquare = po.execute(10.0)
        #     print ("test...")
        #     print (npp)
        #     print (offsetSquare)
        #     print ("done...")

        # testroutine()
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        if interpolation is None:
            interpolation = 500
        if offset is None:
            offset = 0
        else:
            try:
                ll = Length(offset)
                offset = float(ll)
            except ValueError:
                offset = 0
        if radial is None:
            radial = False

        # Create an offsetting object
        clipr_offset = pyclipr.ClipperOffset()
        # Set the scale factor to convert to internal integer representation
        # As mks internal variable representation is already based on tats
        # that should not be necessary
        bounds = Node.union_bounds(data)
        factor = int(1000)
        if bounds[2] > 100000 or bounds[3] > 100000:
            factor = int(1)
        elif bounds[2] > 10000 or bounds[3] > 10000:
            factor = int(10)
        elif bounds[2] > 1000 or bounds[3] > 1000:
            factor = int(100)

        clipr_offset.scaleFactor = factor

        data_out = list()
        for node in data:
            np_list = []
            if hasattr(node, "as_geometry"):
                # Let's get list of points with the
                # required interpolation density
                g = node.as_geometry()
                idx = 0
                for subg in g.as_subpaths():
                    node_points = list(subg.as_interpolated_points(interpolation))
                    np_list.append(node_points)
                    mp = max(np_list)
            else:
                bb = node.bounds
                if bb is None:
                    # Node has no bounds or space, therefore no offset outline.
                    return "elements", data_out
                node_points = (
                    bb[0] + bb[1] * 1j,
                    bb[0] + bb[3] * 1j,
                    bb[2] + bb[3] * 1j,
                    bb[2] + bb[1] * 1j,
                    bb[0] + bb[1] * 1j,
                )
                np_list.append(node_points)

            clipr_offset.clear()
            for node_points in np_list:
                # There may be a smarter way to do this, but geomstr
                # provides an array of complex numbers. pyclipr on the other
                # hand would like to have points as (x, y) and not as (x + y * 1j)
                complex_array = np.array(node_points)
                np_points = np.column_stack((complex_array.real, complex_array.imag))
                # np_points = np.array(node_points, np.cdouble)
                lastx = 0
                lasty = 0
                for idx, p in enumerate(np_points):
                    if p is None:
                        print (f"There was an invalid point at #{idx}")
                    elif p[0] is None:
                        print (f"X was invalid at #{idx}: {p}")
                    elif p[1] is None:
                        print (f"Y was invalid at #{idx}: {p}")
                    else:
                        lastx = p[0]
                        lasty = p[1]
                        continue
                    np_points[idx, 0] = lastx
                    np_points[idx, 1] = lasty

                # add the path - ensuring to use Polygon for the endType argument
                if radial:
                    clipr_offset.addPath(np_points, pyclipr.Round, pyclipr.Polygon)
                else:
                    clipr_offset.addPath(np_points, pyclipr.Miter, pyclipr.Polygon)

            # Apply the offsetting operation using a delta.
            newpath = clipr_offset.execute(offset)
            if len(newpath) == 0:
                channel(f"Collapsed outline for {node.type}:{node.label}")
                continue
            # print (f"Apply offset: {offset}")
            for subp in newpath:
                #  print (f"Type: {type(subp).__name__}")
                result_list = []
                for pt in subp:
                    result_list.append(pt[0])
                    result_list.append(pt[1])
                if len(result_list) == 0:
                    channel(f"Collapsed outline for {node.type}:{node.label}")
                    continue
                # print (np_points)
                # print ("---")
                # print (subp)
                # print (result_list)
                try:
                    p1x = result_list[0]
                    p1y = result_list[1]
                    p2x = result_list[-2]
                    p2y = result_list[-1]
                    dx = abs(p1x - p2x)
                    dy = abs(p1y - p2y)
                    if dx > 1e-3 or dy > 1e-3:
                        result_list.append(p1x)
                        result_list.append(p1y)
                except IndexError:
                    channel(f"Invalid outline for {node.type}:{node.label}")
                    continue

                geom = Geomstr.lines(*result_list)
                # print (geom)
                newnode = self.elem_branch.add(
                    geometry=geom, type="elem polyline", stroke=node.stroke
                )
                newnode.stroke_width = UNITS_PER_PIXEL
                newnode.linejoin = Linejoin.JOIN_ROUND
                newnode.label = (
                    f"Offset of {node.id if node.label is None else node.label}"
                )
                data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
