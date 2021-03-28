from meerk40t.svgelements import Path, Polygon


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":

        @kernel.console_command(
            "vectrace",
            help="return paths around image",
            input_type="image",
            output_type="elements",
        )
        def vectrace(command, channel, _, data, args=tuple(), **kwargs):
            elements = kernel.get_context("/").elements
            path = Path(fill="black", stroke="blue")
            paths = []
            for element in data:
                image = element.image
                width, height = element.image.size
                if image.mode != "L":
                    image = image.convert("L")
                image = image.point(lambda e: int(e > 127) * 255)
                for points in _vectrace(image.load(), width, height):
                    path += Polygon(*points)
                paths.append(elements.elem_branch.add(path, "elem"))
            return "elements", paths


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
    :param pixels:
    :param x:
    :param y:
    :return:
    """
    start_y = y
    start_x = x
    direction = _EAST
    positions = [x + y * 1j]
    scanpoints = list()

    def px(x, y):
        if 0 <= x < width and 0 <= y < height:
            return pixels[x, y]
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
                    for x in range(x0, x1):
                        pixels[x, y0] = 0 if pixels[x, y0] else 255
                yield positions
