#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.0 on Thu Feb  3 06:49:54 2022
#

import wx

_ = wx.GetTranslation

from meerk40t.gui.icons import icons8_connected_50, icons8_disconnected_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener


class SerialControllerPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: SerialControllerPanel.__init__
        self.service = context
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        self.state = None
        self.button_device_connect = wx.Button(self, wx.ID_ANY, "Connection")
        self.button_device_connect.SetBackgroundColour(wx.Colour(102, 255, 102))
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
            "Force connection/disconnection from the device."
        )
        self.button_device_connect.SetBitmap(
            icons8_connected_50.GetBitmap(use_theme=False)
        )
        sizer_1.Add(self.button_device_connect, 0, wx.EXPAND, 0)

        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize((483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)

        self.data_exchange = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        sizer_1.Add(self.data_exchange, 1, wx.EXPAND, 0)

        self.gcode_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.gcode_text.SetFocus()
        sizer_1.Add(self.gcode_text, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_1)

        self.Layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect
        )
        self.Bind(wx.EVT_TEXT_ENTER, self.on_gcode_enter, self.gcode_text)
        # end wxGlade

    def on_button_start_connection(
        self, event
    ):  # wxGlade: SerialControllerPanel.<event_handler>
        if self.state == "connected":
            self.service.controller.stop()
        else:
            self.service.controller.start()

    def on_gcode_enter(self, event):  # wxGlade: SerialControllerPanel.<event_handler>
        self.service(f"gcode {self.gcode_text.GetValue()}")
        self.gcode_text.Clear()

    def update_sent(self, text):
        text = "<--" + text + "\n"
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text))
        else:
            self.update_text_gui(str(text))

    def update_recv(self, text):
        text = "-->\t" + text + "\n"
        if not wx.IsMainThread():
            wx.CallAfter(self.update_text_gui, str(text))
        else:
            self.update_text_gui(str(text))

    def update_text_gui(self, text):
        self.data_exchange.AppendText(text)

    def on_serial_status(self, origin, state):
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


class SerialController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(499, 357, *args, **kwds)
        self.service = self.context.device
        self.SetTitle("SerialController")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)

        self.serial_panel = SerialControllerPanel(self, wx.ID_ANY, context=self.service)
        self.Layout()
        # end wxGlade

    @signal_listener("serial;status")
    def on_serial_status(self, origin, state):
        self.serial_panel.on_serial_status(origin, state)

    def window_open(self):
        self.context.channel(f"send-{self.service.com_port.lower()}").watch(
            self.serial_panel.update_sent
        )
        self.context.channel(f"recv-{self.service.com_port.lower()}").watch(
            self.serial_panel.update_recv
        )

    def window_close(self):
        # TODO: Can be wrong if we start the window then change com ports.
        self.context.channel(f"send-{self.service.com_port.lower()}").unwatch(
            self.serial_panel.update_sent
        )
        self.context.channel(f"recv-{self.service.com_port.lower()}").unwatch(
            self.serial_panel.update_recv
        )

    @staticmethod
    def submenu():
        return _("Device-Control")
