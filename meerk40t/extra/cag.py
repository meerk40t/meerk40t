from meerk40t.svgelements import Path, Point, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np  # pylint: disable=unused-import
        except ImportError:
            return True
    elif lifecycle == "register":
        from meerk40t.tools.clipper import Clipper, ClipType, PolyFillType, PolyType

        _ = kernel.translation
        context = kernel.root

        @context.console_option("keep", "k", type=bool, action="store_true", help="keep original elements")
        @context.console_command(
            ("intersection", "xor", "union", "difference"),
            input_type="elements",
            output_type="elements",
            help=_("Constructive Additive Geometry: Add"),
        )
        def cag(command, channel, _, data=None, keep=False, **kwargs):
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
            from ..core.elements import linearize_path

            for i in range(len(data)):
                node = data[i]
                try:
                    path = node.as_path()
                except AttributeError:
                    return "elements", data

                current_polygon = linearize_path(path, point=True)
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

            if not keep:
                for node in data:
                    node.remove_node()
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
