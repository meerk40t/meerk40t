import math

from meerk40t.core.units import Angle, Length, UNITS_PER_MM
from meerk40t.svgelements import Matrix, Point
from meerk40t.tools.pathtools import EulerianFill, VectorMontonizer


class Wobble:
    def __init__(self, algorithm, radius=50, speed=50, interval=10):
        self._total_count = 0
        self._total_distance = 0
        self.unit_factor = 1
        self._remainder = 0
        self.previous_angle = None
        self.radius = radius
        self.speed = speed
        self.interval = interval
        self.total_length = 0
        self._last_x = None
        self._last_y = None
        self._algorithm = algorithm
        self.flag = None
        self.userdata = None
        self.may_close_path = True

    def __repr__(self):
        return f"Wobble: r={self.radius}, s={self.speed}, i={self.interval}, alg={repr(self._algorithm)}"
    
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
            self._last_x = tx
            self._last_y = ty
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

    The Eulerian Fill performs creates a graph made out of edges and a series of horizontal rungs. It then solves for an
    optimal walk that visits all the horizontal rungs and as many of the edge nodes as needed to perform this walk. This
    should at most walk the entire edge plus 50% for scaffolding.

    @return:
    """
    if matrix is None:
        matrix = Matrix()

    settings = dict(settings)
    h_dist = settings.get("hatch_distance", "1mm")
    h_angle = settings.get("hatch_angle", "0deg")
    distance_y = float(Length(h_dist))
    if isinstance(h_angle, float):
        angle = Angle(f"{h_angle}deg")
    else:
        angle = Angle(h_angle)

    rotate = Matrix.rotate(angle)
    counter_rotate = Matrix.rotate(-angle)

    def mx_rotate(pt):
        if pt is None:
            return None
        return (
            pt.real * rotate.a + pt.imag * rotate.c + 1 * rotate.e,
            pt.real * rotate.b + pt.imag * rotate.d + 1 * rotate.f,
        )

    def mx_counter(pt):
        if pt is None:
            return None
        return (
            pt[0] * counter_rotate.a + pt[1] * counter_rotate.c + 1 * counter_rotate.e,
            pt[0] * counter_rotate.b + pt[1] * counter_rotate.d + 1 * counter_rotate.f,
        )

    def as_polylines():
        pos = 0
        for i in range(len(outlines)):
            p = outlines[i]
            if p is None:
                yield outlines[pos:i]
                pos = i + 1
                continue
        if pos != len(outlines):
            yield outlines[pos:]

    transformed_vector = matrix.transform_vector([0, distance_y])
    distance = abs(complex(transformed_vector[0], transformed_vector[1]))
    efill = EulerianFill(distance)

    for poly in as_polylines():
        sp = list(map(Point, map(mx_rotate, poly)))
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
        angle = Angle(f"{h_angle}deg")
    else:
        angle = Angle(h_angle)

    rotate = Matrix.rotate(angle)
    counter_rotate = Matrix.rotate(-angle)

    def mx_rotate(pt):
        if pt is None:
            return None
        return (
            pt.real * rotate.a + pt.imag * rotate.c + 1 * rotate.e,
            pt.real * rotate.b + pt.imag * rotate.d + 1 * rotate.f,
        )

    def mx_counter(pt):
        if pt is None:
            return None
        return (
            pt[0] * counter_rotate.a + pt[1] * counter_rotate.c + 1 * counter_rotate.e,
            pt[0] * counter_rotate.b + pt[1] * counter_rotate.d + 1 * counter_rotate.f,
        )

    def as_polylines():
        pos = 0
        for idx in range(len(outlines)):
            p = outlines[idx]
            if p is None:
                yield outlines[pos:idx]
                pos = idx + 1
                continue
        if pos != len(outlines):
            yield outlines[pos:]

    transformed_vector = matrix.transform_vector([0, distance_y])
    distance = abs(complex(transformed_vector[0], transformed_vector[1]))

    vm = VectorMontonizer()
    for poly in as_polylines():
        pts = list(map(Point, map(mx_rotate, poly)))
        vm.add_polyline(pts)
    y_min, y_max = vm.event_range()
    if y_min is None:
        return []
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
    points = []
    forward = True
    while vm.current_is_valid_range():
        vm.scanline_increment(distance)
        y = vm.scanline
        actives = vm.actives()
        for i in (
            range(1, len(actives), 2) if forward else range(len(actives) - 1, 0, -2)
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
    rad = wobble.radius
    if rad == 0:
        rad = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        t = wobble._total_distance / (math.tau * rad)
        dx = wobble.radius * math.cos(t * wobble.speed)
        dy = wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def circle_right(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    rad = wobble.radius
    if rad == 0:
        rad = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        dx = wobble.radius * math.cos(angle)
        dy = wobble.radius * math.sin(angle)
        t = wobble._total_distance / (math.tau * rad)
        dx += wobble.radius * math.cos(t * wobble.speed)
        dy += wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def circle_left(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    rad = wobble.radius
    if rad == 0:
        rad = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        dx = -wobble.radius * math.cos(angle)
        dy = -wobble.radius * math.sin(angle)
        t = wobble._total_distance / (math.tau * rad)
        dx += wobble.radius * math.cos(t * wobble.speed)
        dy += wobble.radius * math.sin(t * wobble.speed)
        yield tx + dx, ty + dy


def sinewave(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    spd = wobble.speed
    if spd == 0:
        spd = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        d = math.sin(wobble._total_distance / spd)
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
    spd = wobble.speed
    if spd == 0:
        spd = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0)
        angle_perp = angle + math.tau / 4.0
        d = math.sin(wobble._total_distance / spd)
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
    spd = wobble.speed
    if spd == 0:
        spd = 1
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
        if wobble.previous_angle is None:
            wobble.previous_angle = angle
        amount = 1.0 / spd
        angle = amount * (angle - wobble.previous_angle) + wobble.previous_angle
        d = -1 if wobble._total_count % 2 else 1
        dx = wobble.radius * d * math.cos(angle)
        dy = wobble.radius * d * math.sin(angle)
        wobble.previous_angle = angle
        yield tx + dx, ty + dy


def _meander(wobble, pattern, max_x, max_y, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return

    factors = {
        "l": (-1, 0),
        "r": (1, 0),
        "u": (0, -1),
        "d": (0, 1),
    }

    if int(wobble.speed) % 10 == 1:
        # position_x = "left"
        offset_x = 0 * max_x
    elif int(wobble.speed) % 10 == 2:
        # position_x = "right"
        offset_x = -1 * max_x
    else:
        # position_x = "center"
        offset_x = -0.5 * max_x

    if wobble.speed // 10 == 1:
        # position_y = "top"
        offset_y = 0 * max_y
    elif wobble.speed // 10 == 2:
        # position_y = "bottom"
        offset_y = 1 * max_y
    else:
        # position_y = "center"
        offset_y = 0.5 * max_y

    step = wobble.radius / max_x

    offset_x *= step
    offset_y *= step

    angle = 0
    mat = Matrix()
    if x1 is not None:
        a_x = x1 - x0
        a_y = y1 - y0
        angle = math.atan2(a_y, a_x)
        mat.post_rotate(angle)
    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        dx = 0
        dy = 0
        pt = mat.point_in_matrix_space((dx + offset_x, dy + offset_y))
        yield tx + pt.x, ty + pt.y
        for p in pattern:
            sx, sy = factors[p[0]]
            stepsize = step * p[1]
            dx += sx * stepsize
            dy += sy * stepsize
            pt = mat.point_in_matrix_space((dx + offset_x, dy + offset_y))
            yield tx + pt.x, ty + pt.y


def meander_1(wobble, x0, y0, x1, y1):
    pattern = (
        (
            "r",
            6,
        ),
        (
            "u",
            5,
        ),
        (
            "l",
            4,
        ),
        (
            "d",
            3,
        ),
        (
            "r",
            2,
        ),
        (
            "u",
            1,
        ),
        # transition
        ("l", 1),
        # reverse of upper part
        (
            "u",
            1,
        ),
        (
            "r",
            2,
        ),
        (
            "d",
            3,
        ),
        (
            "l",
            4,
        ),
        (
            "u",
            5,
        ),
        (
            "r",
            6,
        ),
        # transition
        ("d", 6),
    )
    max_x = 0
    for p in pattern:
        max_x = max(max_x, p[1])
    max_y = max_x
    max_x += 1
    yield from _meander(wobble, pattern, max_x, max_y, x0, y0, x1, y1)


def meander_2(wobble, x0, y0, x1, y1):
    pattern = (
        ("u", 3),
        ("r", 3),
        ("d", 2),
        ("l", 1),
        ("u", 1),
        ("l", 1),
        ("d", 2),
        ("r", 5),
        ("u", 2),
        ("l", 1),
        ("d", 1),
        ("l", 1),
        ("u", 2),
        ("r", 3),
        ("d", 3),
    )
    max_x = 8
    max_y = 3

    yield from _meander(wobble, pattern, max_x, max_y, x0, y0, x1, y1)


def meander_3(wobble, x0, y0, x1, y1):
    pattern = (
        ("u", 4),
        ("r", 3),
        ("d", 3),
        ("l", 2),
        ("u", 2),
        ("r", 1),
        ("d", 1),
        # and now backwards...
        # reverse of upper part
        ("u", 1),
        ("l", 1),
        ("d", 2),
        ("r", 2),
        ("u", 3),
        ("l", 3),
        ("d", 4),
        # other side
        ("d", 4),
        ("r", 3),
        ("u", 3),
        ("l", 2),
        ("d", 2),
        ("r", 1),
        ("u", 1),
        # and now backwards...
        ("d", 1),
        ("l", 1),
        ("u", 2),
        ("r", 2),
        ("d", 3),
        ("l", 3),
        ("u", 4),
        # transition
        ("r", 4),
    )
    max_x = 0
    for p in pattern:
        max_x = max(max_x, p[1])
    max_y = max_x
    max_x += 1
    yield from _meander(wobble, pattern, max_x, max_y, x0, y0, x1, y1)


def _tabbed(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    # wobble has the following parameters:
    # speed:  Array of tab positions (percentage of overall pathlength)
    # radius: Length of tab
    # interval: internal resolution
    wobble.may_close_path = False
    if wobble.flag is None:
        wobble.flag = True
    if wobble.userdata is None:
        tablen = wobble.radius * wobble.unit_factor
        pattern_idx = 0
        pattern = []
        positions = []
        if isinstance(wobble.speed, str):
            # This is a string with comma and/or whitespace separated numbers
            sub_comma = wobble.speed.split(",")
            if wobble.speed.startswith("*"):
                # Special case:
                # '*4' means 4 tabs equidistant, all remaining parameters will be ignored
                sub_spaces = sub_comma[0].split()
                s = sub_spaces[0][1:]
                try:
                    value = int(s)
                    if value > 0:
                        for i in range(value):
                            val = (i + 0.5) * 100 / value
                            positions.append( val )
                except ValueError:
                    pass
            else:
                for entry in sub_comma:
                    sub_spaces = entry.split()
                    for s in sub_spaces:
                        try:
                            value = float(s)
                            if value < 0:
                                value = 0
                            elif value > 100:
                                value = 100
                        except ValueError:
                            continue
                        positions.append(value)
        else:
            try:
                positions.append(float(wobble.speed))
            except ValueError:
                pass
        # So now that we have the positions we calculate the start and end position
        # Do we have a chance or are all gaps overlapping
        def repr(info):
            conc = []
            for p in info:
                conc.append(f"({p[0]}, {p[1]:.2f})")
            s = ",".join(conc)
            return "[" + s + "]"

        if len(positions) * tablen < wobble.total_length:
            positions.sort()
            last_end = None
            last_end_idx = None
            gap_at_end = None
            have_gap_at_start = False
            for pos in positions:
                spos = pos / 100.0 * wobble.total_length - 0.5 * tablen
                epos = spos + tablen
                # print (f"And now: {spos:.2f} - {epos:.2f} adding to {repr(pattern)}")
                this_start = spos
                if this_start < 0:
                    this_start = 0
                # Is the new start <= previous end, if yes just extend the end
                if last_end is not None and last_end >= this_start:
                    # print (f"Updating end {last_end:.2f}, ignoring start {this_start:.2f}")
                    pattern[last_end_idx][1] = epos
                    last_end = epos
                    continue

                if spos < 0 and gap_at_end is None:
                    spos = spos + wobble.total_length
                    gap_at_end = spos
                    pattern.append([False, spos])
                    # print (f"Adding a gap at the at the end {spos:.2f}")
                if this_start == 0:
                    if not have_gap_at_start:
                        # print("Set a start to zero")
                        pattern.append([False, 0.0])
                        have_gap_at_start = True
                    else:
                        # print("Ignore start as it was already at zero")
                        pass
                else:
                    if last_end is not None and this_start <= last_end:
                        # print ("Unexpectedly this is still smaller...")
                        pattern[last_end_idx][1] = epos
                        last_end = epos
                        continue
                    # print (f"Adding a gap at {this_start:.2f}")
                    pattern.append([False, this_start])
                # And finally the end
                if gap_at_end is None or gap_at_end > epos:
                    # print (f"Closing the gap at {epos:.2f}")
                    pattern.append([True, epos])
                    last_end = epos
                    last_end_idx = len(pattern) - 1
                else:
                    # print (f"Not closing the gap at {epos:.2f} as it would fall into the endgap {gap_at_end:.2f}")
                    pass
            pattern.sort(key=lambda x: x[1])
            # print ("Before", repr(pattern))
            if len(pattern):
                if pattern[0][1] > 0:
                    # Force a start
                    pattern.insert(0, [True, 0.0])
                # Remove duplicate entries
                idx = len(pattern) - 1
                while idx > 0:  # No need to look at the very first as there are no predecessors
                    if pattern[idx - 1] == pattern[idx]:
                        pattern.pop(idx)
                    idx -= 1
            # print ("at end", repr(pattern))
            # Now amend the sequence to indicate the next position
            for idx, pat in enumerate(pattern):
                if idx < len(pattern) - 1:
                    l = pattern[idx + 1][1]
                else:
                    l = wobble.total_length + 10 * wobble.interval
                pat[1] = l
        # print (f"Start with {wobble.flag}: {pattern}")
        wobble.userdata = [pattern_idx, pattern, -1.0]
    pattern_idx = wobble.userdata[0]
    pattern = wobble.userdata[1]
    next_target = wobble.userdata[2]

    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        if len(pattern) == 0:
            yield (tx, ty)
            continue

        if next_target < wobble._total_distance:
            if pattern_idx < len(pattern):
                wobble.flag, next_target = pattern[pattern_idx]
                pattern_idx += 1
            else:
                next_target = wobble.total_length * 1.25
                wobble.flag = True
            wobble.userdata[0] = pattern_idx
            wobble.userdata[2] = next_target
            # print (f"Changing state: {wobble.flag} at {wobble._total_distance:.2f} ({tx:.2f}, {ty:.2f}) - next target: {next_target:.2f}")
        if wobble.flag:
            yield tx, ty
        else:
            yield None, None

def _dashed(wobble, x0, y0, x1, y1):
    if x1 is None or y1 is None:
        yield x0, y0
        return
    # wobble has the following parameters:
    # speed
    # radius
    # interval
    if wobble.flag is None:
        wobble.flag = False  # Not visible but will immediately be swapped...
    if wobble.userdata is None:
        pattern_idx = 0
        pattern = []
        if isinstance(wobble.radius, str):
            # This is a string with comma and/or whitespace separated numbers
            sub_comma = wobble.radius.split(",")
            for entry in sub_comma:
                sub_spaces = entry.split()
                for s in sub_spaces:
                    try:
                        value = float(s)
                        if value <= 0:
                            continue
                    except ValueError:
                        continue
                    pattern.append(value * UNITS_PER_MM * wobble.unit_factor)
        elif isinstance(wobble.radius, (tuple, list)):
            pattern.extend(r * UNITS_PER_MM * wobble.unit_factor for r in wobble.radius)
        else:
            pattern.append(wobble.radius * UNITS_PER_MM * wobble.unit_factor)
        if len(pattern) % 2 == 1:
            # Needs to be even
            pattern.extend(pattern)
        wobble.userdata = [pattern_idx, pattern, -1.0]
    pattern_idx = wobble.userdata[0]
    pattern = wobble.userdata[1]
    next_target = wobble.userdata[2]

    for tx, ty in wobble.wobble(x0, y0, x1, y1):
        if len(pattern) == 0:
            yield (tx, ty)
            continue

        if next_target < wobble._total_distance:
            gap = pattern[pattern_idx]
            pattern_idx += 1
            if pattern_idx >= len(pattern):
                pattern_idx = 0
            next_target = wobble._total_distance + gap
            wobble.flag = not wobble.flag
            wobble.userdata[0] = pattern_idx
            wobble.userdata[2] = next_target
        # if wobble.flag and wobble._last_x:
        #     yield wobble._last_x, wobble._last_y
        if wobble.flag:
            yield tx, ty
        else:
            yield None, None


def dashed_line(wobble, x0, y0, x1, y1):
    yield from _dashed(wobble, x0, y0, x1, y1)

def tabbed_path(wobble, x0, y0, x1, y1):
    yield from _tabbed(wobble, x0, y0, x1, y1)


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
        context.register("wobble/meander_1", meander_1)
        context.register("wobble/meander_2", meander_2)
        context.register("wobble/meander_3", meander_3)
        # context.register("wobble/dash", dashed_line)
        # context.register("wobble/tabs", tabbed_path)
