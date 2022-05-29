from meerk40t.core.units import Length
from meerk40t.svgelements import Angle, Matrix, Path, Polyline
from meerk40t.tools.pathtools import EulerianFill


def eulerian_fill(self, context, matrix):
    """
    Applies optimized Eulerian fill
    @return:
    """

    def create_eulerian_fill():
        c = list()
        for node in self.children:
            path = node.as_path()
            path.approximate_arcs_with_cubics()
            self.settings["line_color"] = path.stroke
            for subpath in path.as_subpaths():
                sp = Path(subpath)
                if len(sp) == 0:
                    continue
                c.append(sp)
        self.remove_all_children()

        penbox_pass = self.settings.get("penbox_pass")
        if penbox_pass is not None:
            try:
                penbox_pass = context.elements.penbox[penbox_pass]
            except KeyError:
                penbox_pass = None

        polyline_lookup = dict()
        for p in range(self.implicit_passes):
            settings = dict(self.settings)
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
                polylines = polyline_lookup[key]
            else:
                counter_rotate = Matrix.rotate(-angle)
                transformed_vector = matrix.transform_vector([0, distance_y])
                efill = EulerianFill(
                    abs(complex(transformed_vector[0], transformed_vector[1]))
                )
                for sp in c:
                    sp.transform.reset()
                    if angle is not None:
                        sp *= Matrix.rotate(angle)
                    sp = abs(sp)
                    efill += [sp.point(i / 100.0, error=1e-4) for i in range(101)]
                points = efill.get_fill()
                polylines = list()
                for pts in HatchOpNode.split(points):
                    polyline = Polyline(pts, stoke=settings.get("line_color"))
                    polyline *= counter_rotate
                    polylines.append(abs(polyline))
                polyline_lookup[key] = polylines
            for polyline in polylines:
                node = PolylineNode(shape=abs(polyline))
                node.settings.update(settings)
                self.add_node(node)
        return

    return create_eulerian_fill


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.register("hatch/eulerian", eulerian_fill)
        context.register("hatch/scanline", eulerian_fill)

