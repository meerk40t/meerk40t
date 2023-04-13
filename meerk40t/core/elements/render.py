"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from copy import copy
from math import isinf

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.node import Fillrule, Linejoin, Node
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_PIXEL, Length
from meerk40t.svgelements import Color, Matrix

from .element_types import *


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    @self.console_option("dpi", "d", default=500, type=float)
    @self.console_command(
        "render",
        help=_("Create a raster image from the given elements"),
        input_type=(None, "elements"),
        output_type="image",
    )
    def render_elements(command, channel, _, dpi=500.0, data=None, post=None, **kwargs):
        if data is None:
            data = list(self.elems(emphasized=True))
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        bounds = Node.union_bounds(data, attr="paint_bounds")
        # bounds_regular = Node.union_bounds(data)
        # for idx in range(4):
        #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)

        image = make_raster(
            data,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])

        image_node = ImageNode(image=image, matrix=matrix, dpi=dpi)
        self.elem_branch.add_node(image_node)
        self.signal("refresh_scene", "Scene")
        data = [image_node]
        # Newly created! Classification needed?
        post.append(classify_new(data))
        return "image", [image_node]

    @self.console_option(
        "dpi", "d", help=_("interim image resolution"), default=500, type=float
    )
    @self.console_option(
        "turnpolicy",
        "z",
        type=str,
        default="minority",
        help=_("how to resolve ambiguities in path decomposition"),
    )
    @self.console_option(
        "turdsize",
        "t",
        type=int,
        default=2,
        help=_("suppress speckles of up to this size (default 2)"),
    )
    @self.console_option(
        "alphamax", "a", type=float, default=1, help=_("corner threshold parameter")
    )
    @self.console_option(
        "opticurve",
        "n",
        type=bool,
        action="store_true",
        help=_("turn off curve optimization"),
    )
    @self.console_option(
        "opttolerance",
        "O",
        type=float,
        help=_("curve optimization tolerance"),
        default=0.2,
    )
    @self.console_option(
        "color",
        "C",
        type=Color,
        help=_("set foreground color (default Black)"),
    )
    @self.console_option(
        "invert",
        "i",
        type=bool,
        action="store_true",
        help=_("invert bitmap"),
    )
    @self.console_option(
        "blacklevel",
        "k",
        type=float,
        default=0.5,
        help=_("blacklevel?!"),
    )
    @self.console_command(
        "vectorize",
        help=_("Convert given elements to a path"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def vectorize_elements(
        command,
        channel,
        _,
        dpi=500.0,
        turnpolicy=None,
        turdsize=None,
        alphamax=None,
        opticurve=None,
        opttolerance=None,
        color=None,
        invert=None,
        blacklevel=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if data is None:
            data = list(self.elems(emphasized=True))
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        make_vector = self.lookup("render-op/make_vector")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        if not make_vector:
            channel(_("No vectorization engine could be found."))
            return

        policies = {
            "black": 0,  # POTRACE_TURNPOLICY_BLACK
            "white": 1,  # POTRACE_TURNPOLICY_WHITE
            "left": 2,  # POTRACE_TURNPOLICY_LEFT
            "right": 3,  # POTRACE_TURNPOLICY_RIGHT
            "minority": 4,  # POTRACE_TURNPOLICY_MINORITY
            "majority": 5,  # POTRACE_TURNPOLICY_MAJORITY
            "random": 6,  # POTRACE_TURNPOLICY_RANDOM
        }

        if turnpolicy not in policies:
            turnpolicy = "minority"
        ipolicy = policies[turnpolicy]

        if turdsize is None:
            turdsize = 2
        if alphamax is None:
            alphamax = 1
        if opticurve is None:
            opticurve = True
        if opttolerance is None:
            opttolerance = 0.2
        if color is None:
            color = Color("black")
        if invert is None:
            invert = False
        if blacklevel is None:
            blacklevel = 0.5

        bounds = Node.union_bounds(data, attr="paint_bounds")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)

        image = make_raster(
            data,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        path = make_vector(
            image,
            interpolationpolicy=ipolicy,
            invert=invert,
            turdsize=turdsize,
            alphamax=alphamax,
            opticurve=opticurve,
            opttolerance=opttolerance,
            color=color,
            blacklevel=blacklevel,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        path.transform *= Matrix(matrix)
        node = self.elem_branch.add(
            path=abs(path),
            stroke_width=0,
            stroke_scaled=False,
            type="elem path",
            fillrule=Fillrule.FILLRULE_NONZERO,
            linejoin=Linejoin.JOIN_ROUND,
        )
        # Newly created! Classification needed?
        data_out = [node]
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")

        return "elements", data_out

    @self.console_option(
        "dpi", "d", help=_("interim image resolution"), default=500, type=float
    )
    @self.console_option(
        "turnpolicy",
        "z",
        type=str,
        default="minority",
        help=_("how to resolve ambiguities in path decomposition"),
    )
    @self.console_option(
        "turdsize",
        "t",
        type=int,
        default=2,
        help=_("suppress speckles of up to this size (default 2)"),
    )
    @self.console_option(
        "alphamax", "a", type=float, default=1, help=_("corner threshold parameter")
    )
    @self.console_option(
        "opticurve",
        "n",
        type=bool,
        action="store_true",
        help=_("turn off curve optimization"),
    )
    @self.console_option(
        "opttolerance",
        "O",
        type=float,
        help=_("curve optimization tolerance"),
        default=0.2,
    )
    @self.console_option(
        "color",
        "C",
        type=Color,
        help=_("set foreground color (default Black)"),
    )
    @self.console_option(
        "invert",
        "i",
        type=bool,
        action="store_true",
        help=_("invert bitmap"),
    )
    @self.console_option(
        "blacklevel",
        "k",
        type=float,
        default=0.5,
        help=_("blacklevel?!"),
    )
    @self.console_option(
        "outer",
        "u",
        type=bool,
        action="store_true",
        help=_("Only outer line"),
    )
    @self.console_option(
        "steps",
        "x",
        type=int,
        default=1,
        help=_("How many offsetlines (default 1)"),
    )
    @self.console_option(
        "debug",
        "d",
        type=bool,
        action="store_true",
        help=_("Preserve intermediary objects"),
    )
    @self.console_argument("offset", type=Length, help="Offset distance")
    @self.console_command(
        "outline",
        help=_("Create an outline path at the inner and outer side of a path"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_outline(
        command,
        channel,
        _,
        offset=None,
        dpi=500.0,
        turnpolicy=None,
        turdsize=None,
        alphamax=None,
        opticurve=None,
        opttolerance=None,
        color=None,
        invert=None,
        blacklevel=None,
        outer=None,
        steps=None,
        debug=False,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Phase 1: We create a rendered image of the data, then we vectorize
        this representation
        Phase 2: This path will then be adjusted by applying
        altered stroke-widths and rendered and vectorized again.

        This two phase approach is required as not all nodes have
        a proper stroke-width that can be adjusted (eg text or images...)

        The subvariant --outer requires one additional pass where we disassemble
        the first outline and fill the subpaths, This will effectively deal with
        donut-type shapes

        The need for --inner was't high on my priority list (as it is somwhat
        difficult to implement, --outer just uses a clever hack to deal with
        topology edge cases. So if we are in need of inner we need to create
        the outline shape, break it in subpaths and delete the outer shapes
        manually. Sorry.
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if data is None or len(data) == 0:
            channel(_("No elements to outline."))
            return
        if debug is None:
            debug = False
        reverse = self.classify_reverse
        if reverse:
            data = list(reversed(data))
        make_raster = self.lookup("render-op/make_raster")
        make_vector = self.lookup("render-op/make_vector")
        if not make_raster:
            channel(_("No renderer is registered to perform render."))
            return
        if not make_vector:
            channel(_("No vectorization engine could be found."))
            return

        policies = {
            "black": 0,  # POTRACE_TURNPOLICY_BLACK
            "white": 1,  # POTRACE_TURNPOLICY_WHITE
            "left": 2,  # POTRACE_TURNPOLICY_LEFT
            "right": 3,  # POTRACE_TURNPOLICY_RIGHT
            "minority": 4,  # POTRACE_TURNPOLICY_MINORITY
            "majority": 5,  # POTRACE_TURNPOLICY_MAJORITY
            "random": 6,  # POTRACE_TURNPOLICY_RANDOM
        }

        if turnpolicy not in policies:
            turnpolicy = "minority"
        ipolicy = policies[turnpolicy]

        if turdsize is None:
            turdsize = 2
        if alphamax is None:
            alphamax = 1
        if opticurve is None:
            opticurve = True
        if opttolerance is None:
            opttolerance = 0.2
        if color is None:
            pathcolor = Color("blue")
        else:
            pathcolor = color
        if invert is None:
            invert = False
        if blacklevel is None:
            blacklevel = 0.5
        if offset is None:
            offset = self.length("5mm")
        else:
            offset = self.length(offset)
        if steps is None or steps < 1:
            steps = 1
        if outer is None:
            outer = False
        outputdata = []
        mydata = []
        for node in data:
            if outer and hasattr(node, "fill"):
                e = copy(node)
                e.fill = Color("black")
                if hasattr(e, "stroke"):
                    e.stroke = Color("black")
                if hasattr(e, "stroke_width") and e.stroke_width == 0:
                    e.stroke_width = UNITS_PER_PIXEL
                if hasattr(e, "fillrule"):
                    e.fillrule = 0
                mydata.append(e)
            else:
                e = copy(node)
                if hasattr(e, "stroke_width") and e.stroke_width == 0:
                    e.stroke_width = UNITS_PER_PIXEL
                mydata.append(e)
        if debug:
            for node in mydata:
                node.label = "Phase 0: Initial copy"
                self.elem_branch.add_node(node)

        ###############################################
        # Phase 1: render and vectorize first outline
        ###############################################
        bounds = Node.union_bounds(mydata, attr="paint_bounds")
        # bounds_regular = Node.union_bounds(data)
        # for idx in range(4):
        #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
        if bounds is None:
            return
        xmin, ymin, xmax, ymax = bounds
        if isinf(xmin):
            channel(_("No bounds for selected elements."))
            return
        width = xmax - xmin
        height = ymax - ymin

        dots_per_units = dpi / UNITS_PER_INCH
        new_width = width * dots_per_units
        new_height = height * dots_per_units
        new_height = max(new_height, 1)
        new_width = max(new_width, 1)
        dpi = 500

        data_image = make_raster(
            mydata,
            bounds=bounds,
            width=new_width,
            height=new_height,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        image_node_1 = ImageNode(
            image=data_image, matrix=matrix, dpi=dpi, label="Phase 1 render image"
        )

        path = make_vector(
            data_image,
            interpolationpolicy=ipolicy,
            invert=invert,
            turdsize=turdsize,
            alphamax=alphamax,
            opticurve=opticurve,
            opttolerance=opttolerance,
            color=color,
            blacklevel=blacklevel,
        )
        matrix = Matrix.scale(width / new_width, height / new_height)
        matrix.post_translate(bounds[0], bounds[1])
        path.transform *= Matrix(matrix)
        data_node = PathNode(
            path=abs(path),
            stroke_width=1,
            stroke=Color("black"),
            stroke_scaled=False,
            fill=None,
            # fillrule=Fillrule.FILLRULE_NONZERO,
            linejoin=Linejoin.JOIN_ROUND,
            label="Phase 1 Outline path",
        )
        data_node.fill = None
        # If you want to debug the phases then uncomment the following lines to
        # see the interim path and interim render image
        if debug:
            self.elem_branch.add_node(data_node)
            self.elem_branch.add_node(image_node_1)

        copy_data = [image_node_1, data_node]

        ################################################################
        # Phase 2: change outline witdh and render and vectorize again
        ################################################################
        for numidx in range(steps):
            data_node.stroke_width += 2 * offset
            data_node.set_dirty_bounds()
            pb = data_node.paint_bounds
            bounds = Node.union_bounds(copy_data, attr="paint_bounds")
            # print (f"{pb} - {bounds}")
            if bounds is None:
                return
            # bounds_regular = Node.union_bounds(copy_data)
            # for idx in range(4):
            #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds[idx]:.2f}")
            xmin, ymin, xmax, ymax = bounds
            if isinf(xmin):
                channel(_("No bounds for selected elements."))
                return
            width = xmax - xmin
            height = ymax - ymin

            dots_per_units = dpi / UNITS_PER_INCH
            new_width = width * dots_per_units
            new_height = height * dots_per_units
            new_height = max(new_height, 1)
            new_width = max(new_width, 1)
            dpi = 500

            image_2 = make_raster(
                copy_data,
                bounds=bounds,
                width=new_width,
                height=new_height,
            )
            matrix = Matrix.scale(width / new_width, height / new_height)
            matrix.post_translate(bounds[0], bounds[1])
            image_node_2 = ImageNode(
                image=image_2, matrix=matrix, dpi=dpi, label="Phase 2 render image"
            )

            path_2 = make_vector(
                image_2,
                interpolationpolicy=ipolicy,
                invert=invert,
                turdsize=turdsize,
                alphamax=alphamax,
                opticurve=opticurve,
                opttolerance=opttolerance,
                color=color,
                blacklevel=blacklevel,
            )
            matrix = Matrix.scale(width / new_width, height / new_height)
            matrix.post_translate(bounds[0], bounds[1])
            path_2.transform *= Matrix(matrix)
            # That's our final path (or is it? Depends on outer...)
            path_final = path_2
            data_node_2 = PathNode(
                path=abs(path_2),
                stroke_width=1,
                stroke=Color("black"),
                stroke_scaled=False,
                fill=None,
                # fillrule=Fillrule.FILLRULE_NONZERO,
                linejoin=Linejoin.JOIN_ROUND,
                label="Phase 2 Outline path",
            )
            data_node_2.fill = None

            # If you want to debug the phases then uncomment the following line to
            # see the interim image
            if debug:
                self.elem_branch.add_node(image_node_2)
                self.elem_branch.add_node(data_node_2)
            #######################################################
            # Phase 3: render and vectorize last outline for outer
            #######################################################
            if outer:
                # Generate the outline, break it into subpaths
                copy_data = []
                # Now break it into subpaths...
                for pasp in path_final.as_subpaths():
                    subpath = Path(pasp)
                    data_node = PathNode(
                        path=abs(subpath),
                        stroke_width=1,
                        stroke=Color("black"),
                        stroke_scaled=False,
                        fill=Color("black"),
                        # fillrule=Fillrule.FILLRULE_NONZERO,
                        linejoin=Linejoin.JOIN_ROUND,
                        label="Phase 3 Outline subpath",
                    )
                    # This seems to be necessary to make sure the fill sticks
                    data_node.fill = Color("black")
                    copy_data.append(data_node)
                    # If you want to debug the phases then uncomment the following lines to
                    # see the interim path nodes
                    if debug:
                        self.elem_branch.add_node(data_node)

                bounds = Node.union_bounds(copy_data, attr="paint_bounds")
                # bounds_regular = Node.union_bounds(data)
                # for idx in range(4):
                #     print (f"Bounds[{idx}] = {bounds_regular[idx]:.2f} vs {bounds_regular[idx]:.2f}")
                if bounds is None:
                    return
                xmin, ymin, xmax, ymax = bounds
                if isinf(xmin):
                    channel(_("No bounds for selected elements."))
                    return
                width = xmax - xmin
                height = ymax - ymin

                dots_per_units = dpi / UNITS_PER_INCH
                new_width = width * dots_per_units
                new_height = height * dots_per_units
                new_height = max(new_height, 1)
                new_width = max(new_width, 1)
                dpi = 500

                data_image = make_raster(
                    copy_data,
                    bounds=bounds,
                    width=new_width,
                    height=new_height,
                )
                matrix = Matrix.scale(width / new_width, height / new_height)
                matrix.post_translate(bounds[0], bounds[1])

                path_final = make_vector(
                    data_image,
                    interpolationpolicy=ipolicy,
                    invert=invert,
                    turdsize=turdsize,
                    alphamax=alphamax,
                    opticurve=opticurve,
                    opttolerance=opttolerance,
                    color=color,
                    blacklevel=blacklevel,
                )
                matrix = Matrix.scale(width / new_width, height / new_height)
                matrix.post_translate(bounds[0], bounds[1])
                path_final.transform *= Matrix(matrix)

            outline_node = self.elem_branch.add(
                path=abs(path_final),
                stroke_width=1,
                stroke_scaled=False,
                type="elem path",
                fill=None,
                stroke=pathcolor,
                # fillrule=Fillrule.FILLRULE_NONZERO,
                linejoin=Linejoin.JOIN_ROUND,
                label=f"Outline path #{numidx}",
            )
            outline_node.fill = None
            outputdata.append(outline_node)

        # Newly created! Classification needed?
        post.append(classify_new(outputdata))
        self.signal("refresh_scene", "Scene")
        if len(outputdata) > 0:
            self.signal("element_property_update", outputdata)
        return "elements", outputdata

    # --------------------------- END COMMANDS ------------------------------
