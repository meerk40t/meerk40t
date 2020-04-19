import wx

from Kernel import Module
from icons import icon_meerk40t


_ = wx.GetTranslation


class About(wx.Frame, Module):
    def __init__(self, *args, **kwds):
        # begin wxGlade: About.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((699, 442))
        self.bitmap_button_1 = wx.BitmapButton(self, wx.ID_ANY, icon_meerk40t.GetBitmap())

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.device.module_instance_remove(self.name)
        event.Skip()  # Call destroy as regular.

    def initialize(self):
        self.device.module_instance_close(self.name)
        self.Show()

    def shutdown(self):
        self.Close()

    def __set_properties(self):
        # begin wxGlade: About.__set_properties
        self.SetTitle(_("About"))
        self.bitmap_button_1.SetSize(self.bitmap_button_1.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: About.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.bitmap_button_1, 0, 0, 0)
        meerk40t_about_text_header = wx.StaticText(self, wx.ID_ANY, "MeerK40t is a free MIT Licensed open source project for lasering on K40 Devices.\n\nParticipation in the project is highly encouraged. Past participation, and continuing participation is graciously thanked. This program is mostly the brainchild of Tatarize, who sincerely hopes his contributions will be but the barest trickle that becomes a raging river.")
        meerk40t_about_text_header.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        sizer_2.Add(meerk40t_about_text_header, 2, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        meerk40t_about_text = wx.StaticText(self, wx.ID_ANY, "Thanks.\nLi Huiyu is for his controller. \nScorch for lighting our path.\nAlois Zingl for his wonderful Bresenham plotting algorithms.\n@joerlane and all the MeerKittens, past and present, great and small.\n\nIcon8 for their great icons ( https://icons8.com/ ) used throughout the project.\nThe works of countless developers who made everything possible.\nRegebro for his svg.path module.\nThe SVG Working Group.\nHackers (in the general sense).")
        meerk40t_about_text.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        sizer_1.Add(meerk40t_about_text, 2, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        self.Centre()
        # end wxGlade
