"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from meerk40t.svgelements import Viewbox

from .element_types import *


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # ALIGN SUBTYPE
    # Align consist of top level node objects that can be manipulated within the scene.
    # ==========

    def _align_xy(
        channel,
        _,
        mode,
        bounds,
        elements,
        align_x=None,
        align_y=None,
        asgroup=None,
        **kwargs,
    ):
        """
        This routine prepares the data according to some validation.

        The complete validation stuff...
        """
        if elements is None:
            return
        if align_x is None or align_y is None:
            channel(_("You need to provide parameters for both x and y"))
            return
        align_bounds = None
        align_x = align_x.lower()
        align_y = align_y.lower()
        if align_x not in ("min", "max", "center", "none"):
            channel(_("Invalid alignment parameter for x"))
            return
        if align_y not in ("min", "max", "center", "none"):
            channel(_("Invalid alignment parameter for y"))
            return
        if mode == "default":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            # boundaries are the selection boundaries,
            # will be calculated later
        elif mode == "first":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            elements.sort(key=lambda n: n.emphasized_time)
            # Is there a noticeable difference?!
            # If not then we fall back to default
            delta = abs(elements[0].emphasized_time - elements[-1].emphasized_time)
            if delta > 0.5:
                align_bounds = elements[0].bounds
                # print (f"Use bounds of first element, delta was: {delta:.2f}")
                # print (f"Time 1: {elements[0].type} - {elements[0]._emphasized_time}, Time 2: {elements[-1].type} - {elements[-1]._emphasized_time}")
                # elements.pop(0)
        elif mode == "last":
            if len(elements) < 2:
                channel(_("No sense in aligning an element to itself"))
                return
            elements.sort(reverse=True, key=lambda n: n.emphasized_time)
            # Is there a noticeable difference?!
            # If not then we fall back to default
            # print(f"Mode: {mode}, type={elements[0].type}")
            delta = abs(elements[0].emphasized_time - elements[-1].emphasized_time)
            if delta > 0.5:
                align_bounds = elements[0].bounds
                # print (f"Use bounds of last element, delta was: {delta:.2f}")
                # elements.pop(0)
        elif mode == "bed":
            align_bounds = bounds
        elif mode == "ref":
            align_bounds = bounds
        self.align_elements(
            data=elements,
            alignbounds=align_bounds,
            positionx=align_x,
            positiony=align_y,
            as_group=asgroup,
        )

    @self.console_command(
        "push",
        help=_("pushes the current align mode to the stack"),
        input_type="align",
        output_type="align",
    )
    def alignmode_push(channel, _, data, **kwargs):
        """
        Special command to push the current values on the stack
        """
        mode, group, bound, elements = data
        self._align_stack.append((mode, group, bound))
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "pop",
        help=_("pushes the current align mode to the stack"),
        input_type="align",
        output_type="align",
    )
    def alignmode_pop(channel, _, data, **kwargs):
        """
        Special command to push the current values on the stack
        """
        mode, group, bound, elements = data
        if len(self._align_stack) > 0:
            (
                self._align_mode,
                self._align_group,
                self._align_boundaries,
            ) = self._align_stack.pop()
            mode = self._align_mode
            group = self._align_group
            bound = self._align_boundaries
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "group",
        help=_("Set the requested alignment to treat selection as group"),
        input_type="align",
        output_type="align",
    )
    def alignmode_group(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        group = True
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "individual",
        help=_("Set the requested alignment to treat selection as individuals"),
        input_type="align",
        output_type="align",
    )
    def alignmode_individual(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        group = False
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "default",
        help=_("align within selection - all equal"),
        input_type="align",
        output_type="align",
    )
    def alignmode_default(channel, _, data, **kwargs):
        """
        Set the alignment mode to default
        """
        mode, group, bound, elements = data
        mode = "default"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "first",
        help=_("Set the requested alignment to first element selected"),
        input_type="align",
        output_type="align",
    )
    def alignmode_first(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "first"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "last",
        help=_("Set the requested alignment to last element selected"),
        input_type="align",
        output_type="align",
    )
    def alignmode_last(command, channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "last"
        bound = None
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "bed",
        help=_("Set the requested alignment to within the bed"),
        input_type="align",
        output_type="align",
    )
    def alignmode_bed(channel, _, data, **kwargs):
        mode, group, bound, elements = data
        mode = "bed"
        device_width = self.length_x("100%")
        device_height = self.length_y("100%")
        bound = (0, 0, device_width, device_height)
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_option(
        "boundaries", "b", type=self.bounds, parallel_cast=True, nargs=4
    )
    @self.console_command(
        "ref",
        help=_("Set the requested alignment to the reference object"),
        input_type="align",
        output_type="align",
    )
    def alignmode_ref(channel, _, data, boundaries, **kwargs):
        mode, group, bound, elements = data
        if boundaries is None:
            channel(
                _("You need to provide the boundaries for align-mode {mode}").format(
                    mode="ref"
                )
            )
            return
        mode = "ref"
        bound = boundaries
        self._align_mode = mode
        self._align_boundaries = bound
        channel(_("New alignmode = {mode}").format(mode=self._align_mode))
        if self._align_boundaries is not None:
            channel(
                _("Align boundaries = {bound}").format(
                    bound=str(self._align_boundaries)
                )
            )
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "align",
        help=_("align selected elements"),
        input_type=("elements", None),
        output_type="align",
    )
    def align_elements_base(command, channel, _, data=None, remainder=None, **kwargs):
        """
        Base align commands. Triggers other base commands within the command context
        'align'.
        """
        if not remainder:
            channel(
                "top\nbottom\nleft\nright\ncenter\ncenterh\ncenterv\nspaceh\nspacev\n"
                "<any valid svg:Preserve Aspect Ratio, eg xminymin>"
            )
            # Bunch of other things.
            return
        if data is None:
            data = list(self.elems(emphasized=True))
        return "align", (
            self._align_mode,
            self._align_group,
            self._align_boundaries,
            data,
        )

    @self.console_argument(
        "alignx", type=str, help=_("One of 'min', 'center', 'max', 'none'")
    )
    @self.console_argument(
        "aligny", type=str, help=_("One of 'min', 'center', 'max', 'none'")
    )
    @self.console_command(
        "xy",
        help=_("align elements in x and y"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_xy(
        command,
        channel,
        _,
        data=None,
        alignx=None,
        aligny=None,
        **kwargs,
    ):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, alignx, aligny, group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "top",
        help=_("align elements at top"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_top(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "min", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "bottom",
        help=_("align elements at bottom"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_bottom(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "max", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "left",
        help=_("align elements at left"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_left(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "min", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "right",
        help=_("align elements at right"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_right(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "max", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "center",
        help=_("align elements at center"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_center(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "center", "center", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "centerh",
        help=_("align elements at center horizontally"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_centerh(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "center", "none", group)
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "centerv",
        help=_("align elements at center vertically"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_centerv(command, channel, _, data=None, **kwargs):
        mode, group, bound, elements = data
        _align_xy(channel, _, mode, bound, elements, "none", "center", group)
        return "align", (mode, group, bound, elements)

    def distribute_elements(elements, in_x: bool = True, distance: bool = True):
        if len(elements) <= 2:  # Cannot distribute 2 or fewer items.
            return
        if in_x:
            elements.sort(key=lambda n: n.bounds[0])  # sort by left edge
        else:
            elements.sort(key=lambda n: n.bounds[1])  # sort by top edge
        boundary_points = []
        for node in elements:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return
        if in_x:
            idx = 0
        else:
            idx = 1
        if distance:
            left_edge = boundary_points[0][idx]
            right_edge = boundary_points[-1][idx + 2]
            dim_total = right_edge - left_edge
            dim_available = dim_total
            for node in elements:
                bounds = node.bounds
                dim_available -= bounds[idx + 2] - bounds[idx]
            distributed_distance = dim_available / (len(elements) - 1)
            dim_pos = left_edge
        else:
            left_edge = (boundary_points[0][idx] + boundary_points[0][idx + 2]) / 2
            right_edge = (boundary_points[-1][idx] + boundary_points[-1][idx + 2]) / 2
            dim_total = right_edge - left_edge
            dim_available = dim_total
            dim_pos = left_edge
            distributed_distance = dim_available / (len(elements) - 1)

        for node in elements:
            subbox = node.bounds
            if distance:
                delta = subbox[idx] - dim_pos
                dim_pos += subbox[idx + 2] - subbox[idx] + distributed_distance
            else:
                delta = (subbox[idx] + subbox[idx + 2]) / 2 - dim_pos
                dim_pos += distributed_distance
            if in_x:
                dx = -delta
                dy = 0
            else:
                dx = 0
                dy = -delta
            if dx != 0 or dy != 0:
                self.translate_node(node, dx, dy)

    @self.console_command(
        "spaceh",
        help=_("distribute elements across horizontal space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spaceh(command, channel, _, data=None, **kwargs):
        mode, group, bound, raw_elements = data
        haslock = False
        for node in raw_elements:
            if not node.can_move(self.lock_allows_move):
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return "align", (mode, group, bound, raw_elements)
        elements = self.condense_elements(raw_elements)
        distribute_elements(elements, in_x=True, distance=True)
        self.signal("refresh_scene", "Scene")
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "spaceh2",
        help=_("distribute elements across horizontal space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spaceh2(command, channel, _, data=None, **kwargs):
        mode, group, bound, raw_elements = data
        haslock = False
        for node in raw_elements:
            if not node.can_move(self.lock_allows_move):
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return "align", (mode, group, bound, raw_elements)
        elements = self.condense_elements(raw_elements)
        distribute_elements(elements, in_x=True, distance=False)
        self.signal("refresh_scene", "Scene")
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "spacev",
        help=_("distribute elements across vertical space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spacev(command, channel, _, data=None, **kwargs):
        mode, group, bound, raw_elements = data
        haslock = False
        for node in raw_elements:
            if not node.can_move(self.lock_allows_move):
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return "align", (mode, group, bound, raw_elements)
        elements = self.condense_elements(raw_elements)
        distribute_elements(elements, in_x=False, distance=True)
        self.signal("refresh_scene", "Scene")
        return "align", (mode, group, bound, elements)

    @self.console_command(
        "spacev2",
        help=_("distribute elements across vertical space"),
        input_type="align",
        output_type="align",
    )
    def subtype_align_spacev2(command, channel, _, data=None, **kwargs):
        mode, group, bound, raw_elements = data
        haslock = False
        for node in raw_elements:
            if not node.can_move(self.lock_allows_move):
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return "align", (mode, group, bound, raw_elements)
        elements = self.condense_elements(raw_elements)
        distribute_elements(elements, in_x=False, distance=False)
        self.signal("refresh_scene", "Scene")
        return "align", (mode, group, bound, elements)

    @self.console_argument(
        "preserve_aspect_ratio",
        type=str,
        default="none",
        help="preserve aspect ratio value",
    )
    @self.console_command(
        "view",
        help=_("align elements within viewbox"),
        input_type="align",
        output_type="align",
    )
    def subtype_align(
        command, channel, _, data=None, preserve_aspect_ratio="none", **kwargs
    ):
        """
        Align the elements to within the bed according to SVG Viewbox rules. The following aspect ratios
        are valid. These should define all the valid methods of centering data within the laser bed.
        "xminymin",
        "xmidymin",
        "xmaxymin",
        "xminymid",
        "xmidymid",
        "xmaxymid",
        "xminymax",
        "xmidymax",
        "xmaxymax",
        "xminymin meet",
        "xmidymin meet",
        "xmaxymin meet",
        "xminymid meet",
        "xmidymid meet",
        "xmaxymid meet",
        "xminymax meet",
        "xmidymax meet",
        "xmaxymax meet",
        "xminymin slice",
        "xmidymin slice",
        "xmaxymin slice",
        "xminymid slice",
        "xmidymid slice",
        "xmaxymid slice",
        "xminymax slice",
        "xmidymax slice",
        "xmaxymax slice",
        "none"
        """
        mode, group, bound, elements = data
        boundary_points = []
        for node in elements:
            boundary_points.append(node.bounds)
        if not len(boundary_points):
            return

        haslock = False
        for node in elements:
            if not node.can_move(self.lock_allows_move):
                haslock = True
                break
        if haslock:
            channel(_("Your selection contains a locked element, that cannot be moved"))
            return
        left_edge = min([e[0] for e in boundary_points])
        top_edge = min([e[1] for e in boundary_points])
        right_edge = max([e[2] for e in boundary_points])
        bottom_edge = max([e[3] for e in boundary_points])

        if preserve_aspect_ratio in (
            "xminymin",
            "xmidymin",
            "xmaxymin",
            "xminymid",
            "xmidymid",
            "xmaxymid",
            "xminymax",
            "xmidymax",
            "xmaxymax",
            "xminymin meet",
            "xmidymin meet",
            "xmaxymin meet",
            "xminymid meet",
            "xmidymid meet",
            "xmaxymid meet",
            "xminymax meet",
            "xmidymax meet",
            "xmaxymax meet",
            "xminymin slice",
            "xmidymin slice",
            "xmaxymin slice",
            "xminymid slice",
            "xmidymid slice",
            "xmaxymid slice",
            "xminymax slice",
            "xmidymax slice",
            "xmaxymax slice",
            "none",
        ):
            for node in elements:
                device_width = self.length_x("100%")
                device_height = self.length_y("100%")

                matrix = Viewbox.viewbox_transform(
                    0,
                    0,
                    device_width,
                    device_height,
                    left_edge,
                    top_edge,
                    right_edge - left_edge,
                    bottom_edge - top_edge,
                    preserve_aspect_ratio,
                )
                for q in node.flat(types=elem_nodes):
                    try:
                        q.matrix *= matrix
                        q.modified()
                    except AttributeError:
                        continue
                for q in node.flat(types=("file", "group")):
                    q.modified()
        return "align", (mode, group, bound, elements)
