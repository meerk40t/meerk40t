from meerk40t.svgelements import Matrix, Path,  Color
from meerk40t.core.node.node import Fillrule


"""
Potracer routines, please be aware that potrace is not part of the standard
distribution of meerk40t due to the more restrictive licensing of potrace
If you have installed it yourself via 'pip install potracer', well why not...
potracer is a pure python port of Peter Selinger's Potrace by Tatarize
potrace:    https://potrace.sourceforge.net/
potracer:   https://github.com/tatarize/potrace

-   The turdsize parameter can be used to “despeckle” the bitmap to be traced,
    by removing all curves whose enclosed area is below the given threshold.
    The current default for the turdsize parameter is 2; its useful range is
    from 0 to infinity.

-   The turnpolicy parameter determines how to resolve ambiguities during
    decomposition of bitmaps into paths. The possible choices for the turnpolicy
    parameter are:

    BLACK:      prefers to connect black (foreground) components.
    WHITE:      prefers to connect white (background) components.
    LEFT:       always take a left turn.
    RIGHT:      always take a right turn.
    MINORITY:   prefers to connect the color (black or white) that occurs
                least frequently in a local neighborhood of the current position.
    MAJORITY:   prefers to connect the color (black or white) that occurs most
                frequently in a local neighborhood of the current position.
    RANDOM:     choose randomly.
    The current default policy is MINORITY, which tends to keep
    visual lines connected.

-   The alphamax parameter is a threshold for the detection of corners.
    It controls the smoothness of the traced curve.
    The current default is 1.0; useful range of this parameter is
    from 0.0 (polygon) to 1.3333 (no corners).

-   The opticurve parameter is a boolean flag that controls whether Potrace
    will attempt to “simplify” the final curve by reducing the number of
    Bezier curve segments. Opticurve=1 turns on optimization,
    and opticurve=0 turns it off. The current default is on.

-   The opttolerance parameter defines the amount of error
    allowed in this simplification. The current default is 0.2. Larger values tend to decrease the number of segments, at the expense of less accuracy. The useful range is from 0 to infinity, although in practice one would hardly choose values greater than 1 or so. For most purposes, the default value is a good tradeoff between space and accuracy.

"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import potrace
            import numpy
        except ImportError:
            print("Potrace plugin could not load because potracer/pypotrace is not installed.")
            return True

    if lifecycle == "register":
        _ = kernel.translation
        import potrace
        import numpy

        @kernel.console_option(
            "turnpolicy",
            "z",
            type=str,
            default="minority",
            help=_("how to resolve ambiguities in path decomposition"),
        )
        @kernel.console_option(
            "turdsize",
            "t",
            type=int,
            default=2,
            help=_("suppress speckles of up to this size (default 2)"),
        )
        @kernel.console_option(
            "alphamax",
            "a",
            type=float,
            default=1,
            help=_("corner threshold parameter")
        )
        @kernel.console_option(
            "opticurve",
            "n",
            type=bool,
            action="store_true",
            help=_("turn off curve optimization"),
        )
        @kernel.console_option(
            "opttolerance",
            "O",
            type=float,
            help=_("curve optimization tolerance"),
            default=0.2,
        )
        @kernel.console_option(
            "color",
            "C",
            type=Color,
            help=_("set foreground color (default Black)"),
        )
        @kernel.console_option(
            "invert",
            "i",
            type=bool,
            action="store_true",
            help=_("invert bitmap"),
        )
        @kernel.console_option(
            "blacklevel",
            "k",
            type=float,
            default=0.5,
            help=_("blacklevel?!"),
        )
        @kernel.console_command(
            "potrace",
            help=_("return paths around image"),
            input_type="image",
            output_type="elements",
        )
        def do_potrace(
                data,
                turnpolicy=None,
                turdsize=None,
                alphamax=None,
                opticurve=None,
                opttolerance=None,
                color=None,
                invert=None,
                blacklevel=None,
                **kwargs,
        ):
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
            elements = kernel.root.elements
            paths = []
            for node in data:
                matrix = node.matrix
                image = node.image
                using_pypotrace = hasattr(potrace, "potracelib_version")
                if using_pypotrace:
                    invert = not invert

                if image.mode not in ("L", "1"):
                    image = image.convert("L")

                if not invert:
                    image = image.point(lambda e: 0 if (e / 255.0) < blacklevel else 255)
                else:
                    image = image.point(lambda e: 255 if (e / 255.0) < blacklevel else 0)
                if image.mode != "1":
                    image = image.convert("1")
                npimage = numpy.asarray(image)

                bm = potrace.Bitmap(npimage)
                plist = bm.trace(
                    turdsize=turdsize,
                    turnpolicy=ipolicy,
                    alphamax=alphamax,
                    opticurve=opticurve,
                    opttolerance=opttolerance,
                )
                path = Path(
                    fill=color,
                    stroke=color,
                    fillrule=Fillrule.FILLRULE_NONZERO,
                )
                for curve in plist:
                    path.move(curve.start_point)
                    for segment in curve.segments:
                        if segment.is_corner:
                            path.line(segment.c)
                            path.line(segment.end_point)
                        else:
                            path.cubic(segment.c1, segment.c2, segment.end_point)
                    path.closed()
                path.transform *= Matrix(matrix)
                node = elements.elem_branch.add(
                    path=abs(path),
                    stroke_width=0,
                    stroke_scaled=False,
                    type="elem path",
                    fillrule=Fillrule.FILLRULE_NONZERO,
                )
                paths.append(node)
            return "elements", paths
