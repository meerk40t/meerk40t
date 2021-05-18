
import wx

from meerk40t.core.output import TCPOutput
from meerk40t.gui.icons import icons8_connected_50, icons8_disconnected_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class TCPController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 170, *args, **kwds)
        self.spooler, self.input_driver, self.output = self.context.registered["device/%s" % self.context.root.active]
        self.button_device_connect = wx.Button(self, wx.ID_ANY, "Connection")
        self.text_status = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ip_host = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_port = wx.TextCtrl(self, wx.ID_ANY, "")
        self.gauge_buffer = wx.Gauge(self, wx.ID_ANY, 10)
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_buffer_max = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect)
        # end wxGlade
        self.max = 0
        self.state = None

    def __set_properties(self):
        # begin wxGlade: Controller.__set_properties
        self.SetTitle("TCP-Controller")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
        self.button_device_connect.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_device_connect.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_device_connect.SetToolTip("Force connection/disconnection from the device.")
        self.button_device_connect.SetBitmap(icons8_disconnected_50.GetBitmap())
        self.text_status.SetToolTip("Connection status")
        self.text_ip_host.SetToolTip("IP/Host if the server computer")
        self.text_port.SetToolTip("Port for tcp connection on the server computer")
        self.text_buffer_length.SetMinSize((165, 23))
        self.text_buffer_length.SetToolTip("Current number of bytes in the write buffer.")
        self.text_buffer_max.SetMinSize((165, 23))
        self.text_buffer_max.SetToolTip("Current number of bytes in the write buffer.")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Controller.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        write_buffer = wx.BoxSizer(wx.HORIZONTAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, "Status")
        sizer_15.Add(label_7, 1, 0, 0)
        sizer_15.Add(self.text_status, 11, 0, 0)
        label_8 = wx.StaticText(self, wx.ID_ANY, "Address")
        sizer_15.Add(label_8, 1, 0, 0)
        sizer_15.Add(self.text_ip_host, 11, 0, 0)
        sizer_15.Add((20, 20), 0, 0, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "Port")
        sizer_15.Add(label_9, 1, 0, 0)
        sizer_15.Add(self.text_port, 11, 0, 0)
        connection_controller.Add(sizer_15, 0, 0, 0)
        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize((483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)
        sizer_1.Add(self.gauge_buffer, 0, wx.EXPAND, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, "Buffer Size: ")
        write_buffer.Add(label_12, 0, 0, 0)
        write_buffer.Add(self.text_buffer_length, 10, 0, 0)
        write_buffer.Add((20, 20), 0, 0, 0)
        label_13 = wx.StaticText(self, wx.ID_ANY, "Max Buffer Size:")
        write_buffer.Add(label_13, 0, 0, 0)
        write_buffer.Add(self.text_buffer_max, 10, 0, 0)
        sizer_1.Add(write_buffer, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def window_open(self):
        # self.context.listen("tcp;write", self.on_tcp_write)
        self.context.listen("tcp;status", self.on_tcp_status)
        self.context.listen("tcp;buffer", self.on_tcp_buffer)
        self.text_ip_host.SetValue(str(self.output.address))
        self.text_port.SetValue(str(self.output.port))
        self.text_buffer_max.SetValue('0')
        self.text_buffer_length.SetValue('0')

    def window_close(self):
        # self.context.unlisten("tcp;write", self.on_tcp_write)
        self.context.unlisten("tcp;status", self.on_tcp_status)
        self.context.unlisten("tcp;buffer", self.on_tcp_buffer)

    def on_tcp_status(self, origin, state):
        self.text_status.SetValue(str(state))
        self.state = state
        if state == "uninitialized" or state == "disconnected":
            self.button_device_connect.SetBackgroundColour("#ffff00")
            self.button_device_connect.SetLabel(_("Connect"))
            self.button_device_connect.SetBitmap(icons8_disconnected_50.GetBitmap())
            self.button_device_connect.Enable()
        elif state == "connected":
            self.button_device_connect.SetBackgroundColour("#00ff00")
            self.button_device_connect.SetLabel(_("Disconnect"))
            self.button_device_connect.SetBitmap(icons8_connected_50.GetBitmap())
            self.button_device_connect.Enable()

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
        if isinstance(self.output, TCPOutput):
            if self.state == "connected":
                self.output.disconnect()
            else:
                self.output.connect()
