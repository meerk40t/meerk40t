import wx

from .icons import icon_meerk40t, icons8_about_50
from .mwindow import MWindow

_ = wx.GetTranslation


class About(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(699, 442, *args, **kwds)

        self.bitmap_button_1 = wx.BitmapButton(
            self, wx.ID_ANY, icon_meerk40t.GetBitmap()
        )

        self.__set_properties()
        self.__do_layout()

        name = self.context.device_name
        version = self.context.device_version
        self.SetTitle(_("About %s v%s" % (name, version)))
        self.meerk40t_about_version_text.SetLabelText("%s v%s" % (name, version))

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_about_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: About.__set_properties
        self.SetTitle(_("About"))
        self.bitmap_button_1.SetSize(self.bitmap_button_1.GetBestSize())
        self.meerk40t_about_version_text = wx.StaticText(self, wx.ID_ANY, "MeerK40t")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: About.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_3.Add(self.bitmap_button_1, 1, 0, 0)
        self.meerk40t_about_version_text.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        sizer_3.Add(self.meerk40t_about_version_text, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        meerk40t_about_text_header = wx.StaticText(
            self,
            wx.ID_ANY,
            "MeerK40t is a free MIT Licensed open source project for lasering on K40 Devices.\n\nParticipation in the project is highly encouraged. Past participation, and continuing \nparticipation is graciously thanked. This program is mostly the brainchild of \nTatarize, who sincerely hopes his contributions will be but the barest trickle \nthat becomes a raging river.",
        )
        meerk40t_about_text_header.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        sizer_2.Add(meerk40t_about_text_header, 2, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        meerk40t_about_text = wx.StaticText(
            self,
            wx.ID_ANY,
            "Thanks.\nLi Huiyu for their controller. \nScorch for lighting our path.\nAlois Zingl for his wonderful Bresenham plotting algorithms.\n@joerlane and all the MeerKittens, past and present, great and small.\n\nIcon8 for their great icons ( https://icons8.com/ ) used throughout the project.\nThe works of countless developers who made everything possible.\nRegebro for his svg.path module.\nThe SVG Working Group.\nHackers (in the general sense).",
        )
        meerk40t_about_text.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        sizer_1.Add(meerk40t_about_text, 2, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade
