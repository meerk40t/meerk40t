import wx

from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer

from ...core.units import Angle, Length
from ...svgelements import Matrix
from ..wxutils import TextCtrl, set_ctrl_value, wxCheckBox, wxComboBox
from .attributes import ColorPanel, IdPanel

_ = wx.GetTranslation


class HatchPropertyPanel(ScrolledPanel):
    name = _("Hatch")

    def __init__(self, *args, context=None, node=None, **kwds):
        # super().__init__(parent)
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )
        self.node = node
        self.panels = []
        self.SetHelpText("hatches")

        self._Buffer = None

        main_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Hatch:"), wx.VERTICAL)

        # `Id` at top in all cases...
        panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=self.node)
        main_sizer.Add(panel_id, 1, wx.EXPAND, 0)
        self.panels.append(panel_id)
        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        main_sizer.Add(panel_stroke, 1, wx.EXPAND, 0)
        self.panels.append(panel_stroke)

        # panel_fill = ColorPanel(
        #     self,
        #     id=wx.ID_ANY,
        #     context=self.context,
        #     label="Fill:",
        #     attribute="fill",
        #     callback=self.callback_color,
        #     node=self.node,
        # )
        # main_sizer.Add(panel_fill, 1, wx.EXPAND, 0)

        sizer_loops = StaticBoxSizer(self, wx.ID_ANY, _("Loops"), wx.HORIZONTAL)
        self.text_loops = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.loops),
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_loops.Add(self.text_loops, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.slider_loops = wx.Slider(self, wx.ID_ANY, 0, 0, 100)
        sizer_loops.Add(self.slider_loops, 3, wx.EXPAND, 0)
        main_sizer.Add(sizer_loops, 1, wx.EXPAND, 0)

        sizer_distance = StaticBoxSizer(
            self, wx.ID_ANY, _("Hatch Distance:"), wx.HORIZONTAL
        )
        main_sizer.Add(sizer_distance, 0, wx.EXPAND, 0)

        self.text_distance = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.hatch_distance),
            limited=True,
            check="length",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_distance.Add(self.text_distance, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_angle = StaticBoxSizer(self, wx.ID_ANY, _("Angle"), wx.HORIZONTAL)
        self.text_angle = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.hatch_angle),
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_angle.Add(self.text_angle, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.slider_angle = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        sizer_angle.Add(self.slider_angle, 3, wx.EXPAND, 0)
        main_sizer.Add(sizer_angle, 1, wx.EXPAND, 0)

        sizer_angle_delta = StaticBoxSizer(
            self, wx.ID_ANY, _("Angle Delta"), wx.HORIZONTAL
        )
        self.text_angle_delta = TextCtrl(
            self,
            wx.ID_ANY,
            str(node.hatch_angle_delta),
            limited=True,
            check="angle",
            style=wx.TE_PROCESS_ENTER,
        )
        sizer_angle_delta.Add(self.text_angle_delta, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.slider_angle_delta = wx.Slider(self, wx.ID_ANY, 0, 0, 360)
        sizer_angle_delta.Add(self.slider_angle_delta, 3, wx.EXPAND, 0)
        main_sizer.Add(sizer_angle_delta, 1, wx.EXPAND, 0)
        sizer_fill = StaticBoxSizer(self, wx.ID_ANY, _("Fill Style"), wx.VERTICAL)
        main_sizer.Add(sizer_fill, 6, wx.EXPAND, 0)

        self.fills = list(self.context.match("hatch", suffix=True))
        self.combo_fill_style = wxComboBox(
            self, wx.ID_ANY, choices=self.fills, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_fill.Add(self.combo_fill_style, 0, wx.EXPAND, 0)

        self.display_panel = wx.Panel(self, wx.ID_ANY)
        sizer_fill.Add(self.display_panel, 6, wx.EXPAND, 0)

        self.check_classify = wxCheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)
        main_sizer.Add(self.check_classify, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

        self.text_loops.SetActionRoutine(self.on_text_loops)
        self.text_distance.SetActionRoutine(self.on_text_distance)
        self.text_angle.SetActionRoutine(self.on_text_angle)
        self.text_angle_delta.SetActionRoutine(self.on_text_angle_delta)
        self.check_classify.Bind(wx.EVT_CHECKBOX, self.on_check_classify)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_loops, self.slider_loops)
        self.Bind(wx.EVT_COMMAND_SCROLL, self.on_slider_angle, self.slider_angle)
        self.Bind(
            wx.EVT_COMMAND_SCROLL, self.on_slider_angle_delta, self.slider_angle_delta
        )
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_fill, self.combo_fill_style)
        # end wxGlade
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.display_panel.Bind(wx.EVT_PAINT, self.on_display_paint)
        self.display_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_display_erase)

        self.raster_pen = wx.Pen()
        self.raster_pen.SetColour(wx.Colour(0, 0, 0, 180))
        self.raster_pen.SetWidth(1)

        self.travel_pen = wx.Pen()
        self.travel_pen.SetColour(wx.Colour(255, 127, 255, 127))
        self.travel_pen.SetWidth(1)

        self.outline_pen = wx.Pen()
        self.outline_pen.SetColour(wx.Colour(0, 127, 255, 127))
        self.outline_pen.SetWidth(1)

        self.hatch_lines = None
        self.travel_lines = None
        self.outline_lines = None

        self.Layout()

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    @staticmethod
    def accepts(node):
        return node.type in ("effect hatch",)

    def set_widgets(self, node):
        for panel in self.panels:
            panel.set_widgets(node)
        self.node = node
        if self.node is None or not self.accepts(node):
            self.Hide()
            return
        i = 0
        for ht in self.fills:
            if ht == self.node.hatch_type:
                break
            i += 1
        if i == len(self.fills):
            i = 0
        self.combo_fill_style.SetSelection(i)
        try:
            if self.node.hatch_angle is None:
                ang = 0
            elif isinstance(self.node.hatch_angle, float):
                ang = self.node.hatch_angle
            else:
                ang = Angle(self.node.hatch_angle).radians
        except ValueError:
            ang = 0
        set_ctrl_value(self.text_angle, f"{Angle(ang, digits=1).angle_degrees}")

        try:
            if self.node.hatch_angle_delta is None:
                ang = 0
            elif isinstance(self.node.hatch_angle_delta, float):
                ang = self.node.hatch_angle_delta
            else:
                ang = Angle(self.node.hatch_angle_delta).radians
        except ValueError:
            ang = 0
        set_ctrl_value(self.text_angle_delta, f"{Angle(ang, digits=1).angle_degrees}")

        set_ctrl_value(self.text_distance, str(self.node.hatch_distance))
        try:
            h_angle = float(Angle(self.node.hatch_angle).degrees)
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass
        try:
            h_angle = float(Angle(self.node.hatch_angle_delta).degrees)
            self.slider_angle_delta.SetValue(int(h_angle))
        except ValueError:
            pass
        self.Show()

    def on_check_classify(self, event):
        self.context._auto_classify = self.check_classify.GetValue()

    def update_label(self):
        return

    def update(self):
        self.node.modified()
        self.hatch_lines = None
        self.travel_lines = None
        self.refresh_display()
        self.context.elements.signal("element_property_reload", self.node)

    def callback_color(self):
        self.node.altered()
        self.update_label()
        self.Refresh()
        if self.check_classify.GetValue():
            # _("Color classify")
            with self.context.elements.undoscope("Color classify"):
                mynode = self.node
                wasemph = self.node.emphasized
                data = [self.node]
                self.context.elements.remove_elements_from_operations(data)
                self.context.elements.classify(data)
            self.context.elements.signal("tree_changed")
            self.context.elements.signal("element_property_reload", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)

    def on_text_loops(self):
        try:
            loops = int(self.text_loops.GetValue())
            if loops == self.node.loops:
                return
            self.node.loops = loops
        except ValueError:
            return
        try:
            h_loops = int(self.node.loops)
            self.slider_loops.SetValue(int(h_loops))
        except ValueError:
            pass
        self.update()

    def on_slider_loops(self, event):
        value = self.slider_loops.GetValue()
        self.text_loops.SetValue(str(value))
        self.on_text_loops()

    def on_text_distance(self):
        try:
            dist = Length(self.text_distance.GetValue()).length_mm
            if dist == self.node.distance:
                return
            self.node.hatch_distance = dist
            self.node.distance = dist
        except ValueError:
            pass
        self.update()

    def on_text_angle(self):
        try:
            angle = Angle(self.text_angle.GetValue()).angle_degrees
            if angle == self.node.hatch_angle:
                return
            self.node.hatch_angle = angle
            self.node.angle = angle

        except ValueError:
            return
        try:
            h_angle = float(Angle(self.node.angle).degrees)
            while h_angle > self.slider_angle.GetMax():
                h_angle -= 360
            while h_angle < self.slider_angle.GetMin():
                h_angle += 360
            self.slider_angle.SetValue(int(h_angle))
        except ValueError:
            pass
        self.update()

    def on_slider_angle(self, event):
        value = self.slider_angle.GetValue()
        self.text_angle.SetValue(f"{value}deg")
        self.on_text_angle()

    def on_text_angle_delta(self):
        try:
            angle = Angle(self.text_angle_delta.GetValue()).angle_degrees
            if angle == self.node.hatch_angle_delta:
                return
            self.node.hatch_angle_delta = angle
            self.node.delta = angle
        except ValueError:
            return
        try:
            h_angle_delta = float(Angle(self.node.delta).degrees)
            while h_angle_delta > self.slider_angle_delta.GetMax():
                h_angle_delta -= 360
            while h_angle_delta < self.slider_angle_delta.GetMin():
                h_angle_delta += 360
            self.slider_angle_delta.SetValue(int(h_angle_delta))
        except ValueError:
            pass
        self.update()

    def on_slider_angle_delta(self, event):
        value = self.slider_angle_delta.GetValue()
        self.text_angle_delta.SetValue(f"{value}deg")
        self.on_text_angle_delta()

    def on_combo_fill(self, event):  # wxGlade: HatchSettingsPanel.<event_handler>
        hatch_type = self.fills[int(self.combo_fill_style.GetSelection())]
        self.node.hatch_type = hatch_type
        self.update()

    def on_display_paint(self, event=None):
        if self._Buffer is None:
            return
        try:
            wx.BufferedPaintDC(self.display_panel, self._Buffer)
        except RuntimeError:
            pass

    def on_display_erase(self, event=None):
        pass

    def set_buffer(self):
        width, height = self.display_panel.ClientSize
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._Buffer = wx.Bitmap(width, height)

    def on_size(self, event=None):
        self.Layout()
        self.set_buffer()
        self.hatch_lines = None
        self.travel_lines = None
        self.refresh_display()

    def refresh_display(self):
        # print(
        #     f"Distance={self.node.distance} / {self.node.hatch_distance} / {self.node.settings.get('hatch_distance', '')}"
        # )
        # print(
        #     f"Angle={self.node.angle} / {self.node.hatch_angle} / {self.node.settings.get('hatch_angle', '')}"
        # )
        if not wx.IsMainThread():
            wx.CallAfter(self.refresh_in_ui)
        else:
            self.refresh_in_ui()

    def calculate_hatch_lines(self):
        # from time import perf_counter

        # print(f"Calculate hatch lines {perf_counter():.3f}")
        w, h = self._Buffer.Size
        hatch_type = self.node.hatch_type
        hatch_algorithm = self.context.lookup(f"hatch/{hatch_type}")
        if hatch_algorithm is None:
            return
        paths = (
            complex(w * 0.05, h * 0.05),
            complex(w * 0.95, h * 0.05),
            complex(w * 0.95, h * 0.95),
            complex(w * 0.05, h * 0.95),
            complex(w * 0.05, h * 0.05),
            None,
            complex(w * 0.25, h * 0.25),
            complex(w * 0.75, h * 0.25),
            complex(w * 0.75, h * 0.75),
            complex(w * 0.25, h * 0.75),
            complex(w * 0.25, h * 0.25),
        )
        matrix = Matrix.scale(0.018)
        hatch = list(
            hatch_algorithm(
                settings=self.node.__dict__,
                outlines=paths,
                matrix=matrix,
                limit=1000,
            )
        )
        o_start = []
        o_end = []
        last = None
        for c in paths:
            if last is not None and c is not None:
                o_start.append((c.real, c.imag))
                o_end.append((last.real, last.imag))
            last = c
        self.outline_lines = o_start, o_end
        h_start = []
        h_end = []
        t_start = []
        t_end = []
        last_x = None
        last_y = None
        travel = True
        for p in hatch:
            if p is None:
                travel = True
                continue
            x, y = p
            if last_x is None:
                last_x = x
                last_y = y
                travel = False
                continue
            if travel:
                t_start.append((last_x, last_y))
                t_end.append((x, y))
            else:
                h_start.append((last_x, last_y))
                h_end.append((x, y))
            travel = False
            last_x = x
            last_y = y
        self.hatch_lines = h_start, h_end
        self.travel_lines = t_start, t_end

    def refresh_in_ui(self):
        """Performs redrawing of the data in the UI thread."""
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.Shown:
            if self.hatch_lines is None:
                self.calculate_hatch_lines()
            if self.hatch_lines is not None:
                starts, ends = self.hatch_lines
                if len(starts):
                    gc.SetPen(self.raster_pen)
                    gc.StrokeLineSegments(starts, ends)
                else:
                    font = wx.Font(
                        14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
                    )
                    gc.SetFont(font, wx.BLACK)
                    gc.DrawText(_("No hatch preview..."), 0, 0)
            if self.travel_lines is not None:
                starts, ends = self.travel_lines
                if len(starts):
                    gc.SetPen(self.travel_pen)
                    gc.StrokeLineSegments(starts, ends)
            if self.outline_lines is not None:
                starts, ends = self.outline_lines
                if len(starts):
                    gc.SetPen(self.outline_pen)
                    gc.StrokeLineSegments(starts, ends)
        gc.Destroy()
        dc.SelectObject(wx.NullBitmap)
        del dc
        self.display_panel.Refresh()
        self.display_panel.Update()
