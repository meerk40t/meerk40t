import wx

from meerk40t.core.units import Length
from meerk40t.core.elements.element_types import elem_nodes
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
from meerk40t.gui.wxutils import dip_size, TextCtrl, wxToggleButton
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
        self.cap_lbl = wx.StaticText(self.parent, wx.ID_ANY, label=_("Cap"))
        self.cap_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.btn_cap_butt = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )

        self.btn_cap_butt.SetBitmap(
            icon_cap_butt.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_cap_butt.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_butt.SetToolTip(_("Set the end of the lines to a butt-shape"))
        self.btn_cap_butt.Bind(wx.EVT_LEFT_DOWN, self.on_cap_butt)

        self.btn_cap_round = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )
        self.btn_cap_round.SetBitmap(
            icon_cap_round.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_cap_round.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_round.SetToolTip(_("Set the end of the lines to a round-shape"))
        self.btn_cap_round.Bind(wx.EVT_LEFT_DOWN, self.on_cap_round)

        self.btn_cap_square = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )

        self.btn_cap_square.SetBitmap(
            icon_cap_square.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
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
        self.join_lbl = wx.StaticText(self.parent, wx.ID_ANY, label=_("Join"))
        self.join_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )

        self.btn_join_bevel = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )

        self.btn_join_bevel.SetBitmap(
            icon_join_bevel.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_join_bevel.SetMaxSize(wx.Size(50, -1))
        self.btn_join_bevel.SetToolTip(_("Set the join of the lines to a bevel-shape"))
        self.btn_join_bevel.Bind(wx.EVT_LEFT_DOWN, self.on_join_bevel)

        self.btn_join_round = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )
        self.btn_join_round.SetBitmap(
            icon_join_round.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_join_round.SetMaxSize(wx.Size(50, -1))
        self.btn_join_round.SetToolTip(_("Set the join of lines to a round-shape"))
        self.btn_join_round.Bind(wx.EVT_LEFT_DOWN, self.on_join_round)

        self.btn_join_miter = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED
        )
        self.btn_join_miter.SetBitmap(
            icon_join_miter.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_join_miter.SetMaxSize(wx.Size(50, -1))
        self.btn_join_miter.SetToolTip(_("Set the join of lines to a miter-shape"))
        self.btn_join_miter.Bind(wx.EVT_LEFT_DOWN, self.on_join_miter)

        # self.btn_join_arcs = wx.StaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED)
        # self.btn_join_arcs.SetBitmap(icon_join_round.GetBitmap(noadjustment=True))
        # self.btn_join_arcs.SetToolTip(_("Set the join of lines to an arc-shape"))
        # self.btn_join_arcs.Bind(wx.EVT_LEFT_DOWN, self.on_join_arcs)

        # self.btn_join_miterclip = wx.StaticBitmap(self.parent, id=wx.ID_ANY, size=wx.Size(25, -1), style=wx.BORDER_RAISED)
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
        self.fill_lbl = wx.StaticText(self.parent, wx.ID_ANY, label=_("Fill"))
        self.fill_lbl.SetFont(
            wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.btn_fill_nonzero = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )
        self.btn_fill_nonzero.SetMaxSize(wx.Size(50, -1))
        self.btn_fill_nonzero.SetBitmap(
            icon_fill_nonzero.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
        )
        self.btn_fill_nonzero.SetToolTip(_("Set the fillstyle to non-zero (regular)"))
        self.btn_fill_nonzero.Bind(wx.EVT_LEFT_DOWN, self.on_fill_nonzero)

        self.btn_fill_evenodd = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )
        self.btn_fill_evenodd.SetBitmap(
            icon_fill_evenodd.GetBitmap(
                resize=max(20, self.parent.available_height - 4), buffer=1
            )
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
        self.xy_lbl = wx.StaticText(self.parent, wx.ID_ANY, label=_("X, Y"))
        self.node = None
        self.t_x = TextCtrl(self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float")
        self.t_y = TextCtrl(self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float")
        self.unit_lbl = wx.StaticText(self.parent, wx.ID_ANY, label="mm")
        self.wh_lbl = wx.StaticText(self.parent, wx.ID_ANY, label=_("W, H"))
        self.t_w = TextCtrl(self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float")
        self.t_w.SetToolTip(_(""))
        self.t_h = TextCtrl(self.parent, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="float")
        self.unit_lbl2 = wx.StaticText(self.parent, wx.ID_ANY, label="mm")
        self.btn_lock_ratio = wxToggleButton(self.parent, wx.ID_ANY, "")
        self.btn_lock_ratio.SetValue(True)
        self.bitmap_locked = icons8_lock.GetBitmap(
            resize=30, use_theme=False
        )
        self.bitmap_unlocked = icons8_unlock.GetBitmap(
            resize=30, use_theme=False
        )
        self.Add(self.xy_lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.t_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.t_y, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.unit_lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.wh_lbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.t_w, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.t_h, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.unit_lbl2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.btn_lock_ratio, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fnt = wx.Font(
                7,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        for ctl in (self.t_x, self.t_y, self.t_w, self.t_h,):
            ctl.SetSize(dip_size(self.parent, -1, 10))
        for ctl in (self.t_x, self.t_y, self.t_w, self.t_h, self.xy_lbl, self.wh_lbl, self.unit_lbl, self.unit_lbl2):
            ctl.SetFont(fnt)
        self.t_x.SetActionRoutine(self.on_text_x_enter)
        self.t_y.SetActionRoutine(self.on_text_y_enter)
        self.t_w.SetActionRoutine(self.on_text_w_enter)
        self.t_h.SetActionRoutine(self.on_text_h_enter)
        self.btn_lock_ratio.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_ratio)

    def translate_it(self):
        if self.node is None:
            return
        if not self.node.can_move(self.context.elements.lock_allows_move):
            return
        bb = self.node.bounds
        try:
            newx = float(Length(self.t_x.GetValue()+self.unit_lbl.GetLabel()))
            newy = float(Length(self.t_y.GetValue()+self.unit_lbl.GetLabel()))
        except (ValueError, AttributeError):
            return
        dx = newx - bb[0]
        dy = newy - bb[1]
        if dx != 0 or dy != 0:
            self.node.matrix.post_translate(dx, dy)
            # self.node.modified()
            self.node.translated(dx, dy)
            self.context.elements.signal("element_property_update", self.node)
            self.context.elements.signal("refresh_scene", "Scene")

    def scale_it(self, was_width):
        if self.node is None:
            return
        if not self.node.can_scale:
            return
        bb = self.node.bounds
        keep_ratio = self.btn_lock_ratio.GetValue()
        try:
            neww = float(Length(self.t_w.GetValue()+self.unit_lbl.GetLabel()))
            newh = float(Length(self.t_h.GetValue()+self.unit_lbl.GetLabel()))
        except (ValueError, AttributeError):
            return
        if bb[2] != bb[0]:
            sx = neww / (bb[2] - bb[0])
        else:
            sx = 1
        if bb[3] != bb[1]:
            sy = newh / (bb[3] - bb[1])
        else:
            sy = 1
        if keep_ratio:
            if was_width:
                sy = sx
            else:
                sx = sy
        if sx != 1.0 or sy != 1.0:
            self.node.matrix.post_scale(sx, sy, bb[0], bb[1])
            self.node.scaled(sx=sx, sy=sy, ox=bb[0], oy=bb[1])
            # self.node.modified()
            bb = self.node.bounds
            w = bb[2] - bb[0]
            h = bb[3] - bb[1]
            # units = self.context.units_name
            # if units in ("inch", "inches"):
            #     units = "in"
            units = self.unit_lbl.GetLabel()
            self.t_w.SetValue(
                f"{Length(amount=w, preferred_units=units, digits=4).preferred}"
            )
            self.t_h.SetValue(
                f"{Length(amount=h, preferred_units=units, digits=4).preferred}"
            )

            self.context.elements.signal("element_property_update", self.node)
            self.context.elements.signal("refresh_scene", "Scene")

    def on_toggle_ratio(self, event):
        if self.btn_lock_ratio.GetValue():
            self.btn_lock_ratio.SetBitmap(self.bitmap_locked)
        else:
            self.btn_lock_ratio.SetBitmap(self.bitmap_unlocked)

    def on_text_x_enter(self):
        self.translate_it()

    def on_text_y_enter(self):
        self.translate_it()

    def on_text_w_enter(self):
        self.scale_it(True)

    def on_text_h_enter(self):
        self.scale_it(False)

    def set_widgets(self):
        s_x = ""
        s_y = ""
        s_w = ""
        s_h = ""
        self.node = None
        for e in self.context.elements.flat(types=elem_nodes, emphasized=True):
            try:
                bb = e.bounds
                s_x = f"{Length(bb[0]).mm:.2f}"
                s_y = f"{Length(bb[1]).mm:.2f}"
                s_w = f"{Length(bb[2] - bb[0]).mm:.2f}"
                s_h = f"{Length(bb[3] - bb[1]).mm:.2f}"
                self.node = e
                break
            except AttributeError:
                pass
        self.t_x.SetValue(s_x)
        self.t_y.SetValue(s_y)
        self.t_w.SetValue(s_w)
        self.t_h.SetValue(s_h)

    def Signal(self, signal, *args):
        if signal == "emphasized":
            self.set_widgets()
            self.startup = False
        if signal == "modified":
            self.set_widgets()
