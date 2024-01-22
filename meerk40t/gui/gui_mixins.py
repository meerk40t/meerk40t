"""
Routines to check for issues in the design and to give some
warnings to the user
"""

import wx

from meerk40t.core.units import UNITS_PER_MM, Length
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_paint_brush,
    icon_paint_brush_green,
    icon_warning,
)

_ = wx.GetTranslation


INACTIVE = "inactive"
WAITING = "waiting"
PASTING = "pasting"


class FormatPainter:
    def __init__(self, context, button, identifier, *args, **kwds):
        self.context = context
        # Path to button
        self.button = button
        self.identifier = identifier
        self.context.kernel.register(
            self.button,
            {
                "label": _("Paint format"),
                "icon": icon_paint_brush,
                "tip": _(
                    "First select your template, then every subsequent selection will apply the templates properties to the selected elements"
                ),
                "help": "basicediting",
                "action": self.on_click,
                "identifier": self.identifier,
                "toggle": {
                    "label": _("Stop"),
                    "help": "basicediting",
                    "action": self.on_click,
                    "icon": icon_paint_brush_green,
                    "signal": self.identifier,
                    "tip": _("Click again to disable the paint mode"),
                },
            },
        )
        # The node to use
        self.template = None
        # List of tuples with (attribute_name, generic)
        self.possible_attributes = (
            # Standard line and fill attributes
            ("stroke", True),
            ("stroke_width", True),
            ("stroke_scale", True),
            ("fill", True),
            ("linecap", True),
            ("linejoin", True),
            ("fillrule", True),
            # Image attributes
            ("dpi", False),
            ("operations", False),
            ("invert", False),
            ("dither", False),
            ("dither_type", False),
            ("red", False),
            ("green", False),
            ("blue", False),
            ("lightness", False),
            # Text attributes
            ("mkfont", True),
            ("mkfontsize", True),
            ("font_style", False),
            ("font_variant", False),
            ("font_weight", False),
            ("font_stretch", False),
            ("font_size", False),
            ("line_height", False),
            ("font_family", False),
            # Hatches
            ("hatch_distance", False),
            ("hatch_angle", False),
            ("hatch_angle_delta", False),
            ("hatch_type", False),
            # Wobbles
            ("wobble_radius", False),
            ("wobble_interval", False),
            ("wobble_speed", False),
            ("wobble_type", False),
        )
        self.path_update_needed = (
            "mkfont",
            "mkfontsize",
        )
        # State-Machine
        self._state = None
        self.state = INACTIVE

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value not in (INACTIVE, WAITING, PASTING):
            value = INACTIVE
        if value == INACTIVE:
            self.template = None
        elif value == WAITING:
            node = self.context.elements.first_emphasized
            if node is not None and node.type not in ("file", "group"):
                self.template = node
                value = PASTING
        elif value == PASTING:
            pass
        self._state = value
        toggle = bool(value != INACTIVE)
        self.context.signal(self.identifier, toggle)

    def on_emphasis(self, *args):
        if self.state == INACTIVE:
            return
        elif self.state == WAITING:
            node = self.context.elements.first_emphasized
            if node is None:
                return
            if node.type in ("file", "group"):
                return
            self.template = node
            self.state = PASTING
            return
        elif self.state == PASTING:
            try:
                id = self.template.id
            except (RuntimeError, AttributeError):
                # No longer existing or invalid?
                self.state = INACTIVE
            nodes_changed = []
            nodes_classify = []
            nodes_images = []
            for node in self.context.elements.elems(emphasized=True):
                if node is self.template:
                    continue
                flag_changed = False
                flag_classify = False
                flag_pathupdate = False
                for entry in self.possible_attributes:
                    attr = entry[0]
                    generic = entry[1]
                    if not generic and node.type != self.template.type:
                        continue
                    if hasattr(self.template, attr) and hasattr(node, attr):
                        value = getattr(self.template, attr, None)
                        if isinstance(value, (list, tuple)):
                            value = copy(value)
                        try:
                            setattr(node, attr, value)
                            flag_changed = True
                            if attr in ("stroke", "fill"):
                                flag_classify = True
                            if attr in self.path_update_needed:
                                flag_pathupdate = True
                        except ValueError:
                            continue
                if flag_changed:
                    nodes_changed.append(node)
                    if node.type == "elem image":
                        nodes_images.append(node)
                if flag_pathupdate:
                    if hasattr(node, "mktext"):
                        newtext = self.context.elements.wordlist_translate(
                            node.mktext, elemnode=node, increment=False
                        )
                        oldtext = getattr(node, "_translated_text", "")
                        if newtext != oldtext:
                            node._translated_text = newtext
                        kernel = self.context.kernel
                        for property_op in kernel.lookup_all("path_updater/.*"):
                            property_op(kernel.root, node)
                        if hasattr(node, "_cache"):
                            node._cache = None

                if flag_classify:
                    nodes_classify.append(node)
            if len(nodes_changed) > 0:
                for node in nodes_images:
                    node.update(None)
                if len(nodes_classify) > 0 and self.context.elements.classify_new:
                    self.context.elements.classify(nodes_classify)
                self.context.signal("element_property_update", nodes_changed)
                self.context.signal("refresh_scene", "Scene")

    def on_click(self, *args):
        # print(f"On_click called, state was : {self.state}")
        if self.state == INACTIVE:
            self.state = WAITING
        else:
            self.state = INACTIVE


class Warnings:
    def __init__(self, context=None, button=None, *args, **kwargs):
        self.context = context
        self.button = button
        self._concerns = list()
        self._device_acceleration_info = dict()
        self.context.kernel.register(
            self.button,
            {
                "label": _("Warning"),
                "icon": icon_warning,
                "rule_visible": lambda d: len(self._concerns) > 0,
                "action": self.show_concerns,
                "tip": _("There are issues with your project"),
                "size": STD_ICON_SIZE,
                "priority": 2,
            },
        )

    @property
    def concerns(self):
        return "\n".join(self._concerns)

    def show_concerns(self, *args):
        if len(self._concerns):
            wx.MessageBox(self.concerns, _("Warning"), style=wx.OK | wx.ICON_WARNING)

    def warning_indicator(self):
        def has_ambitious_operations(maxspeed, optypes):
            for op in self.context.elements.ops():
                if (
                    hasattr(op, "output")
                    and hasattr(op, "speed")
                    and op.output
                    and op.type in optypes
                    and len(op.children) > 0
                ):
                    # Is a warning defined?
                    checker = f"dangerlevel_{op.type.replace(' ', '_')}"
                    danger = False
                    if hasattr(self.context.device, checker):
                        maxspeed_minpower = getattr(self.context.device, checker)
                        if (
                            isinstance(maxspeed_minpower, (tuple, list))
                            and len(maxspeed_minpower) == 8
                        ):
                            # minpower, maxposer, minspeed, maxspeed
                            # print ("Yes: ", checker, maxspeed_minpower)
                            danger = False
                            if hasattr(op, "power"):
                                value = op.power
                                if (
                                    maxspeed_minpower[0]
                                    and value < maxspeed_minpower[1]
                                ):
                                    danger = True
                                if (
                                    maxspeed_minpower[2]
                                    and value > maxspeed_minpower[3]
                                ):
                                    danger = True
                            if hasattr(op, "speed"):
                                value = op.speed
                                if (
                                    maxspeed_minpower[4]
                                    and value < maxspeed_minpower[5]
                                ):
                                    danger = True
                                if (
                                    maxspeed_minpower[6]
                                    and value > maxspeed_minpower[7]
                                ):
                                    danger = True
                    if danger:
                        return True
                    # Is a generic maximum speed defined?
                    if maxspeed is not None and op.speed >= maxspeed:
                        return True

            return False

        def has_objects_outside():
            wd = self.context.space.display.width
            ht = self.context.space.display.height
            for op in self.context.elements.ops():
                if hasattr(op, "output") and op.output:
                    for refnode in op.children:
                        if not hasattr(refnode, "node"):
                            continue
                        node = refnode.node
                        bb = getattr(node, "paint_bounds", None)
                        if bb is None:
                            bb = getattr(node, "bounds", None)
                        if bb is None:
                            continue
                        if bb[2] > wd or bb[0] < 0 or bb[3] > ht or bb[1] < 0:
                            return True
            return False

        def has_close_to_edge_rasters():
            wd = self.context.space.display.width
            ht = self.context.space.display.height
            additional_info = ""
            devname = self.context.device.name
            if devname not in self._device_acceleration_info:
                acceleration = hasattr(self.context.device, "acceleration_overrun")
                if not acceleration:
                    device_dict = dir(self.context.device)
                    for d in device_dict:
                        if "acceler" in d.lower():
                            acceleration = True
                            break
                    if not acceleration and hasattr(self.context.device, "driver"):
                        device_dict = dir(self.context.device.driver)
                        for d in device_dict:
                            if "acceler" in d.lower():
                                acceleration = True
                                break
                self._device_acceleration_info[devname] = acceleration
            acceleration = self._device_acceleration_info[devname]
            # print(f"Accel info: {devname} = {acceleration}")
            for op in self.context.elements.ops():
                if (
                    hasattr(op, "output")
                    and op.output
                    and op.type in ("op raster", "op image")
                ):
                    dx = 0
                    dy = 0
                    if hasattr(op, "overscan") and op.overscan is not None:
                        try:
                            ov = float(op.overscan)
                        except ValueError:
                            ov = 0
                        dx += ov
                        dy += ov
                    if acceleration:
                        # Acceleration / deceleration plays a role.
                        if hasattr(self.context.device, "acceleration_overrun"):
                            # is_raster is true...
                            ds = self.context.device.acceleration_overrun(
                                True, op.speed
                            )
                            # print("Specific", op.speed, ds, Length(ds).length_mm)
                        else:
                            a = 500  # arbitrary 500 mm/sec²
                            dt = op.speed / a
                            ds = 0.5 * a * dt * dt * UNITS_PER_MM
                            # print("Generic", op.speed, ds, Length(ds).length_mm)
                        dx += ds

                    for refnode in op.children:
                        node = refnode.node
                        bb = getattr(node, "paint_bounds", None)
                        if bb is None:
                            bb = getattr(node, "bounds", None)
                        if bb is None:
                            continue
                        if bb[2] > wd or bb[0] < 0 or bb[3] > ht or bb[1] < 0:
                            # Even though is bad, that's not what we are looking for
                            continue
                        flag = False
                        if bb[2] + dx > wd or bb[0] - dx < 0:
                            if additional_info:
                                additional_info += ", "
                            additional_info += f"x > {Length(dx, digits=1).length_mm}"
                            flag = True
                        if bb[3] + dy > ht or bb[1] - dy < 0:
                            if additional_info:
                                additional_info += ", "
                            additional_info += f"y > {Length(dy, digits=1).length_mm}"
                            return True, additional_info
                        if flag:
                            return True, additional_info

            return False, ""

        self._concerns.clear()
        max_speed = getattr(self.context.device, "max_vector_speed", None)
        if has_ambitious_operations(max_speed, ("op cut", "op engrave")):
            self._concerns.append(
                _("- Vector operations are too fast.")
                + "\n  "
                + _("Could lead to erratic stepper behaviour and incomplete burns.")
            )
        max_speed = getattr(self.context.device, "max_raster_speed", None)
        if has_ambitious_operations(max_speed, ("op raster", "op image")):
            self._concerns.append(
                _("- Raster operations are too fast.")
                + "\n  "
                + _("Could lead to erratic stepper behaviour and incomplete burns.")
            )
        if has_objects_outside():
            self._concerns.append(
                _("- Elements are lying outside the burnable area.")
                + "\n  "
                + _("Could lead to the laserhead bumping into the rails.")
            )
        flag, info = has_close_to_edge_rasters()
        if flag:
            self._concerns.append(
                _("- Raster operations get very close to the edge.")
                + "\n  "
                + _("Could lead to the laserhead bumping into the rails.")
                + "\n  "
                + info
            )

        non_assigned, non_burn = self.context.elements.have_unburnable_elements()
        if non_assigned:
            self._concerns.append(
                _("- Elements aren't assigned to an operation and will not be burnt")
            )
        if non_burn:
            self._concerns.append(
                _(
                    "- Some operations containing elements aren't active, so some elements will not be burnt"
                )
            )
        self.context.signal("icons")