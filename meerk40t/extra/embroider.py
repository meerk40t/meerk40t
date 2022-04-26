from meerk40t.core.units import Length
from meerk40t.svgelements import Angle, Matrix, Path, Polyline
from meerk40t.tools.pathtools import EulerianFill


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root

        @context.console_option(
            "angle", "a", type=Angle.parse, default="0deg", help=_("Angle of the fill")
        )
        @context.console_option(
            "distance",
            "d",
            type=Length,
            default="0.5mm",
            help=_("Length between rungs"),
        )
        @context.console_command("embroider", help=_("embroider <angle> <distance>"))
        def embroider(command, channel, _, angle=None, distance=None, **kwargs):
            elements = context.elements
            channel(_("Embroidery Filling"))
            efill = EulerianFill(float(distance))
            for node in elements.elems(emphasized=True):
                try:
                    e = Path(node.shape)
                except AttributeError:
                    try:
                        e = Path(node.path)
                    except AttributeError:
                        continue
                if angle is not None:
                    e *= Matrix.rotate(angle)
                pts = [abs(e).point(i / 100.0, error=1e-4) for i in range(101)]
                efill += pts

            points = efill.get_fill()

            for s in split(points):
                result = Path(Polyline(s, stroke="black"))
                if angle is not None:
                    result *= Matrix.rotate(-angle)
                node = elements.elem_branch.add(path=result, type="elem path")
                elements.classify([node])


def split(points):
    pos = 0
    for i, pts in enumerate(points):
        if pts is None:
            yield points[pos : i - 1]
            pos = i + 1
    if pos != len(points):
        yield points[pos : len(points)]
