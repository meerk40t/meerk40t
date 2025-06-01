"""
Routines to check for issues in the design and to give some
warnings to the user
"""
from copy import copy

import wx

from meerk40t.core.units import UNITS_PER_MM, Length
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    STD_ICON_SIZE,
    icon_paint_brush,
    icon_paint_brush_green,
    icon_warning,
)
from meerk40t.gui.wxutils import dip_size, wxButton, wxStaticText, TextCtrl

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
            ("stroke_dash", True),
            ("mktablength", False),
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

        def get_effect_parent(node):
            while node.parent is not None:
                if node.parent.type.startswith("effect "):
                    return node.parent
                node = node.parent
            return None

        if self.state == INACTIVE:
            return
        if self.state == WAITING:
            node = self.context.elements.first_emphasized
            if node is None:
                return
            if node.type in ("file", "group"):
                return
            self.template = node
            self.state = PASTING
            return
        if self.state == PASTING:
            try:
                _id = self.template.id
            except (RuntimeError, AttributeError):
                # No longer existing or invalid?
                self.state = INACTIVE
            nodes_changed = []
            nodes_classify = []
            nodes_images = []
            data = list(self.context.elements.elems(emphasized=True))
            if not data:
                return
            effect_parent = get_effect_parent(self.template)
            with self.context.elements.undoscope("Paste format"):
                for node in data:
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
                    this_effect_parent = get_effect_parent(node)
                    # print (f"template: {'no effect' if effect_parent is None else 'effect'}, target: {'no effect' if this_effect_parent is None else 'effect'}")
                    if this_effect_parent is not effect_parent:
                        if effect_parent is None:
                            # print (f"Will reparent to own effect parent: {this_effect_parent.parent.type}")
                            self.context.elements.drag_and_drop([node], this_effect_parent.parent)
                        else:
                            # print (f"Will reparent to template effect: {effect_parent.type}")
                            self.context.elements.drag_and_drop([node], effect_parent)
                        flag_changed = True

                    if flag_changed:
                        if hasattr(node, "empty_cache"):
                            node.empty_cache()
                        nodes_changed.append(node)
                        if node.type == "elem image":
                            nodes_images.append(node)
                    if flag_pathupdate and hasattr(node, "mktext"):
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
                if nodes_changed:
                    for node in nodes_images:
                        self.context.elements.do_image_update(node, self.context)
                    if nodes_classify and self.context.elements.classify_new:
                        self.context.elements.classify(nodes_classify)
                    self.context.signal("element_property_update", nodes_changed)
                    self.context.signal("refresh_scene", "Scene")

    def on_click(self, *args):
        # print(f"On_click called, state was : {self.state}")
        if self.state == INACTIVE:
            self.state = WAITING
        else:
            self.state = INACTIVE

CONCERN_LOW = 1
CONCERN_NORMAL = 2
CONCERN_CRITICAL = 3

class Warnings:
    def __init__(self, context=None, button=None, *args, **kwargs):
        self.context = context
        self.button = button
        self._concerns = list()
        self._device_acceleration_info = dict()
        self.context.setting(int, "concern_level", 1)
        self.context.kernel.register(
            self.button,
            {
                "label": _("Warning"),
                "icon": icon_warning,
                "rule_visible": lambda d: len(self.concerns) > 0,
                "action": self.show_concerns,
                "tip": _("There are issues with your project"),
                "size": STD_ICON_SIZE,
                "priority": 2,
            },
        )

    @property
    def concerns(self):
        list_critical = []
        list_normal = []
        list_low = []
        warn_level = self.context.setting(int, "concern_level", 1)

        for msg, level in self._concerns:
            if level < warn_level:
                continue
            if level == CONCERN_LOW:
                list_low.append(msg)
            if level == CONCERN_NORMAL:
                list_normal.append(msg)
            if level == CONCERN_CRITICAL:
                list_critical.append(msg)
        s = ""
        if len(list_critical):
            if s:
                s += "\n"
            s += "CRITICAL:\n" + "\n".join(list_critical)
        if len(list_normal):
            if s:
                s += "\n"
            s += "NORMAL:\n" + "\n".join(list_normal)
        if len(list_low):
            if s:
                s += "\n"
            s += "LOW:\n" + "\n".join(list_low)
        return s

    def show_concerns(self, *args):
        # Display a more elaborate information
        warn_level = self.context.setting(int, "concern_level", 1)
        list_low = []
        list_normal = []
        list_critical = []
        for msg, level in self._concerns:
            if level == CONCERN_LOW:
                list_low.append(msg)
            if level == CONCERN_NORMAL:
                list_normal.append(msg)
            if level == CONCERN_CRITICAL:
                list_critical.append(msg)
        txt_low = "\n".join(list_low)
        txt_mid = "\n".join(list_normal)
        txt_critical = "\n".join(list_critical)
        dlg = wx.Dialog(
            None,
            wx.ID_ANY,
            title=_("Warning"),
            size=wx.DefaultSize,
            pos=wx.DefaultPosition,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.context.themes.set_window_colors(dlg)

        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)
        l_hi = _("Critical")
        l_mid = _("Normal")
        l_low = _("Low")
        msg = " " + _("(Would not cause the warn-icon to appear)")
        if warn_level > 3:
            l_hi += " " + msg
        if warn_level > 2:
            l_mid += " " + msg
        if warn_level > 1:
            l_low += " " + msg

        label1 = wxStaticText(dlg, wx.ID_ANY, l_hi)
        sizer.Add(label1, 0, wx.EXPAND, 0)
        info_hi = TextCtrl(
            dlg, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_hi.SetValue(txt_critical)
        sizer.Add(info_hi, 1, wx.EXPAND, 0)

        label2 = wxStaticText(dlg, wx.ID_ANY, l_mid)
        sizer.Add(label2, 0, wx.EXPAND, 0)
        info_mid = TextCtrl(
            dlg, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_mid.SetValue(txt_mid)
        sizer.Add(info_mid, 1, wx.EXPAND, 0)

        label3 = wxStaticText(dlg, wx.ID_ANY, l_low)
        sizer.Add(label3, 0, wx.EXPAND, 0)
        info_low = TextCtrl(
            dlg, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_low.SetValue(txt_low)
        sizer.Add(info_low, 1, wx.EXPAND, 0)
        info_hi.SetToolTip(_("Critical: might damage your laser (e.g. laserhead bumping into rail)"))
        info_mid.SetToolTip(_("Normal: might ruin your burn (e.g. unassigned=unburnt elements)"))
        info_low.SetToolTip(_("Low: I hope you know what your doing (e.g. disabled operations)"))

        choices = []
        prechoices = self.context.lookup("choices/preferences")
        for info in prechoices:
            if info["attr"] == "concern_level":
                cinfo = dict(info)
                cinfo["page"] = ""
                choices.append(cinfo)
                break
        panel = ChoicePropertyPanel(
            dlg, wx.ID_ANY, context=self.context, choices=choices
        )
        sizer.Add(panel, 1, wx.EXPAND, 0)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wxButton(dlg, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        # btn = wx.Button(dlg, wx.ID_CANCEL)
        # btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.EXPAND, 0)
        dlg.SetSizer(sizer)
        sizer.Fit(dlg)
        dlg.SetSize(dip_size(dlg, 620, 400))
        dlg.CenterOnScreen()
        answer = dlg.ShowModal()
        # Unlisten
        panel.module_close()
        dlg.Destroy()
        # We need to revisit the new value...
        self.warning_indicator()

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
                        if op.type in ("op cut", "op engrave"):
                            bb = getattr(node, "bounds", None)
                        else:
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

        def has_hidden_elements():
            flag = False
            count = 0
            for node in self.context.elements.elems():
                if hasattr(node, "hidden") and node.hidden:
                    flag = True
                    count += 1
            return flag, count

        def check_dpis(check_type='low'):
            flag = False
            count = 0
            active = self.context.setting(bool, "warning_dpi", True)
            if not active:
                return flag, count
            threshold = self.context.setting(float, "warning_dpi_low", 1.25)
            if threshold is None:
                threshold = 2
            # Compare function based on check type
            compare = (lambda x, y: x >= y) if check_type == 'low' else (lambda x, y: x <= y)

            laserspot = getattr(self.context.device, "laserspot", "0.3mm")
            try:
                diameter = float(Length(laserspot))
            except ValueError:
                diameter = float(Length("0.3mm"))
            for op in self.context.elements.ops():
                if getattr(op, "consider_laserspot", False) and check_type=="high":
                    # This isn't a relevant comparison, as we have a relevant flag in the op set
                    continue

                if (
                    hasattr(op, "output")
                    and op.output
                    and op.type in ("op raster", "op image")
                    and op.children
                ):
                    if op.type == "op raster":
                        step_x, step_y = self.context.device.view.dpi_to_steps(op.dpi)
                        step_x *= self.context.device.view.native_scale_x
                        step_y *= self.context.device.view.native_scale_y
                        # print (f"Stepx={step_x:.1f}, stepy{step_y:.1f}, diameter={diameter:.1f}")
                        if compare(step_x, threshold * diameter) or compare(step_y, threshold * diameter):
                            flag = True
                            count += 1
                            # break
                    elif op.type == "op image":
                        useop = op.overrule_dpi and op.dpi
                        for node in op.children:
                            image_node = node.node if hasattr(node, "node") else node
                            if getattr(image_node, "hidden", False):
                                continue
                            if hasattr(image_node, "dpi"):
                                opdpi = op.dpi if useop else image_node.dpi
                            else:
                                opdpi = op.dpi
                            step_x, step_y = self.context.device.view.dpi_to_steps(opdpi)
                            step_x *= self.context.device.view.native_scale_x
                            step_y *= self.context.device.view.native_scale_y
                            # Get steps from individual images
                            if compare(step_x, threshold * diameter) or compare(step_y, threshold * diameter):
                                flag = True
                                count += 1
                                # break

            return flag, count

        def check_optimisation():
            flag = False
            count = 0
            active = self.context.setting(bool, "warning_optimisation", True)
            if not active:
                return flag, count
            unsupported = ()
            if hasattr(self.context.device, "get_raster_instructions"):
                instructions = self.context.device.get_raster_instructions()
                unsupported = instructions.get("unsupported_opt", ())
            if not unsupported:
                return flag, count
            for op in self.context.elements.ops():
                if hasattr(op, "raster_direction") and op.raster_direction in unsupported:
                    flag = True
                    count += 1

            return flag, count

        self._concerns.clear()

        active = self.context.setting(bool, "warning_fastoperations", True)
        if active:
            max_speed = getattr(self.context.device, "max_vector_speed", None)
            if has_ambitious_operations(max_speed, ("op cut", "op engrave")):
                self._concerns.append(
                    (
                        _("- Vector operations are too fast.")
                        + "\n  "
                        + _("Could lead to erratic stepper behaviour and incomplete burns."),
                        CONCERN_CRITICAL
                    )
                )
            max_speed = getattr(self.context.device, "max_raster_speed", None)
            if has_ambitious_operations(max_speed, ("op raster", "op image")):
                self._concerns.append(
                    (
                        _("- Raster operations are too fast.")
                        + "\n  "
                        + _("Could lead to erratic stepper behaviour and incomplete burns."),
                        CONCERN_CRITICAL
                    )
                )

        active = self.context.setting(bool, "warning_outside", True)
        if active and has_objects_outside():
            self._concerns.append(
                (
                    _("- Elements are lying outside the burnable area.")
                    + "\n  "
                    + _("Could lead to the laserhead bumping into the rails."),
                    CONCERN_CRITICAL
                )
            )

        active = self.context.setting(bool, "warning_closetoedge", True)
        if active:
            flag, info = has_close_to_edge_rasters()
            if flag:
                self._concerns.append(
                    (
                        _("- Raster operations get very close to the edge.")
                        + "\n  "
                        + _("Could lead to the laserhead bumping into the rails.")
                        + "\n  "
                        + info,
                        CONCERN_NORMAL
                    )
                )

        active1 = self.context.setting(bool, "warning_nonassigned", True)
        active2 = self.context.setting(bool, "warning_opdisabled", True)
        if active1 or active2:
            non_assigned, non_burn = self.context.elements.have_unburnable_elements()
        if active1 and non_assigned:
            self._concerns.append(
                (
                    _("- Elements aren't assigned to an operation and will not be burnt"),
                    CONCERN_NORMAL
                )
            )

        if active2 and non_burn:
            self._concerns.append(
                (
                    _(
                        "- Some operations containing elements aren't active, so some elements will not be burnt"
                    ),
                    CONCERN_LOW
                )
            )

        active = self.context.setting(bool, "warning_hidden", True)
        if active:
            non_visible, info = has_hidden_elements()
            if non_visible:
                self._concerns.append(
                    (
                        _("- Elements are hidden and will not be burnt") + f" ({info})\n",
                        CONCERN_LOW
                    )
                )

        low_dpis, info = check_dpis(check_type='low')
        if low_dpis:
            self._concerns.append(
                (
                    _("- Raster/Images have a low dpi and lines will not overlap") + f" ({info})\n",
                    CONCERN_LOW
                )
            )

        high_dpis, info = check_dpis(check_type='high')
        if high_dpis:
            self._concerns.append(
                (
                    _("- Raster/Images have a high dpi and lines will overlap") + f" ({info})\n",
                    CONCERN_LOW
                )
            )

        invalid_opt, info = check_optimisation()
        if invalid_opt:
            self._concerns.append(
                (
                    _("- Raster/Images have a raster method that is unsupported on this device: no optimisation will be applied in these cases") + f" ({info})\n",
                    CONCERN_NORMAL
                )
            )

        self.context.signal("icons")
