from meerk40t.svgelements import Path, Point, Polygon


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
                channel(
                    _(
                        "Not enough items selected to apply constructive geometric function"
                    )
                )
                return "elements", []

            elements = context.elements
            if command == "intersection":
                ct = ClipType.Intersection
            elif command == "xor":
                ct = ClipType.Xor
            elif command == "union":
                ct = ClipType.Union
            else:  # difference
                ct = ClipType.Difference
            solution_path = Path(
                stroke=elements.default_stroke,
                fill=elements.default_fill,
                stroke_width=1000,
            )

            # reorder elements
            data.sort(key=lambda n: n.emphasized_time)
            last_polygon = None
            node = None

            for i in range(len(data)):
                node = data[i]
                try:
                    path = node.as_path()
                except AttributeError:
                    return "elements", data

                current_polygon = []
                for subpath in path.as_subpaths():
                    subj = Path(subpath).npoint(np.linspace(0, 1, 1000))
                    subj.reshape((2, 1000))
                    s = list(map(Point, subj))
                    current_polygon.append(s)

                if last_polygon is not None:
                    pc = Clipper()
                    solution = []
                    pc.AddPolygons(last_polygon, PolyType.Subject)
                    pc.AddPolygons(current_polygon, PolyType.Clip)
                    result = pc.Execute(
                        ct, solution, PolyFillType.EvenOdd, PolyFillType.EvenOdd
                    )
                    current_polygon = solution
                last_polygon = current_polygon

            for se in last_polygon:
                r = Polygon(*se)
                if solution_path is None:
                    solution_path = Path(r)
                else:
                    solution_path += Path(r)
            if solution_path:
                if node is None:
                    new_node = elements.elem_branch.add(
                        path=solution_path,
                        type="elem path",
                    )
                else:
                    new_node = elements.elem_branch.add(
                        path=solution_path,
                        type="elem path",
                        stroke=node.stroke if node is not None else None,
                        fill=node.fill if node is not None else None,
                        stroke_width=node.stroke_width if node is not None else None,
                    )
                context.signal("refresh_scene", "Scene")
                elements.classify([new_node])
                return "elements", [node]
            else:
                return "elements", []
