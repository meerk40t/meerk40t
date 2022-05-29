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


def eulerian_fill(context, settings, matrix, paths):
    """
    Applies optimized Eulerian fill
    @return:
    """
    if matrix is None:
        matrix = Matrix()
    penbox_pass = settings.get("penbox_pass")
    if penbox_pass is not None:
        try:
            penbox_pass = context.elements.penbox[penbox_pass]
        except (KeyError, AttributeError):
            penbox_pass = None

    passes = 1
    pass_custom = settings.get("passes_custom", False)
    if pass_custom:
        passes = settings.get("passes", 1)
    polyline_lookup = dict()
    for p in range(passes):
        settings = dict(settings)
        if penbox_pass is not None:
            try:
                settings.update(penbox_pass[p])
            except IndexError:
                pass
        h_dist = settings.get("hatch_distance", "1mm")
        h_angle = settings.get("hatch_angle", "0deg")
        distance_y = float(Length(h_dist))
        if isinstance(h_angle, float):
            angle = Angle.degrees(h_angle)
            h_angle = str(h_angle)
        else:
            angle = Angle.parse(h_angle)

        key = f"{h_angle},{h_dist}"
        if key in polyline_lookup:
            points = polyline_lookup[key]
        else:
            counter_rotate = Matrix.rotate(-angle)
            transformed_vector = matrix.transform_vector([0, distance_y])
            efill = EulerianFill(
                abs(complex(transformed_vector[0], transformed_vector[1]))
            )
            for sp in paths:
                sp.transform.reset()
                if angle is not None:
                    sp *= Matrix.rotate(angle)
                sp = abs(sp)
                efill += [sp.point(i / 100.0, error=1e-4) for i in range(101)]
            points = efill.get_fill()

            def matrix_point(pt):
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

            points = list(map(matrix_point, points))
            polyline_lookup[key] = points
        yield points


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register("hatch/eulerian", eulerian_fill)
        context.register("hatch/scanline", eulerian_fill)
