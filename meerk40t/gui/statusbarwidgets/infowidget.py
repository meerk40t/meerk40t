import wx

from ...core.element_types import elem_nodes
from ...core.units import Length
from ..icons import icons8_up_50
from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation


class SimpleInfoWidget(StatusBarWidget):
    """
    Placeholder to accept any kind of information,
    if none is given externally it falls back to basic infos
    about the emphasized elements
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We can store multiple lines of information
        self._messages = []
        self._counter = 0
        self.fontsize = None

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)

        self.info_text = wx.StaticText(self.parent, wx.ID_ANY, label="")
        if self.fontsize is not None:
            self.info_text.SetFont(
                wx.Font(
                    self.fontsize,
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            )
        self.btn_next = wx.StaticBitmap(
            self.parent,
            id=wx.ID_ANY,
            bitmap=icons8_up_50.GetBitmap(resize=20),
            size=wx.Size(20, 20),
            style=wx.BORDER_RAISED,
        )
        infocolor = wx.Colour(128, 128, 128, 128)
        self.btn_next.SetBackgroundColour(infocolor)
        self.btn_next.Bind(wx.EVT_LEFT_DOWN, self.on_button_next)
        self.btn_next.Bind(wx.EVT_RIGHT_DOWN, self.on_button_prev)

        self.Add(self.info_text, 1, wx.EXPAND, 0)
        self.Add(self.btn_next, 0, wx.EXPAND, 0)
        self.SetActive(self.btn_next, False)

    def AppendInformation(self, msg):
        self._messages.append(msg)
        self._counter = -1
        self._display_current_line()

    def SetInformation(self, msg):
        self._messages = []
        if isinstance(msg, str):
            self._messages = [msg]
        elif isinstance(msg, (tuple, list)):
            self._messages = msg
        flag = len(self._messages) > 1
        self.SetActive(self.btn_next, enableit=flag)
        self.Layout()
        self._counter = 0
        self._display_current_line()

    def _display_current_line(self):
        msg = ""
        if len(self._messages) > 0:
            if self._counter < 0:
                self._counter = len(self._messages) - 1
            if self._counter >= len(self._messages):
                self._counter = 0
            content = self._messages[self._counter]
            msg = "" if content is None else content
        self.info_text.SetLabel(msg)

    def on_button_prev(self, event):
        self._counter -= 1
        self._display_current_line()

    def on_button_next(self, event):
        self._counter += 1
        self._display_current_line()


class InformationWidget(SimpleInfoWidget):
    """
    This widget displays basic infos about the emphasized elements
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fontsize = 7
        self._needs_generation = False
        # We dont have a context yet...
        self._info_active = True

    def Show(self, showit):
        if self._needs_generation and showit:
            self.calculate_infos()
        super().Show(showit)

    def GenerateControls(self, parent, panelidx, identifier, context):
        super().GenerateControls(parent, panelidx, identifier, context)
        self.context.setting(bool, "statusbar_auto_statistic", True)
        self._info_active = self.context.statusbar_auto_statistic

        self.chk_active = wx.CheckBox(parent, wx.ID_ANY, "")
        self.chk_active.SetToolTip(_("Uncheck if you don't want automatic statistic generation"))
        self.chk_active.SetValue(self._info_active)
        self.chk_active.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
        self.Add(self.chk_active, 0, 0, 0)

    def on_checkbox(self, event):
        self._info_active = self.chk_active.GetValue()
        self.context.statusbar_auto_statistic = self._info_active
        self.calculate_infos()
        event.Skip()

    def GenerateInfos(self):
        if self.visible:
            self.calculate_infos()
        else:
            self._needs_generation = True

    def calculate_infos(self):
        msg = ""
        if self._info_active:
            elements = self.context.elements
            ct = 0
            total_area = 0
            total_length = 0
            _mm = float(Length("1{unit}".format(unit="mm")))
            for e in elements.flat(types=elem_nodes, emphasized=True):
                ct += 1
                this_area, this_length = elements.get_information(e, density=50)
                total_area += this_area
                total_length += this_length

            if ct > 0:
                total_area = total_area / (_mm * _mm)
                total_length = total_length / _mm
                msg = "# = %d, A = %.1f mm², D = %.1f mm" % (ct, total_area, total_length)
        else:
            msg = "---"
        self.StartPopulation()
        self.SetInformation(msg)
        self.EndPopulation()
        self._needs_generation = False

    def Signal(self, signal, *args):
        if signal == "emphasized":
            self.GenerateInfos()


class StatusPanelWidget(SimpleInfoWidget):
    """
    This widget displays basic infos about the emphasized elements
    """

    def __init__(self, panelct, **kwargs):
        super().__init__(**kwargs)
        self.status_text = [""] * panelct
        # self.fontsize = 7

    def GenerateInfos(self):
        compacted_messages = []
        for idx, entry in enumerate(self.status_text):
            if entry != "":
                msg = entry
                if idx > 0:
                    msg = "#" + str(idx) + ": " + msg
                compacted_messages.append(msg)
        self.SetInformation(compacted_messages)

    def Signal(self, signal, *args):
        if signal == "statusmsg":
            msg = ""
            idx = 0
            if len(args) > 0:
                msg = args[0]
            if len(args) > 1:
                idx = args[1]
            self.status_text[idx] = msg
            self.GenerateInfos()
