import wx

from meerk40t.gui.icons import (
    icon_cap_butt,
    icon_cap_round,
    icon_cap_square,
    icon_fill_evenodd,
    icon_fill_nonzero,
    icon_join_bevel,
    icon_join_miter,
    icon_join_round,
)

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
        self.btn_fill_nonzero.SetBitmap(icon_fill_nonzero.GetBitmap(noadjustment=True))
        self.btn_fill_nonzero.SetToolTip(_("Set the fillstyle to non-zero (regular)"))
        self.btn_fill_nonzero.Bind(wx.EVT_LEFT_DOWN, self.on_fill_nonzero)

        self.btn_fill_evenodd = wx.StaticBitmap(
            self.parent, id=wx.ID_ANY, size=wx.Size(30, -1), style=wx.BORDER_RAISED
        )
        self.btn_fill_evenodd.SetBitmap(icon_fill_evenodd.GetBitmap(noadjustment=True))
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
