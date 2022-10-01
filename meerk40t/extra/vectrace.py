from meerk40t.svgelements import Matrix, Path, Polygon, Color
from meerk40t.core.node.node import Fillrule

def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation

        setup_vectrace(kernel)

        # A very simple hack....
        try:
            import potrace
            setup_potrace(kernel)
        except ModuleNotFoundError:
            pass

_NORTH = 3
_EAST = 0
_SOUTH = 1
_WEST = 2


def _trace(pixels, x, y, width, height):
    """
    This function is called only when the scanline polygon tracing has located a
    point with a white values above y and before x.
    Keeping a black pixel on the right. Position 0,0 is the topleft corner
    above and more left than all pixels. There are n+1,m+1 locations for n,m
    pixels. The pixel equal to the current position is always bottom right (se).
    The pixels adjacent to the current location are:
    (x - 1, y - 1),   (x    , y - 1)
                    X
    (x - 1, y    ),   (x    , y    )
    @param pixels:
    @param x:
    @param y:
    @return:
    """
    start_y = y
    start_x = x
    direction = _EAST
    positions = [x + y * 1j]
    scanpoints = list()

    def px(pixel_x, pixel_y):
        if 0 <= pixel_x < width and 0 <= pixel_y < height:
            return pixels[pixel_x, pixel_y]
        else:
            return 255

    while True:
        nw = px(x - 1, y - 1)
        ne = px(x, y - 1)
        sw = px(x - 1, y)
        se = px(x, y)
        if direction == _EAST:
            pixel_right = se
            pixel_left = ne
            # print("Going East (%d,%d): %d vs %d." % (x, y, pixel_left, pixel_right))
        elif direction == _NORTH:
            pixel_right = ne
            pixel_left = nw
            # print("Going North (%d,%d): %d vs %d." % (x, y, pixel_left, pixel_right))
        elif direction == _SOUTH:
            pixel_right = sw
            pixel_left = se
            # print("Going South (%d,%d): %d vs %d." % (x, y, pixel_left, pixel_right))
        else:  # WEST
            pixel_right = nw
            pixel_left = sw
            # print("Going West (%d,%d): %d vs %d." % (y, x, pixel_left, pixel_right))
        # print("%s %s\n%s %s" % (str(nw).ljust(4), str(ne).ljust(4), str(sw).ljust(4), str(se).ljust(4)))

        if pixel_left and pixel_right:
            direction += 1  # Turn right.
            positions.append(x + y * 1j)
        if not pixel_left and not pixel_right:
            direction -= 1  # Turn Left
            positions.append(x + y * 1j)
        if pixel_left and not pixel_right:
            pass  # Pixel still on right.
        if not pixel_left and pixel_right:
            # Turn Policy Right-Only
            direction += 1  # or direction -= 1
            positions.append(x + y * 1j)

        direction = (direction + 4) % 4

        if direction == _EAST:
            x += 1
        elif direction == _NORTH:
            y -= 1
            scanpoints.append((x, y))
        elif direction == _SOUTH:
            scanpoints.append((x, y))
            y += 1
        else:  # WEST
            x -= 1
        if start_y == y and start_x == x:
            break
    positions.append(x + y * 1j)
    return scanpoints, positions


def _vectrace(pixels, width, height):
    """
    Returns a list of points comprising the edge vectors of the image.
    We're only dealing with grayscale images.
    """
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                scanpoints, positions = _trace(pixels, x, y, width, height)
                scanpoints.sort(key=lambda p: p[1] * width + p[0])
                for i in range(0, len(scanpoints), 2):
                    x0 = scanpoints[i][0]
                    x1 = scanpoints[i + 1][0]
                    y0 = scanpoints[i][1]
                    y1 = scanpoints[i + 1][1]
                    if y0 != y1:
                        raise ValueError
                    for xi in range(x0, x1):
                        pixels[xi, y0] = 0 if pixels[xi, y0] else 255
                yield positions


def setup_vectrace(kernel):
    _ = kernel.translation

    @kernel.console_command(
        "vectrace",
        help=_("return paths around image"),
        input_type="image",
        output_type="elements",
    )
    def vectrace(data, **kwargs):
        elements = kernel.root.elements
        path = Path(fill="black", stroke="blue")
        paths = []
        for node in data:
            matrix = node.matrix
            image = node.image
            width, height = node.image.size
            if image.mode != "L":
                image = image.convert("L")
            image = image.point(lambda e: int(e > 127) * 255)
            for points in _vectrace(image.load(), width, height):
                path += Polygon(*points)
            path.transform *= Matrix(matrix)
            paths.append(
                elements.elem_branch.add(
                    path=abs(path),
                    stroke_width=0,
                    stroke_scaled=False,
                    type="elem path",
                )
            )
        return "elements", paths

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

def setup_potrace(kernel):
    _ = kernel.translation
    import potrace
    import numpy
    from PIL import ImageOps

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
        policies ={
            "black": 0, # POTRACE_TURNPOLICY_BLACK
            "white": 1, # POTRACE_TURNPOLICY_WHITE
            "left": 2,  # POTRACE_TURNPOLICY_LEFT
            "right": 3, # POTRACE_TURNPOLICY_RIGHT
            "minority": 4, # POTRACE_TURNPOLICY_MINORITY
            "majority": 5, # POTRACE_TURNPOLICY_MAJORITY
            "random": 6, #POTRACE_TURNPOLICY_RANDOM
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
