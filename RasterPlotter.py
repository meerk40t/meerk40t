X_AXIS = 0
TOP = 0
LEFT = 0
BIDIRECTIONAL = 0
SKIPPING = 0
Y_AXIS = 1
BOTTOM = 2
RIGHT = 4
UNIDIRECTIONAL = 8
NO_SKIP = 16


def leftmost_not_equal(data, width, height, y, skip_pixel):
    for x in range(0, width):
        pixel = data[x, y]
        if pixel != skip_pixel:
            return x
    return -1


def topmost_not_equal(data, width, height, x, skip_pixel):
    for y in range(0, height):
        pixel = data[x, y]
        if pixel != skip_pixel:
            return y
    return -1


def rightmost_not_equal(data, width, height, y, skip_pixel):
    for x in range(width - 1, -1, -1):
        pixel = data[x, y]
        if pixel != skip_pixel:
            return x
    return width


def bottommost_not_equal(data, width, height, x, skip_pixel):
    for y in range(height - 1, -1, -1):
        pixel = data[x, y]
        if pixel != skip_pixel:
            return y
    return height


def nextcolor_left(data, width, height, x, y, default):
    if x <= -1:
        return default
    if x == 0:
        return -1
    if x == width:
        return width - 1
    if width < x:
        return width

    v = data[x, y]
    for ix in range(x, -1, -1):
        pixel = data[ix, y]
        if pixel != v:
            return ix
    return 0


def nextcolor_top(data, width, height, x, y, default):
    if y <= -1:
        return default
    if y == 0:
        return -1
    if y == height:
        return height - 1
    if height < y:
        return height

    v = data[x, y]
    for iy in range(y, -1, -1):
        pixel = data[x, iy]
        if pixel != v:
            return iy
    return 0


def nextcolor_right(data, width, height, x, y, default):
    if x < -1:
        return -1
    if x == -1:
        return 0
    if x == width - 1:
        return width
    if width <= x:
        return default

    v = data[x, y]
    for ix in range(x, width):
        pixel = data[ix, y]
        if pixel != v:
            return ix
    return width - 1


def nextcolor_bottom(data, width, height, x, y, default):
    if y < -1:
        return -1
    if y == -1:
        return 0
    if y == height - 1:
        return height
    if height <= y:
        return default

    v = data[x, y]
    for iy in range(x, height):
        pixel = data[x, iy]
        if pixel != v:
            return iy
    return width - 1


def plot_raster(image, transversal=0, skip_pixel=0, overscan=0,
                offset_x=0, offset_y=0):
    width, height = image.size
    data = image.load()
    x = 0
    y = 0
    pixel = skip_pixel
    dx = 1
    dy = 1

    if (transversal & RIGHT) != 0:
        x = width - 1
        dx = -1

    if (transversal & BOTTOM) != 0:
        y = height - 1
        dy = -1

    yield offset_x + x, offset_y + y, pixel

    if (transversal & Y_AXIS) != 0:
        while 0 <= x < width:
            lower_bound = topmost_not_equal(data, width, height, x, skip_pixel)
            if lower_bound == -1:
                x += dx
                yield offset_x + x, offset_y + y, pixel
                continue
            upper_bound = bottommost_not_equal(data, width, height, x, skip_pixel)
            while lower_bound <= y <= upper_bound:
                if dy == 1:  # going bottom
                    end = upper_bound + overscan
                    if 0 <= x + dx < width:
                        end = max(end, bottommost_not_equal(data, width, height, x + dx, skip_pixel))
                    pixel = data[x, y]
                    y = nextcolor_bottom(data, width, height, x, y, end)
                    y = min(y, end)
                else:
                    end = lower_bound - overscan
                    if 0 <= x + dx < width:
                        end = min(end, topmost_not_equal(data, width, height, x + dx, skip_pixel))
                    pixel = data[x, y]
                    y = nextcolor_top(data, width, height, x, y, end)
                    y = max(y, end)
                yield offset_x + x, offset_y + y, pixel
                if y == end:
                    break
            x += dx
            yield offset_x + x, offset_y + y, pixel
            dy = -dy
    else:
        while 0 <= y < height:
            lower_bound = leftmost_not_equal(data, width, height, y, skip_pixel)
            if lower_bound == -1:
                y += dy
                yield offset_x + x, offset_y + y, pixel
                continue
            upper_bound = rightmost_not_equal(data, width, height, y, skip_pixel)
            while lower_bound <= x <= upper_bound:
                if dx == 1:  # going right
                    end = upper_bound + overscan
                    if 0 <= y + dy < height:
                        end = max(end, rightmost_not_equal(data, width, height, y + dy, skip_pixel))
                    pixel = data[x, y]
                    x = nextcolor_right(data, width, height, x, y, end)
                    x = min(x, end)
                else:
                    end = lower_bound - overscan
                    if 0 <= y + dy < height:
                        end = min(end, leftmost_not_equal(data, width, height, y + dy, skip_pixel))
                    pixel = data[x, y]
                    x = nextcolor_left(data, width, height, x, y, end)
                    x = max(x, end)
                yield offset_x + x, offset_y + y, pixel
                if x == end:
                    break
            y += dy
            yield offset_x + x, offset_y + y, pixel
            dx = -dx
