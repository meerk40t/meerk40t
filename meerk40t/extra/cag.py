from meerk40t.svgelements import Path, Point, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        try:
            import numpy as np  # pylint: disable=unused-import
        except ImportError:
            return True
    elif lifecycle == "register":
        from ..tools import polybool as pb
        from ..core.elements import linearize_path

        _ = kernel.translation
        context = kernel.root

        @context.console_option("consume", "c", type=bool, action="store_true", help="consume the original element")
        @context.console_command(
            ("pintersection", "pxor", "punion", "pdifference"),
            input_type="elements",
            output_type="elements",
            help=_("Constructive Additive Geometry: Add"),
        )
        def cag(command, channel, _, consume=False, data=None, **kwargs):
            if len(data) < 2:
                channel(
                    _(
                        "Not enough items selected to apply constructive geometric function"
                    )
                )
                return "elements", []

            elements = context.elements
            if command == "intersection":
                ct = pb.intersect
            elif command == "xor":
                ct = pb.xor
            elif command == "union":
                ct = pb.union
            else:
                # difference
                ct = pb.difference
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
                current_polygon = linearize_path(path)
                if last_polygon is not None:
                    current_polygon = ct(pb.Polygon(last_polygon), pb.Polygon(current_polygon))
                last_polygon = current_polygon
            if consume:
                for node in data:
                    node.remove_node()
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
