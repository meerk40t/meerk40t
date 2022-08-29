from math import sqrt

import wx
from numpy import linspace

from meerk40t.svgelements import (
    Arc,
    Close,
    CubicBezier,
    Line,
    Move,
    Path,
    Point,
    QuadraticBezier,
)

from ..kernel import signal_listener
from .icons import STD_ICON_SIZE, icons8_arrange_50
from .mwindow import MWindow

_ = wx.GetTranslation


class AlignmentPanel(wx.Panel):
    def __init__(self, *args, context=None, scene=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.scene = scene
        # Amount of currently selected
        self.count = 0

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

        self.rbox_align_y = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Alignment relative to Y-Axis:"),
            choices=self.ychoices,
            majorDimension=4,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_align_y.SetSelection(0)

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
        self.lbl_info = wx.StaticText(self, wx.ID_ANY, "")
        self.btn_align = wx.Button(self, wx.ID_ANY, "Align")
        self.btn_align.SetBitmap(icons8_arrange_50.GetBitmap(resize=25))

        sizer_main.Add(self.rbox_align_x, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_align_y, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_relation, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_treatment, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_align, 0, wx.EXPAND, 0)
        sizer_main.Add(self.lbl_info, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_align, self.btn_align)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_x)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_align_y)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_relation)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_treatment)
        has_emph = self.context.elements.has_emphasis()
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
                or self.scene.reference_object is None
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
                node = self.scene.reference_object
                if node is not None:
                    addition = f" --boundaries {node.bounds[0]},{node.bounds[1]},{node.bounds[2]},{node.bounds[3]}"
                else:
                    mode = "default"
            else:
                mode = "default"
        self.context(f"align {mode}{addition}{' group' if group else ''} xy {xpos} {ypos}")
        self.save_setting()

    def save_setting(self):
        mysettings=(
            self.rbox_treatment.GetSelection(),
            self.rbox_align_x.GetSelection(),
            self.rbox_align_y.GetSelection(),
            self.rbox_relation.GetSelection(),
        )
        setattr(self.context, "align_setting", mysettings)

    def restore_setting(self):
        mysettings = getattr(self.context, "align_setting", None)
        if mysettings is not None and len(mysettings) == 4:
            self.rbox_treatment.SetSelection(mysettings[0])
            self.rbox_align_x.SetSelection(mysettings[1])
            self.rbox_align_y.SetSelection(mysettings[2])
            self.rbox_relation.SetSelection(mysettings[3])

    def show_stuff(self, has_emph):
        self.rbox_align_x.Enable(has_emph)
        self.rbox_align_y.Enable(has_emph)
        self.rbox_relation.Enable(has_emph)
        self.rbox_treatment.Enable(has_emph)
        self.count = 0
        msg = ""
        if has_emph:
            data = list(self.context.elements.flat(emphasized=True))
            self.count = len(data)
            msg = _("Selected elements: {count}").format(count=self.count) + "\n"
            if self.count > 0:
                data.sort(key=lambda n: n.emphasized_time)
                node = data[0]
                msg += (
                    _("First selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                    + "\n"
                )
                node = data[-1]
                msg += (
                    _("Last selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                    + "\n"
                )
        flag = self.scene.reference_object is not None
        self.rbox_relation.EnableItem(4, flag)
        self.lbl_info.SetLabel(msg)
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
        self.check_inside_xy = wx.CheckBox(
            self, id=wx.ID_ANY, label=_("Keep first + last inside")
        )
        self.check_inside_xy.SetValue(True)

        self.rbox_dist_y = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Position of element relative to point for Y-Axis:"),
            choices=self.ychoices,
            majorDimension=5,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_dist_y.SetSelection(0)

        self.rbox_sort = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Work-Sequence:"),
            choices=self.sortchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_sort.SetSelection(0)

        self.rbox_treatment = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("Treatment:"),
            choices=self.treatmentchoices,
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_treatment.SetSelection(0)

        self.lbl_info = wx.StaticText(self, wx.ID_ANY, "")
        self.btn_dist = wx.Button(self, wx.ID_ANY, "Distribute")
        self.btn_dist.SetBitmap(icons8_arrange_50.GetBitmap(resize=25))

        sizer_check = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("First and last element treatment")),
            wx.HORIZONTAL,
        )
        sizer_check.Add(self.check_inside_xy, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(self.rbox_dist_x, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_dist_y, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_check, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_sort, 0, wx.EXPAND, 0)
        sizer_main.Add(self.rbox_treatment, 0, wx.EXPAND, 0)
        sizer_main.Add(self.btn_dist, 0, wx.EXPAND, 0)
        sizer_main.Add(self.lbl_info, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_dist, self.btn_dist)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_dist_x)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_dist_y)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_sort)
        self.Bind(wx.EVT_RADIOBOX, self.validate_data, self.rbox_treatment)
        self.restore_setting()
        has_emph = self.context.elements.has_emphasis()
        self.show_stuff(has_emph)

    def disable_wip(self):
        # Certain functionalities are not ready yet, so let's disable them
        self.rbox_dist_x.EnableItem(4, False)  # Space
        self.rbox_dist_y.EnableItem(4, False)  # Space
        # self.rbox_treatment.EnableItem(1, False)  # Shape
        # self.rbox_treatment.EnableItem(2, False)    # Points

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
            if treat == "default" and self.count < 3:
                active = False
            elif treat in ("shape", "points") and self.count < 3:
                active = False
            if xmode == "none" and ymode == "none":
                active = False
            if self.first_node is None and esort == "first":
                active = False
            if self.last_node is None and esort == "last":
                active = False
            # if self.scene.reference_object is None and mode=="ref":
            #     active = False
            if esort == "first" and self.first_node is not None and treat == "points":
                if not self.first_node.type in (
                    "elem rect",
                    "elem line",
                    "elem polyline",
                    "elem path",
                ):
                    active = False
            if esort == "last" and self.last_node is not None and treat == "points":
                if not self.last_node.type in (
                    "elem rect",
                    "elem line",
                    "elem polyline",
                    "elem path",
                ):
                    active = False
        else:
            active = False
        if treat in ("points", "shape"):
            self.check_inside_xy.Enable(False)
            self.check_inside_xy.SetValue(False)
        else:
            self.check_inside_xy.Enable(True)
        # Have we just selected the treatment? Then set something useful
        if obj == self.rbox_treatment and xmode == "none" and ymode == "none":
            self.rbox_dist_x.SetSelection(2)
            self.rbox_dist_y.SetSelection(2)

        self.btn_dist.Enable(active)
        self.disable_wip()

    def calculate_basis(self, data, target, treatment):
        def calc_basic():
            # equidistant points in rectangle
            target.clear()
            x = left_edge
            y = top_edge
            dlen = len(data)
            target.append((x, y))
            if dlen > 1:
                dx = (right_edge - left_edge) / (dlen - 1)
                dy = (bottom_edge - top_edge) / (dlen - 1)
            while dlen > 1:
                x += dx
                y += dy
                target.append((x, y))
                dlen -= 1

        def calc_points():
            first_point = path.first_point
            if first_point is not None:
                pt = (first_point[0], first_point[1])
                target.append(pt)
            for e in path:
                if isinstance(e, Move):
                    pt = (e.end[0], e.end[1])
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Line):
                    pt = (e.end[0], e.end[1])
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Close):
                    pass
                elif isinstance(e, QuadraticBezier):
                    pt = (e.end[0], e.end[1])
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, CubicBezier):
                    pt = (e.end[0], e.end[1])
                    if pt not in target:
                        target.append(pt)
                elif isinstance(e, Arc):
                    pt = (e.end[0], e.end[1])
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
                    subj = Path(subpath).npoint(linspace(0, 1, interpolation))

                    subj.reshape((2, interpolation))
                    s = list(map(Point, subj))
                    polygons.append(s)

                if len(polygons) > 0:
                    # idx = 0
                    # for pt in polygons[0]:
                    #     if pt.x > 1.0E8 or pt.y > 1.0E8:
                    #         print ("Rather high [%d]: x=%.1f, y=%.1f" % (idx, pt.x, pt.y))
                    #     idx += 1
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

            polypoints = []
            poly_length = generate_polygon()
            if len(polypoints) == 0:
                # Degenerate !!
                return
            # Closed path? -> Different intermediary points
            if closed_path():
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
            for pt in polypoints:
                x = pt[0]
                y = pt[1]
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
                    newpt = (x, y)
                    # print ("I would add another point...")
                    if newpt not in target:
                        # print ("..and added")
                        target.append(newpt)
                        segadded += 1
                    mylen += mydelta

                lastx = pt[0]
                lasty = pt[1]
                lastlen = pt[2]
            # We may have slightly overshot, so in doubt add the last point
            if segadded < segcount:
                # print ("I would add to it the last point...")
                newpt = (lastx, lasty)
                if newpt not in target:
                    # print ("..and added")
                    segadded += 1
                    target.append(newpt)
            # print (f"Target points: {len(target)}")

        # "default", "shape", "points", "bed", "ref")
        if treatment == "ref" and self.scene.reference_object is None:
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
            right_edge = self.context.device.width
            bottom_edge = self.context.device.height
            calc_basic()
        elif treatment == "ref":
            left_edge = self.scene.reference_object.bounds[0]
            top_edge = self.scene.reference_object.bounds[1]
            right_edge = self.scene.reference_object.bounds[2]
            bottom_edge = self.scene.reference_object.bounds[3]
            calc_basic()
        elif treatment == "points":
            # So what's the reference node? And delete it...
            refnode = data[0]
            data.pop(0)
            path = refnode.as_path()
            calc_points()
        elif treatment == "shape":
            # So what's the reference node? And delete it...
            refnode = data[0]
            data.pop(0)
            path = refnode.as_path()
            calc_path()

    def prepare_data(self, data, esort):
        xdata = list(self.context.elements.elems(emphasized=True))

        # Element conversion.
        # We need to establish, if for a given node within a group
        # all its siblings are selected as well.
        # If that's the case then use the parent instead
        d = list()
        elem_branch = self.context.elements.elem_branch
        for node in xdata:
            snode = node
            if snode.parent and snode.parent is not elem_branch:
                # I need all other siblings
                singular = False
                for n in list(node.parent.children):
                    if n not in xdata:
                        singular = True
                        break
                if not singular:
                    while snode.parent and snode.parent is not elem_branch:
                        snode = snode.parent
            if snode is not None and snode not in d:
                d.append(snode)
        for n in d:
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
            if xmode == "none":
                dx = 0
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

            if dx == 0 and dy == 0:
                continue
            if (
                hasattr(node, "lock")
                and node.lock
                and not self.context.elements.lock_allows_move
            ):
                continue
            else:
                try:
                    # q.matrix *= matrix
                    node.matrix.post_translate(dx, dy)
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
        # print(f"Params: x={xmode}, y={ymode}, sort={esort}, treat={treat}")
        # The elements...
        data = []
        target = []
        self.prepare_data(data, esort)
        self.calculate_basis(data, target, treat)
        self.apply_results(data, target, xmode, ymode, remain_inside)
        self.save_setting()

    def save_setting(self):
        mysettings=(
            self.rbox_dist_x.GetSelection(),
            self.rbox_dist_y.GetSelection(),
            self.rbox_treatment.GetSelection(),
            self.rbox_sort.GetSelection(),
            self.check_inside_xy.GetValue(),
        )
        setattr(self.context, "distribute_setting", mysettings)

    def restore_setting(self):
        mysettings = getattr(self.context, "distribute_setting", None)
        if mysettings is not None and len(mysettings) == 5:
            self.rbox_dist_x.SetSelection(mysettings[0])
            self.rbox_dist_y.SetSelection(mysettings[1])
            self.rbox_treatment.SetSelection(mysettings[2])
            self.rbox_sort.SetSelection(mysettings[3])
            self.check_inside_xy.SetValue(mysettings[4])

    def show_stuff(self, has_emph):
        showit = has_emph
        # showit = False # Not yet ready
        self.rbox_dist_x.Enable(showit)
        self.rbox_dist_y.Enable(showit)
        self.rbox_sort.Enable(showit)
        self.rbox_treatment.Enable(showit)
        self.check_inside_xy.Enable(showit)
        msg = ""
        self.count = 0
        if has_emph:
            data = list(self.context.elements.flat(emphasized=True))
            self.count = len(data)
            msg = _("Selected elements: {count}").format(count=self.count) + "\n"
            if self.count > 0:
                data.sort(key=lambda n: n.emphasized_time)
                node = data[0]
                self.first_node = node
                msg += (
                    _("First selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                    + "\n"
                )
                node = data[-1]
                self.last_node = node
                msg += (
                    _("Last selected: {type} {lbl}").format(
                        type=node.type, lbl=node.label
                    )
                    + "\n"
                )
        flag = self.scene.reference_object is not None
        self.rbox_treatment.EnableItem(4, flag)

        self.lbl_info.SetLabel(msg)
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
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def show_stuff(self, has_emph):
        return


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
        # self.panel_main = PreferencesPanel(self, wx.ID_ANY, context=self.context)
        self.panel_align = AlignmentPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.panel_distribution = DistributionPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )
        self.panel_arrange = ArrangementPanel(
            self, wx.ID_ANY, context=self.context, scene=self.scene
        )

        self.notebook_main.AddPage(self.panel_align, _("Alignment"))
        self.notebook_main.AddPage(self.panel_distribution, _("Distribution"))
        self.notebook_main.AddPage(self.panel_arrange, _("Arranging"))
        self.Layout()

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_arrange_50.GetBitmap(resize=25))
        self.SetIcon(_icon)
        self.SetTitle(_("Alignment"))

    def delegates(self):
        yield self.panel_align
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
        buttonsize = int(STD_ICON_SIZE / 2)
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
