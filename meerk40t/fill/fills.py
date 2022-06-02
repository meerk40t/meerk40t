from meerk40t.core.units import Length
from meerk40t.svgelements import Angle, Matrix, Point
from meerk40t.tools.pathtools import EulerianFill, VectorMontonizer


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
        vm.add_cluster(pts)
    vm.sort_clusters()
    y_max = vm.clusters[-1][0]
    y_min = vm.clusters[0][0]
    height = y_max - y_min
    try:
        count = height / distance
    except ZeroDivisionError:
        return []
    if limit and count > limit:
        return []
    vm.valid_low_value = y_min - distance
    vm.valid_high_value = y_max + distance
    vm.scanline(y_min - distance)
    points = list()
    forward = True
    while vm.valid_range():
        vm.next_intercept(distance)
        vm.sort_actives()
        y = vm.current
        for i in (
                range(1, len(vm.actives), 2)
                if forward
                else range(len(vm.actives) - 1, 0, -2)
        ):
            left_segment = vm.actives[i - 1]
            right_segment = vm.actives[i]
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


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register("hatch/scanline", scanline_fill)
        context.register("hatch/eulerian", eulerian_fill)
