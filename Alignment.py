import wx

from LaserCommandConstants import COMMAND_CUT
from icons import icons8_stop_50, icons8_resize_horizontal_50, icons8_resize_vertical_50


class Alignment(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: Alignment.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((382, 218))
        self.button_vertical_align = wx.BitmapButton(self, wx.ID_ANY, icons8_resize_vertical_50.GetBitmap())
        self.spin_vertical_distance = wx.SpinCtrl(self, wx.ID_ANY, "180", min=10, max=300)
        self.check_vertical_done = wx.CheckBox(self, wx.ID_ANY, "Vertical Alignment Finished")
        self.button_horizontal_align = wx.BitmapButton(self, wx.ID_ANY, icons8_resize_horizontal_50.GetBitmap())
        self.spin_horizontal_distance = wx.SpinCtrl(self, wx.ID_ANY, "180", min=10, max=330)
        self.check_horizontal_done = wx.CheckBox(self, wx.ID_ANY, "Horizontal Alignment Finished")
        self.button_square_align = wx.BitmapButton(self, wx.ID_ANY, icons8_stop_50.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_vertical_align, self.button_vertical_align)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_vertical_distance, self.spin_vertical_distance)
        self.Bind(wx.EVT_TEXT, self.on_spin_vertical_distance, self.spin_vertical_distance)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_vertical_distance, self.spin_vertical_distance)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_vertical_done, self.check_vertical_done)
        self.Bind(wx.EVT_BUTTON, self.on_button_horizontal_align, self.button_horizontal_align)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_horizontal_distance, self.spin_horizontal_distance)
        self.Bind(wx.EVT_TEXT, self.on_spin_horizontal_distance, self.spin_horizontal_distance)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_horizontal_distance, self.spin_horizontal_distance)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_horizontal_done, self.check_horizontal_done)
        self.Bind(wx.EVT_BUTTON, self.on_button_square_align, self.button_square_align)
        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.project = None

    def on_close(self, event):
        try:
            del self.project.windows["alignment"]
        except KeyError:
            pass
        self.project = None
        event.Skip()  # Call destroy as regular.

    def set_project(self, project):
        self.project = project

    def __set_properties(self):
        # begin wxGlade: Alignment.__set_properties
        self.SetTitle("Alignment")
        self.button_vertical_align.SetSize(self.button_vertical_align.GetBestSize())
        self.button_horizontal_align.Enable(False)
        self.button_horizontal_align.SetSize(self.button_horizontal_align.GetBestSize())
        self.spin_horizontal_distance.Enable(False)
        self.check_horizontal_done.Enable(False)
        self.button_square_align.Enable(False)
        self.button_square_align.SetSize(self.button_square_align.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Alignment.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3.Add(self.button_vertical_align, 0, 0, 0)
        sizer_3.Add(self.spin_vertical_distance, 0, 0, 0)
        sizer_3.Add(self.check_vertical_done, 0, 0, 0)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_2.Add(self.button_horizontal_align, 0, 0, 0)
        sizer_2.Add(self.spin_horizontal_distance, 0, 0, 0)
        sizer_2.Add(self.check_horizontal_done, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        sizer_1.Add(self.button_square_align, 0, 0, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_button_vertical_align(self, event):  # wxGlade: Alignment.<event_handler>
        writer = self.project.writer
        writer.home()
        writer.set_speed(35)
        writer.set_power(100.0)  # out of 1000
        writer.to_compact_mode()
        writer.down()
        y = round(self.spin_vertical_distance.GetValue() * 39.3701)
        writer.command(COMMAND_CUT, (0, y))
        writer.to_default_mode()

    def on_spin_vertical_distance(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_check_vertical_done(self, event):  # wxGlade: Alignment.<event_handler>
        if self.check_vertical_done.GetValue():
            self.button_horizontal_align.Enable()
            self.spin_horizontal_distance.Enable()
            self.check_horizontal_done.Enable()

    def on_button_horizontal_align(self, event):  # wxGlade: Alignment.<event_handler>
        writer = self.project.writer
        writer.home()
        writer.set_speed(35)
        writer.set_power(100.0)  # out of 1000
        writer.to_compact_mode()
        writer.down()
        x = round(self.spin_vertical_distance.GetValue() * 39.3701)
        writer.command(COMMAND_CUT, (x, 0))
        writer.to_default_mode()

    def on_spin_horizontal_distance(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_check_horizontal_done(self, event):  # wxGlade: Alignment.<event_handler>
        if self.check_horizontal_done.GetValue():
            self.button_square_align.Enable()

    def on_button_square_align(self, event):  # wxGlade: Alignment.<event_handler>
        writer = self.project.writer
        writer.home()
        writer.set_speed(35)
        writer.set_power(100.0)  # out of 1000
        writer.to_compact_mode()
        writer.down()
        y = round(self.spin_vertical_distance.GetValue() * 39.3701)
        x = round(self.spin_vertical_distance.GetValue() * 39.3701)

        writer.command(COMMAND_CUT, (0, y))
        writer.command(COMMAND_CUT, (x, y))
        writer.command(COMMAND_CUT, (x, 0))
        writer.command(COMMAND_CUT, (0, 0))
        writer.to_default_mode()

# end of class Alignment
