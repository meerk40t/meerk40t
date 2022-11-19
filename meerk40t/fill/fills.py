import math

from meerk40t.core.units import Length
from meerk40t.svgelements import Angle, Matrix, Point
from meerk40t.tools.pathtools import EulerianFill, VectorMontonizer


class Wobble:
    def __init__(self, algorithm, radius=50, speed=50, interval=10):
        self._total_count = 0
        self._total_distance = 0
        self._remainder = 0
        self.previous_angle = None
        self.radius = radius
        self.speed = speed
        self.interval = interval
        self._last_x = None
        self._last_y = None
        self._algorithm = algorithm

    def __call__(self, x0, y0, x1, y1):
        yield from self._algorithm(self, x0, y0, x1, y1)

    def wobble(self, x0, y0, x1, y1):
        distance_change = abs(complex(x0, y0) - complex(x1, y1))
        positions = 1 - self._remainder
        # Circumvent a div by zero error
        try:
            intervals = distance_change / self.interval
        except ZeroDivisionError:
            intervals = 1
        while positions <= intervals:
            amount = positions / intervals
            tx = amount * (x1 - x0) + x0
            ty = amount * (y1 - y0) + y0
            self._total_distance += self.interval
            self._total_count += 1
            yield tx, ty
            positions += 1
        self._remainder += intervals
        self._remainder %= 1


def split(points):
    pos = 0
    for i, pts in enumerate(points):
        if pts is None:
            yield points[pos : i - 1]
            pos = i + 1
    if pos != len(points):
        yield points[pos : len(points)]


def eulerian_fill(settings, outlines, matrix, limit=None):
    """
    Applies optimized Eulerian fill
    @return:
    """
    if matrix is None:
        matrix = Matrix()

    settings = dict(settings)
    h_dist = settings.get("hatch_distance", "1mm")
    h_angle = settings.get("hatch_angle", "0deg")
    distance_y = float(Length(h_dist))
    if isinstance(h_angle, float):
        angle = Angle.degrees(h_angle)
    else:
        angle = Angle.parse(h_angle)

    rotate = Matrix.rotate(angle)
    counter_rotate = Matrix.rotate(-angle)

    def mx_rotate(pt):
        if pt is None:
            return None
        return (
            pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
            pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
        )

    def mx_counter(pt):
        if pt is None:
            return None
        return (
            pt[0] * counter_rotate.a + pt[1] * counter_rotate.c + 1 * counter_rotate.e,
            pt[0] * counter_rotate.b + pt[1] * counter_rotate.d + 1 * counter_rotate.f,
        )

    transformed_vector = matrix.transform_vector([0, distance_y])
    distance = abs(complex(transformed_vector[0], transformed_vector[1]))
    efill = EulerianFill(distance)
    for sp in outlines:
        sp = list(map(mx_rotate, sp))
        efill += sp
    if limit and efill.estimate() > limit:
        return []
    points = efill.get_fill()

    points = list(map(mx_counter, points))
    return points


def scanline_fill(settings, outlines, matrix, limit=None):
    """
    Applies optimized scanline fill
    @return:
    """
    if matrix is None:
        matrix = Matrix()

    settings = dict(settings)
    h_dist = settings.get("hatch_distance", "1mm")
    h_angle = settings.get("hatch_angle", "0deg")
    distance_y = float(Length(h_dist))
    if isinstance(h_angle, float):
        angle = Angle.degrees(h_angle)
    else:
        angle = Angle.parse(h_angle)

    rotate = Matrix.rotate(angle)
    counter_rotate = Matrix.rotate(-angle)

    def mx_rotate(pt):
        if pt is None:
            return None
        return (
            pt[0] * rotate.a + pt[1] * rotate.c + 1 * rotate.e,
            pt[0] * rotate.b + pt[1] * rotate.d + 1 * rotate.f,
        )

    def mx_counter(pt):
        if pt is None:
            return None
        return (
            pt[0] * counter_rotate.a + pt[1] * counter_rotate.c + 1 * counter_rotate.e,
            pt[0] * counter_rotate.b + pt[1] * counter_rotate.d + 1 * counter_rotate.f,
        )

    transformed_vector = matrix.transform_vector([0, distance_y])
    distance = abs(complex(transformed_vector[0], transformed_vector[1]))

    vm = VectorMontonizer()
    for outline in outlines:
        pts = list(map(Point, map(mx_rotate, outline)))
        vm.add_polyline(pts)
    y_min, y_max = vm.event_range()
    height = y_max - y_min
    try:
        count = height / distance
    except ZeroDivisionError:
        return []
    if limit and count > limit:
        return []
    vm.valid_low = y_min - distance
    vm.valid_high = y_max + distance
    vm.scanline_to(y_min - distance)
    points = list()
    forward = True
    while vm.current_is_valid_range():
        vm.scanline_increment(distance)
        y = vm.scanline
        actives = vm.actives()
        for i in (
            range(1, len(actives), 2)
            if forward
            else range(len(actives) - 1, 0, -2)
        ):
            left_segment = actives[i - 1]
            right_segment = actives[i]
            left_segment_x = vm.intercept(left_segment, y)
            right_segment_x = vm.intercept(right_segment, y)
            if forward:
                points.append((left_segment_x, y))
                points.append((right_segment_x, y))
            else:
                points.append((right_segment_x, y))
                points.append((left_segment_x, y))
            points.append(None)
        forward = not forward
    points = list(map(mx_counter, points))
    return points


def circle(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        t = wobble._total_distance / (math.tau * wobble.radius)
        dx = wobble.radius * math.cos(t * wobble.speed)
        dy = wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def circle_right(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        dx = wobble.radius * math.cos(angle)
        dy = wobble.radius * math.sin(angle)
        t = wobble._total_distance / (math.tau * wobble.radius)
        dx += wobble.radius * math.cos(t * wobble.speed)
        dy += wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def circle_left(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        dx = -wobble.radius * math.cos(angle)
        dy = -wobble.radius * math.sin(angle)
        t = wobble._total_distance / (math.tau * wobble.radius)
        dx += wobble.radius * math.cos(t * wobble.speed)
        dy += wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def sinewave(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        d = math.sin(wobble._total_distance / wobble.speed)
        dx = wobble.radius * d * math.cos(angle)
        dy = wobble.radius * d * math.sin(angle)
        yield tx + dx, ty + dy


def sawtooth(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        d = -1 if wobble._total_count % 2 else 1
        dx = wobble.radius * d * math.cos(angle)
        dy = wobble.radius * d * math.sin(angle)
        yield tx + dx, ty + dy


def jigsaw(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0)
        angle_perp = angle + math.tau / 4.0
        d = math.sin(wobble._total_distance / wobble.speed)
        dx = wobble.radius * d * math.cos(angle_perp)
        dy = wobble.radius * d * math.sin(angle_perp)

        d = -1 if wobble._total_count % 2 else 1
        dx += wobble.radius * d * math.cos(angle)
        dy += wobble.radius * d * math.sin(angle)
        yield tx + dx, ty + dy


def gear(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        d = -1 if (wobble._total_count // 2) % 2 else 1
        dx = wobble.radius * d * math.cos(angle)
        dy = wobble.radius * d * math.sin(angle)
        yield tx + dx, ty + dy


def slowtooth(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        if wobble.previous_angle is None:
            wobble.previous_angle = angle
        amount = 1.0 / wobble.speed
        angle = amount * (angle - wobble.previous_angle) + wobble.previous_angle
        d = -1 if wobble._total_count % 2 else 1
        dx = wobble.radius * d * math.cos(angle)
        dy = wobble.radius * d * math.sin(angle)
        wobble.previous_angle = angle
        yield tx + dx, ty + dy


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register("hatch/scanline", scanline_fill)
        context.register("hatch/eulerian", eulerian_fill)
        context.register("wobble/circle", circle)
        context.register("wobble/circle_right", circle_right)
        context.register("wobble/circle_left", circle_left)
        context.register("wobble/sinewave", sinewave)
        context.register("wobble/sawtooth", sawtooth)
        context.register("wobble/jigsaw", jigsaw)
        context.register("wobble/gear", gear)
        context.register("wobble/slowtooth", slowtooth)
