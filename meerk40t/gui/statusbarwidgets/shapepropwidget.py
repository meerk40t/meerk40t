import wx
from meerk40t.gui.icons import (
    cap_butt_20,
    cap_round_20,
    cap_square_20,
    join_bevel,
    join_miter,
    join_round,
    fill_evenodd,
    fill_nonzero,
)
from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation

class SBW_Linecap(StatusBarWidget):
    """
    Panel to change / assign the linecap of an element
    """
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
        self.cap_lbl = wx.StaticText(self, wx.ID_ANY, label=_("Cap"))
        self.btn_cap_butt = wx.Button(self, id=wx.ID_ANY, size=wx.Size(30, -1))
        self.btn_cap_butt.SetBitmap(cap_butt_20.GetBitmap(noadjustment=True))
        self.btn_cap_butt.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_butt.SetToolTip(_("Set the end of the lines to a butt-shape"))
        self.btn_cap_butt.Bind(wx.EVT_BUTTON, self.on_cap_butt)

        self.btn_cap_round = wx.Button(self, id=wx.ID_ANY, size=wx.Size(30, -1))
        self.btn_cap_round.SetBitmap(cap_round_20.GetBitmap(noadjustment=True))
        self.btn_cap_round.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_round.SetToolTip(
            _("Set the end of the lines to a round-shape")
        )
        self.btn_cap_round.Bind(wx.EVT_BUTTON, self.on_cap_round)

        self.btn_cap_square = wx.Button(self, id=wx.ID_ANY, size=wx.Size(30, -1))
        self.btn_cap_square.SetBitmap(cap_square_20.GetBitmap(noadjustment=True))
        self.btn_cap_square.SetMaxSize(wx.Size(50, -1))
        self.btn_cap_square.SetToolTip(
            _("Set the end of the lines to a square-shape")
        )
        self.btn_cap_square.Bind(wx.EVT_BUTTON, self.on_cap_square)

        self.parent.Add(self.cap_lbl, 0, wx.EXPAND, 0)
        self.parent.Add(self.btn_cap_butt, 1, wx.EXPAND, 0)
        self.parent.Add(self.btn_cap_round, 1, wx.EXPAND, 0)
        self.parent.Add(self.btn_cap_square, 1, wx.EXPAND, 0)

    def assign_cap(self, captype):
        self.context("linecap {cap}".format(cap=captype))

    def on_cap_square(self, event):
        self.assign_cap("square")

    def on_cap_butt(self, event):
        self.assign_cap("butt")

    def on_cap_round(self, event):
        self.assign_cap("round")


class SBW_Linejoin(StatusBarWidget):
    """
    Panel to change / assign the linejoin of an element
    (actually a subset: arcs and miter-clip have been intentionally omitted)
    """
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
        self.join_lbl = wx.StaticText(self, wx.ID_ANY, label=_("Join"))

        self.btn_join_bevel = wx.Button(self, id=wx.ID_ANY, size=wx.Size(25, -1))
        self.btn_join_bevel.SetBitmap(join_bevel.GetBitmap(noadjustment=True))
        self.btn_join_bevel.SetToolTip(
            _("Set the join of the lines to a bevel-shape")
        )
        self.btn_join_bevel.Bind(wx.EVT_BUTTON, self.on_join_bevel)

        self.btn_join_round = wx.Button(self, id=wx.ID_ANY, size=wx.Size(25, -1))
        self.btn_join_round.SetBitmap(join_round.GetBitmap(noadjustment=True))
        self.btn_join_round.SetToolTip(_("Set the join of lines to a round-shape"))
        self.btn_join_round.Bind(wx.EVT_BUTTON, self.on_join_round)

        self.btn_join_miter = wx.Button(self, id=wx.ID_ANY, size=wx.Size(25, -1))
        self.btn_join_miter.SetBitmap(join_miter.GetBitmap(noadjustment=True))
        self.btn_join_miter.SetToolTip(_("Set the join of lines to a miter-shape"))
        self.btn_join_miter.Bind(wx.EVT_BUTTON, self.on_join_miter)

        # self.btn_join_arcs = wx.Button(self, id=wx.ID_ANY, size=wx.Size(25, -1))
        # self.btn_join_arcs.SetBitmap(join_round.GetBitmap(noadjustment=True))
        # self.btn_join_arcs.SetToolTip(_("Set the join of lines to an arc-shape"))
        # self.btn_join_arcs.Bind(wx.EVT_BUTTON, self.on_join_arcs)

        # self.btn_join_miterclip = wx.Button(self, id=wx.ID_ANY, size=wx.Size(25, -1))
        # self.btn_join_miterclip.SetBitmap(join_miter.GetBitmap(noadjustment=True))
        # self.btn_join_miterclip.SetToolTip(_("Set the join of lines to a miter-clip-shape"))
        # self.btn_join_miterclip.Bind(wx.EVT_BUTTON, self.on_join_miterclip)

        self.parent.Add(self.join_lbl, 0, wx.EXPAND, 0)
        self.parent.Add(self.btn_join_bevel, 1, wx.EXPAND, 0)
        self.parent.Add(self.btn_join_round, 1, wx.EXPAND, 0)
        self.parent.Add(self.btn_join_miter, 1, wx.EXPAND, 0)
        # Who the h... needs those?
        # self.parent.Add(self.btn_join_arcs, 1, wx.EXPAND, 0)
        # self.parent.Add(self.btn_join_miterclip, 1, wx.EXPAND, 0)

    def assign_join(self, jointype):
        self.context("linejoin {join}".format(join=jointype))

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

class SBW_Fillrule(StatusBarWidget):
    """
    Panel to change / assign the fillrule of an element
    """
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
        self.fill_lbl = wx.StaticText(self, wx.ID_ANY, label=_("Fill"))
        self.btn_fill_nonzero = wx.Button(self, id=wx.ID_ANY, size=wx.Size(30, -1))
        self.btn_fill_nonzero.SetMaxSize(wx.Size(50, -1))
        self.btn_fill_nonzero.SetBitmap(fill_nonzero.GetBitmap(noadjustment=True))
        self.btn_fill_nonzero.SetToolTip(
            _("Set the fillstyle to non-zero (regular)")
        )
        self.btn_fill_nonzero.Bind(wx.EVT_BUTTON, self.on_fill_nonzero)

        self.btn_fill_evenodd = wx.Button(self, id=wx.ID_ANY, size=wx.Size(30, -1))
        self.btn_fill_evenodd.SetBitmap(fill_evenodd.GetBitmap(noadjustment=True))
        self.btn_fill_evenodd.SetMaxSize(wx.Size(50, -1))
        self.btn_fill_evenodd.SetToolTip(
            _("Set the fillstyle to even-odd (alternating areas)")
        )
        self.btn_fill_evenodd.Bind(wx.EVT_BUTTON, self.on_fill_evenodd)
        self.parent.Add(self.fill_lbl, 0, wx.EXPAND, 0)
        self.parent.Add(self.btn_fill_nonzero, 1, wx.EXPAND, 0)
        self.parent.Add(self.btn_fill_evenodd, 1, wx.EXPAND, 0)

    def assign_fill(self, filltype):
        self.context("fillrule {fill}".format(fill=filltype))

    def on_fill_evenodd(self, event):
        self.assign_fill("evenodd")

    def on_fill_nonzero(self, event):
        self.assign_fill("nonzero")