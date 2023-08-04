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
Minimal integration of the Clipper2 library by Angus Johnson
    https://github.com/AngusJohnson/Clipper2
via the pyclipr library of Luke Parry
    https://github.com/drlukeparry/pyclipr
"""


def offset_path(
    path, offset_value=0, radial_connector=False, linearize=True, interpolation=500
):

    time_start = perf_counter()
    newpath = copy(path)
    time_end = perf_counter()
    print(f"Done, execution time: {time_end - time_start:.2f}s")
    return newpath


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
        "jointype", "j", type=str, help=_("join type: round, miter, square")
    )
    @self.console_option(
        "separate", "s", action="store_true", type=bool, help=_("deal with subpaths separately")
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
        jointype=None,
        separate=None,
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
        #     po.addPath(npp, pyclipr.JoinType.Miter, pyclipr.EndType.Polygon)
        #     # Apply the offsetting operation using a delta.
        #     offsetSquare = po.execute(10.0)
        #     print ("test for polygon...")
        #     print (npp)
        #     print (offsetSquare)
        #     print ("done...")
        #     po.clear()
        #     path=[ (100, 100), (1500, 100), (100, 1500), (1500, 1500) ]
        #     path = [(25801,  51602), (129005,  51602), (25801, 129005), (129005, 129005)]
        #     po.scaleFactor = int(1000)
        #     # add the path - ensuring to use Polygon for the endType argument
        #     npp = np.array(path)
        #     po.addPath(npp, pyclipr.JoinType.Miter, pyclipr.EndType.Square)
        #     # Apply the offsetting operation using a delta.
        #     offsetSquare = po.execute(10.0)
        #     print ("test for polyline...")
        #     print (npp)
        #     print (offsetSquare)
        #     print ("done...")

        def examine_and_add():
            if len(newpath) == 0:
                # print(f"Collapsed outline for {node.type}:{node.label}\n{np_points}")
                return
            # print (f"Apply offset: {offset}")
            idx = 0
            for subp in newpath:
                # Simplifypath is not peroperly exposed?!
                # if overall_polygon:
                #     ct_before = len(subp)
                #     pyclipr.simplifyPaths(subp, 0.05, False)
                #     ct_after = len(subp)
                #     print (f"Simplify provided: {ct_after} vs {ct_before}")
                result_list = []
                # Sometimes we get artifacts: a small array
                # with very small structures.
                # We try to identify and to discard them
                pt_count = len(subp)
                # 1 tat = 1/65535 of an inch
                # print (f"Subresult #{idx}: {pt_count} pts")
                idx += 1
                if pt_count < 2:
                    #  channel(f"Collapsed outline for {node.type}:{node.label}")
                    continue
                tolerance = 500 * 500 # Structures below 500 tats sidelength are ignored...
                maxd = 0
                lastpt = None
                for pt in subp:
                    if lastpt is not None:
                        dx = abs(lastpt[0] - pt[0])
                        dy = abs(lastpt[1] - pt[1])
                        maxd += dx*dx + dy*dy
                    lastpt = pt
                    if maxd > tolerance:
                        break

                if maxd < tolerance:
                    # print (f"Square-len with {pt_count} pts = {maxd}, Ignored...")
                    continue

                for pt in subp:
                    result_list.append(pt[0])
                    result_list.append(pt[1])
                # print (np_points)
                # print ("---")
                # print (subp)
                # print (result_list)
                # We do closing of the path ourselves...
                try:
                    p1x = result_list[0]
                    p1y = result_list[1]
                    p2x = result_list[-2]
                    p2y = result_list[-1]
                    dx = abs(p1x - p2x)
                    dy = abs(p1y - p2y)
                    if dx > 10 or dy > 10:
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

        # testroutine()
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        if interpolation is None:
            interpolation = 500
        if separate is None:
            separate = False
        if offset is None:
            offset = 0
        else:
            try:
                ll = Length(offset)
                offset = float(ll)
            except ValueError:
                offset = 0
        if jointype is None:
            jointype = "miter"
        jointype = jointype.lower()

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
            polygon_list = []
            if hasattr(node, "as_geometry"):
                # Let's get list of points with the
                # required interpolation density
                g = node.as_geometry()
                idx = 0
                for subg in g.as_contiguous():
                    node_points = list(subg.as_interpolated_points(interpolation))
                    flag = subg.is_closed()
                    # print (node_points, flag)
                    np_list.append(node_points)
                    polygon_list.append(flag)
                    # print (f"Adding structure #{idx}")
                    idx += 1
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
                polygon_list.append(True)

            clipr_offset.clear()
            overall_polygon = True
            for node_points, is_polygon in zip(np_list, polygon_list):
                # print (f"Add {'polygon' if is_polygon else 'polyline'}: {node_points}")
                if not is_polygon:
                    overall_polygon = False

                # There may be a smarter way to do this, but geomstr
                # provides an array of complex numbers. pyclipr on the other
                # hand would like to have points as (x, y) and not as (x + y * 1j)
                complex_array = np.array(node_points)
                temp = np.column_stack((complex_array.real, complex_array.imag))
                np_points = temp.astype(int)
                # np_points = np.array(node_points, np.cdouble)
                # lastx = 0
                # lasty = 0
                # for idx, p in enumerate(np_points):
                #     if p is None:
                #         print (f"There was an invalid point at #{idx}")
                #     elif p[0] is None:
                #         print (f"X was invalid at #{idx}: {p}")
                #     elif p[1] is None:
                #         print (f"Y was invalid at #{idx}: {p}")
                #     else:
                #         lastx = p[0]
                #         lasty = p[1]
                #         continue
                #     np_points[idx, 0] = lastx
                #     np_points[idx, 1] = lasty

                # add the path - ensuring to use Polygon for the endType argument
                if jointype.startswith("r"): # round
                    pyc_jointype = pyclipr.JoinType.Round
                    # endtype = pyclipr.EndType.Round
                elif jointype.startswith("s"): # square
                    pyc_jointype = pyclipr.JoinType.Square
                    # endtype = pyclipr.EndType.Square
                else:
                    pyc_jointype = pyclipr.JoinType.Miter
                    # endtype = pyclipr.EndType.Miter

                if is_polygon:
                    pyc_endtype = pyclipr.EndType.Polygon
                else:
                    pyc_endtype = pyclipr.EndType.Square

                # print ("add path:")
                # print (np_points)
                clipr_offset.addPath(np_points, pyc_jointype, pyc_endtype)

                if separate:
                    # Apply the offsetting operation using a delta.
                    newpath = clipr_offset.execute(offset)
                    # print ("result 1:")
                    # print (newpath)
                    examine_and_add()
                    clipr_offset.clear()

            if not separate:
                # Apply the offsetting operation using a delta.
                newpath = clipr_offset.execute(offset)
                # print ("result 2:")
                # print (newpath)
                examine_and_add()

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # ---- Let's add some CAG commands....
    @self.console_argument(
        "method",
        type=str,
        help=_(
            "method to use (one of union, difference, intersection, xor)"
        ),
    )
    @self.console_option(
        "filltype", "d",
        type=str,
        help=_(
            "filltype to use (one of evenodd, nonzero, negative, positive)"
        ),
    )
    @self.console_option(
        "interpolation", "i", type=int, help=_("interpolation points per segment")
    )
    @self.console_option(
        "keep", "k", action="store_true", type=bool, help=_("keep the original elements, will be removed by default")
    )
    @self.console_command(
        "clipper",
        help=_("create a logical combination of of the given elements"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_clipper(
        command,
        channel,
        _,
        method=None,
        filltype=None,
        interpolation=None,
        keep=None,
        data=None,
        post=None,
        **kwargs,
    ):

        def examine_and_add():
            if len(newpath) == 0:
                # print(f"Collapsed clipline for {node.type}:{node.label}\n{np_points}")
                return
            idx = 0
            allgeom = None
            for subp in newpath:
                result_list = []
                pt_count = len(subp)
                # print (f"{idx}#: {pt_count} pts")
                idx += 1
                if pt_count < 2:
                    continue
                # Sometimes we get artifacts: a small array
                # with very small structures.
                # We try to identify and to discard them
                tolerance = 500 * 500 # Structures below 500 tats sidelength are ignored...
                maxd = 0
                lastpt = None
                for pt in subp:
                    if lastpt is not None:
                        dx = abs(lastpt[0] - pt[0])
                        dy = abs(lastpt[1] - pt[1])
                        maxd += dx*dx + dy*dy
                    lastpt = pt
                    if maxd > tolerance:
                        break

                if maxd < tolerance:
                    # print (f"Artifact ignored: {maxd:.3f}")
                    continue

                for pt in subp:
                    result_list.append(pt[0])
                    result_list.append(pt[1])
                try:
                    p1x = result_list[0]
                    p1y = result_list[1]
                    p2x = result_list[-2]
                    p2y = result_list[-1]
                    dx = abs(p1x - p2x)
                    dy = abs(p1y - p2y)
                    if dx > 10 or dy > 10:
                        result_list.append(p1x)
                        result_list.append(p1y)
                except IndexError:
                    # channel(f"Invalid clipline for {node.type}:{node.label}")
                    continue
                geom = Geomstr.lines(*result_list)
                if allgeom is None:
                    allgeom = geom
                else:
                    # Add a end marker
                    allgeom.end()
                    allgeom.append(geom)
            # print (geom)
            if allgeom is not None:
                newnode = self.elem_branch.add(
                    geometry=allgeom, type="elem polyline", stroke=firstnode.stroke
                )
                newnode.stroke_width = UNITS_PER_PIXEL
                newnode.linejoin = Linejoin.JOIN_ROUND
                newnode.label = (
                    f"{long_method} of {firstnode.id if firstnode.label is None else firstnode.label}"
                )
                data_out.append(newnode)

        # def testroutine():
        #     # Tuple definition of a path
        #     path1 = [(0.0, 0.), (0, 105.1234), (100, 105.1234), (100, 0), (0, 0)]
        #     path2 = [(0, 0), (0, 50), (100, 50), (100, 0), (0,0)]

        #     # Create a clipping object
        #     pc = pyclipr.Clipper()
        #     pc.scaleFactor = int(1000)

        #     # Add the paths to the clipping object. Ensure the subject and clip arguments are set to differentiate
        #     # the paths during the Boolean operation. The final argument specifies if the path is
        #     # open.
        #     pc.addPath(np.array(path1), pyclipr.PathType.Subject)
        #     pc.addPath(np.array(path2), pyclipr.PathType.Clip)

        #     """ Test Polygon Clipping """
        #     # Below returns paths
        #     out1 = pc.execute(pyclipr.ClipType.Intersection, pyclipr.FillType.EvenOdd)
        #     out2 = pc.execute(pyclipr.ClipType.Union, pyclipr.FillType.EvenOdd)
        #     out3 = pc.execute(pyclipr.ClipType.Difference, pyclipr.FillType.EvenOdd)
        #     out4 = pc.execute(pyclipr.ClipType.Xor, pyclipr.FillType.EvenOdd)
        #     print("In:")
        #     print (path1)
        #     print (path2)
        #     print ("intersect")
        #     print (out1)
        #     print ("union")
        #     print (out2)
        #     print ("difference")
        #     print (out3)
        #     print ("xor")
        #     print (out4)


        #  testroutine()
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        # Sort data according to selection data so that first selected element becomes the master
        data.sort(key=lambda n: n.emphasized_time)

        if interpolation is None:
            interpolation = 500
        if method is None:
            method = "union"
        method = method.lower()
        if filltype is None:
            filltype = "evenodd"
        filltype = filltype.lower()
        if keep is None:
            keep = False

        # Create a clipper object
        clipr_clipper = pyclipr.Clipper()
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

        clipr_clipper.scaleFactor = factor

        data_out = list()
        firstnode = None
        np_list = []
        polygon_list = []
        for node in data:
            # print (f"Looking at {node.type} - {node.label}")
            if firstnode is None:
                firstnode = node
            if hasattr(node, "as_geometry"):
                # Let's get list of points with the
                # required interpolation density
                g = node.as_geometry()
                idx = 0
                for subg in g.as_contiguous():
                    node_points = list(subg.as_interpolated_points(interpolation))
                    flag = subg.is_closed()
                    # print (node_points, flag)
                    np_list.append(node_points)
                    polygon_list.append(flag)
                    # print (f"Adding structure #{idx} with {len(node_points)} pts")
                    idx += 1
            else:
                bb = node.bounds
                if bb is None:
                    # Node has no bounds or space, therefore no clipline.
                    return "elements", data_out
                node_points = (
                    bb[0] + bb[1] * 1j,
                    bb[0] + bb[3] * 1j,
                    bb[2] + bb[3] * 1j,
                    bb[2] + bb[1] * 1j,
                    bb[0] + bb[1] * 1j,
                )
                np_list.append(node_points)
                polygon_list.append(True)

        clipr_clipper.clear()
        first = True
        for node_points, is_polygon in zip(np_list, polygon_list):
            # print (f"Add {'polygon' if is_polygon else 'polyline'}: {node_points}")

            # There may be a smarter way to do this, but geomstr
            # provides an array of complex numbers. pyclipr on the other
            # hand would like to have points as (x, y) and not as (x + y * 1j)
            complex_array = np.array(node_points)
            temp = np.column_stack((complex_array.real, complex_array.imag))
            np_points = temp.astype(int)

            if first:
                first = False
                pyc_pathtype = pyclipr.PathType.Subject
            else:
                pyc_pathtype = pyclipr.PathType.Clip

            # print (f"Add path {pyc_pathtype} with {is_polygon}: {len(np_points)} pts")
            clipr_clipper.addPath(np_points, pyc_pathtype, not is_polygon)

        if method.startswith("d"):
            pyc_method = pyclipr.ClipType.Difference
            long_method = "Difference"
        elif method.startswith("i"):
            pyc_method = pyclipr.ClipType.Intersection
            long_method = "Intersection"
        elif method.startswith("x"):
            pyc_method = pyclipr.ClipType.Xor
            long_method = "Xor"
        else:
            pyc_method = pyclipr.ClipType.Union
            long_method = "Union"

        if filltype.startswith("no") or filltype.startswith("z"):
            pyc_filltype = pyclipr.FillType.NonZero
        elif filltype.startswith("p") or filltype.startswith("+"):
            pyc_filltype = pyclipr.FillType.Positive
        elif filltype.startswith("ne") or filltype.startswith("-"):
            pyc_filltype = pyclipr.FillType.Negative
        else:
            pyc_filltype = pyclipr.FillType.EvenOdd

        # print (f"Method={method} - {pyc_method}, filltype={filltype} - {pyc_filltype}")
        # Perform the clip operation
        newpath = clipr_clipper.execute(pyc_method, pyc_filltype)
        examine_and_add()

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
            if not keep:
                self.remove_nodes(data)

        return "elements", data_out


    # --------------------------- END COMMANDS ------------------------------
