"""
Basic Module to provide inforation about GUI
"""
import wx

from meerk40t.kernel import Service


class Themes(Service):
    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(self, kernel, "themes" if index is None else f"themes{index}")
        self.registered_themes = {
            "system": self.load_system_default,
        }
        self._theme = None
        self._dark = False
        self._theme_properties = dict()
        self.theme = "system"

    @property
    def dark(self):
        return self._dark

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, new_theme):
        if new_theme in self.registered_themes:
            self._theme = new_theme
            self.registered_themes[new_theme]()

    def get(self, property):
        if property in self._theme_properties:
            return self._theme_properties[property]
        # property not found
        return None

    def load_system_default(self):
        self._theme = "system"
        self._dark = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        from platform import system

        if system() == "Darwin" and not self._dark:
            buggy_darwin = True
        else:
            buggy_darwin = False

        self._theme_properties = dict()
        tp = self._theme_properties
        # Just a scaffold, will be extended later
        # tp["button"] = wx.Button
        tp["pause_bg"] = wx.Colour(200, 200, 0)
        # wx.Colour("ORANGE") if self._dark else wx.Colour("YELLOW")
        tp["pause_fg"] = wx.Colour("WHITE") if self._dark else wx.Colour("BLACK")
        # Start Button
        tp["start_bg"] = wx.Colour(0, 127, 0)
        tp["start_fg"] = wx.Colour("WHITE")
        tp["start_bg_inactive"] = (
            wx.Colour("DARK SLATE GREY") if self._dark else wx.Colour(0, 127, 0)
        )
        tp["start_fg_focus"] = wx.BLACK
        # Stop button
        tp["stop_bg"] = wx.Colour(127, 0, 0)  # red
        tp["stop_fg"] = wx.Colour("WHITE")
        tp["stop_fg_focus"] = wx.BLACK

        tp["arm_bg"] = wx.Colour(0, 127, 0)  # green
        tp["arm_fg"] = wx.WHITE
        tp["arm_bg_inactive"] = (
            # wx.Colour("MAROON") if self._dark else wx.Colour("PALE_GREEN")
            wx.Colour(127, 0, 0)
        )
        tp["arm_fg_focus"] = wx.BLACK

        if buggy_darwin:
            for key, item in tp.items():
                if isinstance(item, wx.Colour):
                    # System default
                    tp[key] = None
