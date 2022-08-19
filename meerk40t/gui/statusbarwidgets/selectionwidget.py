import wx

from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class SelectionWidget(StatusBarWidget):
    """
    Panel to set some of the options for the selection rectangle
    around an emphasized element
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)

        FONT_SIZE = 7

        # These will fall into the last field
        self.cb_move = wx.CheckBox(self.parent, id=wx.ID_ANY, label=_("Move"))
        self.cb_handle = wx.CheckBox(self.parent, id=wx.ID_ANY, label=_("Resize"))
        self.cb_rotate = wx.CheckBox(self.parent, id=wx.ID_ANY, label=_("Rotate"))
        self.cb_skew = wx.CheckBox(self.parent, id=wx.ID_ANY, label=_("Skew"))
        self.cb_move.SetFont(
            wx.Font(
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.cb_handle.SetFont(
            wx.Font(
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.cb_rotate.SetFont(
            wx.Font(
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.cb_skew.SetFont(
            wx.Font(
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )

        self.parent.Bind(wx.EVT_CHECKBOX, self.on_toggle_move, self.cb_move)
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_toggle_handle, self.cb_handle)
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_toggle_rotate, self.cb_rotate)
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_toggle_skew, self.cb_skew)
        self.StartPopulation()
        self.cb_move.SetValue(self.context.enable_sel_move)
        self.cb_handle.SetValue(self.context.enable_sel_size)
        self.cb_rotate.SetValue(self.context.enable_sel_rotate)
        self.cb_skew.SetValue(self.context.enable_sel_skew)
        self.EndPopulation()
        self.cb_move.SetToolTip(_("Toggle visibility of Move-indicator"))
        self.cb_handle.SetToolTip(_("Toggle visibility of Resize-handles"))
        self.cb_rotate.SetToolTip(_("Toggle visibility of Rotation-handles"))
        self.cb_skew.SetToolTip(_("Toggle visibility of Skew-handles"))
        self.PrependSpacer(5)
        self.Add(self.cb_move, 1, wx.EXPAND, 0)
        self.Add(self.cb_handle, 1, wx.EXPAND, 0)
        self.Add(self.cb_rotate, 1, wx.EXPAND, 0)
        self.Add(self.cb_skew, 1, wx.EXPAND, 0)

    # the checkbox was clicked
    def on_toggle_move(self, event):
        if not self.startup:
            value = self.cb_move.GetValue()
            self.context.enable_sel_move = value
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_handle(self, event):
        if not self.startup:
            value = self.cb_handle.GetValue()
            self.context.enable_sel_size = value
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_rotate(self, event):
        if not self.startup:
            value = self.cb_rotate.GetValue()
            self.context.enable_sel_rotate = value
            self.context.signal("refresh_scene", "Scene")

    def on_toggle_skew(self, event):
        if not self.startup:
            value = self.cb_skew.GetValue()
            self.context.enable_sel_skew = value
            self.context.signal("refresh_scene", "Scene")
