
from meerk40t.svgelements import Path, Polyline, Matrix, Angle, Length, Shape
from meerk40t.tools.pathtools import EulerianFill


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        context = kernel.get_context("/")

        @context.console_option(
            "angle", "a", type=Angle.parse, default=0, help="Angle of the fill"
        )
        @context.console_option(
            "distance", "d", type=Length, default=16, help="Length between rungs"
        )
        @context.console_command("embroider", help="embroider <angle> <distance>")
        def embroider(
            command, channel, _, angle=None, distance=None, args=tuple(), **kwargs
        ):
            bed_dim = context.get_context("/")
            elements = context.elements
            channel(_("Embroidery Filling"))
            if distance is not None:
                distance = distance.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
            else:
                distance = 16

            efill = EulerianFill(distance)
            for element in elements.elems(emphasized=True):
                if not isinstance(element, Shape):
                    continue
                e = Path(element)
                if angle is not None:
                    e *= Matrix.rotate(angle)
                pts = [abs(e).point(i / 100.0, error=1e-4) for i in range(101)]
                efill += pts

            points = efill.get_fill()

            for s in split(points):
                result = Path(Polyline(s, stroke="black"))
                if angle is not None:
                    result *= Matrix.rotate(-angle)
                elements.add_elem(result)


def split(points):
    pos = 0
    for i, pts in enumerate(points):
        if pts is None:
            yield points[pos : i - 1]
            pos = i + 1
    if pos != len(points):
        yield points[pos : len(points)]



