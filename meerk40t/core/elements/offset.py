"""
This adds console commands that deal with the creation of an offset

Minimal integration of the Clipper2 library by Angus Johnson
    https://github.com/AngusJohnson/Clipper2
via the pyclipr library of Luke Parry
    https://github.com/drlukeparry/pyclipr
"""

def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "invalidate":
        try:
            import pyclipr
        except ImportError:
            # print ("Clipper plugin could not load because pyclipr is not installed.")
            return True

    if lifecycle == "postboot":
        init_commands(kernel)

def init_commands(kernel):
    import numpy as np
    import pyclipr

    from meerk40t.core.node.node import Linejoin, Node
    from meerk40t.core.units import UNITS_PER_PIXEL, Length
    from meerk40t.tools.geomstr import Geomstr
    self = kernel.elements

    _ = kernel.translation

    class ClipperOffset:
        """
        Wraps around the pyclpr interface to clipper offset (inflate paths).

        Typical invocation:
            data = (node1, node2,)
            offs = ClipperOffset(interpolation=500)
            offs.add_nodes(data)
            offset = float(Length("2mm"))
            offs.process_data(offset, jointype="round", separate=False)
            for geom in offs.result_geometry():
                newnode = self.elem_branch.add(geometry=geom, type="elem polyline")

        """

        def __init__(self, interpolation=None):
            self.np_list = []
            self.polygon_list = []
            self._interpolation = None
            self.interpolation = interpolation
            self.any_open = False
            # Create a clipper object
            self.clipr_offset = pyclipr.ClipperOffset()
            self.newpath = None
            self._factor = 1000
            self.factor = self._factor

            # @staticmethod
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

        @property
        def interpolation(self):
            return self._interpolation

        @interpolation.setter
        def interpolation(self, value):
            if value is None:
                value = 500
            self._interpolation = 500

        @property
        def factor(self):
            return self._factor

        @factor.setter
        def factor(self, value):
            self._factor = value
            self.clipr_offset.scaleFactor = self._factor

        def clear(self):
            self.np_list = []
            self.polygon_list = []

        def add_geometries(self, geomlist):
            for g in geomlist:
                for subg in g.as_contiguous():
                    node_points = list(subg.as_interpolated_points(self.interpolation))
                    flag = subg.is_closed()
                    # print (node_points, flag)
                    self.np_list.append(node_points)
                    self.polygon_list.append(flag)

        def add_nodes(self, nodelist):
            # breaks down the path to a list of subgeometries.
            self.clear()
            # Set the scale factor to convert to internal integer representation
            # As mks internal variable representation is already based on tats
            # that should not be necessary
            bounds = Node.union_bounds(nodelist)
            factor = int(1000)
            if bounds[2] > 100000 or bounds[3] > 100000:
                factor = int(1)
            elif bounds[2] > 10000 or bounds[3] > 10000:
                factor = int(10)
            elif bounds[2] > 1000 or bounds[3] > 1000:
                factor = int(100)
            self.factor = factor
            geom_list = []
            for node in nodelist:
                # print (f"Looking at {node.type} - {node.label}")
                if hasattr(node, "as_geometry"):
                    # Let's get list of points with the
                    # required interpolation density
                    g = node.as_geometry()
                    geom_list.append(g)
                else:
                    bb = node.bounds
                    if bb is None:
                        # Node has no bounds or space, therefore no clipline.
                        continue
                    g = Geomstr.rect(bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1], rx=0, ry=0)
                    geom_list.append(g)
            self.add_geometries(geom_list)

        def add_path(self, path):
            # breaks down the path to a list of subgeometries.
            self.clear()
            # Set the scale factor to convert to internal integer representation
            # As mks internal variable representation is already based on tats
            # that should not be necessary
            bounds = path.bbox(transformed=True)
            factor = int(1000)
            if bounds[2] > 100000 or bounds[3] > 100000:
                factor = int(1)
            elif bounds[2] > 10000 or bounds[3] > 10000:
                factor = int(10)
            elif bounds[2] > 1000 or bounds[3] > 1000:
                factor = int(100)
            self.factor = factor
            geom_list = []
            g = Geomstr.svg(path)
            geom_list.append(g)
            self.add_geometries(geom_list)

        def process_data(self, offset, jointype="round", separate=False):
            self.clipr_offset.clear()
            self.newpath = None
            if jointype.startswith("r"):  # round
                pyc_jointype = pyclipr.JoinType.Round
            elif jointype.startswith("s"):  # square
                pyc_jointype = pyclipr.JoinType.Square
            else:
                pyc_jointype = pyclipr.JoinType.Miter
            for node_points, is_polygon in zip(self.np_list, self.polygon_list):
                # There may be a smarter way to do this, but geomstr
                # provides an array of complex numbers. pyclipr on the other
                # hand would like to have points as (x, y) and not as (x + y * 1j)
                complex_array = np.array(node_points)
                temp = np.column_stack((complex_array.real, complex_array.imag))
                np_points = temp.astype(int)

                # add the path - ensuring to use Polygon for the endType argument

                if is_polygon:
                    pyc_endtype = pyclipr.EndType.Polygon
                else:
                    pyc_endtype = pyclipr.EndType.Square

                self.clipr_offset.addPath(np_points, pyc_jointype, pyc_endtype)
                if separate:
                    # Apply the offsetting operation using a delta.
                    newp = self.clipr_offset.execute(offset)
                    if self.newpath is None:
                        self.newpath = list()
                    self.newpath.append(newp)
                    self.clipr_offset.clear()

            if not separate:
                # Apply the offsetting operation using a delta.
                self.newpath = self.clipr_offset.execute(offset)

        def result_geometry(self):
            if len(self.newpath) == 0:
                # print(f"Collapsed clipline for {node.type}:{node.label}\n{np_points}")
                return None
            if isinstance(self.newpath[0], (tuple, list)):
                # Can execute directly
                target = self.newpath
            else:
                # Create a temporary list
                target = (self.newpath,)

            idx = 0
            for newp in target:
                # print (f"Type of newp: {type(newp).__name__}")
                # print(newp)
                for subp in newp:
                    # print (f"Type of subp: {type(subp).__name__}")
                    # print (subp)
                    result_list = []
                    pt_count = len(subp)
                    # print (f"{idx}#: {pt_count} pts")
                    idx += 1
                    if pt_count < 2:
                        continue
                    # Sometimes we get artifacts: a small array
                    # with very small structures.
                    # We try to identify and to discard them
                    tolerance = int(
                        0.5 * self.factor * 0.5 * self.factor
                    )  # Structures below 500 tats sidelength are ignored...
                    maxd = 0
                    lastpt = None
                    had_error = False
                    for pt in subp:
                        if lastpt is not None:
                            try:
                                dx = abs(lastpt[0] - pt[0])
                                dy = abs(lastpt[1] - pt[1])
                            except IndexError:
                                # Invalid structure! Ignore
                                had_error = True
                                break
                            maxd += dx * dx + dy * dy
                        lastpt = pt
                        if maxd > tolerance:
                            break

                    if had_error or maxd < tolerance:
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
                    yield geom


    class ClipperCAG:
        """
        Wraps around the pyclpr interface to clipper to run clip operations:
        supported:
        method: Union, Difference, Intersect, Xor
        filltype: EvenOdd, Positive, Negative, NonZero

        Typical invocation:
            data = (node1, node2,)
            cag = ClipperCAG(interpolation=500)
            cag.add_nodes(data)
            cag.process_data(method="union", filltype="EvenOdd")
            geom = cag.result_geometry()
            newnode = self.elem_branch.add(geometry=geom, type="elem polyline")

        """

        def __init__(self, interpolation=None):
            # Create a clipper object
            self.clipr_clipper = pyclipr.Clipper()

            self.np_list = []
            self.polygon_list = []
            self._interpolation = None
            self.interpolation = interpolation
            self.any_open = False
            self.newpath = None
            self._factor = 1000
            self.factor = self._factor


            # @staticmethod
            # def testroutine():
            #     # Tuple definition of a path
            #     path_clip = [(0.0, 0.), (0, 105.1234), (100, 105.1234), (100, 0), (0, 0)]
            #     open1 = False
            #     # path_subject = [(0, 0), (0, 50), (100, 50), (100, 0), (0,0)]
            #     path_subject = [(0, 0), (300, 300)]
            #     open2 = True

            #     # Create a clipping object
            #     pc = pyclipr.Clipper()
            #     pc.scaleFactor = int(1000)

            #     # Add the paths to the clipping object. Ensure the subject and clip arguments are set to differentiate
            #     # the paths during the Boolean operation. The final argument specifies if the path is
            #     # open.
            #     pc.addPath(np.array(path_subject), pyclipr.PathType.Subject, open2)
            #     pc.addPath(np.array(path_clip), pyclipr.PathType.Clip, open1)

            #     """ Test Polygon Clipping """
            #     # Below returns paths
            #     out1 = pc.execute(pyclipr.ClipType.Intersection, pyclipr.FillType.EvenOdd)
            #     out2 = pc.execute(pyclipr.ClipType.Union, pyclipr.FillType.EvenOdd)
            #     out3 = pc.execute(pyclipr.ClipType.Difference, pyclipr.FillType.EvenOdd)
            #     out4 = pc.execute(pyclipr.ClipType.Xor, pyclipr.FillType.EvenOdd)
            #     # Return open paths...
            #     out5 = pc.execute(pyclipr.ClipType.Union, pyclipr.FillType.EvenOdd, returnOpenPaths=True)
            #     print("In:")
            #     print (path_clip)
            #     print (path_subject)
            #     print ("intersect")
            #     print (out1)
            #     print ("union")
            #     print (out2)
            #     print ("difference")
            #     print (out3)
            #     print ("xor")
            #     print (out4)
            #     print ("union with open paths")
            #     print (out5)

        @property
        def interpolation(self):
            return self._interpolation

        @interpolation.setter
        def interpolation(self, value):
            if value is None:
                value = 500
            self._interpolation = 500

        @property
        def factor(self):
            return self._factor

        @factor.setter
        def factor(self, value):
            self._factor = value
            self.clipr_clipper.scaleFactor = self._factor

        def clear(self):
            self.np_list = []
            self.polygon_list = []

        def add_nodes(self, nodelist):
            # breaks down the path to a list of subgeometries.
            self.clear()
            # Set the scale factor to convert to internal integer representation
            # As mks internal variable representation is already based on tats
            # that should not be necessary
            bounds = Node.union_bounds(nodelist)
            factor = int(1000)
            if bounds[2] > 100000 or bounds[3] > 100000:
                factor = int(1)
            elif bounds[2] > 10000 or bounds[3] > 10000:
                factor = int(10)
            elif bounds[2] > 1000 or bounds[3] > 1000:
                factor = int(100)
            self.factor = factor
            for node in nodelist:
                # print (f"Looking at {node.type} - {node.label}")
                if hasattr(node, "as_geometry"):
                    # Let's get list of points with the
                    # required interpolation density
                    g = node.as_geometry()
                    idx = 0
                    for subg in g.as_contiguous():
                        node_points = list(subg.as_interpolated_points(self.interpolation))
                        flag = subg.is_closed()
                        # print (node_points, flag)
                        self.np_list.append(node_points)
                        self.polygon_list.append(flag)
                        # print (f"Adding structure #{idx} with {len(node_points)} pts")
                        idx += 1
                else:
                    bb = node.bounds
                    if bb is None:
                        # Node has no bounds or space, therefore no clipline.
                        continue
                    node_points = (
                        bb[0] + bb[1] * 1j,
                        bb[0] + bb[3] * 1j,
                        bb[2] + bb[3] * 1j,
                        bb[2] + bb[1] * 1j,
                        bb[0] + bb[1] * 1j,
                    )
                    self.np_list.append(node_points)
                    self.polygon_list.append(True)

        def _add_data(self):
            self.clipr_clipper.clear()
            first = True
            self.any_open = False
            for node_points, is_polygon in zip(self.np_list, self.polygon_list):
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
                if not is_polygon:
                    self.any_open = True
                self.clipr_clipper.addPath(np_points, pyc_pathtype, not is_polygon)

        def process_data(self, method, filltype):
            self._add_data()
            if method.startswith("d"):
                pyc_method = pyclipr.ClipType.Difference
            elif method.startswith("i"):
                pyc_method = pyclipr.ClipType.Intersection
            elif method.startswith("x"):
                pyc_method = pyclipr.ClipType.Xor
            else:
                pyc_method = pyclipr.ClipType.Union
            if filltype.startswith("no") or filltype.startswith("z"):
                pyc_filltype = pyclipr.FillType.NonZero
            elif filltype.startswith("p") or filltype.startswith("+"):
                pyc_filltype = pyclipr.FillType.Positive
            elif filltype.startswith("ne") or filltype.startswith("-"):
                pyc_filltype = pyclipr.FillType.Negative
            else:
                pyc_filltype = pyclipr.FillType.EvenOdd

            if self.any_open and pyc_method in (pyclipr.ClipType.Union,):
                self.newpath = self.clipr_clipper.execute(
                    pyc_method, pyc_filltype, returnOpenPaths=True
                )
            else:
                self.newpath = self.clipr_clipper.execute(pyc_method, pyc_filltype)

        def result_geometry(self):
            if len(self.newpath) == 0:
                # print(f"Collapsed clipline for {node.type}:{node.label}\n{np_points}")
                return None
            if isinstance(self.newpath[0], (tuple, list)):
                # Can execute directly
                target = self.newpath
            else:
                # Create a temporary list
                target = (self.newpath,)

            idx = 0
            allgeom = None
            for newp in target:
                # print (f"Type of newp: {type(newp).__name__}")
                # print(newp)
                for subp in newp:
                    # print (f"Type of subp: {type(subp).__name__}")
                    # print (subp)
                    result_list = []
                    pt_count = len(subp)
                    # print (f"{idx}#: {pt_count} pts")
                    idx += 1
                    if pt_count < 2:
                        continue
                    # Sometimes we get artifacts: a small array
                    # with very small structures.
                    # We try to identify and to discard them
                    tolerance = (
                        0.5 * self.factor * 0.5 * self.factor
                    )  # Structures below 500 tats sidelength are ignored...
                    maxd = 0
                    lastpt = None
                    had_error = False
                    for pt in subp:
                        if lastpt is not None:
                            try:
                                dx = abs(lastpt[0] - pt[0])
                                dy = abs(lastpt[1] - pt[1])
                            except IndexError:
                                # Invalid structure! Ignore
                                had_error = True
                                break
                            maxd += dx * dx + dy * dy
                        lastpt = pt
                        if maxd > tolerance:
                            break

                    if had_error or maxd < tolerance:
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
            yield allgeom


    def offset_path(self, path, offset_value=0):
        # As this oveloading a regular method in a class
        # it needs to have the very same definition (including the class
        # reference self)
        offs = ClipperOffset(interpolation=500)
        offs.add_path(path)
        offs.process_data(offset_value, jointype="round", separate=False)
        p = None
        for g in offs.result_geometry():
            if g is not None:
                p = g.as_path()
                break
        if p is None:
            p = path
        return p

    classify_new = self.post_classify
    # We are pathing the class in general, so that it can use the new functionality
    from meerk40t.core.node.op_cut import CutOpNode
    CutOpNode.offset_routine = offset_path

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
        "separate",
        "s",
        action="store_true",
        type=bool,
        help=_("deal with subpaths separately"),
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
        if offset == 0.0:
            channel("Invalid offset, nothing to do")
            return
        if jointype is None:
            jointype = "miter"
        jointype = jointype.lower()
        default_stroke = None
        for node in data:
            if hasattr(node, "stroke"):
                default_stroke = node.stroke
                break
        if default_stroke is None:
            default_stroke = self._default_stroke
        data_out = []
        c_off = ClipperOffset(interpolation=interpolation)
        c_off.add_nodes(data)
        c_off.process_data(offset, jointype=jointype, separate=separate)
        for geom in c_off.result_geometry():
            if geom is not None:
                newnode = self.elem_branch.add(
                    geometry=geom, type="elem polyline",
                    stroke=default_stroke)
                newnode.stroke_width = UNITS_PER_PIXEL
                newnode.linejoin = Linejoin.JOIN_ROUND
                newnode.label = f"Offset: {Length(offset).length_mm}"
                data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # ---- Let's add some CAG commands....
    @self.console_argument(
        "method",
        type=str,
        help=_("method to use (one of union, difference, intersection, xor)"),
    )
    @self.console_option(
        "filltype",
        "f",
        type=str,
        help=_("filltype to use (one of evenodd, nonzero, negative, positive)"),
    )
    @self.console_option(
        "interpolation", "i", type=int, help=_("interpolation points per segment")
    )
    @self.console_option(
        "keep",
        "k",
        action="store_true",
        type=bool,
        help=_("keep the original elements, will be removed by default"),
    )
    @self.console_command(
        "clipper",
        help=_("create a logical combination of the given elements"),
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

        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No elements selected"))
            return "elements", data
        # Sort data according to selection data so that first selected element becomes the master
        data.sort(key=lambda n: n.emphasized_time)
        firstnode = data[0]

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

        if method.startswith("d"):
            long_method = "Difference"
        elif method.startswith("i"):
            long_method = "Intersection"
        elif method.startswith("x"):
            long_method = "Xor"
        else:
            long_method = "Union"

        if filltype.startswith("no") or filltype.startswith("z"):
            long_filltype = "NonZero"
        elif filltype.startswith("p") or filltype.startswith("+"):
            long_filltype = "Positive"
        elif filltype.startswith("ne") or filltype.startswith("-"):
            long_filltype = "Negative"
        else:
            long_filltype = "EvenOdd"

        channel(f"Method={long_method}, filltype={long_filltype}")

        data_out = list()

        # Create a clipper object
        clipper = ClipperCAG(interpolation=interpolation)
        clipper.add_nodes(data)
        # Perform the clip operation
        clipper.process_data(method=method, filltype=filltype)
        for geom in clipper.result_geometry():
            if geom is not None:
                newnode = self.elem_branch.add(
                    geometry=geom, type="elem polyline", stroke=firstnode.stroke
                )
                newnode.stroke_width = UNITS_PER_PIXEL
                newnode.linejoin = Linejoin.JOIN_ROUND
                newnode.label = f"{long_method} of {firstnode.id if firstnode.label is None else firstnode.label}"
                data_out.append(newnode)

        # Newly created! Classification needed?
        if len(data_out) > 0:
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
            if not keep:
                self.remove_nodes(data)

        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
