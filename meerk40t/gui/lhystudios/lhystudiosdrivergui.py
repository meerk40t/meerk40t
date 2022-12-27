# -*- coding: ISO-8859-1 -*-

import wx

from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation

MILS_IN_MM = 39.3701


class LhystudiosConfigurationPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.bed_dim = self.context.root
        self.bed_dim.setting(int, "bed_width", 310)
        self.bed_dim.setting(int, "bed_height", 210)
        self.combobox_board = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["M2", "B2", "M", "M1", "A", "B", "B1"],
            style=wx.CB_READONLY,
        )
        self.checkbox_fix_speeds = wx.CheckBox(
            self, wx.ID_ANY, _("Fix rated to actual speed")
        )
        self.checkbox_twitchfull = wx.CheckBox(
            self, wx.ID_ANY, _("Revert to legacy vector twitching")
        )
        self.checkbox_alternative_raster = wx.CheckBox(
            self, wx.ID_ANY, _("Alternative Rastering (BETA)")
        )
        self.checkbox_flip_x = wx.CheckBox(self, wx.ID_ANY, _("Flip X"))
        self.checkbox_home_right = wx.CheckBox(self, wx.ID_ANY, _("Home Right"))
        self.checkbox_flip_y = wx.CheckBox(self, wx.ID_ANY, _("Flip Y"))
        self.checkbox_home_bottom = wx.CheckBox(self, wx.ID_ANY, _("Home Bottom"))
        self.checkbox_swap_xy = wx.CheckBox(self, wx.ID_ANY, _("Swap X and Y"))
        self.checkbox_strict = wx.CheckBox(
            self, wx.ID_ANY, _("Strict Programmed Speed Mode")
        )
        self.spin_home_x = wx.SpinCtrl(self, wx.ID_ANY, "0.0", min=-50000, max=50000)
        self.spin_home_y = wx.SpinCtrl(self, wx.ID_ANY, "0.0", min=-50000, max=50000)
        self.button_home_by_current = wx.Button(self, wx.ID_ANY, _("Set Current"))
        self.checkbox_plot_shift = wx.CheckBox(self, wx.ID_ANY, _("Pulse Grouping"))
        self.checkbox_random_ppi = wx.CheckBox(self, wx.ID_ANY, _("Randomize PPI"))
        self.checkbox_limit_buffer = wx.CheckBox(
            self, wx.ID_ANY, _("Limit Write Buffer")
        )
        self.text_buffer_length = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.spin_packet_buffer_max = wx.SpinCtrl(
            self, wx.ID_ANY, "1500", min=1, max=1000000
        )
        self.checkbox_autolock = wx.CheckBox(
            self, wx.ID_ANY, _("Leave rail locked after burn")
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combobox_boardtype, self.combobox_board)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_fix_speeds, self.checkbox_fix_speeds)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_x, self.checkbox_flip_x)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_right, self.checkbox_home_right)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_flip_y, self.checkbox_flip_y)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_bottom, self.checkbox_home_bottom)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_swapxy, self.checkbox_swap_xy)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_strict, self.checkbox_strict)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_twitchfull, self.checkbox_twitchfull)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_alt_raster, self.checkbox_alternative_raster
        )
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_TEXT, self.spin_on_home_x, self.spin_home_x)
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_home_y, self.spin_home_y)
        self.Bind(wx.EVT_TEXT, self.spin_on_home_y, self.spin_home_y)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_set_home_current, self.button_home_by_current
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_pulse_shift, self.checkbox_plot_shift)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_random_ppi, self.checkbox_random_ppi)
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_limit_packet_buffer,
            self.checkbox_limit_buffer,
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT,
            self.on_spin_packet_buffer_max,
            self.spin_packet_buffer_max,
        )
        self.Bind(wx.EVT_CHECKBOX, self.on_check_autolock, self.checkbox_autolock)
        # end wxGlade
        # end wxGlade
        self.Bind(
            wx.EVT_KEY_DOWN,
            lambda e: self.context.console("webhelp help\n")
            if e.GetKeyCode() == wx.WXK_F1
            else None,
            self,
        )
        self.set_widgets()

    def __set_properties(self):
        self.combobox_board.SetToolTip(
            _("Select the board to use. This has an effects the speedcodes used.")
        )
        self.combobox_board.SetSelection(0)
        self.checkbox_fix_speeds.SetToolTip(
            _(
                "Lhystudios speeds are approximately 92% of the speed requested. "
                + "This option applies a correcting factor so that actual burn speeds are the same as in the Operation. "
            )
        )
        self.checkbox_flip_x.SetToolTip(
            _("Flip the Right and Left commands sent to the controller")
        )
        self.checkbox_home_right.SetToolTip(
            _("Indicates the device Home is on the right")
        )
        self.checkbox_flip_y.SetToolTip(
            _("Flip the Top and Bottom commands sent to the controller")
        )
        self.checkbox_home_bottom.SetToolTip(
            _("Indicates the device Home is on the bottom")
        )
        self.checkbox_swap_xy.SetToolTip(
            _("Swaps the X and Y axis. This happens before the FlipX and FlipY.")
        )
        self.checkbox_strict.SetToolTip(
            _(
                "Forces the device to enter and exit programmed speed mode from the same direction. "
                + "This may prevent devices like the M2-V4 and earlier from having issues. Not typically needed."
            )
        )
        self.checkbox_alternative_raster.SetToolTip(
            _(
                "This is a change we would like you to try because it opens up possibilities for future enhancements. "
                + "We do not believe it will create any issues, but in case it does we are giving you the choice to switch it on or not. "
            )
            + "\n\n"
            + _(
                "If this works OK for you please leave it on. "
                + "If you have any problems, we would very much appreciate it "
                + "if you could leave a comment on Github issue #{issue}."
            ).format(issue=773)
        )
        self.checkbox_twitchfull.SetToolTip(
            _(
                "Twitching is an unnecessary move in an unneeded direction at the start and end of travel moves between vector burns. "
                "It is most noticeable when you are doing a number of small burns (e.g. stitch holes in leather). "
                "A revised twitchless mode is now default in 0.7.6 or later which results in a noticeable faster travel time. "
                "This option allows you to revert to the previous mode if you experience problems."
            )
        )
        self.spin_home_x.SetMinSize((80, 23))
        self.spin_home_x.SetToolTip(_("Translate Home X"))
        self.spin_home_y.SetMinSize((80, 23))
        self.spin_home_y.SetToolTip(_("Translate Home Y"))
        self.button_home_by_current.SetToolTip(
            _("Set Home Position based on the current position")
        )
        self.checkbox_plot_shift.SetToolTip(
            "\n\n".join(
                (
                    _(
                        "Pulse Grouping is an alternative means of reducing the incidence of stuttering, allowing you potentially to burn at higher speeds. "
                        + "This setting is a global equivalent to the Pulse Grouping option in Operation Properties."
                    ),
                    _(
                        "It works by swapping adjacent on or off bits to group on and off together and reduce the number of switches "
                        + "e.g. instead of 1010 it will burn 1100. "
                        + 'Because the laser beam is overlapping, and because a bit is only moved at most 1/1000", '
                        + "the difference should not be visible even under magnification."
                    ),
                    _(
                        "The Pulse Grouping option in Operations are set for that operation before the job is spooled "
                        + "and cannot be changed during the burn, "
                        + "however this global Pulse Grouping option is checked as instructions are sent to the laser "
                        + "and can turned on and off during the burn process if needed."
                    ),
                    _(
                        "Because the changes are believed to be small enough to be undetectable, you may wish to leave this permanently checked."
                    ),
                )
            )
        )
        self.checkbox_random_ppi.SetToolTip(
            _("Rather than orderly PPI, we perform PPI based on a randomized average")
        )
        self.checkbox_random_ppi.Enable(False)
        self.checkbox_limit_buffer.SetToolTip(
            _(
                "Limit the write buffer to a certain amount. Permits on-the-fly command production."
            )
        )
        self.checkbox_limit_buffer.SetValue(1)
        self.text_buffer_length.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        self.spin_packet_buffer_max.SetToolTip(_("Current maximum write buffer limit."))
        self.checkbox_autolock.SetToolTip(
            _(
                "Leave the steppers energised and the rail locked after the burn has finished. "
                + "By default, if this option is not selected, the rail is unlocked at the end of the burn."
            )
        )
        self.checkbox_autolock.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        checkbox_border = (wx.TOP, 3)
        static_text_border = (wx.TOP, 4)
        # begin wxGlade: LhystudiosDriver.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_general = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("General Options:")), wx.HORIZONTAL
        )
        sizer_buffer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Write Buffer:")), wx.HORIZONTAL
        )
        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Pulse Planner:")), wx.HORIZONTAL
        )
        sizer_home = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Shift Home Position:")), wx.HORIZONTAL
        )
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_config = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Configuration:")), wx.HORIZONTAL
        )
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_17 = wx.BoxSizer(wx.VERTICAL)

        sizer_board = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Board Setup:")), wx.HORIZONTAL
        )
        sizer_board_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_board_2 = wx.BoxSizer(wx.VERTICAL)

        sizer_board_1.Add(self.combobox_board, 1, wx.EXPAND | wx.RIGHT, 1)
        sizer_board_1.Add(self.checkbox_fix_speeds, 0, *checkbox_border)
        sizer_board_1.Add(self.checkbox_strict, 0, *checkbox_border)

        sizer_board_2.Add(self.checkbox_twitchfull, 0, *checkbox_border)
        sizer_board_2.Add(self.checkbox_alternative_raster, 0, *checkbox_border)

        sizer_board.Add(sizer_board_1, 1, 0, 0)
        sizer_board.Add(sizer_board_2, 1, wx.EXPAND | wx.LEFT, 10)

        sizer_main.Add(sizer_board, 1, wx.EXPAND, 0)
        sizer_17.Add(self.checkbox_flip_x, 0, *checkbox_border)
        sizer_17.Add(self.checkbox_home_right, 0, *checkbox_border)
        sizer_config.Add(sizer_17, 1, wx.EXPAND, 0)
        sizer_16.Add(self.checkbox_flip_y, 0, *checkbox_border)
        sizer_16.Add(self.checkbox_home_bottom, 0, *checkbox_border)
        sizer_config.Add(sizer_16, 1, wx.EXPAND, 0)
        sizer_3.Add(self.checkbox_swap_xy, 0, *checkbox_border)
        sizer_config.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_config, 1, wx.EXPAND, 0)
        label_9 = wx.StaticText(self, wx.ID_ANY, "X ")
        sizer_4.Add(label_9, 0, *static_text_border)
        sizer_4.Add(self.spin_home_x, 0, 0, 0)
        label_12 = wx.StaticText(self, wx.ID_ANY, _("mils"))
        sizer_4.Add(label_12, 0, *static_text_border)
        sizer_home.Add(sizer_4, 1, wx.EXPAND, 0)
        label_10 = wx.StaticText(self, wx.ID_ANY, "Y ")
        sizer_2.Add(label_10, 0, *static_text_border)
        sizer_2.Add(self.spin_home_y, 0, 0, 0)
        label_11 = wx.StaticText(self, wx.ID_ANY, _("mils"))
        sizer_2.Add(label_11, 0, *static_text_border)
        sizer_home.Add(sizer_2, 1, wx.EXPAND | wx.LEFT, 10)
        sizer_home.Add(self.button_home_by_current, 0, wx.LEFT, 10)
        sizer_main.Add(sizer_home, 1, wx.EXPAND, 0)
        sizer_6.Add(self.checkbox_plot_shift, 1, *checkbox_border)
        sizer_6.Add(self.checkbox_random_ppi, 0, *checkbox_border)
        sizer_main.Add(sizer_6, 0, wx.EXPAND, 0)
        sizer_buffer.Add(self.checkbox_limit_buffer, 1, *checkbox_border)
        sizer_buffer.Add(self.text_buffer_length, 1, 0, 0)
        label_14 = wx.StaticText(self, wx.ID_ANY, " / ")
        sizer_buffer.Add(label_14, 0, *static_text_border)
        sizer_buffer.Add(self.spin_packet_buffer_max, 1, 0, 0)
        sizer_main.Add(sizer_buffer, 1, wx.EXPAND, 0)
        sizer_general.Add(self.checkbox_autolock, 0, 0, 0)
        sizer_main.Add(sizer_general, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        # end wxGlade

    def initialize(self):
        self.context.listen("pipe;buffer", self.on_buffer_update)
        self.context.listen("active", self.on_active_change)
        self.checkbox_flip_x.SetFocus()

    def finalize(self):
        self.context.unlisten("pipe;buffer", self.on_buffer_update)
        self.context.unlisten("active", self.on_active_change)

    def on_active_change(self, origin, active):
        # self.Close()
        pass

    def set_widgets(self):
        context = self.context
        context.setting(bool, "fix_speeds", False)
        context.setting(bool, "swap_xy", False)
        context.setting(bool, "flip_x", False)
        context.setting(bool, "flip_y", False)
        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        context.setting(bool, "strict", False)
        context.setting(bool, "nse_raster", False)
        context.setting(bool, "twitchfull", False)

        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(bool, "autolock", True)
        context.setting(str, "board", "M2")
        context.setting(bool, "buffer_limit", True)
        context.setting(int, "buffer_max", 1500)
        context.setting(bool, "random_ppi", False)
        context.setting(bool, "plot_shift", False)
        context.setting(bool, "raster_accel_table", False)
        context.setting(bool, "vector_accel_table", False)

        self.checkbox_fix_speeds.SetValue(context.fix_speeds)
        self.checkbox_swap_xy.SetValue(context.swap_xy)
        self.checkbox_flip_x.SetValue(context.flip_x)
        self.checkbox_flip_y.SetValue(context.flip_y)
        self.checkbox_home_right.SetValue(context.home_right)
        self.checkbox_home_bottom.SetValue(context.home_bottom)
        self.checkbox_strict.SetValue(context.strict)
        self.checkbox_twitchfull.SetValue(context.twitchfull)
        self.checkbox_alternative_raster.SetValue(context.nse_raster)

        self.spin_home_x.SetValue(context.home_adjust_x)
        self.spin_home_y.SetValue(context.home_adjust_y)
        self.checkbox_autolock.SetValue(context.autolock)
        self.combobox_board.SetValue(context.board)
        self.checkbox_limit_buffer.SetValue(context.buffer_limit)
        self.spin_packet_buffer_max.SetValue(context.buffer_max)

        self.checkbox_random_ppi.SetValue(context.random_ppi)
        self.checkbox_plot_shift.SetValue(context.plot_shift)

    def calc_home_position(self):
        x = 0
        y = 0
        if self.context.home_right:
            x = int(self.bed_dim.bed_width * MILS_IN_MM)
        if self.context.home_bottom:
            y = int(self.bed_dim.bed_height * MILS_IN_MM)
        return x, y

    def on_combobox_boardtype(self, event=None):
        self.context.board = self.combobox_board.GetValue()

    def on_check_swapxy(self, event=None):
        self.context.swap_xy = self.checkbox_swap_xy.GetValue()
        self.context("dev code_update\n")

    def on_check_fix_speeds(self, event=None):
        self.context.fix_speeds = self.checkbox_fix_speeds.GetValue()

    def on_check_strict(self, event=None):
        self.context.strict = self.checkbox_strict.GetValue()

    def on_check_twitchfull(self, event=None):
        self.context.twitchfull = self.checkbox_twitchfull.GetValue()

    def on_check_alt_raster(self, event=None):
        self.context.nse_raster = self.checkbox_alternative_raster.GetValue()

    def on_check_flip_x(self, event=None):
        self.context.flip_x = self.checkbox_flip_x.GetValue()
        self.context("dev code_update\n")

    def on_check_home_right(self, event=None):
        self.context.home_right = self.checkbox_home_right.GetValue()

    def on_check_flip_y(self, event=None):
        self.context.flip_y = self.checkbox_flip_y.GetValue()
        self.context("dev code_update\n")

    def on_check_home_bottom(self, event=None):
        self.context.home_bottom = self.checkbox_home_bottom.GetValue()

    def spin_on_home_x(self, event=None):
        self.context.home_adjust_x = int(self.spin_home_x.GetValue())

    def spin_on_home_y(self, event=None):
        self.context.home_adjust_y = int(self.spin_home_y.GetValue())

    def on_button_set_home_current(self, event=None):
        x, y = self.calc_home_position()
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        current_x = input_driver.current_x - x
        current_y = input_driver.current_y - y
        self.context.home_adjust_x = int(current_x)
        self.context.home_adjust_y = int(current_y)
        self.spin_home_x.SetValue(self.context.home_adjust_x)
        self.spin_home_y.SetValue(self.context.home_adjust_y)

    def on_check_autolock(self, event=None):
        self.context.autolock = self.checkbox_autolock.GetValue()

    def on_check_limit_packet_buffer(
        self, event=None
    ):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_limit = self.checkbox_limit_buffer.GetValue()

    def on_spin_packet_buffer_max(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_max = self.spin_packet_buffer_max.GetValue()

    def on_check_pulse_shift(
        self, event=None
    ):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.plot_shift = self.checkbox_plot_shift.GetValue()
        try:
            _, driver, _ = self.context.root.device()
            driver.plot_planner.force_shift = self.context.plot_shift
        except (AttributeError, TypeError):
            pass

    def on_check_random_ppi(
        self, event=None
    ):  # wxGlade: LhystudiosDriver.<event_handler>
        self.context.random_ppi = self.checkbox_random_ppi.GetValue()

    def on_buffer_update(self, origin, value, *args):
        self.text_buffer_length.SetValue(str(value))


class LhystudiosDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(365, 365, *args, **kwds)

        self.panel = LhystudiosConfigurationPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Lhystudios-Configuration"))

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()

    def window_preserve(self):
        return False
