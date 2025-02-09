from meerk40t.svgelements import Color, Path, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np  # pylint: disable=unused-import
        except ImportError:
            return True
    elif lifecycle == "register":
        from ..core.elements.elements import linearize_path
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
                stroke_width=elements.default_strokewidth,
                fill=elements.default_fill,
            )

            # reorder elements
            data.sort(key=lambda n: n.emphasized_time)

            last_fill = None
            last_stroke = None
            last_stroke_width = None
            segment_list = []
            for i, node in enumerate(data):
                try:
                    path = abs(node.as_path())
                except AttributeError:
                    return "elements", data
                if last_fill is None and hasattr(node, "fill"):
                    last_fill = node.fill
                if last_stroke is None and hasattr(node, "stroke"):
                    last_stroke = node.stroke
                    last_stroke_width = node.stroke_width
                c = linearize_path(path)
                try:
                    c = pb.Polygon(c)
                    c = pb.segments(c)
                    segment_list.append(c)
                except pb.PolyBoolException:
                    channel(_("Polybool could not solve."))
            if not segment_list:
                return "elements", data
            segs = segment_list[0]
            for s in segment_list[1:]:
                try:
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
                except pb.PolyBoolException:
                    channel(_("Polybool could not solve."))

            last_polygon = pb.polygon(segs)
            for se in last_polygon.regions:
                r = Polygon(*[(p.x, p.y) for p in se])
                if solution_path is None:
                    solution_path = Path(r)
                else:
                    solution_path += Path(r)
            if solution_path:
                with elements.undoscope("Constructive Additive Geometry: Add"):
                    if not keep:
                        for node in data:
                            node.remove_node()
                    stroke = last_stroke if last_stroke is not None else Color("blue")
                    fill = last_fill
                    stroke_width = last_stroke_width if last_stroke_width is not None else elements.default_strokewidth
                    new_node = elements.elem_branch.add(
                        path=solution_path,
                        type="elem path",
                        stroke=stroke,
                        fill=fill,
                        stroke_width=stroke_width,
                    )
                    context.signal("refresh_scene", "Scene")
                    if elements.classify_new:
                        elements.classify([new_node])
                return "elements", [node]
            else:
                channel(_("No solution found (empty path)"))
                return "elements", []
