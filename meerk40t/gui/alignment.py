import wx

from ..kernel import Module
from .icons import (
    icons8_resize_horizontal_50,
    icons8_resize_vertical_50,
    icons8_info_50,
    icons8_laser_beam_hazard_50,
    icons8_end_50,
)
from ..device.lasercommandconstants import (
    COMMAND_HOME,
    COMMAND_MODE_RAPID,
    COMMAND_SET_ABSOLUTE,
    COMMAND_SET_SPEED,
    COMMAND_SET_POWER,
    COMMAND_MODE_PROGRAM,
    COMMAND_LASER_ON,
    COMMAND_MOVE,
    COMMAND_UNLOCK,
    COMMAND_WAIT_FINISH,
    COMMAND_WAIT,
    COMMAND_LASER_OFF,
    COMMAND_CUT,
)

_ = wx.GetTranslation


class Alignment(wx.Frame, Module):
    def __init__(self, context, path, parent, *args, **kwds):
        # begin wxGlade: Alignment.__init__
        wx.Frame.__init__(
            self,
            parent,
            -1,
            "",
            style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL,
        )
        Module.__init__(self, context, path)
        self.SetSize((631, 365))

        self.spin_vertical_distance = wx.SpinCtrl(
            self, wx.ID_ANY, "180", min=10, max=400
        )
        self.spin_vertical_power = wx.SpinCtrl(self, wx.ID_ANY, "180", min=10, max=500)
        self.check_vertical_done = wx.CheckBox(
            self, wx.ID_ANY, _("Vertical Alignment Finished")
        )
        self.spin_horizontal_distance = wx.SpinCtrl(
            self, wx.ID_ANY, "220", min=10, max=400
        )
        self.spin_horizontal_power = wx.SpinCtrl(
            self, wx.ID_ANY, "180", min=10, max=500
        )
        self.check_horizontal_done = wx.CheckBox(
            self, wx.ID_ANY, _("Horizontal Alignment Finished")
        )
        self.slider_square_power = wx.Slider(
            self, wx.ID_ANY, 200, 0, 1000, style=wx.SL_HORIZONTAL | wx.SL_LABELS
        )

        self.button_vertical_align_nearfar = wx.BitmapButton(
            self, wx.ID_ANY, icons8_resize_vertical_50.GetBitmap()
        )
        self.button_horizontal_align_nearfar = wx.BitmapButton(
            self, wx.ID_ANY, icons8_resize_horizontal_50.GetBitmap()
        )
        self.button_vertical_align = wx.BitmapButton(
            self, wx.ID_ANY, icons8_resize_vertical_50.GetBitmap()
        )
        self.button_horizontal_align = wx.BitmapButton(
            self, wx.ID_ANY, icons8_resize_horizontal_50.GetBitmap()
        )
        self.button_square_align_4_corner = wx.BitmapButton(
            self, wx.ID_ANY, icons8_end_50.GetBitmap()
        )
        self.button_square_align = wx.BitmapButton(
            self, wx.ID_ANY, icons8_end_50.GetBitmap()
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_vertical_align_nearfar,
            self.button_vertical_align_nearfar,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_vertical_align, self.button_vertical_align
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_vertical_distance, self.spin_vertical_distance
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_vertical_distance, self.spin_vertical_distance
        )
        self.Bind(
            wx.EVT_TEXT_ENTER,
            self.on_spin_vertical_distance,
            self.spin_vertical_distance,
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_vertical_power, self.spin_vertical_power
        )
        self.Bind(wx.EVT_TEXT, self.on_spin_vertical_power, self.spin_vertical_power)
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_spin_vertical_power, self.spin_vertical_power
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_vertical_done, self.check_vertical_done
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_horizontal_align_nearfar,
            self.button_horizontal_align_nearfar,
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_horizontal_align, self.button_horizontal_align
        )
        self.Bind(
            wx.EVT_SPINCTRL,
            self.on_spin_horizontal_distance,
            self.spin_horizontal_distance,
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_horizontal_distance, self.spin_horizontal_distance
        )
        self.Bind(
            wx.EVT_TEXT_ENTER,
            self.on_spin_horizontal_distance,
            self.spin_horizontal_distance,
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_horizontal_power, self.spin_horizontal_power
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_horizontal_power, self.spin_horizontal_power
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_spin_horizontal_power, self.spin_horizontal_power
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_horizontal_done, self.check_horizontal_done
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_square_align_4_corners,
            self.button_square_align_4_corner,
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_square_align, self.button_square_align)
        self.Bind(
            wx.EVT_COMMAND_SCROLL,
            self.on_slider_square_power_change,
            self.slider_square_power,
        )
        self.Bind(
            wx.EVT_COMMAND_SCROLL_CHANGED,
            self.on_slider_square_power_change,
            self.slider_square_power,
        )

        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
            return
        else:
            self.state = 5
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, *args, **kwargs):
        self.context.close(self.name)
        self.Show()

    def finalize(self, *args, **kwargs):
        try:
            self.Close()
        except RuntimeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_hazard_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Alignment.__set_properties
        self.SetTitle(_("Alignment."))
        self.button_vertical_align_nearfar.SetToolTip(
            _("Perform vertical near-far alignment test")
        )
        self.button_vertical_align_nearfar.SetSize(
            self.button_vertical_align_nearfar.GetBestSize()
        )
        self.button_vertical_align.SetBackgroundColour(wx.Colour(128, 128, 128))
        self.button_vertical_align.SetToolTip(
            _("Perform a vertical line alignment test")
        )
        self.button_vertical_align.SetSize(self.button_vertical_align.GetBestSize())
        self.spin_vertical_distance.SetMinSize((110, 23))
        self.spin_vertical_distance.SetToolTip(
            _("How far down should we move to test?")
        )
        self.spin_vertical_power.SetMinSize((110, 23))
        self.spin_vertical_power.SetToolTip(
            _(
                "Heavily misaligned mirrors will need more power to see the line. Once you can see the line. Turn this down."
            )
        )
        self.check_vertical_done.SetToolTip(_("We are done with vertical alignment."))
        self.button_horizontal_align_nearfar.SetToolTip(
            _("Perform horizontal near-far alignment test")
        )
        self.button_horizontal_align_nearfar.Enable(False)
        self.button_horizontal_align_nearfar.SetSize(
            self.button_horizontal_align_nearfar.GetBestSize()
        )
        self.button_horizontal_align.SetBackgroundColour(wx.Colour(128, 128, 128))
        self.button_horizontal_align.SetToolTip(
            _("Perform horizontal line alignment test")
        )
        self.button_horizontal_align.Enable(False)
        self.button_horizontal_align.SetSize(self.button_horizontal_align.GetBestSize())
        self.spin_horizontal_distance.SetMinSize((110, 23))
        self.spin_horizontal_distance.SetToolTip(
            _("How far right should we move to test?")
        )
        self.spin_horizontal_distance.Enable(False)
        self.spin_horizontal_power.SetMinSize((110, 23))
        self.spin_horizontal_power.SetToolTip(
            _(
                "Heavily misaligned mirrors will need more power to see the line. Once you can see the line. Turn this down."
            )
        )
        self.spin_horizontal_power.Enable(False)
        self.check_horizontal_done.Enable(False)
        self.button_square_align_4_corner.SetToolTip(
            _("Perform 4 corners confirmation test")
        )
        self.button_square_align_4_corner.Enable(False)
        self.button_square_align_4_corner.SetSize(
            self.button_square_align_4_corner.GetBestSize()
        )
        self.button_square_align.SetBackgroundColour(wx.Colour(128, 128, 128))
        self.button_square_align.SetToolTip(_("Perform square confirmation test"))
        self.button_square_align.Enable(False)
        self.button_square_align.SetSize(self.button_square_align.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        text_horizontal_advise = wx.StaticText(
            self,
            wx.ID_ANY,
            _(
                "You are not centering. The misalignment increases over distance.\nGet the beam to hit the same point regardless of distance. (Usually not the center)\nAll beam points should overlap at exactly 1 point, when misalignment is zero.\nThe overlap point should be nearer to the close point. Aim for that. Repeat.\n"
            ),
        )
        text_horizontal_advise.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        sizer_1.Add(text_horizontal_advise, 0, 0, 0)
        sizer_3.Add(self.button_vertical_align_nearfar, 0, 0, 0)
        sizer_3.Add((20, 20), 0, 0, 0)
        sizer_3.Add(self.button_vertical_align, 0, 0, 0)
        sizer_4.Add(self.spin_vertical_distance, 0, 0, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Testing width in mm"))
        label_1.SetMinSize((110, 16))
        sizer_4.Add(label_1, 0, 0, 0)
        sizer_3.Add(sizer_4, 1, 0, 0)
        sizer_3.Add((40, 20), 0, 0, 0)
        sizer_5.Add(self.spin_vertical_power, 0, 0, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Testing power"))
        sizer_5.Add(label_2, 0, 0, 0)
        sizer_3.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_3.Add(self.check_vertical_done, 0, 0, 0)
        sizer_1.Add(sizer_3, 1, 0, 0)
        text_vertical_advise = wx.StaticText(
            self, wx.ID_ANY, _("Get the movement of the beam going right to overlap. ")
        )
        sizer_1.Add(text_vertical_advise, 0, 0, 0)
        sizer_2.Add(self.button_horizontal_align_nearfar, 0, 0, 0)
        sizer_2.Add((20, 20), 0, 0, 0)
        sizer_2.Add(self.button_horizontal_align, 0, 0, 0)
        sizer_6.Add(self.spin_horizontal_distance, 0, 0, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, _("Testing height in mm"))
        sizer_6.Add(label_3, 0, 0, 0)
        sizer_2.Add(sizer_6, 1, 0, 0)
        sizer_2.Add((40, 20), 0, 0, 0)
        sizer_7.Add(self.spin_horizontal_power, 0, 0, 0)
        label_4 = wx.StaticText(self, wx.ID_ANY, _("Testing power"))
        sizer_7.Add(label_4, 0, 0, 0)
        sizer_2.Add(sizer_7, 1, wx.EXPAND, 0)
        sizer_2.Add(self.check_horizontal_done, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, 0, 0)
        sizer_8.Add(self.button_square_align_4_corner, 0, 0, 0)
        sizer_8.Add((20, 20), 0, 0, 0)
        sizer_8.Add(self.button_square_align, 0, 0, 0)
        sizer_8.Add(self.slider_square_power, 0, wx.EXPAND, 0)
        sizer_1.Add(sizer_8, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_button_vertical_align_nearfar(
        self, event
    ):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.vertical_near_far_test)

    def on_button_vertical_align(self, event):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.vertical_test)

    def on_spin_vertical_distance(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_spin_vertical_power(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_check_vertical_done(self, event):  # wxGlade: Alignment.<event_handler>
        self.spin_horizontal_power.Enable(self.check_vertical_done.GetValue())
        self.button_horizontal_align.Enable(self.check_vertical_done.GetValue())
        self.button_horizontal_align_nearfar.Enable(self.check_vertical_done.GetValue())
        self.spin_horizontal_distance.Enable(self.check_vertical_done.GetValue())
        self.check_horizontal_done.Enable(self.check_vertical_done.GetValue())

    def on_button_horizontal_align_nearfar(
        self, event
    ):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.horizontal_near_far_test)

    def on_button_horizontal_align(self, event):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.horizontal_test)

    def on_spin_horizontal_distance(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_spin_horizontal_power(self, event):  # wxGlade: Alignment.<event_handler>
        pass

    def on_check_horizontal_done(self, event):  # wxGlade: Alignment.<event_handler>
        self.button_square_align.Enable(self.check_horizontal_done.GetValue())
        self.button_square_align_4_corner.Enable(self.check_horizontal_done.GetValue())

    def on_slider_square_power_change(
        self, event
    ):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.set_power(self.slider_square_power.GetValue())

    def on_button_square_align_4_corners(
        self, event
    ):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.square4_test)

    def on_button_square_align(self, event):  # wxGlade: Alignment.<event_handler>
        spooler = self.context.spooler
        spooler.job(self.square_test)

    def square_test(self):
        yield COMMAND_HOME
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_SET_SPEED, 35
        yield COMMAND_SET_POWER, self.slider_square_power.GetValue()
        yield COMMAND_MODE_PROGRAM
        yield COMMAND_LASER_ON
        y = round(self.spin_vertical_distance.GetValue() * 39.3701)
        x = round(self.spin_horizontal_distance.GetValue() * 39.3701)
        yield COMMAND_MOVE, 0, y
        yield COMMAND_MOVE, x, y
        yield COMMAND_MOVE, x, 0
        yield COMMAND_MOVE, 0, 0
        yield COMMAND_MODE_RAPID
        yield COMMAND_UNLOCK

    def dotfield_test(self):
        yield COMMAND_HOME
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        y_max = round(self.spin_vertical_distance.GetValue() * 39.3701)
        x_max = round(self.spin_horizontal_distance.GetValue() * 39.3701)
        y_val = self.context.current_y
        x_val = self.context.current_x
        y_step = round(5 * 39.3701)

        while y_val < y_max:
            yield COMMAND_WAIT_FINISH
            yield COMMAND_LASER_ON
            yield COMMAND_WAIT, 0.001
            yield COMMAND_LASER_OFF
            yield COMMAND_MOVE, x_val, y_val
            y_val += y_step

    def horizontal_test(self):
        yield COMMAND_HOME
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_SET_SPEED, 35
        yield COMMAND_SET_POWER, self.spin_horizontal_power.GetValue()
        yield COMMAND_MODE_PROGRAM
        x = round(self.spin_horizontal_distance.GetValue() * 39.3701)
        yield COMMAND_CUT, x, 0
        yield COMMAND_MODE_RAPID
        yield COMMAND_UNLOCK

    def vertical_test(self):
        yield COMMAND_HOME
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_SET_SPEED, 35
        yield COMMAND_SET_POWER, self.spin_vertical_power.GetValue()
        yield COMMAND_MODE_PROGRAM
        y = round(self.spin_vertical_distance.GetValue() * 39.3701)
        yield COMMAND_CUT, 0, y
        yield COMMAND_MODE_RAPID
        yield COMMAND_UNLOCK

    def vertical_near_far_test(self):
        yield COMMAND_HOME
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MODE_RAPID
        y_max = round(self.spin_vertical_distance.GetValue() * 39.3701)
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.2
        yield COMMAND_LASER_OFF
        yield COMMAND_MODE_RAPID
        yield COMMAND_MOVE, 0, y_max
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.2
        yield COMMAND_LASER_OFF

    def horizontal_near_far_test(self):
        yield COMMAND_HOME
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MODE_RAPID
        x_max = round(self.spin_horizontal_distance.GetValue() * 39.3701)
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.2
        yield COMMAND_LASER_OFF
        yield COMMAND_MODE_RAPID
        yield COMMAND_MOVE, x_max, 0
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.2
        yield COMMAND_LASER_OFF

    def square4_test(self):
        yield COMMAND_HOME
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MODE_RAPID
        y_max = round(self.spin_vertical_distance.GetValue() * 39.3701)
        x_max = round(self.spin_horizontal_distance.GetValue() * 39.3701)
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.1
        yield COMMAND_LASER_OFF

        yield COMMAND_MOVE, 0, y_max
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.1
        yield COMMAND_LASER_OFF

        yield COMMAND_MOVE, x_max, y_max
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.1
        yield COMMAND_LASER_OFF

        yield COMMAND_MOVE, x_max, 0
        yield COMMAND_WAIT_FINISH
        yield COMMAND_LASER_ON
        yield COMMAND_WAIT, 0.1
        yield COMMAND_LASER_OFF
