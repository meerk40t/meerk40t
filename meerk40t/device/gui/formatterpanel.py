import wx

from meerk40t.gui.icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
)
from meerk40t.gui.wxutils import TextCtrl

_ = wx.GetTranslation


class FormatterPanel(wx.Panel):
    """
    WarningPanel is a panel that should work for all devices (hence in its own directory)
    It allows to define Min and Max Values for Speed and Power per operation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        infolabel = wx.StaticText(
            self,
            id=wx.ID_ANY,
            label=_("Placeholder"),
        )

        sizer_main.Add(infolabel, 0, 0, 0)
        self.SetSizer(sizer_main)

        self.Layout()

        self.update_widgets()

    def on_checkbox_check(self, entry, isMax):
        def check(event=None):
            event.Skip()

        return check

    def on_text_formatter(self, textctrl, entry, isMax):
        def check(event=None):
            return
        return check

    def update_settings(self, operation, attribute, minmax, active, value):
        return

    def update_widgets(self):
        return

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()
