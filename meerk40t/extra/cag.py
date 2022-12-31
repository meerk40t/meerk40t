from meerk40t.svgelements import Color, Path, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np  # pylint: disable=unused-import
        except ImportError:
            return True
    elif lifecycle == "register":
        from ..core.elements import linearize_path
        from ..tools import polybool as pb

        _ = kernel.translation
        context = kernel.root

        @context.console_option(
            "keep", "k", type=bool, action="store_true", help="keep original elements"
        )
        @context.console_command(
            ("intersection", "xor", "union", "difference"),
            input_type="elements",
            output_type="elements",
            help=_("Constructive Additive Geometry: Add"),
        )
        def cag(command, channel, _, keep=False, data=None, **kwargs):
            if len(data) < 2:
                channel(
                    _(
                        "Not enough items selected to apply constructive geometric function"
                    )
                )
                return "elements", []

            elements = context.elements
            solution_path = Path(
                stroke=elements.default_stroke,
                fill=elements.default_fill,
                stroke_width=1000,
            )

            # reorder elements
            data.sort(key=lambda n: n.emphasized_time)

            node = None
            segment_list = []
            for i in range(len(data)):
                node = data[i]
                try:
                    path = node.as_path()
                except AttributeError:
                    return "elements", data
                c = linearize_path(path)
                c = pb.Polygon(c)
                c = pb.segments(c)
                segment_list.append(c)
            if len(segment_list) == 0:
                return "elements", data
            if not keep:
                for node in data:
                    node.remove_node()
            segs = segment_list[0]
            for s in segment_list[1:]:
                combined = pb.combine(segs, s)
                if command == "intersection":
                    segs = pb.selectIntersect(combined)
                elif command == "xor":
                    segs = pb.selectXor(combined)
                elif command == "union":
                    segs = pb.selectUnion(combined)
                else:
                    # difference
                    segs = pb.selectDifference(combined)

            last_polygon = pb.polygon(segs)
            for se in last_polygon.regions:
                r = Polygon(*[(p.x, p.y) for p in se])
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
                    try:
                        stroke = node.stroke if node is not None else None
                    except AttributeError:
                        stroke = Color("blue")
                    try:
                        fill = node.fill if node is not None else None
                    except AttributeError:
                        fill = None
                    try:
                        stroke_width = node.stroke_width if node is not None else None
                    except AttributeError:
                        stroke_width = 1000
                    new_node = elements.elem_branch.add(
                        path=solution_path,
                        type="elem path",
                        stroke=stroke,
                        fill=fill,
                        stroke_width=stroke_width,
                    )
                context.signal("refresh_scene", "Scene")
                elements.classify([new_node])
                return "elements", [node]
            else:
                channel(_("No solution found (empty path)"))
                return "elements", []
