from copy import copy
from math import tau
from time import perf_counter

import wx

from meerk40t.core.units import ACCEPTED_UNITS, Angle, Length
from meerk40t.fill.patterns import LivingHinges
from meerk40t.gui.icons import STD_ICON_SIZE, icon_hinges
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxStaticText,
)
from meerk40t.kernel import signal_listener
from meerk40t.svgelements import Color, Matrix, Path

# from meerk40t.fill.patternfill import LivingHinges


_ = wx.GetTranslation

"""
TODO:
a) get rid of row / col range limitation and iterate until boundary exceeds frame
b) Come up with a better inner offset algorithm
"""

_FACTOR = 1000


class HingePanel(wx.Panel):
    """
    UI for LivingHinges, allows setting of parameters including preview of the expected result
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.debug_counter = 0
        self.SetHelpText("hinges")
        self.hinge_generator = LivingHinges(
            0, 0, float(Length("5cm")), float(Length("5cm"))
        )
        self.hinge_origin_x = "0cm"
        self.hinge_origin_y = "0cm"
        self.hinge_width = "5cm"
        self.hinge_height = "5cm"
        self.hinge_cells_x = 200
        self.hinge_cells_y = 200
        self.hinge_padding_x = 100
        self.hinge_padding_y = 100
        self.hinge_param_a = 0.7
        self.hinge_param_b = 0.7
        self.hinge_rotate = 0.0

        self.renderer = LaserRender(context)
        self.in_draw_event = False
        self.in_change_event = False
        self.in_show_event = False
        self.require_refresh = True
        self.last_show_event = 0
        self._Buffer = None

        self.text_origin_x = TextCtrl(self, wx.ID_ANY, "")
        self.text_origin_y = TextCtrl(self, wx.ID_ANY, "")
        self.text_width = TextCtrl(self, wx.ID_ANY, "")
        self.text_height = TextCtrl(self, wx.ID_ANY, "")
        self.combo_style = wxComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN
        )
        self.button_default = wxButton(self, wx.ID_ANY, "D")

        self.slider_rotate = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            0,
            359,
            style=wx.SL_HORIZONTAL,
        )
        self.slider_rotate_label = wxStaticText(self, wx.ID_ANY, "0°")
        self.slider_rotate_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.text_rotate = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )

        _default = 200
        self.slider_width = wx.Slider(
            self,
            wx.ID_ANY,
            _default,
            1,
            _FACTOR,
            style=wx.SL_HORIZONTAL,
        )
        self.slider_width_label = wxStaticText(
            self, wx.ID_ANY, f"{_default/_FACTOR:.1%}"
        )
        self.slider_width_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.text_cell_width = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_height = wx.Slider(
            self,
            wx.ID_ANY,
            _default,
            1,
            _FACTOR,
            style=wx.SL_HORIZONTAL,
        )
        self.slider_height_label = wxStaticText(
            self, wx.ID_ANY, f"{_default/_FACTOR:.1%}"
        )
        self.slider_height_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.text_cell_height = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_offset_x = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            int(1 - _FACTOR / 2) + 1,
            int(_FACTOR / 2),
            style=wx.SL_HORIZONTAL,
        )
        self.slider_offx_label = wxStaticText(self, wx.ID_ANY)
        self.slider_offx_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.text_cell_offset_x = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.slider_offset_y = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            int(1 - _FACTOR / 2) + 1,
            int(_FACTOR / 2),
            style=wx.SL_HORIZONTAL,
        )
        self.slider_offy_label = wxStaticText(self, wx.ID_ANY)
        self.slider_offy_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.text_cell_offset_y = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        # Slider times ten
        self.slider_param_a = wx.Slider(
            self,
            wx.ID_ANY,
            7,
            -50,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_param_b = wx.Slider(
            self,
            wx.ID_ANY,
            7,
            -50,
            +50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.button_generate = wxButton(self, wx.ID_ANY, _("Generate"))
        self.button_close = wxButton(self, wx.ID_ANY, _("Close"))
        self.context.setting(bool, "hinge_preview_pattern", True)
        self.context.setting(bool, "hinge_preview_shape", True)
        self.check_preview_show_pattern = wxCheckBox(
            self, wx.ID_ANY, _("Preview Pattern")
        )
        self.check_preview_show_pattern.SetValue(
            bool(self.context.hinge_preview_pattern)
        )
        self.check_preview_show_shape = wxCheckBox(self, wx.ID_ANY, _("Preview Shape"))
        self.check_preview_show_shape.SetValue(bool(self.context.hinge_preview_shape))

        #  self.check_debug_outline = wxCheckBox(self, wx.ID_ANY, "Show outline")

        self.patterns = list()
        self.defaults = list()
        self.pattern_entry = list()

        for entry in context.match("pattern/", suffix=True):
            pattern = context.lookup(f"pattern/{entry}")
            default = pattern[4]
            self.pattern_entry.append(pattern)
            self.patterns.append(entry)
            self.defaults.append(default)
        self.combo_style.Set(self.patterns)
        self.combo_style.SetSelection(0)
        # self.check_debug_outline.SetValue(True)
        self._set_layout()
        self._set_logic()

        self._setup_settings()
        if self._restore_settings(source="_init_"):
            self.sync_controls(True)
            self.apply_generator_values("_init_")

        self.Layout()

    def _set_logic(self):
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_paint)
        self.button_close.Bind(wx.EVT_BUTTON, self.on_button_close)
        self.button_generate.Bind(wx.EVT_BUTTON, self.on_button_generate)
        self.text_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_x.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_y.Bind(wx.EVT_TEXT, self.on_option_update)
        # We don't call the update routine for every mouse movement,
        # just at the end of the sliding action
        self.slider_width.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_height.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_x.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_y.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_a.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_b.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_rotate.Bind(wx.EVT_SLIDER, self.on_option_update)

        self.combo_style.Bind(wx.EVT_COMBOBOX, self.on_pattern_update)
        self.button_default.Bind(wx.EVT_BUTTON, self.on_default_button)
        self.check_preview_show_pattern.Bind(wx.EVT_CHECKBOX, self.on_preview_options)
        self.check_preview_show_shape.Bind(wx.EVT_CHECKBOX, self.on_preview_options)
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.text_rotate.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_height.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_width.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_offset_x.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)
        self.text_cell_offset_y.Bind(wx.EVT_TEXT_ENTER, self.on_option_update)

        self.text_rotate.Bind(wx.EVT_KILL_FOCUS, self.on_option_update)
        self.text_cell_height.Bind(wx.EVT_KILL_FOCUS, self.on_option_update)
        self.text_cell_width.Bind(wx.EVT_KILL_FOCUS, self.on_option_update)
        self.text_cell_offset_x.Bind(wx.EVT_KILL_FOCUS, self.on_option_update)
        self.text_cell_offset_y.Bind(wx.EVT_KILL_FOCUS, self.on_option_update)

        self.text_rotate.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_cell_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_cell_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_cell_offset_x.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_cell_offset_y.Bind(wx.EVT_TEXT, self.on_option_update)

    def _set_layout(self):
        def size_it(ctrl, value):
            ctrl.SetMaxSize(dip_size(self, int(value), -1))
            ctrl.SetMinSize(dip_size(self, int(value * 0.75), -1))
            ctrl.SetSize(dip_size(self, value, -1))

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        size_it(self.slider_rotate, 120)
        size_it(self.slider_height, 120)
        size_it(self.slider_width, 120)
        size_it(self.slider_offset_x, 120)
        size_it(self.slider_offset_y, 120)
        size_it(self.slider_param_a, 120)
        size_it(self.slider_param_b, 120)
        size_it(self.text_rotate, 90)
        size_it(self.text_cell_height, 90)
        size_it(self.text_cell_width, 90)
        size_it(self.text_cell_offset_x, 90)
        size_it(self.text_cell_offset_y, 90)
        size_it(self.text_width, 90)
        size_it(self.text_height, 90)
        size_it(self.text_origin_x, 90)
        size_it(self.text_origin_y, 90)
        size_it(self.combo_style, 120)
        # size_it(self.button_generate, 120)
        # size_it(self.button_close, 90)

        main_left = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(main_left, 0, wx.EXPAND | wx.FIXED_MINSIZE, 0)

        vsizer_dimension = StaticBoxSizer(self, wx.ID_ANY, _("Dimension"), wx.VERTICAL)
        main_left.Add(vsizer_dimension, 0, wx.EXPAND, 0)

        hsizer_origin = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_origin, 0, wx.EXPAND, 0)

        hsizer_originx = StaticBoxSizer(self, wx.ID_ANY, _("X:"), wx.VERTICAL)
        self.text_origin_x.SetToolTip(_("X-Coordinate of the hinge area"))
        hsizer_originx.Add(self.text_origin_x, 1, wx.EXPAND, 0)

        hsizer_originy = StaticBoxSizer(self, wx.ID_ANY, _("Y:"), wx.VERTICAL)

        self.text_origin_y.SetToolTip(_("Y-Coordinate of the hinge area"))
        hsizer_originy.Add(self.text_origin_y, 1, wx.EXPAND, 0)

        hsizer_origin.Add(hsizer_originx, 1, wx.EXPAND, 0)
        hsizer_origin.Add(hsizer_originy, 1, wx.EXPAND, 0)

        hsizer_wh = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_wh, 0, wx.EXPAND, 0)

        hsizer_width = StaticBoxSizer(self, wx.ID_ANY, _("Width:"), wx.VERTICAL)

        self.text_width.SetToolTip(_("Width of the hinge area"))
        hsizer_width.Add(self.text_width, 1, wx.EXPAND, 0)

        hsizer_height = StaticBoxSizer(self, wx.ID_ANY, _("Height:"), wx.VERTICAL)

        self.text_height.SetToolTip(_("Height of the hinge area"))
        hsizer_height.Add(self.text_height, 1, wx.EXPAND, 0)

        hsizer_wh.Add(hsizer_width, 1, wx.EXPAND, 0)
        hsizer_wh.Add(hsizer_height, 1, wx.EXPAND, 0)

        vsizer_options = StaticBoxSizer(self, wx.ID_ANY, _("Options"), wx.VERTICAL)
        main_left.Add(vsizer_options, 0, wx.EXPAND, 0)

        hsizer_pattern = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_pattern, 0, wx.EXPAND, 0)

        label_pattern = wxStaticText(self, wx.ID_ANY, _("Pattern:"))
        label_pattern.SetMinSize(dip_size(self, 90, -1))
        hsizer_pattern.Add(label_pattern, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.combo_style.SetToolTip(_("Choose the hinge pattern"))
        hsizer_pattern.Add(self.combo_style, 1, wx.EXPAND, 0)

        self.button_default.SetToolTip(_("Default Values"))
        self.button_default.SetMinSize(dip_size(self, 30, -1))
        hsizer_pattern.Add(self.button_default, 0, wx.EXPAND, 0)

        hsizer_rotate = wx.BoxSizer(wx.HORIZONTAL)
        label_rotate = wxStaticText(self, wx.ID_ANY, _("Rotation:"))
        label_rotate.SetMinSize(dip_size(self, 90, -1))
        hsizer_rotate.Add(label_rotate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        ro_width = wx.BoxSizer(wx.VERTICAL)
        ro_width.Add(self.slider_rotate, 0, wx.EXPAND, 0)
        ro_width.Add(self.slider_rotate_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        hsizer_rotate.Add(ro_width, 2, wx.EXPAND, 0)
        hsizer_rotate.Add(self.text_rotate, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        vsizer_options.Add(hsizer_rotate, 0, wx.EXPAND, 0)

        self.slider_rotate.SetToolTip(_("Set a rotation value for the pattern"))
        self.text_rotate.SetToolTip(_("Set a rotation value for the pattern"))

        hsizer_cellwidth = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellwidth, 1, wx.EXPAND, 0)

        label_cell_width = wxStaticText(self, wx.ID_ANY, _("Cell-Width:"))
        label_cell_width.SetMinSize(dip_size(self, 90, -1))
        hsizer_cellwidth.Add(label_cell_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
        )
        self.text_cell_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
        )
        vs_width = wx.BoxSizer(wx.VERTICAL)
        vs_width.Add(self.slider_width, 0, wx.EXPAND, 0)
        vs_width.Add(self.slider_width_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        hsizer_cellwidth.Add(vs_width, 2, wx.EXPAND, 0)
        hsizer_cellwidth.Add(self.text_cell_width, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_cellheight = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellheight, 1, wx.EXPAND, 0)

        label_cell_height = wxStaticText(self, wx.ID_ANY, _("Cell-Height:"))
        label_cell_height.SetMinSize(dip_size(self, 90, -1))
        hsizer_cellheight.Add(label_cell_height, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_height.SetToolTip(
            _("Select the ratio of the cell height compared to the overall height")
        )
        self.text_cell_height.SetToolTip(
            _("Select the ratio of the cell height compared to the overall height")
        )
        vs_height = wx.BoxSizer(wx.VERTICAL)
        vs_height.Add(self.slider_height, 0, wx.EXPAND, 0)
        vs_height.Add(self.slider_height_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        hsizer_cellheight.Add(vs_height, 2, wx.EXPAND, 0)
        hsizer_cellheight.Add(self.text_cell_height, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_offsetx = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsetx, 1, wx.EXPAND, 0)

        label_offset_x = wxStaticText(self, wx.ID_ANY, _("Offset X:"))
        label_offset_x.SetMinSize(dip_size(self, 90, -1))
        hsizer_offsetx.Add(label_offset_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_x.SetToolTip(_("Select the pattern-offset in X-direction"))
        self.text_cell_offset_x.SetToolTip(
            _("Select the pattern-offset in X-direction")
        )
        vs_offx = wx.BoxSizer(wx.VERTICAL)
        vs_offx.Add(self.slider_offset_x, 0, wx.EXPAND, 0)
        vs_offx.Add(self.slider_offx_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        hsizer_offsetx.Add(vs_offx, 2, wx.EXPAND, 0)
        hsizer_offsetx.Add(self.text_cell_offset_x, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        hsizer_offsety = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsety, 0, wx.EXPAND, 0)

        label_offset_y = wxStaticText(self, wx.ID_ANY, _("Offset Y:"))
        label_offset_y.SetMinSize(dip_size(self, 90, -1))
        hsizer_offsety.Add(label_offset_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_y.SetToolTip(_("Select the pattern-offset in Y-direction"))
        self.text_cell_offset_y.SetToolTip(
            _("Select the pattern-offset in Y-direction")
        )
        vs_offy = wx.BoxSizer(wx.VERTICAL)
        vs_offy.Add(self.slider_offset_y, 0, wx.EXPAND, 0)
        vs_offy.Add(self.slider_offy_label, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        hsizer_offsety.Add(vs_offy, 2, wx.EXPAND, 0)
        hsizer_offsety.Add(self.text_cell_offset_y, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_param_a.SetToolTip(_("Change the shape appearance"))
        self.slider_param_b.SetToolTip(_("Change the shape appearance"))
        hsizer_param_a = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_param_a.Add(self.slider_param_a, 1, wx.EXPAND, 0)
        hsizer_param_a.Add(self.slider_param_b, 1, wx.EXPAND, 0)
        vsizer_options.Add(hsizer_param_a, 0, wx.EXPAND, 0)
        # main_left.Add(self.check_debug_outline, 0, wx.EXPAND, 0)

        hsizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        main_left.Add(hsizer_buttons, 0, wx.EXPAND, 0)

        self.button_generate.SetToolTip(_("Generates the hinge"))
        hsizer_buttons.Add(self.button_generate, 2, 0, 0)

        hsizer_buttons.Add(self.button_close, 1, 0, 0)

        main_right = StaticBoxSizer(self, wx.ID_ANY, _("Preview"), wx.VERTICAL)
        main_sizer.Add(main_right, 1, wx.EXPAND, 0)

        hsizer_preview = wx.BoxSizer(wx.HORIZONTAL)
        main_right.Add(hsizer_preview, 0, wx.EXPAND, 0)
        self.check_preview_show_pattern.SetMinSize(dip_size(self, -1, 23))
        self.check_preview_show_shape.SetMinSize(dip_size(self, -1, 23))
        hsizer_preview.Add(self.check_preview_show_pattern, 1, wx.EXPAND, 0)
        hsizer_preview.Add(self.check_preview_show_shape, 1, wx.EXPAND, 0)
        self.panel_preview = wx.Panel(self, wx.ID_ANY)
        main_right.Add(self.panel_preview, 1, wx.EXPAND, 0)
        main_left.Layout()
        main_right.Layout()
        main_sizer.Layout()
        self.SetSizer(main_sizer)

    def on_preview_options(self, event):
        self.context.hinge_preview_pattern = self.check_preview_show_pattern.GetValue()
        self.context.hinge_preview_shape = self.check_preview_show_shape.GetValue()
        self.refresh_display()

    def on_display_paint(self, event=None):
        try:
            wx.BufferedPaintDC(self.panel_preview, self._Buffer)
        except RuntimeError:
            pass

    def set_buffer(self):
        width, height = self.panel_preview.Size
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)

    def refresh_display(self):
        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def on_paint(self, event):
        self.Layout()
        self.set_buffer()
        wx.CallAfter(self.refresh_in_ui)

    def on_size(self, event=None):
        self.Layout()
        self.set_buffer()
        wx.CallAfter(self.refresh_in_ui)

    def refresh_in_ui(self):
        if self.in_draw_event:
            return
        # Create paint DC
        self.in_draw_event = True
        if self._Buffer is None:
            self.set_buffer()
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            wd, ht = self.panel_preview.GetSize()
            try:
                ratio = min(
                    wd / self.hinge_generator.width, ht / self.hinge_generator.height
                )
            except ZeroDivisionError:
                return
            ratio *= 0.9
            matrix = gc.CreateMatrix(
                a=ratio,
                b=0,
                c=0,
                d=ratio,
                tx=ratio
                * (0.05 * self.hinge_generator.width - self.hinge_generator.start_x),
                ty=ratio
                * (0.05 * self.hinge_generator.height - self.hinge_generator.start_y),
            )
            gc.SetTransform(matrix)
            if ratio == 0:
                ratio = 1
            linewidth = max(int(1 / ratio), 1)
            if self.check_preview_show_shape.GetValue():
                mypen_border = wx.Pen(wx.BLUE, linewidth, wx.PENSTYLE_SOLID)
                gc.SetPen(mypen_border)
                if self.hinge_generator.outershape is None:
                    # Draw the hinge area:
                    gc.DrawRectangle(
                        0, 0, self.hinge_generator.width, self.hinge_generator.height
                    )
                else:
                    path = self.hinge_generator.outershape.as_path()
                    if path:
                        gcpath = self.renderer.make_path(gc, path)
                        gc.StrokePath(gcpath)
            if self.check_preview_show_pattern.GetValue():
                mypen_path = wx.Pen(wx.RED, linewidth, wx.PENSTYLE_SOLID)
                # flag = self.check_debug_outline.GetValue()
                self.hinge_generator.generate(
                    show_outline=False,
                    final=False,
                )
                gc.SetPen(mypen_path)
                gspath = self.hinge_generator.preview_path
                if gspath is not None and self.hinge_generator.outershape is not None:
                    if isinstance(gspath, Path):
                        bb = self.hinge_generator.outershape.bbox()
                        gspath.transform *= Matrix.translate(-bb[0], -bb[1])
                        gcpath = self.renderer.make_path(gc, gspath)
                    else:
                        gcpath = self.renderer.make_geomstr(gc, gspath)
                    gc.StrokePath(gcpath)
        self.panel_preview.Refresh()
        self.panel_preview.Update()
        self.in_draw_event = False

    def on_button_close(self, event):
        self.context("window close Hingetool\n")

    def on_default_button(self, event):
        idx = self.combo_style.GetSelection()
        if idx < 0:
            return
        pattern = self.patterns[idx]
        entry = self.context.lookup(f"pattern/{pattern}")
        default = entry[4]
        self.slider_rotate.SetValue(0)
        self.slider_rotate_label.SetLabel(f"{self.slider_rotate.GetValue()}°")
        self.slider_width.SetValue(200)
        self.slider_width_label.SetLabel(f"{self.slider_width.GetValue()/_FACTOR:.1%}")
        self.slider_height.SetValue(200)
        self.slider_height_label.SetLabel(
            f"{self.slider_height.GetValue()/_FACTOR:.1%}"
        )
        self.slider_offset_x.SetValue(default[0])
        self.slider_offx_label.SetLabel(f"{default[0]/_FACTOR:.1%}")
        self.slider_offset_y.SetValue(default[1])
        self.slider_offy_label.SetLabel(f"{default[1]/_FACTOR:.1%}")
        self.slider_param_a.SetValue(int(10 * default[2]))
        self.slider_param_b.SetValue(int(10 * default[3]))
        self.on_option_update(None)

    def on_button_generate(self, event):
        from time import time

        oldlabel = self.button_generate.Label
        self.button_generate.Enable(False)
        self.button_generate.SetLabel(_("Processing..."))
        start_time = time()
        if self.hinge_generator.outershape is not None and hasattr(
            self.hinge_generator.outershape, "as_geometry"
        ):
            # As we have a reference shape, we make sure
            # we update the information...
            units = self.context.units_name
            bounds = self.hinge_generator.outershape.bbox()
            start_x = bounds[0]
            start_y = bounds[1]
            wd = bounds[2] - bounds[0]
            ht = bounds[3] - bounds[1]
            self.hinge_origin_x = Length(
                amount=start_x, digits=3, preferred_units=units
            ).preferred_length
            self.hinge_origin_y = Length(
                amount=start_y, digits=3, preferred_units=units
            ).preferred_length
            self.hinge_width = Length(
                amount=wd, digits=2, preferred_units=units
            ).preferred_length
            self.hinge_height = Length(
                amount=ht, digits=2, preferred_units=units
            ).preferred_length
            self.text_origin_x.ChangeValue(self.hinge_origin_x)
            self.text_origin_y.ChangeValue(self.hinge_origin_y)
            self.text_width.ChangeValue(self.hinge_width)
            self.text_height.ChangeValue(self.hinge_height)
            self.hinge_generator.set_hinge_area(start_x, start_y, wd, ht)

        self.hinge_generator.generate(show_outline=False, final=True)
        path = copy(self.hinge_generator.path)
        if path is None:
            # print ("Invalid path")
            self.button_generate.Enable(True)
            self.button_generate.SetLabel(oldlabel)
            return
        if hasattr(path, "as_path"):
            path = path.as_path()
        with self.context.elements.undoscope("Living hinge"):
            node = self.context.elements.elem_branch.add(
                path=path,
                stroke_width=500,
                stroke=Color("red"),
                type="elem path",
            )
            # Let's simplify things...
            self.context.elements.simplify_node(node)

            if self.hinge_generator.outershape is not None:
                group_node = self.hinge_generator.outershape.parent.add(
                    type="group", label="Hinge"
                )
                group_node.append_child(self.hinge_generator.outershape)
                group_node.append_child(node)
        end_time = time()
        self.Parent.SetTitle(_("Living-Hinges") + f" ({end_time-start_time:.2f}s.)")

        self.context.signal("classify_new", node)
        self.context.signal("refresh_scene", "Scene")
        self.button_generate.Enable(True)
        self.button_generate.SetLabel(oldlabel)

    def on_pattern_update(self, event):
        # Save the old values...
        # self._save_settings()
        idx = self.combo_style.GetSelection()
        if idx < 0:
            idx = 0
        style = self.patterns[idx]
        if style != self.context.hinge_type:
            self.context.hinge_type = style
            # Load new set of values...
            if self._restore_settings(reload=True, source="on_pattern"):
                self.sync_controls(True)
                self.apply_generator_values(source="on_pattern")
                self.refresh_display()

    def sync_controls(self, to_text=True):
        # print (f"Sync-Control called: {to_text}")
        try:
            wd = float(Length(self.text_width.GetValue()))
        except ValueError:
            wd = 0
        try:
            ht = float(Length(self.text_height.GetValue()))
        except ValueError:
            ht = 0
        if to_text:
            rotation = self.slider_rotate.GetValue()
            angle_value = rotation / 360 * tau
            self.text_rotate.ChangeValue(Angle(angle_value).angle_degrees)
            self.slider_rotate_label.SetLabel(f"{rotation}°")
            cell_x = self.slider_width.GetValue()
            cell_y = self.slider_height.GetValue()
            offset_x = self.slider_offset_x.GetValue()
            offset_y = self.slider_offset_y.GetValue()
            units = self.context.units_name
            cx = cell_x / _FACTOR * wd
            cy = cell_y / _FACTOR * ht
            self.text_cell_width.ChangeValue(
                Length(amount=cx, preferred_units=units).preferred_length
            )
            self.text_cell_height.ChangeValue(
                Length(amount=cy, preferred_units=units).preferred_length
            )

            self.text_cell_offset_x.ChangeValue(
                Length(
                    amount=cx * offset_x / _FACTOR, preferred_units=units
                ).preferred_length
            )
            self.text_cell_offset_y.ChangeValue(
                Length(
                    amount=cy * offset_y / _FACTOR, preferred_units=units
                ).preferred_length
            )
        else:
            try:
                ang = int(Angle(self.text_rotate.GetValue()).degrees + 0.5)
            except ValueError as e:
                ang = 0
            if self.slider_rotate.GetValue() != ang:
                self.slider_rotate.SetValue(ang)
                self.hinge_rotate = ang
                self.slider_rotate_label.SetLabel(f"{ang}°")

            try:
                cx = float(Length(self.text_cell_width.GetValue()))
            except ValueError:
                cx = 0
            try:
                cy = float(Length(self.text_cell_height.GetValue()))
            except ValueError:
                cy = 0
            try:
                offset_x = float(Length(self.text_cell_offset_x.GetValue()))
            except ValueError:
                offset_x = 0
            try:
                offset_y = float(Length(self.text_cell_offset_y.GetValue()))
            except ValueError:
                offset_y = 0
            if wd != 0:
                px = int(_FACTOR * cx / wd)
            else:
                px = _FACTOR
            if ht != 0:
                py = int(_FACTOR * cy / ht)
            else:
                py = _FACTOR
            if self.slider_width.GetValue() != px and px != 0:
                self.hinge_cells_x = px
                self.slider_width.SetValue(px)
                self.slider_width_label.SetLabel(f"{self.hinge_cells_x/_FACTOR:.1%}")
            if self.slider_height.GetValue() != py and py != 0:
                self.hinge_cells_y = py
                self.slider_height.SetValue(py)
                self.slider_height_label.SetLabel(f"{self.hinge_cells_y/_FACTOR:.1%}")
            if cx != 0:
                px = int(_FACTOR * offset_x / cx)
            else:
                px = 0
            if cy != 0:
                py = int(_FACTOR * offset_y / cy)
            else:
                py = 0
            if self.slider_offset_x.GetValue() != px:
                self.hinge_padding_x = px
                self.slider_offset_x.SetValue(px)
                self.slider_offx_label.SetLabel(f"{px/_FACTOR:.1%}")
            if self.slider_offset_y.GetValue() != py:
                self.hinge_padding_y = py
                self.slider_offset_y.SetValue(py)
                self.slider_offy_label.SetLabel(f"{py/_FACTOR:.1%}")

    def on_option_update(self, event):
        """
        Generic update within a pattern
        """
        if event:
            # origin = event.GetEventObject()
            # print (f"Event was called with: {str(origin)}, type={event.GetEventType()}")
            event.Skip()
            # Wait until the user has stopped to move the slider
            if (
                not self.context.process_while_sliding
                and wx.GetMouseState().LeftIsDown()
            ):
                return
        if self.in_change_event:
            return
        self.in_change_event = True
        if event is None:
            origin = None
        else:
            origin = event.GetEventObject()
            if event.GetEventType() == wx.wxEVT_TEXT and not getattr(
                self.context.root, "process_while_typing", False
            ):
                self.in_change_event = False
                return
            if origin is self.text_rotate:
                # Angle checks...
                newvalue = origin.GetValue().strip().lower()
                # Some basic checks:
                # a) Empty?
                # b) Is it a valid length?
                # c) Does it have a unit at the end?
                if len(newvalue) == 0:
                    self.in_change_event = False
                    return
                try:
                    testangle = float(Angle(newvalue))
                except ValueError:
                    self.in_change_event = False
                    return
            elif isinstance(origin, TextCtrl):
                newvalue = origin.GetValue().strip().lower()
                # Some basic checks:
                # a) Empty?
                # b) Is it a valid length?
                # c) Does it have a unit at the end?
                if len(newvalue) == 0:
                    self.in_change_event = False
                    return
                try:
                    testlen = float(Length(newvalue))
                except ValueError:
                    self.in_change_event = False
                    return
                valid = False
                for unit in ACCEPTED_UNITS:
                    if unit == "" or unit == "%":
                        # no relative units or no units at all
                        continue
                    if newvalue.endswith(unit):
                        valid = True
                        break
                if not valid:
                    self.in_change_event = False
                    return
        # etype = event.GetEventType()
        sync_direction = True
        if (
            origin is self.text_cell_height
            or origin is self.text_cell_width
            or origin is self.text_cell_offset_x
            or origin is self.text_cell_offset_y
            or origin is self.text_rotate
        ):
            sync_direction = False

        try:
            wd = float(Length(self.text_width.GetValue()))
            if wd > 0:
                self.hinge_width = self.text_width.GetValue()
        except ValueError:
            pass
        try:
            ht = float(Length(self.text_height.GetValue()))
            if ht > 0:
                self.hinge_height = self.text_height.GetValue()
        except ValueError:
            pass
        try:
            x = float(Length(self.text_origin_x.GetValue()))
            self.hinge_origin_x = self.text_origin_x.GetValue()
        except ValueError:
            pass
        try:
            y = float(Length(self.text_origin_y.GetValue()))
            self.hinge_origin_y = self.text_origin_y.GetValue()
        except ValueError:
            pass
        cell_x = self.slider_width.GetValue()
        cell_y = self.slider_height.GetValue()
        self.hinge_cells_x = cell_x
        self.hinge_cells_y = cell_y
        self.slider_width_label.SetLabel(f"{self.hinge_cells_x/_FACTOR:.1%}")
        self.slider_height_label.SetLabel(f"{self.hinge_cells_y/_FACTOR:.1%}")

        offset_x = self.slider_offset_x.GetValue()
        offset_y = self.slider_offset_y.GetValue()
        self.hinge_padding_x = offset_x
        self.hinge_padding_y = offset_y
        self.slider_offx_label.SetLabel(f"{self.hinge_padding_x/_FACTOR:.1%}")
        self.slider_offy_label.SetLabel(f"{self.hinge_padding_y/_FACTOR:.1%}")
        self.hinge_rotate = self.slider_rotate.GetValue()
        self.slider_rotate_label.SetLabel(f"{self.hinge_rotate}°")


        p_a = self.slider_param_a.GetValue() / 10.0
        p_b = self.slider_param_b.GetValue() / 10.0
        self.hinge_param_a = p_a
        self.hinge_param_b = p_b

        self.sync_controls(to_text=sync_direction)
        self._save_settings()
        self.apply_generator_values("on_option_update")
        self.refresh_display()
        self.in_change_event = False

    def _setup_settings(self):
        firstpattern = self.patterns[0]
        for pattern, recommended in zip(self.patterns, self.defaults):
            default = (
                pattern,
                200,
                200,
                recommended[0],
                recommended[1],
                recommended[2],
                recommended[3],
            )
            self.context.setting(list, f"hinge_{pattern}", default)
        self.context.setting(str, "hinge_type", firstpattern)

    def apply(self):
        self.refresh_display()

    def _save_settings(self):
        pattern = self.context.hinge_type
        default = (
            pattern,
            self.hinge_cells_x,
            self.hinge_cells_y,
            self.hinge_padding_x,
            self.hinge_padding_y,
            self.hinge_param_a,
            self.hinge_param_b,
            self.hinge_rotate,
        )
        setattr(self.context, f"hinge_{pattern}", default)
        # print (f"Stored defaults for {pattern}: {default}")

    def apply_generator_values(self, source:str):
        # print (f"Application of values from {source}")
        try:
            x = float(Length(self.hinge_origin_x))
        except ValueError:
            x = 0
        try:
            y = float(Length(self.hinge_origin_y))
        except ValueError:
            y = 0
        try:
            wd = float(Length(self.hinge_width))
        except ValueError:
            wd = float(Length("5cm"))
        try:
            ht = float(Length(self.hinge_height))
        except ValueError:
            ht = float(Length("5cm"))
        if self.hinge_cells_x <= 0:
            # print (f"Needed to reset x (reload={reload}, entry={entry})")
            self.hinge_cells_x = 200
        if self.hinge_cells_y <= 0:
            # print ("Needed to reset y")
            self.hinge_cells_y = 200
        self.hinge_generator.set_hinge_area(x, y, wd, ht)
        self.hinge_generator.set_cell_values(self.hinge_cells_x, self.hinge_cells_y)
        self.hinge_generator.set_padding_values(
            self.hinge_padding_x, self.hinge_padding_y
        )
        self.hinge_generator.set_additional_parameters(
            self.hinge_param_a, self.hinge_param_b
        )
        self.hinge_generator.set_rotation(self.hinge_rotate)

    def _restore_settings(self, reload=False, source=""):
        require_sync = False
        pattern = self.context.hinge_type
        if pattern not in self.patterns:
            pattern = self.patterns[0]
            self.context.hinge_type = pattern

        if reload:
            default = getattr(self.context, f"hinge_{pattern}", None)
            # print (f"Got defaults for {pattern}: {default}")
            # for i, s in enumerate(default):
            #     print (f"#{i} = {s} ({type(s).__name__})")
            if default is None or len(default) < 7:
                # strange
                # print(f"Could not get a setting for {pattern}: {default}")
                return
            self.hinge_cells_x = default[1]
            self.hinge_cells_y = default[2]
            self.hinge_padding_x = default[3]
            self.hinge_padding_y = default[4]
            self.hinge_param_a = default[5]
            self.hinge_param_b = default[6]
            if len(default) > 7:
                self.hinge_rotate = float(default[7])

        entry = self.context.lookup(f"pattern/{pattern}")
        flag, info1, info2 = self.hinge_generator.set_predefined_pattern(entry)
        self.slider_param_a.Enable(flag)
        self.slider_param_b.Enable(flag)
        self.slider_param_a.Show(flag)
        self.slider_param_b.Show(flag)
        if not info1:
            info1 = "Change the shape appearance"
        if not info2:
            info2 = "Change the shape appearance"
        self.slider_param_a.SetToolTip(_(info1))
        self.slider_param_b.SetToolTip(_(info2))
        if self.combo_style.GetSelection() != self.patterns.index(
            self.context.hinge_type
        ):
            self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        # if self.text_origin_x.GetValue() != self.hinge_origin_x:
        #     self.text_origin_x.ChangeValue(self.hinge_origin_x)
        # if self.text_origin_y.GetValue() != self.hinge_origin_y:
        #     self.text_origin_y.ChangeValue(self.hinge_origin_y)
        # if self.text_width.GetValue() != self.hinge_width:
        #     self.text_width.ChangeValue(self.hinge_width)
        # if self.text_height.GetValue() != self.hinge_height:
        #     self.text_height.ChangeValue(self.hinge_height)
        if self.slider_rotate.GetValue() != self.hinge_rotate:
            self.slider_rotate.SetValue(int(self.hinge_rotate))
            self.slider_rotate_label.SetLabel(f"{self.hinge_rotate}°")
            require_sync = True
        if self.slider_width.GetValue() != self.hinge_cells_x:
            self.slider_width.SetValue(self.hinge_cells_x)
            self.slider_width_label.SetLabel(f"{self.hinge_cells_x/_FACTOR:.1%}")
            require_sync = True
        if self.slider_height.GetValue() != self.hinge_cells_y:
            self.slider_height.SetValue(self.hinge_cells_y)
            self.slider_height_label.SetLabel(f"{self.hinge_cells_y/_FACTOR:.1%}")
            require_sync = True
        if self.slider_offset_x.GetValue() != self.hinge_padding_x:
            self.slider_offset_x.SetValue(self.hinge_padding_x)
            self.slider_offx_label.SetLabel(f"{self.hinge_padding_x/_FACTOR:.1%}")
            require_sync = True
        if self.slider_offset_y.GetValue() != self.hinge_padding_y:
            self.slider_offset_y.SetValue(self.hinge_padding_y)
            self.slider_offy_label.SetLabel(f"{self.hinge_padding_y/_FACTOR:.1%}")
            require_sync = True
        if self.slider_param_a.GetValue() != int(10 * self.hinge_param_a):
            self.slider_param_a.SetValue(int(10 * self.hinge_param_a))
        if self.slider_param_b.GetValue() != int(10 * self.hinge_param_b):
            self.slider_param_b.SetValue(int(10 * self.hinge_param_b))
        wd = self.hinge_generator.width
        ht = self.hinge_generator.height
        flag = wd > 0 and ht > 0 and self.hinge_generator.outershape is not None
        self.button_generate.Enable(flag)
        self.Layout()
        return require_sync

    def pane_show(self):
        time_call = perf_counter()
        if self.in_show_event or time_call - self.last_show_event < 0.5:
            return
        self.last_show_event = time_call
        self.in_show_event = True
        units = self.context.units_name
        flag = True
        for node in self.context.elements.elems(emphasized=True):
            if hasattr(node, "as_path"):
                bounds = node.bbox()
                self.hinge_generator.set_hinge_shape(node)
                flag = False
                self.button_generate.Enable(True)
                break
        if flag:
            self.hinge_generator.set_hinge_shape(None)
            self.button_generate.Enable(False)
            if units in ("in", "inch"):
                s = "2in"
            else:
                s = "5cm"
            bounds = (0, 0, float(Length(s)), float(Length(s)))
        # self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        start_x = bounds[0]
        start_y = bounds[1]
        wd = bounds[2] - bounds[0]
        ht = bounds[3] - bounds[1]
        self.hinge_origin_x = Length(
            amount=start_x, digits=3, preferred_units=units
        ).preferred_length
        self.hinge_origin_y = Length(
            amount=start_y, digits=3, preferred_units=units
        ).preferred_length
        self.hinge_width = Length(
            amount=wd, digits=2, preferred_units=units
        ).preferred_length
        self.hinge_height = Length(
            amount=ht, digits=2, preferred_units=units
        ).preferred_length
        self.text_origin_x.ChangeValue(self.hinge_origin_x)
        self.text_origin_y.ChangeValue(self.hinge_origin_y)
        self.text_width.ChangeValue(self.hinge_width)
        self.text_height.ChangeValue(self.hinge_height)
        self.text_origin_x.Enable(flag)
        self.text_origin_y.Enable(flag)
        self.text_width.Enable(flag)
        self.text_height.Enable(flag)
        self.hinge_generator.set_hinge_area(start_x, start_y, wd, ht)
        self.sync_controls(True)
        self.apply_generator_values(source="pane_show")
        self.refresh_display()
        self.in_show_event = False


class LivingHingeTool(MWindow):
    """
    LivingHingeTool is the wrapper class to set up the
    required calls to open the HingePanel window
    In addition it listens to element selection and passes this
    information to HingePanel
    """

    def __init__(self, *args, **kwds):
        super().__init__(570, 420, submenu="Laser-Tools", *args, **kwds)
        self.panel_template = HingePanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.sizer.Add(self.panel_template, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_hinges.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Living-Hinges"))
        self.Layout()
        self.Bind(wx.EVT_ACTIVATE, self.window_active, self)
        self.restore_aspect()

    def window_open(self):
        self.panel_template.pane_show()

    def window_close(self):
        pass

    def window_active(self, event):
        self.panel_template.pane_show()

    @signal_listener("emphasized")
    def on_emphasized_elements_changed(self, origin, *args):
        self.context.elements.set_start_time("living hinges")
        self.panel_template.pane_show()
        self.context.elements.set_end_time("living hinges", display=True)

    @staticmethod
    def submenu():
        return "Laser-Tools", "Living-Hinges"

    @staticmethod
    def helptext():
        return _("Create a living hinges pattern")

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/extended_tools/LivingHinge",
            {
                "label": _("Hinge"),
                "icon": icon_hinges,
                "tip": _("Fill area with a living hinge pattern"),
                "help": "hinges",
                "action": lambda v: kernel.console("window open Hingetool\n"),
                "size": STD_ICON_SIZE,
                "rule_enabled": lambda cond: len(
                    list(kernel.elements.elems(emphasized=True))
                )
                > 0,
            },
        )
