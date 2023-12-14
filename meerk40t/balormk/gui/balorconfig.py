import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class BalorConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(420, 570, *args, **kwds)
        self.context = self.context.device
        self.SetHelpText("balorconfig")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_(_("Balor-Configuration")))
        self._test_pin = False
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )

        options = (
            ("balor", "Balor"),
            ("balor-redlight", "Redlight"),
            ("balor-global", "Global"),
            ("balor-global-timing", "Timings"),
            ("balor-extra", "Extras"),
        )
        injector = (
            {
                "attr": "test_pin",
                "object": self,
                "default": False,
                "type": bool,
                "style": "button",
                "label": _("Test"),
                "tip": _("Turn red dot on for test purposes"),
                "section": "_10_Parameters",
                "subsection": "_30_Pin-Index",
            },
        )
        self.panels = []
        for item in options:
            section = item[0]
            pagetitle = _(item[1])
            addpanel = self.visible_choices(section)
            if addpanel:
                if item[0] == "balor":
                    injection = injector
                else:
                    injection = None
                newpanel = ChoicePropertyPanel(
                    self, wx.ID_ANY, context=self.context, choices=section, injector=injection,
                )
                self.panels.append(newpanel)
                self.notebook_main.AddPage(newpanel, pagetitle)
        newpanel = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Warning"))

        newpanel = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Default Actions"))

        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Display Options"))

        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)

    @property
    def test_pin(self):
        return self._test_pin

    @test_pin.setter
    def test_pin(self, value):
        self._test_pin = not self._test_pin
        if self._test_pin:
            self.context("red on\n")
        else:
            self.context("red off\n")

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()

    @signal_listener("balorpin")
    def on_pin_change(self, origina, *args):
        self.context.driver.connection.define_pins()

    @signal_listener("corfile")
    def on_corfile_changed(self, origin, *args):
        from meerk40t.balormk.controller import GalvoController

        try:
            scale = GalvoController.get_scale_from_correction_file(self.context.corfile)
        except FileNotFoundError:
            return
        self.context.lens_size = f"{65536.0 / scale:.03f}mm"
        self.context.signal("lens_size", self.context.lens_size, self.context)
        self.context.signal("bedsize", False)

    def window_preserve(self):
        return False

    def visible_choices(self, section):
        result = False
        devmode = self.context.root.setting(bool, "developer_mode", False)
        choices = self.context.lookup("choices", section)
        if choices is not None:
            for item in choices:
                try:
                    dummy = str(item["hidden"])
                    if dummy == "" or dummy == "0":
                        hidden = False
                    else:
                        hidden = False if devmode else True
                except KeyError:
                    hidden = False
                if not hidden:
                    result = True
                    break
        return result

    @staticmethod
    def submenu():
        return "Device-Settings", "Configuration"
