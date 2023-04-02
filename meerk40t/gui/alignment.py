from math import atan, sqrt, tau

import numpy as np
import wx

from meerk40t.core.element_types import elem_nodes
from meerk40t.core.node.node import Node
from meerk40t.svgelements import (
    Arc,
    Close,
    Color,
    CubicBezier,
    Line,
    Move,
    Path,
    Point,
    Polyline,
    QuadraticBezier,
)

from ..core.units import Length
from ..gui.wxutils import StaticBoxSizer, TextCtrl
from ..kernel import signal_listener
from .icons import STD_ICON_SIZE, icons8_arrange_50
from .mwindow import MWindow

_ = wx.GetTranslation


class InfoPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.lbl_info_main = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_default = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_first = wx.StaticText(self, wx.ID_ANY, "")
        self.lbl_info_last = wx.StaticText(self, wx.ID_ANY, "")
        self.preview_size = 25
        self.image_default = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        self.image_first = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        self.image_last = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(self.preview_size, self.preview_size)
        )
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_default = wx.BoxSizer(wx.HORIZONTAL)
        sizer_default.Add(self.image_default, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_default.Add(self.lbl_info_default, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_first = wx.BoxSizer(wx.HORIZONTAL)
        sizer_first.Add(self.image_first, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_first.Add(self.lbl_info_first, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_last = wx.BoxSizer(wx.HORIZONTAL)
        sizer_last.Add(self.image_last, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_last.Add(self.lbl_info_last, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(self.lbl_info_main, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_default, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_first, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_last, 0, wx.EXPAND, 0)
        self.make_raster = None
        self.SetSizer(sizer_main)
        self.Layout

    def show_stuff(self, has_emph):
        def mklabel(label):
            result = ""
            if label is not None:
                result = label
            return result

        def create_image_from_node(node, iconsize):
            image = wx.NullBitmap
            c = None
            # Do we have a standard representation?
            defaultcolor = Color("black")
            data = None
            if node.type.startswith("elem "):
                if (
                    hasattr(node, "stroke")
                    and node.stroke is not None
                    and node.stroke.argb is not None
                ):
                    c = node.stroke
            if node.type.startswith("elem ") and node.type != "elem point":
                data = node
                bounds = node.paint_bounds
            elif node.type in ("group", "file"):
                data = list(node.flat(types=elem_nodes))
                bounds = Node.union_bounds(data, attr="paint_bounds")
            if data is not None:
                image = self.make_raster(
                    data,
                    bounds,
                    width=iconsize,
                    height=iconsize,
                    bitmap=True,
                    keep_ratio=True,
                )

            if c is None:
                c = defaultcolor
            return c, image

        if self.make_raster is None:
            self.make_raster = self.context.elements.lookup("render-op/make_raster")

        count = 0
        first_node = None
        last_node = None
        msg = ""
        if has_emph:
            xdata = list(self.context.elements.elems_nodes(emphasized=True))
            data = []
            for n in xdata:
                if n.type.startswith("elem"):  # n.type == "group":
                    data.append(n)
            count = len(data)
            self.lbl_info_main.SetLabel(
                _("Selected elements: {count}").format(count=count)
            )
            if count > 0:
                node = data[0]
                c, image = create_image_from_node(node, self.preview_size)
                self.image_default.SetBitmap(image)
                self.lbl_info_default.SetLabel(
                    _("As in Selection: {type} {lbl}").format(
                        type=node.type,
                        lbl=mklabel(node.label),
                    )
                )

                data.sort(key=lambda n: n.emphasized_time)
                node = data[0]
                first_node = node
                c, image = create_image_from_node(node, self.preview_size)
                self.image_first.SetBitmap(image)
                self.lbl_info_first.SetLabel(
                    _("First selected: {type} {lbl}").format(
                        type=node.type,
                        lbl=mklabel(node.label),
                    )
                )

                node = data[-1]
                last_node = node
                c, image = create_image_from_node(node, self.preview_size)
                self.image_last.SetBitmap(image)
                self.lbl_info_last.SetLabel(
                    _("Last selected: {type} {lbl}").format(
                        type=node.type,
                        lbl=mklabel(node.label),
                    )
                )
        else:
            self.lbl_info_default.SetLabel("")
            self.lbl_info_first.SetLabel("")
            self.lbl_info_last.SetLabel("")
            self.lbl_info_main.SetLabel(_("No elements selected"))
            self.image_default.SetBitmap(wx.NullBitmap)
            self.image_first.SetBitmap(wx.NullBitmap)
            self.image_last.SetBitmap(wx.NullBitmap)
        return count, first_node, last_node


class AlignmentPanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0
        self.first_node = None
        self.last_node = None
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.relchoices = (
            _("Selection"),
            _("First Selected"),
            _("Last Selected"),
            _("Laserbed"),
            _("Reference-Object"),
        )
        self.xchoices = (_("Leave"), _("Left"), _("Center"), _("Right"))
        self.ychoices = (_("Leave"), _("Top"), _("Center"), _("Bottom"))
        self.modeparam = ("default", "first", "last", "bed", "ref")
        self.xyparam = ("none", "min", "center", "max")

        self.rbox_align_x = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Alignment relative to X-Axis:"),
            choices=self.xchoices,
            majorDimension=4,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_align_x.SetSelection(0)
        self.rbox_align_x.SetToolTip(
            _(
                "Align object at the left side, centered or to the right side in relation to the target point"
            )
        )

        self.rbox_align_y = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Alignment relative to Y-Axis:"),
            choices=self.ychoices,
            majorDimension=4,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_align_y.SetSelection(0)
        self.rbox_align_y.SetToolTip(
            _(
                "Align object to the top, centered or to the bottom in relation to the target point"
            )
        )

        self.rbox_relation = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Relative to:"),
            choices=self.relchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_relation.SetSelection(0)

        self.rbox_treatment = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Treatment:"),
            choices=[_("Individually"), _("As Group")],
            majorDimension=2,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_treatment.SetSelection(0)
        self.btn_align = wx.Button(self, wx.ID_ANY, "Align")
        self.btn_align.SetBitmap(icons8_arrange_50.GetBitmap(resize=25))

        sizer_main.Add(self.rbox_align_x, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_align_y, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_relation, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_treatment, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_align, 0, wx.EXPAND, 0)

        self.info_panel = InfoPanel(self, wx.ID_ANY, context=self.context)
        sizer_main.Add(self.info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_align, self.btn_align)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_x)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_y)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_relation)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_treatment)
        has_emph = self.context.elements.has_emphasis()
        self.context.setting(int, "align_treatment", 0)
        self.context.setting(int, "align_x", 0)
        self.context.setting(int, "align_y", 0)
        self.context.setting(int, "align_relation", 0)
        self.restore_setting()
        self.show_stuff(has_emph)

    def validate_data(self, event=None):
        if event is not None:
            event.Skip()
        if self.context.elements.has_emphasis():
            active = True
            idx = self.rbox_treatment.GetSelection()
            if idx == 1:
                asgroup = 1
            else:
                asgroup = 0
            idx = self.rbox_align_x.GetSelection()
            if idx < 0:
                idx = 0
            xpos = self.xyparam[idx]
            idx = self.rbox_align_y.GetSelection()
            if idx < 0:
                idx = 0
            ypos = self.xyparam[idx]

            idx = self.rbox_relation.GetSelection()
            if idx < 0:
                idx = 0
            mode = self.modeparam[idx]

            if xpos == "none" and ypos == "none":
                active = False
            if mode == "default" and asgroup == 1:
                # That makes no sense...
                active = False
            if (
                self.scene is None
                or self.scene.pane.reference_object is None
                and mode == "ref"
            ):
                active = False
        else:
            active = False
        self.btn_align.Enable(active)

    def on_button_align(self, event):
        idx = self.rbox_treatment.GetSelection()
        group = idx == 1
        idx = self.rbox_align_x.GetSelection()
        if idx < 0:
            idx = 0
        xpos = self.xyparam[idx]
        idx = self.rbox_align_y.GetSelection()
        if idx < 0:
            idx = 0
        ypos = self.xyparam[idx]

        idx = self.rbox_align_y.GetSelection()
        if idx < 0:
            idx = 0
        mode = self.xyparam[idx]

        idx = self.rbox_relation.GetSelection()
        if idx < 0:
            idx = 0
        mode = self.modeparam[idx]

        addition = ""
        if mode == "ref":
            if self.scene is not None:
                node = self.scene.pane.reference_object
                if node is not None:
                    addition = f" --boundaries {node.bounds[0]},{node.bounds[1]},{node.bounds[2]},{node.bounds[3]}"
                else:
                    mode = "default"
            else:
                mode = "default"
        self.context(
            f"align {mode}{addition}{' group' if group else ''} xy {xpos} {ypos}"
        )
        self.save_setting()

    def save_setting(self):
        self.context.align_treatment = self.rbox_treatment.GetSelection()
        self.context.align_x = self.rbox_align_x.GetSelection()
        self.context.align_y = self.rbox_align_y.GetSelection()
        self.context.align_relation = self.rbox_relation.GetSelection()

    def restore_setting(self):
        try:
            self.rbox_treatment.SetSelection(self.context.align_treatment)
            self.rbox_align_x.SetSelection(self.context.align_x)
            self.rbox_align_y.SetSelection(self.context.align_y)
            self.rbox_relation.SetSelection(self.context.align_relation)
        except (RuntimeError, AttributeError, ValueError):
            pass

    def show_stuff(self, has_emph):
        self.rbox_align_x.Enable(has_emph)
        self.rbox_align_y.Enable(has_emph)
        self.rbox_relation.Enable(has_emph)
        self.rbox_treatment.Enable(has_emph)
        self.count, self.first_node, self.last_node = self.info_panel.show_stuff(
            has_emph
        )
        flag = self.scene.pane.reference_object is not None
        self.rbox_relation.EnableItem(4, flag)
        self.validate_data()


class DistributionPanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0
        self.first_node = None
        self.last_node = None
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sortchoices = (
            _("Position"),
            _("First Selected"),
            _("Last Selected"),
        )
        self.xchoices = (_("Leave"), _("Left"), _("Center"), _("Right"), _("Space"))
        self.ychoices = (_("Leave"), _("Top"), _("Center"), _("Bottom"), _("Space"))
        self.treatmentchoices = (
            _("Position"),
            _("Shape"),
            _("Points"),
            _("Laserbed"),
            _("Ref-Object"),
        )

        self.sort_param = ("default", "first", "last")
        self.xy_param = ("none", "min", "center", "max", "space")
        self.treat_param = ("default", "shape", "points", "bed", "ref")

        self.rbox_dist_x = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Position of element relative to point for X-Axis:"),
            choices=self.xchoices,
            majorDimension=5,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_dist_x.SetSelection(0)
        self.rbox_dist_x.SetToolTip(
            _(
                "Align object at the left side, centered or to the right side in relation to the target point"
            )
        )

        self.rbox_dist_y = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Position of element relative to point for Y-Axis:"),
            choices=self.ychoices,
            majorDimension=5,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_dist_y.SetSelection(0)
        self.rbox_dist_y.SetToolTip(
            _(
                "Align object to the top, centered or to the bottom in relation to the target point"
            )
        )

        self.check_inside_xy = wx.CheckBox(
            self, id=wx.ID_ANY, label=_("Keep first + last inside")
        )
        self.check_inside_xy.SetValue(True)
        self.check_inside_xy.SetToolTip(
            _(
                "Keep the first and last element inside the target area, effectively ignoring the X- and Y-settings"
            )
        )

        self.check_rotate = wx.CheckBox(self, id=wx.ID_ANY, label=_("Rotate"))
        self.check_rotate.SetToolTip(_("Rotate elements parallel to the path"))

        self.rbox_sort = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Work-Sequence:"),
            choices=self.sortchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_sort.SetSelection(0)
        self.rbox_sort.SetToolTip(
            _("Defines the order in which the selection is being processed")
        )

        self.rbox_treatment = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Treatment:"),
            choices=self.treatmentchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_treatment.SetSelection(0)
        self.rbox_treatment.SetToolTip(
            _(
                "Defines the area / the shape on which the selection will be distributed:"
            )
            + "\n"
            + _(
                "- Position: along the boundaries of the surrounding rectangle of the selection"
            )
            + "\n"
            + _("- Shape: along the shape of the first/last selected element")
            + "\n"
            + _("- Points: on the defined points of the first/last selected element")
            + "\n"
            + _("- Laserbed: along the boundaries of the laserbed")
            + "\n"
            + _("- Ref-Object: along the boundaries of a reference-object")
        )

        self.btn_dist = wx.Button(self, wx.ID_ANY, "Distribute")
        self.btn_dist.SetBitmap(icons8_arrange_50.GetBitmap(resize=25))

        sizer_check = StaticBoxSizer(
            self,
            wx.ID_ANY,
            _("First and last element treatment"),
            wx.HORIZONTAL,
        )
        sizer_check.Add(self.check_inside_xy, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_treat = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rotate = StaticBoxSizer(self, wx.ID_ANY, _("Rotation"), wx.HORIZONTAL)
        sizer_rotate.Add(self.check_rotate, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_treat.Add(self.rbox_treatment, 1, wx.EXPAND, 0)
        sizer_treat.Add(sizer_rotate, 0, wx.EXPAND, 0)

        sizer_main.Add(self.rbox_dist_x, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_dist_y, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_check, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_sort, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_treat, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_dist, 0, wx.EXPAND, 0)

        self.info_panel = InfoPanel(self, wx.ID_ANY, context=self.context)
        sizer_main.Add(self.info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.btn_dist.Bind(wx.EVT_BUTTON, self.on_button_dist)
        self.rbox_dist_x.Bind(wx.EVT_RADIOBOX, self.validate_data)
        self.rbox_dist_y.Bind(wx.EVT_RADIOBOX, self.validate_data)
        self.rbox_sort.Bind(wx.EVT_RADIOBOX, self.validate_data)
        self.rbox_treatment.Bind(wx.EVT_RADIOBOX, self.validate_data)
        self.context.setting(int, "distribute_x", 0)
        self.context.setting(int, "distribute_y", 0)
        self.context.setting(int, "distribute_treatment", 0)
        self.context.setting(int, "distribute_sort", 0)
        self.context.setting(bool, "distribute_inside", False)
        self.context.setting(bool, "distribute_rotate", False)

        self.restore_setting()
        has_emph = self.context.elements.has_emphasis()
        self.show_stuff(has_emph)

    def validate_data(self, event=None):
        obj = None
        if event is not None:
            event.Skip()
            obj = event.GetEventObject()
        if self.context.elements.has_emphasis():
            active = True
            idx = max(0, self.rbox_treatment.GetSelection())
            treat = self.treat_param[idx]
            idx = max(0, self.rbox_dist_x.GetSelection())
            xmode = self.xy_param[idx]
            idx = max(0, self.rbox_dist_y.GetSelection())
            ymode = self.xy_param[idx]
            idx = max(0, self.rbox_sort.GetSelection())
            esort = self.sort_param[idx]
            rotate_elem = self.check_rotate.GetValue()

            # Have we just selected the treatment? Then set something useful
            if obj == self.rbox_treatment and xmode == "none" and ymode == "none":
                self.rbox_dist_x.SetSelection(2)
                self.rbox_dist_y.SetSelection(2)
                xmode = "center"
                ymode = "center"
            if treat == "default" and self.count < 3:
                active = False
            elif treat in ("shape", "points") and self.count < 3:
                active = False

            if treat in ("shape", "points") and xmode == "space":
                self.rbox_dist_x.SetSelection(2)
                xmode = "center"
            if treat in ("shape", "points") and ymode == "space":
                self.rbox_dist_y.SetSelection(2)
                ymode = "center"
            if xmode == "none" and ymode == "none":
                active = False
            if self.first_node is None and esort == "first":
                active = False
            if self.last_node is None and esort == "last":
                active = False
        else:
            treat = None
            active = False
        if treat in ("points", "shape"):
            self.check_inside_xy.Enable(False)
            self.check_inside_xy.SetValue(False)
        elif xmode == "space" or ymode == "space":
            self.check_inside_xy.Enable(False)
            self.check_inside_xy.SetValue(False)
        else:
            self.check_inside_xy.Enable(True)
            self.check_rotate.Enable(False)
        if treat == "shape":
            self.check_rotate.Enable(True)
        else:
            self.check_rotate.Enable(False)
            self.check_rotate.SetValue(False)

        self.btn_dist.Enable(active)

    def calculate_basis(self, data, target, treatment, equidist_x, equidist_y, rotate):
        def calc_basic():
            # equidist_x<:
            #   if True create equidistant points across line
            #   if False create equal distances between edges of elements
            target.clear()
            x = left_edge
            y = top_edge
            dlen = len(data)
            x_values = [x]
            y_values = [y]
            if dlen > 1:
                if equidist_x:
                    dx = (right_edge - left_edge) / (dlen - 1)
                    dl = dlen
                    while dl > 1:
                        x += dx
                        x_values.append(x)
                        dl -= 1
                else:
                    total_wd = right_edge - left_edge
                    data_wd = 0
                    firstwd = None
                    lastwd = None
                    for node in data:
                        bb = node.bounds
                        wd = bb[2] - bb[0]
                        if firstwd is None:
                            firstwd = wd
                        lastwd = wd
                        data_wd += wd
                    # Reduce by first and last half width
                    # data_wd -= (firstwd + lastwd) / 2
                    dx = (total_wd - data_wd) / (dlen - 1)
                    # print(
                    #     "Totalwidth={w1:.3f}, Element={w2:.3f}, Gap={w3:.3f}".format(
                    #         w1=Length(amount=total_wd, unitless=1).mm,
                    #         w2=Length(amount=data_wd, unitless=1).mm,
                    #         w3=Length(amount=dx, unitless=1).mm,
                    #     )
                    # )
                    for i, node in enumerate(data):
                        bb = node.bounds
                        wd = bb[2] - bb[0]
                        if i == 0:
                            lastx = left_edge + wd
                            x_values[0] = left_edge + wd / 2
                        else:
                            x = lastx + wd / 2 + dx
                            lastx = lastx + wd + dx
                            x_values.append(x)

                if equidist_y:
                    dy = (bottom_edge - top_edge) / (dlen - 1)
                    dl = dlen
                    while dl > 1:
                        y += dy
                        y_values.append(y)
                        dl -= 1
                else:
                    total_ht = bottom_edge - top_edge
                    data_ht = 0
                    firstht = None
                    lastht = None
                    for node in data:
                        bb = node.bounds
                        ht = bb[3] - bb[1]
                        if firstht is None:
                            firstht = ht
                        lastht = ht
                        data_ht += ht
                    # Reduce by first and last half height
                    # data_ht -= (firstht + lastht) / 2
                    dy = (total_ht - data_ht) / (dlen - 1)
                    # print(
                    #     "Totalheight={w1:.3f}, Element={w2:.3f}, Gap={w3:.3f}".format(
                    #         w1=Length(amount=total_ht, unitless=1).mm,
                    #         w2=Length(amount=data_ht, unitless=1).mm,
                    #         w3=Length(amount=dy, unitless=1).mm,
                    #     )
                    # )
                    for i, node in enumerate(data):
                        bb = node.bounds
                        ht = bb[3] - bb[1]
                        if i == 0:
                            lasty = top_edge + ht
                            y_values[0] = top_edge + ht / 2
                        else:
                            y = lasty + ht / 2 + dy
                            lasty = lasty + ht + dy
                            y_values.append(y)

            for i in range(dlen):
                x = x_values[i]
                y = y_values[i]
                target.append((x, y, 0))

        def calc_points():
            first_point = path.first_point
            if first_point is not None:
                pt = (first_point[0], first_point[1], 0)
                target.append(pt)
            for e in path:
                if isinstance(e, Move):
                    pt = (e.end[0], e.end[1], 0)
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Line):
                    pt = (e.end[0], e.end[1], 0)
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Close):
                    pass
                elif isinstance(e, QuadraticBezier):
                    pt = (e.end[0], e.end[1], 0)
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, CubicBezier):
                    pt = (e.end[0], e.end[1], 0)
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Arc):
                    pt = (e.end[0], e.end[1], 0)
                    if pt not in target:
                        target.append(pt)

        def calc_path():
            def closed_path():
                p1 = path.first_point
                p2 = path.current_point
                # print (p1, p2)
                # print (type(p1).__name__, type(p2).__name__)
                return p1 == p2

            def generate_polygon():
                this_length = 0
                interpolation = 100

                polypoints.clear()
                polygons = []
                for subpath in path.as_subpaths():
                    subj = Path(subpath).npoint(np.linspace(0, 1, interpolation))

                    subj.reshape((2, interpolation))
                    s = list(map(Point, subj))
                    polygons.append(s)

                if len(polygons) > 0:
                    # idx = 0
                    # for pt in polygons[0]:
                    #     if pt.x > 1.0E8 or pt.y > 1.0E8:
                    #         print ("Rather high [%d]: x=%.1f, y=%.1f" % (idx, pt.x, pt.y))
                    #     idx += 1
                    last_x = None
                    last_y = None
                    idx = -1
                    for pt in polygons[0]:
                        if pt is None or pt.x is None or pt.y is None:
                            continue
                        if abs(pt.x) > 1.0e8 or abs(pt.y) > 1.0e8:
                            # this does not seem to be a valid coord...
                            continue
                        idx += 1
                        if idx > 0:
                            dx = pt.x - last_x
                            dy = pt.y - last_y
                            this_length += sqrt(dx * dx + dy * dy)
                        polypoints.append((pt.x, pt.y, this_length))
                        last_x = pt.x
                        last_y = pt.y
                return this_length

            def calc_slope(index):
                try:
                    this_point = polypoints[index]
                except IndexError:
                    this_point = (0, 0, 0)
                try:
                    last_point = polypoints[index - 1]
                except IndexError:
                    last_point = (0, 0, 0)
                dx = this_point[0] - last_point[0]
                dy = this_point[1] - last_point[1]
                # TODO: Replace remaining code with atan2
                # if dx < 1.0E-07:
                #     dx = 0
                # if dy < 1.0E-07:
                #     dy = 0
                # calc_atan(dx, dy):
                if dx == 0:
                    if dy < 0:
                        c_angle = -1 / 4 * tau
                        quadrant = 4
                    elif dy == 0:
                        c_angle = 0
                        quadrant = 0
                    else:
                        c_angle = +1 / 4 * tau
                        quadrant = 1
                elif dx > 0 and dy >= 0:
                    # Quadrant 1: angle between 0 und 90 (0 - tau / 4)
                    c_angle = atan(dy / dx)
                    quadrant = 1
                elif dx < 0 and dy >= 0:
                    # Quadrant 2: angle between 90 und 180 (1/4 tau - 2/4 tau)
                    c_angle = atan(dy / dx) + tau / 2
                    quadrant = 2
                elif dx < 0 and dy < 0:
                    # Quadrant 3: angle between 180 und 270 (2/4 tau - 3/4 tau)
                    c_angle = atan(dy / dx) + tau / 2
                    quadrant = 3
                elif dx > 0 and dy < 0:
                    # Quadrant 4: angle between 270 und 360 (2/4 tau - 3/4 tau)
                    c_angle = atan(dy / dx)
                    quadrant = 4
                # print(
                #     f"dx, dy={dx:.2f}, {dy:.2f}, Quadrant={quadrant}, "
                #     + f"angle={c_angle:.2f} ({c_angle / tau * 360.0:.2f})"
                # )
                return c_angle

            polypoints = []
            poly_length = generate_polygon()
            if len(polypoints) == 0:
                # Degenerate !!
                return
            # Closed path? -> Different intermediary points
            is_closed_path = closed_path()
            if is_closed_path:
                segcount = len(data)
            else:
                segcount = len(data) - 1
            if segcount <= 0:
                segcount = 1
            mylen = 0
            mydelta = poly_length / segcount
            lastx = 0
            lasty = 0
            lastlen = 0
            segadded = 0
            # print(f"Expected segcount= {segcount}")
            # Now iterate over all points and establish the positions
            idx = -1
            for idxpt, pt in enumerate(polypoints):
                x = pt[0]
                y = pt[1]
                if len(polypoints) > 1:
                    if idxpt == 0:
                        ptangle = calc_slope(idxpt + 1)
                    else:
                        ptangle = calc_slope(idxpt)
                else:
                    ptangle = 0
                plen = pt[2]
                if abs(x) > 1.0e8 or abs(y) > 1.0e8:
                    # this does not seem to be a valid coord...
                    continue
                idx += 1
                # print(f"Compare {mylen:.1f} to {plen:.1f}")
                while plen >= mylen:
                    if idx != 0 and plen > mylen:
                        # Adjust the point...
                        if lastlen != plen:  # Only if different
                            fract = (mylen - lastlen) / (plen - lastlen)
                            x = lastx + fract * (x - lastx)
                            y = lasty + fract * (y - lasty)
                    newpt = (x, y, ptangle)
                    # print (f"I add: ({x:.1f}, {y:.1f}, {ptangle:.3f}) {ptangle/tau*360.0:.3f} ")
                    if newpt not in target:
                        # print ("..and added")
                        target.append(newpt)
                        segadded += 1
                    mylen += mydelta

                lastx = pt[0]
                lasty = pt[1]
                lastlen = pt[2]
                last_angle = ptangle
            # We may have slightly overshot, so in doubt add the last point
            if segadded < segcount:
                # print ("I would add to it the last point...")
                newpt = (lastx, lasty, last_angle)
                if newpt not in target:
                    # print (f"Finally: ({last_x:.1f}, {last_y:.1f}, {last_angle:.3f})")
                    segadded += 1
                    target.append(newpt)
            # print (f"Target points: {len(target)}")

        # "default", "shape", "points", "bed", "ref")
        if treatment == "ref" and self.scene.pane.reference_object is None:
            treatment = "default"
        if treatment == "default":
            # Let's get the boundaries of the data-set
            left_edge = float("inf")
            right_edge = -left_edge
            top_edge = float("inf")
            bottom_edge = -top_edge
            for node in data:
                left_edge = min(left_edge, node.bounds[0])
                top_edge = min(top_edge, node.bounds[1])
                right_edge = max(right_edge, node.bounds[2])
                bottom_edge = max(bottom_edge, node.bounds[3])
            calc_basic()
        elif treatment == "bed":
            left_edge = 0
            top_edge = 0
            right_edge = float(Length(self.context.device.width))
            bottom_edge = float(Length(self.context.device.height))
            calc_basic()
        elif treatment == "ref":
            left_edge = self.scene.pane.reference_object.bounds[0]
            top_edge = self.scene.pane.reference_object.bounds[1]
            right_edge = self.scene.pane.reference_object.bounds[2]
            bottom_edge = self.scene.pane.reference_object.bounds[3]
            calc_basic()
        elif treatment == "points":
            # So what's the reference node? And delete it...
            refnode = data[0]
            if hasattr(refnode, "as_path"):
                path = refnode.as_path()
            elif hasattr(refnode, "bounds"):
                points = [
                    [refnode.bounds[0], refnode.bounds[1]],
                    [refnode.bounds[2], refnode.bounds[1]],
                    [refnode.bounds[2], refnode.bounds[3]],
                    [refnode.bounds[0], refnode.bounds[3]],
                    [refnode.bounds[0], refnode.bounds[1]],
                ]
                path = abs(Path(Polyline(points)))
            else:
                # has no path
                wx.Bell()
                return
            data.pop(0)
            calc_points()
        elif treatment == "shape":
            # So what's the reference node? And delete it...
            refnode = data[0]
            if hasattr(refnode, "as_path"):
                path = refnode.as_path()
            elif hasattr(refnode, "bounds"):
                points = [
                    [refnode.bounds[0], refnode.bounds[1]],
                    [refnode.bounds[2], refnode.bounds[1]],
                    [refnode.bounds[2], refnode.bounds[3]],
                    [refnode.bounds[0], refnode.bounds[3]],
                    [refnode.bounds[0], refnode.bounds[1]],
                ]
                path = abs(Path(Polyline(points)))
            else:
                # has no path
                wx.Bell()
                return
            data.pop(0)
            calc_path()

    def prepare_data(self, data, esort):
        xdata = list(self.context.elements.elems(emphasized=True))
        data.clear()
        for n in xdata:
            if n.type.startswith("elem"):
                data.append(n)
        if esort == "first":
            data.sort(key=lambda n: n.emphasized_time)
        elif esort == "last":
            data.sort(reverse=True, key=lambda n: n.emphasized_time)

    def apply_results(self, data, target, xmode, ymode, remain_inside):
        modified = 0
        # TODO: establish when the first and last element may not been adjusted
        idxmin = 0
        idxmax = min(len(target), len(data)) - 1
        for idx, node in enumerate(data):
            if idx >= len(target):
                break
            dx = target[idx][0] - node.bounds[0]
            dy = target[idx][1] - node.bounds[1]
            ptangle = target[idx][2]
            if xmode == "none":
                dx = 0
                # Makes no sense if not both xmode and ymode are set...
                ptangle = 0
            elif remain_inside and idx == idxmin:
                # That's already fine
                pass
            elif remain_inside and idx == idxmax:
                dx -= node.bounds[2] - node.bounds[0]
            elif xmode == "min":
                # That's already fine
                pass
            elif xmode == "center":
                dx -= (node.bounds[2] - node.bounds[0]) / 2
            elif xmode == "max":
                dx -= node.bounds[2] - node.bounds[0]

            if ymode == "none":
                dy = 0
                # Makes no sense if not both xmode and ymode are set...
                ptangle = 0
            elif remain_inside and idx == idxmin:
                # That's already fine
                pass
            elif remain_inside and idx == idxmax:
                dy -= node.bounds[3] - node.bounds[1]
            elif ymode == "min":
                # That's already fine
                pass
            elif ymode == "center":
                dy -= (node.bounds[3] - node.bounds[1]) / 2
            elif ymode == "max":
                dy -= node.bounds[3] - node.bounds[1]

            if dx == 0 and dy == 0 and ptangle == 0:
                continue
            if (
                hasattr(node, "lock")
                and node.lock
                and not self.context.elements.lock_allows_move
            ):
                continue
            else:
                try:
                    cx = (node.bounds[2] + node.bounds[0]) / 2 + dx
                    cy = (node.bounds[3] + node.bounds[1]) / 2 + dy
                    change = 0
                    if dx != 0 or dy != 0:
                        node.matrix.post_translate(dx, dy)
                        change = 1
                    # Do we have a rotation to take into account?
                    if ptangle != 0:
                        node.matrix.post_rotate(ptangle, cx, cy)
                        change = 2
                    if change == 1:
                        node.translated(dx, dy)
                    elif change == 2:
                        node.modified()

                    modified += 1
                except AttributeError:
                    continue
        # print(f"Modified: {modified}")

    def on_button_dist(self, event):
        idx = max(0, self.rbox_treatment.GetSelection())
        treat = self.treat_param[idx]
        idx = max(0, self.rbox_dist_x.GetSelection())
        xmode = self.xy_param[idx]
        idx = max(0, self.rbox_dist_y.GetSelection())
        ymode = self.xy_param[idx]
        idx = max(0, self.rbox_sort.GetSelection())
        esort = self.sort_param[idx]
        remain_inside = bool(self.check_inside_xy.GetValue())
        if treat in ("points", "shape"):
            remain_inside = False
        rotate_elem = self.check_rotate.GetValue()
        if treat not in ("points", "shape"):
            rotate_elem = False
        # print(f"Params: x={xmode}, y={ymode}, sort={esort}, treat={treat}")
        # The elements...
        data = []
        target = []
        self.prepare_data(data, esort)
        if xmode == "space":
            # Space
            equidist_x = False
            xmode = "center"
        else:
            equidist_x = True
        if ymode == "space":
            # Space
            equidist_y = False
            ymode = "center"
        else:
            equidist_y = True
        self.calculate_basis(data, target, treat, equidist_x, equidist_y, rotate_elem)
        self.apply_results(data, target, xmode, ymode, remain_inside)
        self.context.signal("refresh_scene", "Scene")
        self.save_setting()

    def save_setting(self):
        self.context.distribute_x = self.rbox_dist_x.GetSelection()
        self.context.distribute_y = self.rbox_dist_y.GetSelection()
        self.context.distribute_treatment = self.rbox_treatment.GetSelection()
        self.context.distribute_sort = self.rbox_sort.GetSelection()
        self.context.distribute_inside = self.check_inside_xy.GetValue()
        self.context.distribute_rotate = self.check_rotate.GetValue()

    def restore_setting(self):
        try:
            self.rbox_dist_x.SetSelection(self.context.distribute_x)
            self.rbox_dist_y.SetSelection(self.context.distribute_y)
            self.rbox_treatment.SetSelection(self.context.distribute_treatment)
            self.rbox_sort.SetSelection(self.context.distribute_sort)
            self.check_inside_xy.SetValue(bool(self.context.distribute_inside))
            self.check_rotate.SetValue(bool(self.context.distribute_rotate))
        except (ValueError, AttributeError, RuntimeError):
            pass

    def show_stuff(self, has_emph):
        showit = has_emph
        # showit = False # Not yet ready
        self.rbox_dist_x.Enable(showit)
        self.rbox_dist_y.Enable(showit)
        self.rbox_sort.Enable(showit)
        self.rbox_treatment.Enable(showit)
        self.check_inside_xy.Enable(showit)
        self.check_rotate.Enable(showit)
        self.count, self.first_node, self.last_node = self.info_panel.show_stuff(
            has_emph
        )
        flag = self.scene.pane.reference_object is not None
        self.rbox_treatment.EnableItem(4, flag)

        if showit:
            self.validate_data()
        else:
            self.btn_dist.Enable(showit)


class ArrangementPanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0
        self.first_node = None
        self.last_node = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.relchoices = (
            _("Adjacent"),
            _("Set distances"),
        )
        self.relparam = ("selection", "distance")

        self.selchoices = (
            _("Selection"),
            _("First Selected"),
            _("Last Selected"),
        )
        self.selectparam = ("default", "first", "last")

        self.xchoices = (_("Left"), _("Center"), _("Right"))
        self.ychoices = (_("Top"), _("Center"), _("Bottom"))
        self.xyparam = ("min", "center", "max")

        self.rbox_align_x = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Alignment relative to X-Axis:"),
            choices=self.xchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_align_x.SetSelection(0)

        self.rbox_align_y = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Alignment relative to Y-Axis:"),
            choices=self.ychoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_align_y.SetSelection(0)

        self.arrange_x = wx.SpinCtrl(self, wx.ID_ANY, initial=1, min=1, max=100)
        self.arrange_y = wx.SpinCtrl(self, wx.ID_ANY, initial=1, min=1, max=100)

        self.check_same_x = wx.CheckBox(self, wx.ID_ANY, label=_("Same width"))
        self.check_same_y = wx.CheckBox(self, wx.ID_ANY, label=_("Same height"))

        self.rbox_relation = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Arrangement inside grid:"),
            choices=self.relchoices,
            majorDimension=2,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.rbox_relation.SetSelection(0)

        self.rbox_selection = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Order to process:"),
            choices=self.selchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_selection.SetSelection(0)

        self.txt_gap_x = TextCtrl(
            self, id=wx.ID_ANY, value="5mm", limited=True, check="length"
        )
        self.txt_gap_y = TextCtrl(
            self, id=wx.ID_ANY, value="5mm", limited=True, check="length"
        )

        self.btn_arrange = wx.Button(self, wx.ID_ANY, _("Arrange"))
        self.btn_arrange.SetBitmap(icons8_arrange_50.GetBitmap(resize=25))

        sizer_dimensions = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dim_x = StaticBoxSizer(
            self,
            wx.ID_ANY,
            _("X-Axis:"),
            wx.VERTICAL,
        )
        sizer_dim_x.Add(self.arrange_x, 0, wx.EXPAND, 0)
        sizer_dim_x.Add(self.check_same_x, 0, wx.EXPAND, 0)

        sizer_dim_y = StaticBoxSizer(
            self,
            wx.ID_ANY,
            _("Y-Axis:"),
            wx.VERTICAL,
        )
        sizer_dim_y.Add(self.arrange_y, 0, wx.EXPAND, 0)
        sizer_dim_y.Add(self.check_same_y, 0, wx.EXPAND, 0)

        sizer_dimensions.Add(sizer_dim_x, 1, wx.EXPAND, 0)
        sizer_dimensions.Add(sizer_dim_y, 1, wx.EXPAND, 0)

        sizer_gaps_x = wx.BoxSizer(wx.HORIZONTAL)
        sizer_gaps_x.Add(
            wx.StaticText(self, wx.ID_ANY, _("X:")), 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        sizer_gaps_x.Add(self.txt_gap_x, 1, wx.EXPAND, 0)
        sizer_gaps_y = wx.BoxSizer(wx.HORIZONTAL)
        sizer_gaps_y.Add(
            wx.StaticText(self, wx.ID_ANY, _("Y:")), 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        sizer_gaps_y.Add(self.txt_gap_y, 1, wx.EXPAND, 0)
        sizer_gaps_xy = StaticBoxSizer(self, wx.ID_ANY, _("Gaps:"), wx.VERTICAL)
        sizer_gaps_xy.Add(sizer_gaps_x, 1, wx.EXPAND, 0)
        sizer_gaps_xy.Add(sizer_gaps_y, 1, wx.EXPAND, 0)
        sizer_gaps = wx.BoxSizer(wx.HORIZONTAL)
        sizer_gaps.Add(self.rbox_relation, 1, wx.EXPAND, 0)
        sizer_gaps.Add(sizer_gaps_xy, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_dimensions, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_align_x, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_align_y, 0, wx.EXPAND, 0)

        sizer_main.Add(self.rbox_selection, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_gaps, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_arrange, 0, wx.EXPAND, 0)

        self.info_panel = InfoPanel(self, wx.ID_ANY, context=self.context)
        sizer_main.Add(self.info_panel, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()
        self.btn_arrange.SetToolTip(_("Rearrange all selected elements"))
        # self.rbox_align_x.SetToolTip(_(""))
        # self.rbox_align_y.SetToolTip(_(""))
        self.check_same_x.SetToolTip(
            _(
                "Set if all columns need to have the same size (ie maximum width over all columns)"
            )
        )
        self.check_same_y.SetToolTip(
            _(
                "Set if all rows need to have the same size (ie maximum height over all row)"
            )
        )
        # self.rbox_relation.SetToolTip(_(""))
        # self.rbox_selection.SetToolTip(_(""))
        # self.arrange_x.SetToolTip(_(""))
        # self.arrange_y.SetToolTip(_(""))
        self.txt_gap_x.SetToolTip(_("Set the distance between columns"))
        self.txt_gap_y.SetToolTip(_("Set the distance between rows"))

        self.Bind(wx.EVT_BUTTON, self.on_button_align, self.btn_arrange)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_x)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_y)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_selection)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_relation)
        self.Bind(wx.EVT_CHECKBOX, self.validate_data, self.check_same_x)
        self.Bind(wx.EVT_CHECKBOX, self.validate_data, self.check_same_y)
        self.Bind(wx.EVT_SPINCTRL, self.validate_data, self.arrange_x)
        self.Bind(wx.EVT_SPINCTRL, self.validate_data, self.arrange_y)
        self.Bind(wx.EVT_TEXT, self.validate_data, self.txt_gap_x)
        self.Bind(wx.EVT_TEXT, self.validate_data, self.txt_gap_y)
        has_emph = self.context.elements.has_emphasis()
        self.context.setting(int, "arrange_x", 0)
        self.context.setting(int, "arrange_y", 0)
        self.context.setting(int, "arrange_relation", 0)
        self.context.setting(int, "arrange_selection", 0)
        self.context.setting(int, "arrange_cols", 0)
        self.context.setting(int, "arrange_rows", 0)
        self.context.setting(bool, "arrange_checkx", 0)
        self.context.setting(bool, "arrange_checky", 0)
        self.context.setting(str, "arrange_gapx", "5mm")
        self.context.setting(str, "arrange_gapy", "5mm")
        self.restore_setting()
        self.show_stuff(has_emph)

    def validate_data(self, event=None):
        if event is not None:
            event.Skip()
        if self.context.elements.has_emphasis():
            active = True
            num_cols = self.arrange_x.GetValue()
            num_rows = self.arrange_y.GetValue()
            if self.count < 2 or self.count > num_cols * num_rows:
                # print(f"Too small: {self.count} vs. {num_cols}x{num_rows}")
                active = False
            idx = self.rbox_selection.GetSelection()
            if idx < 0:
                idx = 0
            esort = self.selectparam[idx]
            idx = self.rbox_relation.GetSelection()
            if idx < 0:
                idx = 0
            relat = self.relparam[idx]
            self.txt_gap_x.Enable(relat == "distance")
            self.txt_gap_y.Enable(relat == "distance")
            idx = self.rbox_align_x.GetSelection()
            if idx < 0:
                idx = 0
            xpos = self.xyparam[idx]
            idx = self.rbox_align_y.GetSelection()
            if idx < 0:
                idx = 0
            ypos = self.xyparam[idx]
            try:
                gapx = float(Length(self.txt_gap_x.GetValue()))
            except ValueError:
                gapx = -1
            try:
                gapy = float(Length(self.txt_gap_y.GetValue()))
            except ValueError:
                gapy = -1
            # Invalid gaps?
            if relat == "distance" and (gapx < 0 or gapy < 0):
                # print("Invalid gaps")
                active = False
        else:
            active = False
        # active = True
        self.btn_arrange.Enable(active)

    def on_button_align(self, event):
        def prepare_data():
            xdata = list(self.context.elements.elems(emphasized=True))
            data.clear()
            for n in xdata:
                if n.type.startswith("elem"):
                    data.append(n)
            if esort == "first":
                data.sort(key=lambda n: n.emphasized_time)
            elif esort == "last":
                data.sort(reverse=True, key=lambda n: n.emphasized_time)

        def calculate_arrays():
            row = 0
            col = 0
            max_colwid = [0] * num_cols
            max_rowht = [0]
            total_max_wid = 0
            total_max_ht = 0
            for node in data:
                bb = node.bounds
                wd = bb[2] - bb[0]
                ht = bb[3] - bb[1]
                total_max_ht = max(total_max_ht, ht)
                max_rowht[row] = max(max_rowht[row], ht)
                total_max_wid = max(total_max_wid, wd)
                max_colwid[col] = max(max_colwid[col], wd)

                col += 1
                if col >= num_cols:
                    col = 0
                    row += 1
                    max_rowht.append(0)
            max_xx = 0
            max_yy = 0
            xx = 0
            yy = 0
            # target contains the bound of the grid segment
            target.clear()
            for idx2 in range(len(max_rowht)):
                if same_y:
                    dy = total_max_ht
                else:
                    dy = max_rowht[idx2]
                for idx1 in range(num_cols):
                    if same_x:
                        dx = total_max_wid
                    else:
                        dx = max_colwid[idx1]
                    bb = (xx, yy, xx + dx, yy + dy)
                    max_xx = max(max_xx, xx + dy)
                    max_yy = max(max_yy, yy + dy)
                    target.append(bb)
                    xx = xx + dx + gapx
                xx = 0
                yy = yy + dy + gapy
            # Now that we have established the global boundaries,
            # we are going to center it on the scene...
            # By definition the origin was set to 0 0
            dx = float(Length(self.context.device.width)) / 2 - (0 + max_xx) / 2
            dy = float(Length(self.context.device.height)) / 2 - (0 + max_yy) / 2
            for idx, bb in enumerate(target):
                newbb = (bb[0] + dx, bb[1] + dy, bb[2] + dx, bb[3] + dy)
                target[idx] = newbb

        def arrange_elements():
            for idx, node in enumerate(data):
                bb = node.bounds
                if idx >= len(target):
                    # no more information available
                    break
                # target contains the bound of the grid segment
                left_edge = target[idx][0]
                right_edge = target[idx][2]
                top_edge = target[idx][1]
                bottom_edge = target[idx][3]

                if xpos == "min":
                    dx = left_edge - bb[0]
                elif xpos == "center":
                    dx = (right_edge + left_edge) / 2 - (bb[2] + bb[0]) / 2
                elif xpos == "max":
                    dx = right_edge - bb[2]
                else:
                    dx = 0
                if ypos == "min":
                    dy = top_edge - bb[1]
                elif ypos == "center":
                    dy = (bottom_edge + top_edge) / 2 - (bb[3] + bb[1]) / 2
                elif ypos == "max":
                    dy = bottom_edge - bb[3]
                else:
                    dy = 0

                # s = f"{node.type} pos: {Length(amount=bb[0], unitless=1, digits=1).length_mm}, "
                # s += f"{Length(amount=bb[0], unitless=1, digits=1).length_mm} - "
                # s += f"{Length(amount=bb[2], unitless=1, digits=1).length_mm} - "
                # s += f"{Length(amount=bb[3], unitless=1, digits=1).length_mm}"
                # print (s)
                # s = f"Set to: {Length(amount=left_edge, unitless=1, digits=1).length_mm}, "
                # s += f"{Length(amount=top_edge, unitless=1, digits=1).length_mm} - "
                # s += f"{Length(amount=right_edge, unitless=1, digits=1).length_mm} - "
                # s += f"{Length(amount=bottom_edge, unitless=1, digits=1).length_mm}"
                # print (s)
                # s = f"dx={Length(amount=dx, unitless=1, digits=1).length_mm}, "
                # s += f"dx={Length(amount=dy, unitless=1, digits=1).length_mm}"
                # print (s)
                if dx != 0 or dy != 0:
                    if (
                        hasattr(node, "lock")
                        and node.lock
                        and not self.context.elements.lock_allows_move
                    ):
                        continue
                    else:
                        try:
                            node.matrix.post_translate(dx, dy)
                            # node.modified()
                            node.translated(dx, dy)
                        except AttributeError:
                            pass

        num_cols = self.arrange_x.GetValue()
        num_rows = self.arrange_y.GetValue()
        same_x = self.check_same_x.GetValue()
        same_y = self.check_same_y.GetValue()
        idx = self.rbox_selection.GetSelection()
        if idx < 0:
            idx = 0
        esort = self.selectparam[idx]
        idx = self.rbox_relation.GetSelection()
        if idx < 0:
            idx = 0
        relat = self.relparam[idx]
        gapx = 0
        gapy = 0
        if relat == "distance":
            try:
                gapx = float(Length(self.txt_gap_x.GetValue()))
            except ValueError:
                gapx = 0
            try:
                gapy = float(Length(self.txt_gap_y.GetValue()))
            except ValueError:
                gapy = 0
        idx = self.rbox_align_x.GetSelection()
        if idx < 0:
            idx = 0
        xpos = self.xyparam[idx]
        idx = self.rbox_align_y.GetSelection()
        if idx < 0:
            idx = 0
        ypos = self.xyparam[idx]
        # print(f"cols={num_cols}, rows={num_rows}")
        # print(f"samex={same_x}, samey={same_y}")
        # print(f"Relat={relat}, esort={esort}")
        # print(f"xpos={xpos}, ypos={ypos}")
        # print(f"Gapx={gapx:.1f}, Gapy={gapy:.1f}")
        data = []
        target = []
        prepare_data()
        calculate_arrays()
        arrange_elements()
        # self.apply_results(data, target, xmode, ymode, remain_inside)
        self.context.signal("refresh_scene", "Scene")
        self.save_setting()

    def save_setting(self):
        self.context.arrange_x = self.rbox_align_x.GetSelection()
        self.context.arrange_y = self.rbox_align_y.GetSelection()
        self.context.arrange_relation = self.rbox_relation.GetSelection()
        self.context.arrange_selection = self.rbox_selection.GetSelection()
        self.context.arrange_cols = self.arrange_x.GetValue()
        self.context.arrange_rows = self.arrange_y.GetValue()
        self.context.arrange_checkx = self.check_same_x.GetValue()
        self.context.arrange_checky = self.check_same_y.GetValue()
        self.context.arrange_gapx = self.txt_gap_x.GetValue()
        self.context.arrange_gapy = self.txt_gap_y.GetValue()

    def restore_setting(self):
        try:
            self.rbox_align_x.SetSelection(self.context.arrange_x)
            self.rbox_align_y.SetSelection(self.context.arrange_y)
            self.rbox_relation.SetSelection(self.context.arrange_relation)
            self.rbox_selection.SetSelection(self.context.arrange_selection)
            self.arrange_x.SetValue(self.context.arrange_cols)
            self.arrange_y.SetValue(self.context.arrange_rows)
            self.check_same_x.SetValue(bool(self.context.arrange_checkx))
            self.check_same_y.SetValue(bool(self.context.arrange_check))
            self.txt_gap_x.SetValue(self.context.arrange_gapx)
            self.txt_gap_y.SetValue(self.context.arrange_gapy)
        except (ValueError, AttributeError, RuntimeError):
            pass

    def show_stuff(self, has_emph):
        self.count, self.first_node, self.last_node = self.info_panel.show_stuff(
            has_emph
        )
        self.rbox_align_x.Enable(has_emph)
        self.rbox_align_y.Enable(has_emph)
        self.rbox_relation.Enable(has_emph)
        self.rbox_selection.Enable(has_emph)
        self.arrange_x.Enable(has_emph)
        self.arrange_y.Enable(has_emph)
        self.check_same_x.Enable(has_emph)
        self.check_same_y.Enable(has_emph)
        self.txt_gap_x.Enable(has_emph)
        self.txt_gap_y.Enable(has_emph)
        self.validate_data()


class Alignment(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(
            350,
            350,
            *args,
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.TAB_TRAVERSAL
            | wx.RESIZE_BORDER,
            **kwds,
        )
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.scene = getattr(self.context.root, "mainscene", None)
        self.panel_align = AlignmentPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.notebook_main.AddPage(self.panel_align, _("Align"))
        self.panel_distribution = DistributionPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.notebook_main.AddPage(self.panel_distribution, _("Distribute"))
        self.panel_arrange = ArrangementPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.notebook_main.AddPage(self.panel_arrange, _("Arrange"))

        self.Layout()

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_arrange_50.GetBitmap(resize=25))
        self.SetIcon(_icon)
        self.SetTitle(_("Alignment"))

    def delegates(self):
        yield self.panel_align
        yield self.panel_distribution
        yield self.panel_arrange

    @signal_listener("reference")
    @signal_listener("emphasized")
    def on_emphasize_signal(self, origin, *args):
        has_emph = self.context.elements.has_emphasis()
        self.panel_align.show_stuff(has_emph)
        self.panel_distribution.show_stuff(has_emph)
        self.panel_arrange.show_stuff(has_emph)

    @staticmethod
    def sub_register(kernel):
        buttonsize = STD_ICON_SIZE
        kernel.register(
            "button/align/AlignExpert",
            {
                "label": _("Expert Mode"),
                "icon": icons8_arrange_50,
                "tip": _("Open alignment dialog with advanced options"),
                "action": lambda v: kernel.console("window toggle Alignment\n"),
                "size": buttonsize,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    @staticmethod
    def submenu():
        return ("Editing", "Element Alignment")
