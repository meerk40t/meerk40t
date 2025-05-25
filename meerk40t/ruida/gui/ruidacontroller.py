import threading

import wx

from meerk40t.gui.icons import (
    get_default_icon_size,
    icons8_connected,
    icons8_disconnected,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl, dip_size, wxButton
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class RuidaControllerPanel(wx.ScrolledWindow):
    def __init__(self, *args, context=None, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)

        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.button_device_connect = wxButton(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self._buffer = ""
        self._buffer_lock = threading.Lock()
        self.text_usb_log = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.text_usb_log.SetFont(font)

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect
        )
        # end wxGlade
        self.max = 0
        self.state = None

    def __set_properties(self):
        self.button_device_connect.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_device_connect.SetForegroundColour(wx.BLACK)
        self.button_device_connect.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_device_connect.SetToolTip(
            _("Force connection/disconnection from the device.")
        )
        self.button_device_connect.SetBitmap(
            icons8_disconnected.GetBitmap(
                use_theme=False, resize=get_default_icon_size(self.context)
            )
        )
        # end wxGlade

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)
        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize(dip_size(self, 483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_usb_log, 5, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def update_text(self, text):
        with self._buffer_lock:
            self._buffer += f"{text}\n"
        self.context.signal("ruida_controller_update")

    @signal_listener("ruida_controller_update")
    def update_text_gui(self, origin):
        with self._buffer_lock:
            buffer = self._buffer
            self._buffer = ""
        self.text_usb_log.AppendText(buffer)

    def set_button_connected(self):
        self.button_device_connect.SetBackgroundColour("#00ff00")
        self.button_device_connect.SetBitmap(
            icons8_connected.GetBitmap(use_theme=False, resize=get_default_icon_size(self.context))
        )
        self.button_device_connect.Enable()

    def set_button_disconnected(self):
        self.button_device_connect.SetBackgroundColour("#dfdf00")
        self.button_device_connect.SetBitmap(
            icons8_disconnected.GetBitmap(
                use_theme=False, resize=get_default_icon_size(self.context)
            )
        )
        self.button_device_connect.Enable()

    @signal_listener("pipe;usb_status")
    def on_usb_update(self, origin=None, status=None):
        if origin != self.service.path:
            return
        if status is None:
            status = "Unknown"
        connected = self.service.connected
        if status == "connected":
            self.button_device_connect.SetLabel(_("Connected"))
        if status == "disconnected":
            self.button_device_connect.SetLabel(_("Disconnected"))
        if connected:
            self.set_button_connected()
        else:
            self.set_button_disconnected()

    def on_button_start_connection(self, event):  # wxGlade: Controller.<event_handler>
        connected = self.service.connected
        if self.service.is_connecting:
            self.service.abort_connect()
            self.service.set_disable_connect(False)
            return

        if connected:
            self.context("ruida_disconnect\n")
            self.service.set_disable_connect(False)
        else:
            self.service.set_disable_connect(False)
            self.context("ruida_connect\n")

    def pane_show(self):
        self._name = self.service.safe_label
        self.context.channel(f"{self._name}/recv", pure=True).watch(self.update_text)
        self.context.channel(f"{self._name}/send", pure=True).watch(self.update_text)
        self.context.channel(f"{self._name}/real", pure=True).watch(self.update_text)
        self.context.channel(f"{self._name}/events").watch(self.update_text)

        connected = self.service.connected
        if connected:
            self.set_button_connected()
        else:
            self.set_button_disconnected()

    def pane_hide(self):
        self.context.channel(f"{self._name}/recv").unwatch(self.update_text)
        self.context.channel(f"{self._name}/send").unwatch(self.update_text)
        self.context.channel(f"{self._name}/real").unwatch(self.update_text)
        self.context.channel(f"{self._name}/events").unwatch(self.update_text)


class RuidaController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 170, *args, **kwds)
        self.panel = RuidaControllerPanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        self.SetTitle(_("Ruida-Controller"))
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected.GetBitmap())
        self.SetIcon(_icon)
        self.Layout()
        self.restore_aspect()

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return "Device-Control", "Balor-Controller"

    @staticmethod
    def helptext():
        return _("Display the device controller window")
