import re
import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation

DOLLAR_INFO = re.compile(r"\$([0-9]+)=(.*)")


class GRBLConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(345, 415, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("GRBL-Configuration"))

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.panels = []
        self._requested_status = False

        inject_choices = [
            {
                "attr": "aquire_properties",
                "object": self,
                "default": False,
                "type": bool,
                "style": "button",
                "label": _("Query properties"),
                "tip": _("Connect to laser and try to establish some properties"),
                "section": "_ZZ_Auto-Configuration",
                "width": 250,
                "weight": 0,
            },
        ]

        panel_main = ChoicePropertyPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            choices="grbl-connection",
            injector=inject_choices,
        )
        panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-global"
        )
        panel_dim = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="bed_dim"
        )
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(panel_main)
        self.panels.append(panel_global)
        self.panels.append(panel_dim)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(newpanel)

        self.notebook_main.AddPage(panel_main, _("Connection"))
        self.notebook_main.AddPage(panel_dim, _("Dimensions"))
        self.notebook_main.AddPage(panel_global, _("Global Settings"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(newpanel, _("Display Options"))
        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()

    def window_preserve(self):
        return False

    @staticmethod
    def submenu():
        return ("Device-Settings", "GRBL-Configuration")

    @property
    def aquire_properties(self):
        # Not relevant
        return False

    @aquire_properties.setter
    def aquire_properties(self, value):
        if not value:
            return
        try:
            self.context.driver.grbl("$$\r")
            self._requested_status = True
        except:
            wx.MessageBox(
                _("Could not query laser-data!"),
                _("Connect failed"),
                wx.OK | wx.ICON_ERROR,
            )

    @signal_listener("grbl;response")
    def on_serial_status(self, origin, cmd_issued, responses):
        if cmd_issued == "$$":
            # Right command
            if self._requested_status:
                # coming from myself
                if responses is not None:
                    changes = False
                    for resp in responses:
                        index = -1
                        value = None
                        match = DOLLAR_INFO.match(resp)
                        if match:
                            # $xx=yy
                            index = int(match.group(1))
                            value = match.group(2)
                        if index >= 0 and value is not None:
                            self.context.controller.grbl_settings[index] = value
                        if index == 21:
                            flag = bool(int(value) == 1)
                            self.context.has_endstops = flag
                            self.context.signal("has_endstops", flag, self.context)
                        elif index == 130:
                            self.context.bedwidth = f"{value}mm"
                            self.context.signal(
                                "bedwidth", self.context.bedwidth, self.context
                            )
                            changes = True
                        elif index == 131:
                            self.context.bedheight = f"{value}mm"
                            self.context.signal(
                                "bedheight", self.context.bedheight, self.context
                            )
                            changes = True
                    if changes:
                        self.context("viewport_update\n")
                        self.context.signal("guide")
                        self.context.signal("grid")
                        self.context.signal("refresh_scene", "Scene")
                self._requested_status = False
                wx.MessageBox(
                    _("Successfully queried laser-data!"),
                    _("Connect succeeded"),
                    wx.OK | wx.ICON_INFORMATION,
                )

        else:
            # Different command
            pass
