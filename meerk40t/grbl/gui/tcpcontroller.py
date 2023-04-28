import wx

from meerk40t.gui.icons import icons8_connected_50, icons8_disconnected_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class TCPController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 170, *args, **kwds)
        self.button_device_connect = wx.Button(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self.text_status = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_ip_host = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER, check="empty"
        )
        self.text_port = TextCtrl(
            self, wx.ID_ANY, "", check="float", style=wx.TE_PROCESS_ENTER
        )
        self.gauge_buffer = wx.Gauge(self, wx.ID_ANY, 10)
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_buffer_max = wx.TextCtrl(self, wx.ID_ANY, "")

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

    def on_port_change(self):
        try:
            self.service.port = int(self.text_port.GetValue())
        except ValueError:
            pass

    def on_address_change(self):
        self.service.address = str(self.text_ip_host.GetValue())

    def __set_properties(self):
        # begin wxGlade: Controller.__set_properties
        self.SetTitle(_("TCP-Controller"))
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
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
            icons8_disconnected_50.GetBitmap(use_theme=False)
        )
        self.text_status.SetToolTip(_("Connection status"))
        self.text_ip_host.SetToolTip(_("IP/Host if the server computer"))
        self.text_port.SetToolTip(_("Port for tcp connection on the server computer"))
        self.text_buffer_length.SetMinSize((165, 23))
        self.text_buffer_length.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        self.text_buffer_max.SetMinSize((165, 23))
        self.text_buffer_max.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Controller.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        write_buffer = wx.BoxSizer(wx.HORIZONTAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, _("Status"))
        label_8 = wx.StaticText(self, wx.ID_ANY, _("Address"))
        label_9 = wx.StaticText(self, wx.ID_ANY, _("Port"))

        sizer_15.Add(label_7, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_15.Add(self.text_status, 11, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_15.Add(label_8, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_15.Add(self.text_ip_host, 11, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_15.Add((20, 20), 0, 0, 0)
        sizer_15.Add(label_9, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_15.Add(self.text_port, 11, wx.ALIGN_CENTER_VERTICAL, 0)

        connection_controller.Add(sizer_15, 0, 0, 0)

        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize((483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)
        sizer_1.Add(self.gauge_buffer, 0, wx.EXPAND, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, _("Buffer Size: "))
        write_buffer.Add(label_12, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        write_buffer.Add(self.text_buffer_length, 10, wx.ALIGN_CENTER_VERTICAL, 0)
        write_buffer.Add((20, 20), 0, 0, 0)
        label_13 = wx.StaticText(self, wx.ID_ANY, _("Max Buffer Size:"))
        write_buffer.Add(label_13, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        write_buffer.Add(self.text_buffer_max, 10, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_1.Add(write_buffer, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def window_open(self):
        self.text_ip_host.SetValue(str(self.service.address))
        self.text_port.SetValue(str(self.service.port))
        self.text_buffer_max.SetValue("0")
        self.text_buffer_length.SetValue("0")
        self.on_network_update()

    @signal_listener("interface_update")
    def on_network_update(self, origin=None, *args):
        self.button_device_connect.Enable(self.service.interface == "tcp")

    @signal_listener("tcp;status")
    def on_tcp_status(self, origin, state):
        self.text_status.SetValue(str(state))
        self.state = state
        if state == "uninitialized" or state == "disconnected":
            self.button_device_connect.SetBackgroundColour("#ffff00")
            self.button_device_connect.SetLabel(_("Connect"))
            self.button_device_connect.SetBitmap(
                icons8_disconnected_50.GetBitmap(use_theme=False)
            )
            self.button_device_connect.Enable()
        elif state == "connected":
            self.button_device_connect.SetBackgroundColour("#00ff00")
            self.button_device_connect.SetLabel(_("Disconnect"))
            self.button_device_connect.SetBitmap(
                icons8_connected_50.GetBitmap(use_theme=False)
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
        connection = self.service.controller.connection
        if connection is None:
            # No connection cannot do anything.
            return
        if self.state == "connected":
            connection.disconnect()
        else:
            connection.connect()

    @staticmethod
    def submenu():
        return ("Device-Control", "GRBL TCP Controller")
