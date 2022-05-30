from meerk40t.core.units import Length
from meerk40t.svgelements import Angle, Matrix
from meerk40t.tools.pathtools import EulerianFill


def split(points):
    pos = 0
    for i, pts in enumerate(points):
        if pts is None:
            yield points[pos : i - 1]
            pos = i + 1
    if pos != len(points):
        yield points[pos : len(points)]


def eulerian_fill(settings, outlines, matrix):
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
            pt[0] * rotate.a
            + pt[1] * rotate.c
            + 1 * rotate.e,
            pt[0] * rotate.b
            + pt[1] * rotate.d
            + 1 * rotate.f,
        )

    def mx_counter(pt):
        if pt is None:
            return None
        return (
            pt[0] * counter_rotate.a
            + pt[1] * counter_rotate.c
            + 1 * counter_rotate.e,
            pt[0] * counter_rotate.b
            + pt[1] * counter_rotate.d
            + 1 * counter_rotate.f,
        )

    transformed_vector = matrix.transform_vector([0, distance_y])
    efill = EulerianFill(
        abs(complex(transformed_vector[0], transformed_vector[1]))
    )
    for sp in outlines:
        sp = list(map(mx_rotate, sp))
        efill += sp
    points = efill.get_fill()

    points = list(map(mx_counter, points))
    return points


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register("hatch/eulerian", eulerian_fill)
        context.register("hatch/scanline", eulerian_fill)
