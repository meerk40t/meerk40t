import wx
from wx import aui

from meerk40t.gui.panes.jog import MILS_IN_MM

_ = wx.GetTranslation


def register_panel(window, context):
    panel = JogDistancePanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(190, 110)
        .FloatingSize(190, 110)
        .Hide()
        .Caption(_("Distances"))
        .CaptionVisible(not context.pane_lock)
        .Name("jogdist")
    )
    pane.dock_proportion = 110
    pane.control = panel
    pane.submenu = _("Navigation")

    window.on_pane_add(pane)
    context.register("pane/jogdist", pane)


class JogDistancePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: JogDistancePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.spin_jog_mils = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "100.0", min=0.0, max=10000.0
        )
        self.spin_jog_mm = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "10.0", min=0.0, max=254.0
        )
        self.spin_jog_cm = wx.SpinCtrlDouble(self, wx.ID_ANY, "1.0", min=0.0, max=25.4)
        self.spin_jog_inch = wx.SpinCtrlDouble(
            self, wx.ID_ANY, "0.394", min=0.0, max=10.0
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mils)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_mm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_cm)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin_jog_distance, self.spin_jog_inch)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_jog_distance, self.spin_jog_inch)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: JogDistancePanel.__set_properties
        self.spin_jog_mils.SetMinSize((80, 23))
        self.spin_jog_mils.SetToolTip(
            _("Set Jog Distance in mils (1/1000th of an inch)")
        )
        self.spin_jog_mm.SetMinSize((80, 23))
        self.spin_jog_mm.SetToolTip(_("Set Jog Distance in mm"))
        self.spin_jog_cm.SetMinSize((80, 23))
        self.spin_jog_cm.SetToolTip(_("Set Jog Distance in cm"))
        self.spin_jog_inch.SetMinSize((80, 23))
        self.spin_jog_inch.SetToolTip(_("Set Jog Distance in inch"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JogDistancePanel.__do_layout
        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Jog Distance")), wx.HORIZONTAL
        )
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_9 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("cm")), wx.VERTICAL)
        sizer_8 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("mm")), wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_10 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("inches")), wx.VERTICAL
        )
        sizer_7 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("steps")), wx.VERTICAL
        )
        sizer_7.Add(self.spin_jog_mils, 0, 0, 0)
        sizer_3.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_10.Add(self.spin_jog_inch, 0, 0, 0)
        sizer_3.Add(sizer_10, 0, wx.EXPAND, 0)
        sizer_6.Add(sizer_3, 0, wx.EXPAND, 0)
        sizer_8.Add(self.spin_jog_mm, 0, 0, 0)
        sizer_2.Add(sizer_8, 0, wx.EXPAND, 0)
        sizer_9.Add(self.spin_jog_cm, 0, 0, 0)
        sizer_2.Add(sizer_9, 0, wx.EXPAND, 0)
        sizer_6.Add(sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_6)
        sizer_6.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.set_jog_distances(self.context.navigate_jog)

    def set_jog_distances(self, jog_mils):
        self.spin_jog_mils.SetValue(jog_mils)
        self.spin_jog_mm.SetValue(jog_mils / MILS_IN_MM)
        self.spin_jog_cm.SetValue(jog_mils / (MILS_IN_MM * 10.0))
        self.spin_jog_inch.SetValue(jog_mils / 1000.0)

    def on_spin_jog_distance(self, event):  # wxGlade: Navigation.<event_handler>
        if event.Id == self.spin_jog_mils.Id:
            self.context.navigate_jog = float(self.spin_jog_mils.GetValue())
        elif event.Id == self.spin_jog_mm.Id:
            self.context.navigate_jog = float(self.spin_jog_mm.GetValue() * MILS_IN_MM)
        elif event.Id == self.spin_jog_cm.Id:
            self.context.navigate_jog = float(
                self.spin_jog_cm.GetValue() * MILS_IN_MM * 10.0
            )
        else:
            self.context.navigate_jog = float(self.spin_jog_inch.GetValue() * 1000.0)
        self.set_jog_distances(int(self.context.navigate_jog))
