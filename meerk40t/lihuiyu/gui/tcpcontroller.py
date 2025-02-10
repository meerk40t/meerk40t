import wx

from meerk40t.gui.icons import (
    get_default_icon_size,
    icons8_connected,
    icons8_disconnected,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxStaticText,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class TCPController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 200, *args, **kwds)
        self.SetHelpText("k40tcp")

        self.button_device_connect = wxButton(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self.text_status = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_ip_host = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="empty"
        )
        self.text_ip_host.SetMinSize(dip_size(self, 125, -1))
        self.text_port = TextCtrl(
            self, wx.ID_ANY, "", check="int", limited=True, style=wx.TE_PROCESS_ENTER
        )
        self.text_port.lower_limit = 0
        self.text_port.upper_limit = 65535
        self.text_port.lower_limit_err = 0
        self.text_port.upper_limit_err = 65535
        self.gauge_buffer = wx.Gauge(self, wx.ID_ANY, 10)
        self.text_buffer_length = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_buffer_max = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect
        )
        self.text_port.SetActionRoutine(self.on_port_change)
        self.text_ip_host.SetActionRoutine(self.on_address_change)
        # end wxGlade
        self.max = 0
        self.state = None
        # self.on_tcp_buffer(None, 20)
        self.restore_aspect()

    def on_port_change(self):
        try:
            self.service.port = max(0, min(65535, int(self.text_port.GetValue())))
        except ValueError:
            pass

    def on_address_change(self):
        self.service.address = str(self.text_ip_host.GetValue())

    def __set_properties(self):
        # begin wxGlade: Controller.__set_properties
        self.SetTitle(_("TCP-Controller"))
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected.GetBitmap())
        self.SetIcon(_icon)
        # For whatever reason the windows backgroundcolor is a dark grey,
        # not sure why but, we just set it back to standard value
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
        self.text_status.SetToolTip(_("Connection status"))
        self.text_ip_host.SetToolTip(_("IP/hostname of the server computer"))
        self.text_port.SetToolTip(_("Port for tcp connection on the server computer"))
        self.text_buffer_length.SetMinSize(dip_size(self, 45, -1))
        self.text_buffer_length.SetMaxSize(dip_size(self, 75, -1))
        self.text_buffer_length.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        self.text_buffer_max.SetMinSize(dip_size(self, 45, -1))
        self.text_buffer_max.SetMaxSize(dip_size(self, 75, -1))
        self.text_buffer_max.SetToolTip(
            _("Highest number of bytes in the write buffer.")
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Controller.__do_layout
        sizer_main = self.sizer
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)

        sizer_connection = wx.BoxSizer(wx.HORIZONTAL)
        info_left = StaticBoxSizer(
            self, wx.ID_ANY, label=_("Status"), orientation=wx.HORIZONTAL
        )
        info_left.Add(self.text_status, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_connection.Add(info_left, 1, wx.EXPAND, 0)

        info_right = StaticBoxSizer(
            self, wx.ID_ANY, label=_("Connection"), orientation=wx.HORIZONTAL
        )
        label_8 = wxStaticText(self, wx.ID_ANY, _("Address"))
        info_right.Add(label_8, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        info_right.Add(self.text_ip_host, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        info_right.AddSpacer(20)
        label_9 = wxStaticText(self, wx.ID_ANY, _("Port"))
        info_right.Add(label_9, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        info_right.Add(self.text_port, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_connection.Add(info_right, 2, wx.EXPAND, 0)
        connection_controller.Add(sizer_connection, 0, wx.EXPAND, 0)

        sizer_main.Add(connection_controller, 0, wx.EXPAND, 0)
        buffer_sizer = StaticBoxSizer(
            self, wx.ID_ANY, label=_("Buffer"), orientation=wx.VERTICAL
        )
        buffer_sizer.Add(self.gauge_buffer, 0, wx.EXPAND, 0)

        label_12 = wxStaticText(self, wx.ID_ANY, _("Buffer Size: "))
        total_write_buffer = wx.BoxSizer(wx.HORIZONTAL)
        left_buffer = wx.BoxSizer(wx.HORIZONTAL)
        right_buffer = wx.BoxSizer(wx.HORIZONTAL)
        left_buffer.Add(label_12, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        left_buffer.Add(self.text_buffer_length, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        total_write_buffer.Add(left_buffer, 1, wx.EXPAND, 0)

        label_13 = wxStaticText(self, wx.ID_ANY, _("Max Buffer Size:"))
        right_buffer.Add(label_13, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        right_buffer.Add(self.text_buffer_max, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        total_write_buffer.Add(right_buffer, 1, wx.EXPAND, 0)
        buffer_sizer.Add(total_write_buffer, 0, wx.EXPAND, 0)

        sizer_main.Add(buffer_sizer, 0, wx.EXPAND, 0)
        self.Layout()
        # end wxGlade

    def window_open(self):
        self.text_ip_host.SetValue(str(self.service.address))
        self.text_port.SetValue(str(self.service.port))
        self.text_buffer_max.SetValue("0")
        self.text_buffer_length.SetValue("0")
        self.on_network_update()

    @signal_listener("network_update")
    def on_network_update(self, origin=None, *args):
        try:
            if not self.service.networked:
                self.button_device_connect.Enable(False)
            else:
                self.button_device_connect.Enable(True)
        except AttributeError:
            pass

    @signal_listener("tcp;status")
    def on_tcp_status(self, origin, state):
        self.text_status.SetValue(str(state))
        self.state = state
        if state in ["uninitialized", "disconnected"]:
            self.button_device_connect.SetBackgroundColour("#ffff00")
            self.button_device_connect.SetLabel(_("Connect"))
            self.button_device_connect.SetBitmap(
                icons8_disconnected.GetBitmap(
                    use_theme=False, resize=get_default_icon_size(self.context)
                )
            )
            self.button_device_connect.Enable()
        elif state == "connected":
            self.button_device_connect.SetBackgroundColour("#00ff00")
            self.button_device_connect.SetLabel(_("Disconnect"))
            self.button_device_connect.SetBitmap(
                icons8_connected.GetBitmap(
                    use_theme=False, resize=get_default_icon_size(self.context)
                )
            )
            self.button_device_connect.Enable()

    @signal_listener("tcp;buffer")
    def on_tcp_buffer(self, origin, status):
        self.text_buffer_length.SetValue(str(status))
        if self.max < status:
            self.max = status
            self.text_buffer_max.SetValue(str(status))
            self.gauge_buffer.SetRange(self.max)
        self.gauge_buffer.SetValue(min(status, self.gauge_buffer.GetRange()))

    def on_tcp_write(self, origin, status):
        self.text_port.SetValue(str(status))

    def on_button_start_connection(self, event):  # wxGlade: Controller.<event_handler>
        if self.service.tcp is not None:
            if self.state == "connected":
                self.service.tcp.disconnect()
            else:
                self.service.tcp.connect()

    @staticmethod
    def submenu():
        return "Device-Control", "TCP Controller"

    @staticmethod
    def helptext():
        return _("Display the TCP communication controller window")
