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


class NewlyControllerPanel(wx.ScrolledWindow):
    def __init__(self, *args, context=None, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("newlycontroller")

        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.button_device_connect = wxButton(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self._buffer = []
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
            self._buffer.append(f"{text}\n")
        self.context.signal("newly_controller_update")

    @signal_listener("newly_controller_update")
    def update_text_gui(self, origin):
        with self._buffer_lock:
            buffer = "".join(self._buffer)
            self._buffer.clear()
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
        if status is None:
            status = "Unknown"
        try:
            connected = self.service.driver.connected
        except AttributeError:
            return
        try:
            if isinstance(status, bytes):
                status = status.decode("unicode-escape")
            self.button_device_connect.SetLabel(status)
            if connected:
                self.set_button_connected()
            else:
                self.set_button_disconnected()
        except RuntimeError:
            pass

    def on_button_start_connection(self, event):  # wxGlade: Controller.<event_handler>
        try:
            connected = self.service.driver.connected
        except AttributeError:
            return
        try:
            if self.service.driver.connection.is_connecting:
                self.service.driver.connection.abort_connect()
                self.service.driver.connection.set_disable_connect(False)
                return
        except AttributeError:
            pass

        if connected:
            self.context("usb_disconnect\n")
            self.service.driver.connection.set_disable_connect(False)
        else:
            self.service.driver.connection.set_disable_connect(False)
            self.context("usb_connect\n")

    def pane_show(self):
        self._channel_watching = f"{self.service.safe_label}/usb"
        self.context.channel(self._channel_watching).watch(self.update_text)
        try:
            connected = self.service.driver.connected
            if connected:
                self.set_button_connected()
            else:
                self.set_button_disconnected()
        except RuntimeError:
            pass

    def pane_hide(self):
        self.context.channel(self._channel_watching).unwatch(self.update_text)


class NewlyController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 170, *args, **kwds)
        self.panel = NewlyControllerPanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        self.SetTitle(_("Newly-Controller"))
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
        return "Device-Control", "Newly-Controller"

    @staticmethod
    def helptext():
        return _("Display the device controller window")
