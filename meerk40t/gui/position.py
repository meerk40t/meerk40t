import wx
from wx import aui

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.gui.icons import get_default_icon_size, icons8_compress
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxBitmapButton,
    wxCheckBox,
    wxComboBox,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_position(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(225, 110)
        .FloatingSize(225, 110)
        .Caption(_("Position"))
        .CaptionVisible(not context.pane_lock)
        .Name("position")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = PositionPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_40_" + _("Editing")
    pane.helptext = _("Edit object dimensions and position")
    window.on_pane_create(pane)
    context.register("pane/position", pane)


class PositionPanel(wx.Panel):
    def __init__(self, *args, context=None, small=False, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("position")
        self.small = small

        self.offset_index = 0  # 0 to 8 tl tc tr cl cc cr bl bc br
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.text_x = TextCtrl(
            self, wx.ID_ANY, "", check="float", style=wx.TE_PROCESS_ENTER
        )
        self.text_y = TextCtrl(
            self, wx.ID_ANY, "", check="float", style=wx.TE_PROCESS_ENTER
        )
        self.text_w = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            check="float",
            style=wx.TE_PROCESS_ENTER,
            nonzero=True,
        )
        self.text_h = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            check="float",
            style=wx.TE_PROCESS_ENTER,
            nonzero=True,
        )
        self.text_x.SetMinSize(dip_size(self, 60, 23))
        self.text_y.SetMinSize(dip_size(self, 60, 23))
        self.text_w.SetMinSize(dip_size(self, 60, 23))
        self.text_h.SetMinSize(dip_size(self, 60, 23))
        self.chk_individually = wxCheckBox(self, wx.ID_ANY, _("Individ."))
        # Remember last lock dimension status
        self.context.setting(bool, "lock_active", True)
        self.chk_lock = wxCheckBox(self, wx.ID_ANY, _("Keep ratio"))
        self.chk_lock.SetValue(context.lock_active)
        if self.small:
            resize_param = 0.5 * get_default_icon_size(self.context)
        else:
            resize_param = 0.75 * get_default_icon_size(self.context)

        self.button_execute = wxBitmapButton(self, wx.ID_ANY)
        self.button_param = wxBitmapButton(self, wx.ID_ANY)
        self.choices = ["mm", "cm", "inch", "mil", "%"]
        self.combo_box_units = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_units.SetSelection(0)

        self.__set_properties()
        self.__do_layout()

        # This is a bug within wxPython! It seems to appear only here at very high scale factors under windows
        bmp = icons8_compress.GetBitmap(resize=resize_param)
        s = bmp.Size
        icon_size = s[0]
        self.button_execute.SetBitmap(bmp)
        self.pos_bitmaps = self.calculate_icons(icon_size)
        self.button_param.SetBitmap(self.pos_bitmaps[self.offset_index])

        self.text_x.SetActionRoutine(self.on_text_x_enter)
        self.text_y.SetActionRoutine(self.on_text_y_enter)
        self.text_w.SetActionRoutine(self.on_text_w_enter)
        self.text_h.SetActionRoutine(self.on_text_h_enter)
        self.text_x.execute_action_on_change = False
        self.text_y.execute_action_on_change = False
        self.text_w.execute_action_on_change = False
        self.text_h.execute_action_on_change = False

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_box_units, self.combo_box_units)
        self.Bind(wx.EVT_BUTTON, self.on_button_execute, self.button_execute)
        self.button_param.Bind(wx.EVT_LEFT_DOWN, self.on_button_param)
        self.Bind(wx.EVT_CHECKBOX, self.on_chk_lock, self.chk_lock)
        # end wxGlade

        self.position_aspect_ratio = True
        self.chk_lock.SetValue(self.position_aspect_ratio)
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.org_x = None
        self.org_y = None
        self.org_w = None
        self.org_h = None
        self.context.setting(str, "units_name", "mm")
        self.position_units = self.context.units_name

        if self.position_units in ("in", "inches"):
            self.position_units = "inch"
        self._update_position()

    def calculate_icons(self, bmap_size):
        result = []
        for y in range(3):
            for x in range(3):
                imgBit = wx.Bitmap(bmap_size, bmap_size)
                dc = wx.MemoryDC(imgBit)
                dc.SelectObject(imgBit)
                dc.SetBackground(wx.WHITE_BRUSH)
                dc.Clear()
                dc.SetPen(wx.BLACK_PEN)
                delta = (bmap_size - 1) / 3
                for xx in range(4):
                    dc.DrawLine(int(delta * xx), 0, int(delta * xx), int(bmap_size - 1))
                    dc.DrawLine(0, int(delta * xx), int(bmap_size - 1), int(delta * xx))
                # And now fill the area
                dc.SetBrush(wx.BLACK_BRUSH)
                dc.DrawRectangle(
                    int(x * delta),
                    int(y * delta),
                    int(delta + 1),
                    int(delta + 1),
                )
                # Now release dc
                dc.SelectObject(wx.NullBitmap)
                result.append(imgBit)
        return result

    def pane_show(self, *args):
        self.context.listen("units", self.space_changed)
        self.context.listen("emphasized", self._update_position)
        self.context.listen("modified", self._update_position)
        self.context.listen("altered", self._update_position)
        self.context.listen("lock_active", self._on_lock_active)
        self._update_position(True)
        # To get an update about translation / scaling
        # updates to an element we have two options....
        # Option 1: plug yourself to the rootnode update
        # self.context.elements.listen_tree(self)

    def pane_hide(self, *args):
        self.context.unlisten("units", self.space_changed)
        self.context.unlisten("emphasized", self._update_position)
        self.context.unlisten("modified", self._update_position)
        self.context.unlisten("altered", self._update_position)
        self.context.unlisten("lock_active", self._on_lock_active)
        # Option 1: plug yourself to the rootnode update
        # self.context.elements.unlisten_tree(self)

    # Option 2: attach yourself to the refresh_scene and the tool_modified signals
    @signal_listener("refresh_scene")
    def on_refresh_scene(self, origin, scene_name=None, *args):
        if scene_name == "Scene":
            self.update_position(True)

    @signal_listener("modified_by_tool")
    def on_modified(self, *args):
        self.update_position(True)

    # This the foolproofest way of getting informed
    # about such changes, as it is called by rootnode.
    # Drawback: it's called for every node in the selection
    # that has been moved / scaled...
    # def translated(self, node, dx, dy):
    #     if node is None:
    #         return
    #     if node.emphasized:
    #         prev = self.last_update
    #         self.last_update = perf_counter()
    #         if self.last_update - prev > 0.1:
    #             self.update_position(True)

    # def scaled(self, node, sx, sy, ox, oy):
    #     if node is None:
    #         return
    #     if node.emphasized:
    #         prev = self.last_update
    #         self.last_update = perf_counter()
    #         if self.last_update - prev > 0.1:
    #             self.update_position(True)

    def __set_properties(self):
        # begin wxGlade: PositionPanel.__set_properties
        self.text_h.SetToolTip(_("New height (enter to apply)"))
        self.text_w.SetToolTip(_("New width (enter to apply)"))
        self.text_x.SetToolTip(
            _("New X-coordinate of left top corner (enter to apply)")
        )
        self.text_y.SetToolTip(
            _("New Y-coordinate of left top corner (enter to apply)")
        )
        self.button_execute.SetToolTip(
            _("Apply the changes to all emphasized elements in the scene")
        )
        self.chk_individually.SetToolTip(
            _(
                "If checked then each element will get the new value of the current field, if unchecked then the new values apply to the selection-dimensions"
            )
        )
        self.chk_lock.SetToolTip(
            _("If checked then the aspect ratio (width / height) will be maintained")
        )
        self.button_param.SetToolTip(
            _(
                "Set the point of reference for the element,\n"
                + "which edge/corner should be put on the given location"
            )
        )
        self.button_execute.SetSize(self.button_execute.GetBestSize())
        self.combo_box_units.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        if self.small:
            target = StaticBoxSizer(
                self, wx.ID_ANY, _("Object Dimensions"), wx.VERTICAL
            )
            sizer_main.Add(target, 1, wx.EXPAND, 0)
        else:
            target = sizer_main
        sizer_h = StaticBoxSizer(self, wx.ID_ANY, _("Height:"), wx.HORIZONTAL)
        sizer_w = StaticBoxSizer(self, wx.ID_ANY, _("Width:"), wx.HORIZONTAL)
        sizer_y = StaticBoxSizer(self, wx.ID_ANY, "Y:", wx.HORIZONTAL)
        sizer_x = StaticBoxSizer(self, wx.ID_ANY, "X:", wx.HORIZONTAL)

        sizer_x.Add(self.text_x, 1, wx.EXPAND, 0)
        sizer_y.Add(self.text_y, 1, wx.EXPAND, 0)
        sizer_w.Add(self.text_w, 1, wx.EXPAND, 0)
        sizer_h.Add(self.text_h, 1, wx.EXPAND, 0)

        self.sizer_h_xy = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_h_xy.Add(sizer_x, 1, wx.EXPAND, 0)
        self.sizer_h_xy.Add(sizer_y, 1, wx.EXPAND, 0)

        self.sizer_h_wh = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_h_wh.Add(sizer_w, 1, wx.EXPAND, 0)
        self.sizer_h_wh.Add(sizer_h, 1, wx.EXPAND, 0)

        sizer_v_xywh = wx.BoxSizer(wx.VERTICAL)
        sizer_v_xywh.Add(self.sizer_h_xy, 0, wx.EXPAND, 0)
        sizer_v_xywh.Add(self.sizer_h_wh, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons.Add(self.button_execute, 0, 0, 0)
        sizer_buttons.Add(self.button_param, 0, 0, 0)

        sizer_h_all = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h_all.Add(sizer_buttons, 0, 0, 0)
        sizer_h_all.Add(sizer_v_xywh, 1, wx.EXPAND, 0)
        target.Add(sizer_h_all, 0, wx.EXPAND, 0)
        sizer_h_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h_options.Add(self.chk_individually, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_options.Add(self.chk_lock, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_h_options.Add(self.combo_box_units, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        if self.small:
            target.Add(sizer_h_options, 0, wx.EXPAND, 0)
        else:
            sizer_v_xywh.Add(sizer_h_options, 0, wx.EXPAND, 0)
        # Only show x + y if required.
        show_wh = True
        show_xy = not self.small
        show_indiv = not self.small

        self.sizer_h_wh.Show(show_wh)
        self.sizer_h_wh.ShowItems(show_wh)
        self.sizer_h_xy.Show(show_xy)
        self.sizer_h_xy.ShowItems(show_xy)
        self.chk_individually.Show(show_indiv)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        # end wxGlade

    def _update_position(self, *args):
        self.context.elements.set_start_time("Emphasis positionpanel")
        self.update_position(True)
        self.context.elements.set_end_time("Emphasis positionpanel")

    def update_position(self, reset):
        if not self.IsShown():
            return
        more_than_one = False
        ct = 0
        for _e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            ct += 1
            if ct > 1:
                more_than_one = True
                break

        bounds = self.context.elements.selected_area()
        if bounds is None:
            if self.text_x.IsEnabled():
                self.text_w.Enable(False)
                self.text_h.Enable(False)
                self.text_x.Enable(False)
                self.text_y.Enable(False)
                self.button_execute.Enable(False)
                self.chk_individually.SetValue(False)
                self.chk_individually.Enable(False)
                self.chk_lock.Enable(False)
                self.combo_box_units.Enable(False)
            if self.position_units in self.choices:
                self.combo_box_units.SetSelection(
                    self.choices.index(self.position_units)
                )
            return
        if not self.text_x.IsEnabled():
            self.text_w.Enable(True)
            self.text_h.Enable(True)
            self.text_x.Enable(True)
            self.text_y.Enable(True)
            self.combo_box_units.Enable(True)
            self.button_execute.Enable(True)
            self.chk_individually.SetValue(False)
            self.chk_lock.Enable(True)
        self.chk_individually.Enable(more_than_one)

        if reset:
            x0, y0, x1, y1 = bounds
            # conversion = ViewPort.conversion(self.position_units)
            conversion_x = float(
                Length(
                    f"1{self.position_units}",
                    relative_length=self.context.device.view.unit_width,
                )
            )
            conversion_y = float(
                Length(
                    f"1{self.position_units}",
                    relative_length=self.context.device.view.unit_height,
                )
            )
            # print ("Size: x0 = %.2f, conversion=%.5f, new=%.2f (units %s)" % (x0, conversion, x0/conversion, self.position_units))
            self.position_x = x0 / conversion_x
            self.position_y = y0 / conversion_y
            self.position_w = (x1 - x0) / conversion_x
            self.position_h = (y1 - y0) / conversion_y
            self.org_x = self.position_x
            self.org_y = self.position_y
            self.org_w = self.position_w
            self.org_h = self.position_h

        pos_x = self.position_x + self.offset_x * self.position_w
        pos_y = self.position_y + self.offset_y * self.position_h
        self.text_x.SetValue(f"{pos_x:.2f}")
        self.text_y.SetValue(f"{pos_y:.2f}")
        self.text_w.SetValue(f"{self.position_w:.2f}")
        self.text_h.SetValue(f"{self.position_h:.2f}")
        self.combo_box_units.SetSelection(self.choices.index(self.position_units))

    def space_changed(self, origin, *args):
        self.position_units = self.context.units_name
        self.update_position(True)

    def on_button_param(self, event):
        pt_mouse = event.GetPosition()
        ob = event.GetEventObject()
        rect_ob = ob.GetRect()
        col = int(3 * pt_mouse[0] / rect_ob[2])
        row = int(3 * pt_mouse[1] / rect_ob[3])
        idx = 3 * row + col
        # print(idx, col, row, pt_mouse, rect_ob)
        self.offset_index = idx
        if self.offset_index > 8:
            self.offset_index = 0
        x_offsets = (0, 0.5, 1, 0, 0.5, 1, 0, 0.5, 1)
        y_offsets = (0, 0, 0, 0.5, 0.5, 0.5, 1, 1, 1)
        self.offset_x = x_offsets[self.offset_index]
        self.offset_y = y_offsets[self.offset_index]
        self.button_param.SetBitmap(self.pos_bitmaps[self.offset_index])
        self.button_param.Refresh()
        self.update_position(True)

    def on_button_execute(self, event):  # wxGlade: MyFrame.<event_handler>
        event.Skip()
        do_xy = self.position_x != self.org_x or self.position_y != self.org_y
        do_wh = self.position_w != self.org_w or self.position_h != self.org_h
        if self.chk_individually.GetValue():
            if do_wh:
                self.execute_wh_changes(False)
            if do_xy:
                self.execute_xy_changes(False)
            self.context.signal("refresh_scene", "Scene")
        else:
            if do_wh and do_xy:
                # One is enough as both routines will call resize with all parameters
                self.execute_wh_changes(False)
            elif do_wh:
                self.execute_wh_changes(False)

            elif do_xy:
                self.execute_xy_changes(False)
            self.context.signal("refresh_scene", "Scene")

        self.update_position(True)

    def on_chk_lock(self, event):
        flag = self.chk_lock.GetValue()
        self.position_aspect_ratio = flag
        if self.context.lock_active != flag:
            self.context.lock_active = flag
            self.context.signal("lock_active")

    def on_text_w_enter(self):
        if self.text_w.is_changed:
            self.on_text_w_action(True)

    def on_text_h_enter(self):
        if self.text_h.is_changed:
            self.on_text_h_action(True)

    def on_text_x_enter(self):
        if self.text_x.is_changed:
            self.on_text_x_action(True)

    def on_text_y_enter(self):
        if self.text_y.is_changed:
            self.on_text_y_action(True)

    def execute_wh_changes(self, refresh_after=True):
        delta = 1.0e-6
        if (
            abs(self.position_w - self.org_w) < delta
            and abs(self.position_h - self.org_h) < delta
        ):
            return
        if self.chk_individually.GetValue():
            for elem in self.context.elements.flat(types=elem_nodes, emphasized=True):
                _bb = elem.bounds
                bb = [_bb[0], _bb[1], _bb[2], _bb[3]]
                new_w = float(
                    Length(f"{round(self.position_w, 6)}{self.position_units}")
                )
                new_h = float(
                    Length(f"{round(self.position_h, 6)}{self.position_units}")
                )
                # A line may have a zero dimension
                if abs(bb[2] - bb[0]) < delta:
                    scalex = 1
                else:
                    scalex = new_w / (bb[2] - bb[0])
                    if abs(scalex) < delta:
                        scalex = 1
                if abs(bb[3] - bb[1]) < delta:
                    scaley = 1
                else:
                    scaley = new_h / (bb[3] - bb[1])
                    if abs(scaley) < delta:
                        scaley = 1
                # print("Old=%.1f, new=%.1f, sx=%.1f" % ((bb[2]-bb[0]), new_w, scalex))
                if abs(scalex - 1) < delta:
                    scalex = 1
                if abs(scaley - 1) < delta:
                    scaley = 1
                if scalex == 1 and scaley == 1:
                    continue
                if scalex != 0:
                    bb[2] = bb[0] + (bb[2] - bb[0]) * scalex
                if scaley != 0:
                    bb[3] = bb[1] + (bb[3] - bb[1]) * scaley

                elem.matrix.post_scale(scalex, scaley, bb[0], bb[1])
                elem.scaled(sx=scalex, sy=scaley, ox=bb[0], oy=bb[1])
                # elem._bounds = bb
        else:
            u = self.position_units
            cmd1 = ""
            cmd2 = ""
            if (
                abs(self.position_x - self.org_x) >= delta
                or abs(self.position_y - self.org_y) >= delta
            ):
                cmd1 = f"position {round(self.position_x, 6)}{u}"
                cmd1 += f" {round(self.position_y, 6)}{u}\n"
            if (
                abs(self.position_w - self.org_w) >= delta
                or abs(self.position_h - self.org_h) >= delta
            ):
                if abs(self.org_w) > delta:
                    sx = round(self.position_w / self.org_w, 6)
                else:
                    sx = 1
                if abs(self.org_h) > delta:
                    sy = round(self.position_h / self.org_h, 6)
                else:
                    sy = 1
                if sx != 1.0 or sy != 1.0:
                    cmd2 = f"scale {sx} {sy}\n"
            # cmd = f"resize {round(self.position_x, 6)}{u} {round(self.position_y, 0)}{u}"
            # cmd += f" {round(self.position_w, 6)}{u} {round(self.position_h, 6)}{u}\n"
            cmd = cmd1 + cmd2
            self.context(cmd)
        if refresh_after:
            self.update_position(True)

    def execute_xy_changes(self, refresh_after=True):
        delta = 1.0e-6
        if (
            abs(self.position_x - self.org_x) < delta
            and abs(self.position_y - self.org_y) < delta
        ):
            return
        if self.chk_individually.GetValue():
            for elem in self.context.elements.flat(types=elem_nodes, emphasized=True):
                _bb = elem.bounds
                bb = [_bb[0], _bb[1], _bb[2], _bb[3]]
                newx = float(
                    Length(f"{round(self.position_x, 6)}{self.position_units}")
                )
                newy = float(
                    Length(f"{round(self.position_y, 6)}{self.position_units}")
                )
                if self.position_x == self.org_x:
                    dx = 0
                else:
                    dx = newx - bb[0]
                if self.position_y == self.org_y:
                    dy = 0
                else:
                    dy = newy - bb[1]
                # print("Old=%.1f, new=%.1f, dx=%.1f" % (bb[0], newx, dx))
                if dx == 0 and dy == 0:
                    continue
                oldw = bb[2] - bb[0]
                oldh = bb[3] - bb[1]
                if dx != 0:
                    bb[0] = newx
                    bb[2] = newx + oldw
                if dy != 0:
                    bb[1] = newy
                    bb[3] = newy + oldh
                elem.matrix.post_translate(dx, dy)
                elem.translated(dx, dy)
                # elem._bounds = bb
                # elem.modified()
        else:
            u = self.position_units
            cmd1 = ""
            cmd2 = ""
            if (
                abs(self.position_x - self.org_x) >= delta
                or abs(self.position_y - self.org_y) >= delta
            ):
                cmd1 = f"position {round(self.position_x, 6)}{u}"
                cmd1 += f" {round(self.position_y, 6)}{u}\n"
            if (
                abs(self.position_w - self.org_w) >= delta
                or abs(self.position_h - self.org_h) >= delta
            ):
                if self.org_w != 0 and self.org_h != 0:
                    sx = round(self.position_w / self.org_w, 6)
                    sy = round(self.position_h / self.org_h, 6)
                    if sx != 1.0 or sy != 1.0:
                        cmd2 = f"scale {sx} {sy}\n"
            # cmd = f"resize {round(self.position_x, 6)}{u} {round(self.position_y, 0)}{u}"
            # cmd += f" {round(self.position_w, 6)}{u} {round(self.position_h, 6)}{u}\n"
            cmd = cmd1 + cmd2
            self.context(cmd)
        if refresh_after:
            self.update_position(True)

    def on_text_w_action(self, force):
        original = self.position_w

        try:
            w = float(self.text_w.GetValue())
        except ValueError:
            try:
                w = Length(
                    self.text_w.GetValue(),
                    relative_length=self.context.device.view.width,
                    unitless=UNITS_PER_PIXEL,
                    preferred_units=self.context.units_name,
                )
            except ValueError:
                return
        if isinstance(w, str):
            return
        if abs(w) < 1e-8:
            self.text_w.SetValue(str(self.position_w))
            return
        self.position_w = w

        if self.position_aspect_ratio:
            if abs(original) < 1e-8:
                self.update_position(True)
                return
            self.position_h *= self.position_w / original
            self.update_position(False)

        if force:
            self.execute_wh_changes()
            self.context.signal("refresh_scene", "Scene")

    def on_text_h_action(self, force):
        original = self.position_h
        try:
            h = float(self.text_h.GetValue())
        except ValueError:
            try:
                h = Length(
                    self.text_h.GetValue(),
                    relative_length=self.context.device.view.height,
                    unitless=UNITS_PER_PIXEL,
                    preferred_units=self.context.units_name,
                )
            except ValueError:
                return
        if isinstance(h, str):
            return
        if abs(h) < 1e-8:
            self.text_h.SetValue(str(self.position_h))
            return

        self.position_h = h
        if self.position_aspect_ratio:
            if abs(original) < 1e-8:
                self.update_position(True)
                return
            self.position_w *= self.position_h / original
            self.update_position(False)

        if force:
            self.execute_wh_changes()
            self.context.signal("refresh_scene", "Scene")

    def on_text_x_action(self, force):
        try:
            pos_x = float(self.text_x.GetValue())
        except ValueError:
            try:
                pos_x = Length(
                    self.text_h.GetValue(),
                    relative_length=self.context.device.view.height,
                    unitless=UNITS_PER_PIXEL,
                    preferred_units=self.context.units_name,
                )
            except ValueError:
                return
        self.position_x = pos_x - self.offset_x * self.position_w
        if force:
            self.execute_xy_changes()
            self.context.signal("refresh_scene", "Scene")

    def on_text_y_action(self, force):
        try:
            pos_y = float(self.text_y.GetValue())
        except ValueError:
            try:
                pos_y = Length(
                    self.text_h.GetValue(),
                    relative_length=self.context.device.view.width,
                    unitless=UNITS_PER_PIXEL,
                    preferred_units=self.context.units_name,
                )
            except ValueError:
                return

        self.position_y = pos_y - self.offset_y * self.position_h

        if force:
            self.execute_xy_changes()
            self.context.signal("refresh_scene", "Scene")

    def on_combo_box_units(self, event):
        self.position_units = self.choices[self.combo_box_units.GetSelection()]
        self.update_position(True)

    def _on_lock_active(self, *args):
        if self.chk_lock.GetValue() != self.context.lock_active:
            self.chk_lock.SetValue(self.context.lock_active)
