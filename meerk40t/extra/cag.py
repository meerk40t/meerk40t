from meerk40t.svgelements import Path, Point, Polygon, Shape


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np
        except ImportError:
            return True
    elif lifecycle == "register":
        from meerk40t.tools.clipper import Clipper, ClipType, PolyFillType, PolyType

        _ = kernel.translation
        context = kernel.root

        @context.console_command(
            ("intersection", "xor", "union", "difference"),
            input_type="elements",
            output_type="elements",
            help=_("Constructive Additive Geometry: Add"),
        )
        def cag(command, channel, _, data=None, **kwargs):
            import numpy as np

            if len(data) < 2:
                channel(_("Not enough items selected to apply constructive geometric function"))
                return "elements", []

            clip_polygons = None
            for element in data:
                if isinstance(element, Shape) and not isinstance(element, Path):
                    element = Path(element)
                element = abs(element)
                subject_polygons = []
                for subpath in element.as_subpaths():
                    subj = Path(subpath).npoint(np.linspace(0, 1, 1000))
                    subj.reshape((2, 1000))
                    s = list(map(Point, subj))
                    subject_polygons.append(s)
                if clip_polygons is None:
                    clip_polygons = subject_polygons
                    continue
                pc = Clipper()
                solution = []
                pc.AddPolygons(subject_polygons, PolyType.Subject)
                pc.AddPolygons(clip_polygons, PolyType.Clip)

                if command == "intersection":
                    ct = ClipType.Intersection
                elif command == "xor":
                    ct = ClipType.Xor
                elif command == "union":
                    ct = ClipType.Union
                else:  # difference
                    ct = ClipType.Difference
                result = pc.Execute(
                    ct, solution, PolyFillType.EvenOdd, PolyFillType.EvenOdd
                )
                solution_path = None
                for se in solution:
                    r = Polygon(*se, stroke="blue", stroke_width=1000)
                    if solution_path is None:
                        solution_path = Path(r)
                    else:
                        solution_path += Path(r)
                if solution_path:
                    context.elements.add_elem(solution_path, classify=True)
                    return "elements", [solution_path]
                else:
                    return "elements", []
