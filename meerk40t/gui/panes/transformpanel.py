import wx
from wx import aui

_ = wx.GetTranslation


from meerk40t.gui.icons import (
    icons8_compress_50,
    icons8_delete_50,
    icons8_down_50,
    icons8_enlarge_50,
    icons8_left_50,
    icons8_right_50,
    icons8_rotate_left_50,
    icons8_rotate_right_50,
    icons8_up_50,
)


def register_panel(window, context):
    panel = Transform(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(174, 220)
        .FloatingSize(174, 220)
        .MaxSize(300, 300)
        .Caption(_("Transform"))
        .Name("transform")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 220
    pane.control = panel
    pane.submenu = _("Navigation")

    window.on_pane_add(pane)
    context.register("pane/transform", pane)


class Transform(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: Transform.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.button_scale_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_compress_50.GetBitmap()
        )
        self.button_translate_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8_up_50.GetBitmap()
        )
        self.button_scale_up = wx.BitmapButton(
            self, wx.ID_ANY, icons8_enlarge_50.GetBitmap()
        )
        self.button_translate_left = wx.BitmapButton(
            self, wx.ID_ANY, icons8_left_50.GetBitmap()
        )
        self.button_reset = wx.BitmapButton(
            self, wx.ID_ANY, icons8_delete_50.GetBitmap()
        )
        self.button_translate_right = wx.BitmapButton(
            self, wx.ID_ANY, icons8_right_50.GetBitmap()
        )
        self.button_rotate_ccw = wx.BitmapButton(
            self, wx.ID_ANY, icons8_rotate_left_50.GetBitmap()
        )
        self.button_translate_down = wx.BitmapButton(
            self, wx.ID_ANY, icons8_down_50.GetBitmap()
        )
        self.button_rotate_cw = wx.BitmapButton(
            self, wx.ID_ANY, icons8_rotate_right_50.GetBitmap()
        )
        self.text_a = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_c = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_e = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_b = wx.TextCtrl(self, wx.ID_ANY, "0.000000")
        self.text_d = wx.TextCtrl(self, wx.ID_ANY, "1.000000")
        self.text_f = wx.TextCtrl(self, wx.ID_ANY, "0.000000")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_scale_down, self.button_scale_down)
        self.Bind(wx.EVT_BUTTON, self.on_translate_up, self.button_translate_up)
        self.Bind(wx.EVT_BUTTON, self.on_scale_up, self.button_scale_up)
        self.Bind(wx.EVT_BUTTON, self.on_translate_left, self.button_translate_left)
        self.Bind(wx.EVT_BUTTON, self.on_reset, self.button_reset)
        self.Bind(wx.EVT_BUTTON, self.on_translate_right, self.button_translate_right)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_ccw, self.button_rotate_ccw)
        self.Bind(wx.EVT_BUTTON, self.on_translate_down, self.button_translate_down)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_cw, self.button_rotate_cw)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_a)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_c)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_e)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_b)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_d)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_f)
        # end wxGlade
        self.select_ready(False)

    def __set_properties(self):
        # begin wxGlade: Transform.__set_properties
        self.button_scale_down.SetSize(self.button_scale_down.GetBestSize())
        self.button_translate_up.SetSize(self.button_translate_up.GetBestSize())
        self.button_scale_up.SetSize(self.button_scale_up.GetBestSize())
        self.button_translate_left.SetSize(self.button_translate_left.GetBestSize())
        self.button_reset.SetSize(self.button_reset.GetBestSize())
        self.button_translate_right.SetSize(self.button_translate_right.GetBestSize())
        self.button_rotate_ccw.SetSize(self.button_rotate_ccw.GetBestSize())
        self.button_translate_down.SetSize(self.button_translate_down.GetBestSize())
        self.button_rotate_cw.SetSize(self.button_rotate_cw.GetBestSize())

        self.button_scale_down.SetToolTip(_("Scale Down"))
        self.button_translate_up.SetToolTip(_("Translate Top"))
        self.button_scale_up.SetToolTip(_("Scale Up"))
        self.button_translate_left.SetToolTip(_("Translate Left"))
        self.button_reset.SetToolTip(_("Reset Matrix"))
        self.button_translate_right.SetToolTip(_("Translate Right"))
        self.button_rotate_ccw.SetToolTip(_("Rotate Counterclockwise"))
        self.button_translate_down.SetToolTip(_("Translate Bottom"))
        self.button_rotate_cw.SetToolTip(_("Rotate Clockwise"))
        self.text_a.SetMinSize((58, 23))
        self.text_a.SetToolTip(_("Transform: Scale X"))
        self.text_c.SetMinSize((58, 23))
        self.text_c.SetToolTip(_("Transform: Skew Y"))
        self.text_e.SetMinSize((58, 23))
        self.text_e.SetToolTip(_("Transform: Translate X"))
        self.text_b.SetMinSize((58, 23))
        self.text_b.SetToolTip(_("Transform: Skew X"))
        self.text_d.SetMinSize((58, 23))
        self.text_d.SetToolTip(_("Transform: Scale Y"))
        self.text_f.SetMinSize((58, 23))
        self.text_f.SetToolTip(_("Transform: Translate Y"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Transform.__do_layout
        matrix_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_2 = wx.FlexGridSizer(5, 3, 0, 0)
        grid_sizer_2.Add(self.button_scale_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_scale_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_left, 0, 0, 0)
        grid_sizer_2.Add(self.button_reset, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_right, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_ccw, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_cw, 0, 0, 0)
        grid_sizer_2.Add(self.text_a, 0, 0, 0)
        grid_sizer_2.Add(self.text_c, 0, 0, 0)
        grid_sizer_2.Add(self.text_e, 0, 0, 0)
        grid_sizer_2.Add(self.text_b, 0, 0, 0)
        grid_sizer_2.Add(self.text_d, 0, 0, 0)
        grid_sizer_2.Add(self.text_f, 0, 0, 0)
        matrix_sizer.Add(grid_sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(matrix_sizer)
        matrix_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.context.listen("emphasized", self.on_emphasized_elements_changed)
        self.update_matrix_text()

    def finalize(self, *args):
        self.context.unlisten("emphasized", self.on_emphasized_elements_changed)

    def on_emphasized_elements_changed(self, origin, elements):
        self.select_ready(self.context.elements.has_emphasis())
        self.update_matrix_text()

    def update_matrix_text(self):
        f = self.context.elements.first_element(emphasized=True)
        v = f is not None
        self.text_a.Enable(v)
        self.text_b.Enable(v)
        self.text_c.Enable(v)
        self.text_d.Enable(v)
        self.text_e.Enable(v)
        self.text_f.Enable(v)
        if v:
            matrix = f.transform
            self.text_a.SetValue(str(matrix.a))
            self.text_b.SetValue(str(matrix.b))
            self.text_c.SetValue(str(matrix.c))
            self.text_d.SetValue(str(matrix.d))
            self.text_e.SetValue(str(matrix.e))
            self.text_f.SetValue(str(matrix.f))

    def select_ready(self, v):
        """
        Enables the relevant buttons when there is a selection in the elements.
        :param v: whether selection is currently drag ready.
        :return:
        """
        self.button_scale_down.Enable(v)
        self.button_scale_up.Enable(v)
        self.button_rotate_ccw.Enable(v)
        self.button_rotate_cw.Enable(v)
        self.button_translate_down.Enable(v)
        self.button_translate_up.Enable(v)
        self.button_translate_left.Enable(v)
        self.button_translate_right.Enable(v)
        self.button_reset.Enable(v)

    def matrix_updated(self):
        self.context.signal("refresh_scene")
        self.update_matrix_text()

    def on_scale_down(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 19.0 / 20.0
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        x = input_driver.current_x if input_driver is not None else 0
        y = input_driver.current_y if input_driver is not None else 0
        self.context(
            "scale %f %f %f %f\n"
            % (
                scale,
                scale,
                x,
                y,
            )
        )
        self.matrix_updated()

    def on_scale_up(self, event=None):  # wxGlade: Navigation.<event_handler>
        scale = 20.0 / 19.0
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        x = input_driver.current_x if input_driver is not None else 0
        y = input_driver.current_y if input_driver is not None else 0
        self.context(
            "scale %f %f %f %f\n"
            % (
                scale,
                scale,
                x,
                y,
            )
        )
        self.matrix_updated()

    def on_translate_up(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = -self.context.navigate_jog
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_left(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = -self.context.navigate_jog
        dy = 0
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_right(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = self.context.navigate_jog
        dy = 0
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_translate_down(self, event=None):  # wxGlade: Navigation.<event_handler>
        dx = 0
        dy = self.context.navigate_jog
        self.context("translate %f %f\n" % (dx, dy))
        self.matrix_updated()

    def on_reset(self, event=None):  # wxGlade: Navigation.<event_handler>
        self.context("reset\n")
        self.matrix_updated()

    def on_rotate_ccw(self, event=None):  # wxGlade: Navigation.<event_handler>
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        x = input_driver.current_x if input_driver is not None else 0
        y = input_driver.current_y if input_driver is not None else 0
        self.context("rotate %fdeg %f %f\n" % (-5, x, y))
        self.matrix_updated()

    def on_rotate_cw(self, event=None):  # wxGlade: Navigation.<event_handler>
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        x = input_driver.current_x if input_driver is not None else 0
        y = input_driver.current_y if input_driver is not None else 0
        self.context("rotate %fdeg %f %f\n" % (5, x, y))
        self.matrix_updated()

    def on_text_matrix(self, event=None):  # wxGlade: Navigation.<event_handler>
        try:
            self.context(
                "matrix %f %f %f %f %s %s\n"
                % (
                    float(self.text_a.GetValue()),
                    float(self.text_b.GetValue()),
                    float(self.text_c.GetValue()),
                    float(self.text_d.GetValue()),
                    self.text_e.GetValue(),
                    self.text_f.GetValue(),
                )
            )
        except ValueError:
            self.update_matrix_text()
        self.context.signal("refresh_scene")
