import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.units import Length, UNITS_PER_PIXEL
from meerk40t.gui.icons import (
    icon_cap_butt,
    icon_cap_round,
    icon_cap_square,
    icon_fill_evenodd,
    icon_fill_nonzero,
    icon_join_bevel,
    icon_join_miter,
    icon_join_round,
    icons8_lock,
    icons8_unlock,
)
from meerk40t.gui.wxutils import TextCtrl, dip_size, wxStaticBitmap, wxStaticText

from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class LinecapWidget(StatusBarWidget):
    """
    Panel to change / assign the linecap of an element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.cap_lbl = wxStaticText(self.parent, wx.ID_ANY, label=_("Cap"))
        self.cap_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.btn_cap_butt = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(self.height, -1), style=wx.BORDER_RAISED
        )
        isize = int(max(20, self.parent.available_height - 4) * self.context.root.bitmap_correction_scale)

        self.btn_cap_butt.SetBitmap(
            icon_cap_butt.GetBitmap(
                resize=isize, buffer=1
            )
        )
        self.btn_cap_butt.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_butt.SetToolTip(_("Set the end of the lines to a butt-shape"))
        self.btn_cap_butt.Bind(wx.EVT_LEFT_DOWN, self.on_cap_butt)

        self.btn_cap_round = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(self.height, -1), style=wx.BORDER_RAISED
        )
        self.btn_cap_round.SetBitmap(
            icon_cap_round.GetBitmap(
                resize=isize, buffer=1
            )
        )
        self.btn_cap_round.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_round.SetToolTip(_("Set the end of the lines to a round-shape"))
        self.btn_cap_round.Bind(wx.EVT_LEFT_DOWN, self.on_cap_round)

        self.btn_cap_square = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(self.height, -1), style=wx.BORDER_RAISED
        )

        self.btn_cap_square.SetBitmap(
            icon_cap_square.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_cap_square.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_square.SetToolTip(_("Set the end of the lines to a square-shape"))
        self.btn_cap_square.Bind(wx.EVT_LEFT_DOWN, self.on_cap_square)

        self.Add(self.cap_lbl, 0, 0, 0)
        self.Add(self.btn_cap_butt, 1, wx.EXPAND, 0)
        self.Add(self.btn_cap_round, 1, wx.EXPAND, 0)
        self.Add(self.btn_cap_square, 1, wx.EXPAND, 0)

    def assign_cap(self, captype):
        self.context(f"linecap {captype}")

    def on_cap_square(self, event):
        self.assign_cap("square")

    def on_cap_butt(self, event):
        self.assign_cap("butt")

    def on_cap_round(self, event):
        self.assign_cap("round")


class LinejoinWidget(StatusBarWidget):
    """
    Panel to change / assign the linejoin of an element
    (actually a subset: arcs and miter-clip have been intentionally omitted)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.join_lbl = wxStaticText(self.parent, wx.ID_ANY, label=_("Join"))
        self.join_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        isize = int(
            max(20, self.parent.available_height - 4) *
            self.context.root.bitmap_correction_scale
        )
        self.btn_join_bevel = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )

        self.btn_join_bevel.SetBitmap(
            icon_join_bevel.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_join_bevel.SetMaxSize(wx.Size(50, -1))
        self.btn_join_bevel.SetToolTip(_("Set the join of the lines to a bevel-shape"))
        self.btn_join_bevel.Bind(wx.EVT_LEFT_DOWN, self.on_join_bevel)

        self.btn_join_round = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )
        self.btn_join_round.SetBitmap(
            icon_join_round.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_join_round.SetMaxSize(wx.Size(50, -1))
        self.btn_join_round.SetToolTip(_("Set the join of lines to a round-shape"))
        self.btn_join_round.Bind(wx.EVT_LEFT_DOWN, self.on_join_round)

        self.btn_join_miter = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )
        self.btn_join_miter.SetBitmap(
            icon_join_miter.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_join_miter.SetMaxSize(wx.Size(50, -1))
        self.btn_join_miter.SetToolTip(_("Set the join of lines to a miter-shape"))
        self.btn_join_miter.Bind(wx.EVT_LEFT_DOWN, self.on_join_miter)

        # self.btn_join_arcs = wxStaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED)
        # self.btn_join_arcs.SetBitmap(icon_join_round.GetBitmap(noadjustment=True))
        # self.btn_join_arcs.SetToolTip(_("Set the join of lines to an arc-shape"))
        # self.btn_join_arcs.Bind(wx.EVT_LEFT_DOWN, self.on_join_arcs)

        # self.btn_join_miterclip = wxStaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED)
        # self.btn_join_miterclip.SetBitmap(icon_join_miter.GetBitmap(noadjustment=True))
        # self.btn_join_miterclip.SetToolTip(_("Set the join of lines to a miter-clip-shape"))
        # self.btn_join_miterclip.Bind(wx.EVT_LEFT_DOWN, self.on_join_miterclip)

        self.Add(self.join_lbl, 0, 0, 0)
        self.Add(self.btn_join_bevel, 1, wx.EXPAND, 0)
        self.Add(self.btn_join_round, 1, wx.EXPAND, 0)
        self.Add(self.btn_join_miter, 1, wx.EXPAND, 0)
        # Who the h... needs those?
        # self.parent.Add(self.btn_join_arcs, 1, wx.EXPAND, 0)
        # self.parent.Add(self.btn_join_miterclip, 1, wx.EXPAND, 0)

    def assign_join(self, jointype):
        self.context(f"linejoin {jointype}")

    def on_join_miter(self, event):
        self.assign_join("miter")

    def on_join_miterclip(self, event):
        self.assign_join("miter-clip")

    def on_join_bevel(self, event):
        self.assign_join("bevel")

    def on_join_arcs(self, event):
        self.assign_join("arcs")

    def on_join_round(self, event):
        self.assign_join("round")


class FillruleWidget(StatusBarWidget):
    """
    Panel to change / assign the fillrule of an element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.fill_lbl = wxStaticText(self.parent, wx.ID_ANY, label=_("Fill"))
        self.fill_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        isize = int(
            max(20, self.parent.available_height - 4) *
            self.context.root.bitmap_correction_scale
        )

        self.btn_fill_nonzero = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(self.height, -1), style=wx.BORDER_RAISED
        )
        self.btn_fill_nonzero.SetMaxSize(wx.Size(50, -1))
        self.btn_fill_nonzero.SetBitmap(
            icon_fill_nonzero.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_fill_nonzero.SetToolTip(_("Set the fillstyle to non-zero (regular)"))
        self.btn_fill_nonzero.Bind(wx.EVT_LEFT_DOWN, self.on_fill_nonzero)

        self.btn_fill_evenodd = wxStaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(self.height, -1), style=wx.BORDER_RAISED
        )
        self.btn_fill_evenodd.SetBitmap(
            icon_fill_evenodd.GetBitmap(resize=isize, buffer=1)
        )
        self.btn_fill_evenodd.SetMaxSize(wx.Size(50, -1))
        self.btn_fill_evenodd.SetToolTip(
            _("Set the fillstyle to even-odd (alternating areas)")
        )
        self.btn_fill_evenodd.Bind(wx.EVT_LEFT_DOWN, self.on_fill_evenodd)
        self.Add(self.fill_lbl, 0, 0, 0)
        self.Add(self.btn_fill_nonzero, 1, wx.EXPAND, 0)
        self.Add(self.btn_fill_evenodd, 1, wx.EXPAND, 0)

    def assign_fill(self, filltype):
        self.context(f"fillrule {filltype}")

    def on_fill_evenodd(self, event):
        self.assign_fill("evenodd")

    def on_fill_nonzero(self, event):
        self.assign_fill("nonzero")


class PositionWidget(StatusBarWidget):
    """
    Panel to change / assign the linecap of an element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.context.setting(bool, "lock_active", True)
        self._needs_generation = False
        self.xy_lbl = wxStaticText(self.parent, wx.ID_ANY, label=_("X, Y"))
        self.node = None
        self.units = ("mm", "cm", "in", "mil", "%")
        self.unit_index = 0
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.org_x = None
        self.org_y = None
        self.org_w = None
        self.org_h = None

        self.text_x = TextCtrl(
            self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float"
        )
        self.text_y = TextCtrl(
            self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float"
        )
        self.wh_lbl = wxStaticText(self.parent, wx.ID_ANY, label=_("W, H"))
        self.text_w = TextCtrl(
            self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float"
        )
        self.text_w.SetToolTip(_(""))
        self.text_h = TextCtrl(
            self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float"
        )
        self.unit_lbl = wxStaticText(
            self.parent, wx.ID_ANY, label=self.units[self.unit_index]
        )
        icon_size = int(
            max(20, self.parent.available_height - 4) *
            self.context.root.bitmap_correction_scale
        )

        self.button_lock_ratio = wxStaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(icon_size, -1), style=wx.BORDER_RAISED)
        self.bitmap_locked = icons8_lock.GetBitmap(resize=icon_size, use_theme=False)
        self.bitmap_unlocked = icons8_unlock.GetBitmap(resize=icon_size, use_theme=False)

        self.offset_index = 0  # 0 to 8 tl tc tr cl cc cr bl bc br
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.button_param = wxStaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(icon_size, -1), style=wx.BORDER_RAISED)
        self.pos_bitmaps = self.calculate_icons(icon_size)
        self.button_param.SetBitmap(self.pos_bitmaps[self.offset_index])

        self.Add(self.xy_lbl, 0, 0, 0)
        self.Add(self.text_x, 1, 0, 0)
        self.Add(self.text_y, 1, 0, 0)
        self.Add(self.wh_lbl, 0, 0, 0)
        self.Add(self.text_w, 1, 0, 0)
        self.Add(self.text_h, 1, 0, 0)
        self.Add(self.unit_lbl, 0, 0, 0)
        self.Add(self.button_lock_ratio, 0, 0, 0)
        self.Add(self.button_param, 0, 0, 0)
        fnt = wx.Font(
            7,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        for ctl in (
            self.text_x,
            self.text_y,
            self.text_w,
            self.text_h,
        ):
            ctl.SetSize(dip_size(self.parent, -1, 20))
        for ctl in (
            self.text_x,
            self.text_y,
            self.text_w,
            self.text_h,
            self.xy_lbl,
            self.wh_lbl,
            self.unit_lbl,
        ):
            ctl.SetFont(fnt)
        # Event Handlers
        self.text_x.SetActionRoutine(self.on_text_x_enter)
        self.text_y.SetActionRoutine(self.on_text_y_enter)
        self.text_w.SetActionRoutine(self.on_text_w_enter)
        self.text_h.SetActionRoutine(self.on_text_h_enter)
        self.text_w.Bind(wx.EVT_KEY_DOWN, self.on_key_w)
        self.text_h.Bind(wx.EVT_KEY_DOWN, self.on_key_h)
        self.text_x.Bind(wx.EVT_KEY_DOWN, self.on_key_x)
        self.text_y.Bind(wx.EVT_KEY_DOWN, self.on_key_y)
        self.unit_lbl.Bind(wx.EVT_LEFT_DOWN, self.on_click_units_l)
        self.unit_lbl.Bind(wx.EVT_RIGHT_DOWN, self.on_click_units_r)
        self.button_lock_ratio.Bind(wx.EVT_LEFT_DOWN, self.on_toggle_ratio)
        self.button_param.Bind(wx.EVT_LEFT_DOWN, self.on_button_param)

        self.text_h.SetToolTip(_("New height (enter to apply)"))
        self.text_w.SetToolTip(_("New width (enter to apply)"))
        self.text_x.SetToolTip(
            _("New X-coordinate of left top corner (enter to apply)")
        )
        self.text_y.SetToolTip(
            _("New Y-coordinate of left top corner (enter to apply)")
        )
        self.button_lock_ratio.SetToolTip(
            _("If checked then the aspect ratio (width / height) will be maintained")
        )
        self.button_param.SetToolTip(
            _(
                "Set the point of reference for the element,\n"
                + "which edge/corner should be put on the given location"
            )
        )

        self._lock_ratio = True
        self.lock_ratio =  self.context.lock_active


    @property
    def units_name(self):
        return self.units[self.unit_index]

    @property
    def lock_ratio(self):
        return self._lock_ratio

    @lock_ratio.setter
    def lock_ratio(self, value):
        self._lock_ratio = value
        if value:
            self.button_lock_ratio.SetBitmap(self.bitmap_locked)
        else:
            self.button_lock_ratio.SetBitmap(self.bitmap_unlocked)
        if self.context.lock_active != value:
            self.context.lock_active = value
            self.context.signal("lock_active")

    # Position icon routines
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

    def on_toggle_ratio(self, event):
        self.lock_ratio = not self.lock_ratio

    # Handle Unit switching
    def click_unit(self, delta):
        self.unit_index += delta
        if self.unit_index >= len(self.units):
            self.unit_index = 0
        if self.unit_index < 0:
            self.unit_index = len(self.units) - 1
        self.unit_lbl.SetLabel(self.units[self.unit_index])
        self.update_position(True)

    def on_click_units_l(self, event):
        self.click_unit(+1)
        event.Skip()

    def on_click_units_r(self, event):
        self.click_unit(-1)
        event.Skip()

    # Controls are not properly handing over to the next on a Tab-key,
    # so this needs to be done manually :-(
    def on_key_w(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            self.text_h.SetFocus()
        event.Skip()

    def on_key_h(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            self.text_x.SetFocus()
        event.Skip()

    def on_key_x(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            self.text_y.SetFocus()
        event.Skip()

    def on_key_y(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            self.text_w.SetFocus()
        event.Skip()

    def update_position(self, reset):
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
                self.button_lock_ratio.Enable(False)
                self.button_param.Enable(False)
            return
        if not self.text_x.IsEnabled():
            self.text_w.Enable(True)
            self.text_h.Enable(True)
            self.text_x.Enable(True)
            self.text_y.Enable(True)
            self.button_lock_ratio.Enable(True)
            self.button_param.Enable(True)

        if reset:
            x0, y0, x1, y1 = bounds
            # conversion = ViewPort.conversion(self.units_name)
            conversion_x = float(
                Length(
                    f"1{self.units_name}",
                    relative_length=self.context.device.view.unit_width,
                )
            )
            conversion_y = float(
                Length(
                    f"1{self.units_name}",
                    relative_length=self.context.device.view.unit_height,
                )
            )
            # print ("Size: x0 = %.2f, conversion=%.5f, new=%.2f (units %s)" % (x0, conversion, x0/conversion, self.units_name))
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
        u = self.units_name
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
        u = self.units_name
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
                    preferred_units=self.units_name,
                )
            except ValueError:
                return
        if isinstance(w, str):
            return
        if abs(w) < 1e-8:
            self.text_w.SetValue(str(self.position_w))
            return
        self.position_w = w

        if self.lock_ratio:
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
                    preferred_units=self.units_name,
                )
            except ValueError:
                return
        if isinstance(h, str):
            return
        if abs(h) < 1e-8:
            self.text_h.SetValue(str(self.position_h))
            return

        self.position_h = h
        if self.lock_ratio:
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
                    preferred_units=self.units_name,
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
                    preferred_units=self.units_name,
                )
            except ValueError:
                return

        self.position_y = pos_y - self.offset_y * self.position_h

        if force:
            self.execute_xy_changes()
            self.context.signal("refresh_scene", "Scene")

    def Show(self, showit=True):
        if self._needs_generation and showit:
            self.update_position(True)
            self.startup = False
        super().Show(showit)

    def GenerateInfos(self):
        if self.visible:
            self.context.elements.set_start_time("positionwidget")
            self.update_position(True)
            self.startup = False
            self.context.elements.set_end_time("positionwidget")
        else:
            self._needs_generation = True

    def Signal(self, signal, *args):
        if signal in ("emphasized", "modified", "modified", "element_property_update"):
            self.GenerateInfos()
        if signal == "lock_active":
            self.lock_ratio = self.context.lock_active
