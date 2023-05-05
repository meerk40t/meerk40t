"""
This adds console commands that deal with the creation of an offset
"""

from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Path, Polygon
from meerk40t.tools.offset import OffsetPath


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    # ==========
    # OFFSET Commands
    # ==========

    @self.console_argument("offset", type=str, help=_("offset"))
    @self.console_option(
        "connector",
        "c",
        type=int,
        help=_("Optional connector: 0=line (default), 1=curve"),
    )
    @self.console_option(
        "both",
        "b",
        type=bool,
        action="store_true",
        help=_("Create offset copy at both sides?"),
    )
    @self.console_command(
        "offset",
        help=_("offset <distance> - creates a copy of the element with an offset"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_offset(
        command,
        channel,
        _,
        offset: str,
        connector=None,
        both=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if offset is None:
            raise CommandSyntaxError
        try:
            value = self.length_x(offset)
        except ValueError:
            channel(_("Invalid offset provided"))
            return
        if both is None:
            both = False
        if both:
            value = abs(value)
        if data is None:
            data = list(self.elems(emphasized=True))
        if connector is None:
            connector = 0
        try:
            connector = int(connector)
        except ValueError:
            channel(_("Invalid connector type (0, 1)"))
            return
        # Make sure its between 0 and 1
        connector = max(0, min(1, connector))

        if len(data) == 0:
            channel(_("No item selected."))
            return
        data_out = list()
        offset_routine = OffsetPath(
            originalpath=None, offset=value, connection=connector
        )
        for node in data:
            # Valid element?
            path = None
            if node.type == "elem image":
                box = node.bbox()
                path = Path(
                    Polygon(
                        (box[0], box[1]),
                        (box[0], box[3]),
                        (box[2], box[3]),
                        (box[2], box[1]),
                    )
                )
            elif node.type == "elem path":
                path = abs(node.path)
                # path.approximate_arcs_with_cubics()
            elif hasattr(node, "shape"):
                path = abs(Path(node.shape))
                # path.approximate_arcs_with_cubics()
            if path is not None:
                offset_routine.offset = value
                offset_routine.path = path
                sp = offset_routine.result()
                if sp is not None:
                    newnode = self.elem_branch.add(type="elem path", path=sp)
                    data_out.append(newnode)
                if both:
                    offset_routine.offset = -1 * value
                    offset_routine.path = path
                    sp = offset_routine.result()
                    if sp is not None:
                        newnode = self.elem_branch.add(type="elem path", path=sp)
                        data_out.append(newnode)

        if len(data_out):
            # Newly created! Classification needed?
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
