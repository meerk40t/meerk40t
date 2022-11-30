from copy import deepcopy

import wx

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.gui.wxutils import StaticBoxSizer

_ = wx.GetTranslation


class ContrastPanel(wx.Panel):
    name = _("Contrast")
    priority = 10

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "contrast":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable_contrast = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset_contrast = wx.Button(self, wx.ID_ANY, _("Reset"))
        self.slider_contrast_contrast = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_contrast_contrast = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_contrast_brightness = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_contrast_brightness = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_enable_contrast, self.check_enable_contrast
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_reset_contrast, self.button_reset_contrast
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_contrast_contrast,
            self.slider_contrast_contrast,
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_contrast_brightness,
            self.slider_contrast_brightness,
        )
        # end wxGlade

        op = None
        for n in node.operations:
            if n.get("name") == "contrast":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable_contrast.SetValue(self.op["enable"])
        self.text_contrast_contrast.SetValue(str(self.op["contrast"]))
        self.text_contrast_brightness.SetValue(str(self.op["brightness"]))
        self.slider_contrast_contrast.SetValue(self.op["contrast"])
        self.slider_contrast_brightness.SetValue(self.op["brightness"])

    def __set_properties(self):
        # begin wxGlade: ContrastPanel.__set_properties
        self.check_enable_contrast.SetToolTip(_("Enable Contrast"))
        self.check_enable_contrast.SetValue(1)
        self.button_reset_contrast.SetToolTip(_("Reset Contrast"))
        self.slider_contrast_contrast.SetToolTip(_("Contrast amount"))
        self.text_contrast_contrast.SetToolTip(
            _("Contrast the lights and darks by how much?")
        )
        self.slider_contrast_brightness.SetToolTip(_("Brightness amount"))
        self.text_contrast_brightness.SetToolTip(
            _("Make the image how much more bright?")
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ContrastPanel.__do_layout
        sizer_contrast = StaticBoxSizer(self, wx.ID_ANY, _("Contrast"), wx.VERTICAL)
        sizer_contrast_brightness = StaticBoxSizer(
            self, wx.ID_ANY, _("Brightness Amount"), wx.HORIZONTAL
        )
        sizer_contrast_contrast = StaticBoxSizer(
            self, wx.ID_ANY, _("Contrast Amount"), wx.HORIZONTAL
        )
        sizer_contrast_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_contrast_main.Add(self.check_enable_contrast, 0, 0, 0)
        sizer_contrast_main.Add(self.button_reset_contrast, 0, 0, 0)
        sizer_contrast.Add(sizer_contrast_main, 0, wx.EXPAND, 0)
        sizer_contrast_contrast.Add(self.slider_contrast_contrast, 5, wx.EXPAND, 0)
        sizer_contrast_contrast.Add(self.text_contrast_contrast, 1, 0, 0)
        sizer_contrast.Add(sizer_contrast_contrast, 0, wx.EXPAND, 0)
        sizer_contrast_brightness.Add(self.slider_contrast_brightness, 5, wx.EXPAND, 0)
        sizer_contrast_brightness.Add(self.text_contrast_brightness, 1, 0, 0)
        sizer_contrast.Add(sizer_contrast_brightness, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_contrast)
        sizer_contrast.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable_contrast(
        self, event=None
    ):  # wxGlade: ContrastPanel.<event_handler>
        self.op["enable"] = self.check_enable_contrast.GetValue()
        self.node.update(self.context)

    def on_button_reset_contrast(
        self, event=None
    ):  # wxGlade: ContrastPanel.<event_handler>
        self.op["contrast"] = self.original_op["contrast"]
        self.op["brightness"] = self.original_op["brightness"]
        self.text_contrast_contrast.SetValue(str(self.op["contrast"]))
        self.text_contrast_brightness.SetValue(str(self.op["brightness"]))
        self.slider_contrast_contrast.SetValue(self.op["contrast"])
        self.slider_contrast_brightness.SetValue(self.op["brightness"])
        self.node.update(self.context)

    def on_slider_contrast_contrast(
        self, event=None
    ):  # wxGlade: ContrastPanel.<event_handler>
        self.op["contrast"] = int(self.slider_contrast_contrast.GetValue())
        self.text_contrast_contrast.SetValue(str(self.op["contrast"]))
        self.node.update(self.context)

    def on_slider_contrast_brightness(
        self, event=None
    ):  # wxGlade: ContrastPanel.<event_handler>
        self.op["brightness"] = int(self.slider_contrast_brightness.GetValue())
        self.text_contrast_brightness.SetValue(str(self.op["brightness"]))
        self.node.update(self.context)


class HalftonePanel(wx.Panel):
    name = _("Halftone")
    priority = 15

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "halftone":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable_halftone = wx.CheckBox(self, wx.ID_ANY, "Enable")
        self.button_reset_halftone = wx.Button(self, wx.ID_ANY, "Reset")
        self.check_halftone_black = wx.CheckBox(self, wx.ID_ANY, "Black")
        self.slider_halftone_sample = wx.Slider(
            self, wx.ID_ANY, 10, 0, 50, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_halftone_sample = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_halftone_angle = wx.Slider(
            self, wx.ID_ANY, 22, 0, 90, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_halftone_angle = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_halftone_oversample = wx.Slider(
            self, wx.ID_ANY, 2, 0, 50, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_halftone_oversample = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_enable_halftone, self.check_enable_halftone
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_reset_halftone, self.button_reset_halftone
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_halftone_black, self.check_halftone_black
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_halftone_sample, self.slider_halftone_sample
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_halftone_angle, self.slider_halftone_angle
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_halftone_oversample,
            self.slider_halftone_oversample,
        )
        # end wxGlade
        op = None
        for n in node.operations:
            if n.get("name") == "halftone":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable_halftone.SetValue(self.op["enable"])
        self.check_halftone_black.SetValue(self.op["black"])
        self.text_halftone_sample.SetValue(str(self.op["sample"]))
        self.slider_halftone_sample.SetValue(self.op["sample"])
        self.text_halftone_angle.SetValue(str(self.op["angle"]))
        self.slider_halftone_angle.SetValue(self.op["angle"])
        self.text_halftone_oversample.SetValue(str(self.op["oversample"]))
        self.slider_halftone_oversample.SetValue(self.op["oversample"])

    def __set_properties(self):
        # begin wxGlade: HalftonePanel.__set_properties
        self.check_enable_halftone.SetToolTip(_("Enable Halftone"))
        self.check_enable_halftone.SetValue(1)
        self.button_reset_halftone.SetToolTip(_("Halftone Reset"))
        self.check_halftone_black.SetToolTip(_("Use black rather than white dots"))
        self.slider_halftone_sample.SetToolTip(_("Sample size for halftone dots"))
        self.text_halftone_sample.SetToolTip(_("Halftone dot size"))
        self.slider_halftone_angle.SetToolTip(_("Angle for halftone dots"))
        self.text_halftone_angle.SetToolTip(_("Halftone dot angle"))
        self.slider_halftone_oversample.SetToolTip(
            _("Oversampling amount for halftone-dots")
        )
        self.text_halftone_oversample.SetToolTip(_("Halftone dot oversampling amount"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: HalftonePanel.__do_layout
        sizer_halftone = StaticBoxSizer(self, wx.ID_ANY, _("Halftone"), wx.VERTICAL)
        sizer_halftone_oversample = StaticBoxSizer(
            self, wx.ID_ANY, _("Oversample"), wx.HORIZONTAL
        )
        sizer_halftone_angle = StaticBoxSizer(
            self, wx.ID_ANY, _("Angle"), wx.HORIZONTAL
        )
        sizer_halftone_sample = StaticBoxSizer(
            self, wx.ID_ANY, _("Sample"), wx.HORIZONTAL
        )
        sizer_halftone_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_halftone_main.Add(self.check_enable_halftone, 0, 0, 0)
        sizer_halftone_main.Add(self.button_reset_halftone, 0, 0, 0)
        sizer_halftone_main.Add((20, 20), 0, 0, 0)
        sizer_halftone_main.Add(self.check_halftone_black, 0, 0, 0)
        sizer_halftone.Add(sizer_halftone_main, 0, wx.EXPAND, 0)
        sizer_halftone_sample.Add(self.slider_halftone_sample, 5, wx.EXPAND, 0)
        sizer_halftone_sample.Add(self.text_halftone_sample, 1, 0, 0)
        sizer_halftone.Add(sizer_halftone_sample, 0, wx.EXPAND, 0)
        sizer_halftone_angle.Add(self.slider_halftone_angle, 5, wx.EXPAND, 0)
        sizer_halftone_angle.Add(self.text_halftone_angle, 1, 0, 0)
        sizer_halftone.Add(sizer_halftone_angle, 0, wx.EXPAND, 0)
        sizer_halftone_oversample.Add(self.slider_halftone_oversample, 5, wx.EXPAND, 0)
        sizer_halftone_oversample.Add(self.text_halftone_oversample, 1, 0, 0)
        sizer_halftone.Add(sizer_halftone_oversample, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_halftone)
        sizer_halftone.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable_halftone(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["enable"] = self.check_enable_halftone.GetValue()
        self.node.update(self.context)

    def on_button_reset_halftone(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["black"] = self.original_op["black"]
        self.op["sample"] = self.original_op["sample"]
        self.op["angle"] = self.original_op["angle"]
        self.op["oversample"] = self.original_op["oversample"]
        self.check_enable_halftone.SetValue(self.op["enable"])
        self.check_halftone_black.SetValue(self.op["black"])
        self.text_halftone_sample.SetValue(str(self.op["sample"]))
        self.slider_halftone_sample.SetValue(self.op["sample"])
        self.text_halftone_angle.SetValue(str(self.op["angle"]))
        self.slider_halftone_angle.SetValue(self.op["angle"])
        self.text_halftone_oversample.SetValue(str(self.op["oversample"]))
        self.slider_halftone_oversample.SetValue(self.op["oversample"])
        self.node.update(self.context)

    def on_check_halftone_black(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["black"] = self.check_halftone_black.GetValue()
        self.node.update(self.context)

    def on_slider_halftone_sample(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["sample"] = int(self.slider_halftone_sample.GetValue())
        self.text_halftone_sample.SetValue(str(self.op["sample"]))
        self.node.update(self.context)

    def on_slider_halftone_angle(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["angle"] = int(self.slider_halftone_angle.GetValue())
        self.text_halftone_angle.SetValue(str(self.op["angle"]))
        self.node.update(self.context)

    def on_slider_halftone_oversample(
        self, event=None
    ):  # wxGlade: HalftonePanel.<event_handler>
        self.op["oversample"] = int(self.slider_halftone_oversample.GetValue())
        self.text_halftone_oversample.SetValue(str(self.op["oversample"]))
        self.node.update(self.context)


class ToneCurvePanel(wx.Panel):
    name = _("Tone")
    priority = 20

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "tone":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self._tone_panel_buffer = None
        self.check_enable_tone = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset_tone = wx.Button(self, wx.ID_ANY, _("Reset"))
        self.curve_panel = wx.Panel(self, wx.ID_ANY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable_tone, self.check_enable_tone)
        self.Bind(wx.EVT_BUTTON, self.on_button_reset_tone, self.button_reset_tone)
        # end wxGlade
        self.curve_panel.Bind(wx.EVT_PAINT, self.on_tone_panel_paint)
        # self.curve_panel.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.curve_panel.Bind(wx.EVT_MOTION, self.on_curve_mouse_move)
        self.curve_panel.Bind(wx.EVT_LEFT_DOWN, self.on_curve_mouse_left_down)
        self.curve_panel.Bind(wx.EVT_LEFT_UP, self.on_curve_mouse_left_up)
        self.curve_panel.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_curve_mouse_lost)
        self.point = -1

        self.graph_brush = wx.Brush()
        self.graph_pen = wx.Pen()
        c = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)
        self.graph_brush.SetColour(c)
        self.graph_pen.SetColour(wx.Colour(255 - c[0], 255 - c[1], 255 - c[2]))
        self.graph_pen.SetWidth(5)

        op = None
        for n in node.operations:
            if n.get("name") == "tone":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable_tone.SetValue(op["enable"])
        self.Layout()
        width, height = self.curve_panel.Size
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        self._tone_panel_buffer = wx.Bitmap(width, height)
        self.update_in_gui_thread()

    def __set_properties(self):
        # begin wxGlade: ToneCurvePanel.__set_properties
        self.check_enable_tone.SetToolTip(_("Enable Tone Curve"))
        self.check_enable_tone.SetValue(1)
        self.button_reset_tone.SetToolTip(_("Reset Tone Curve"))
        self.curve_panel.SetMinSize((256, 256))
        self.curve_panel.SetMaxSize((256, 256))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ToneCurvePanel.__do_layout
        sizer_tone = StaticBoxSizer(self, wx.ID_ANY, _("Tone Curve"), wx.VERTICAL)
        sizer_tone_curve = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tone_curve.Add(self.check_enable_tone, 0, 0, 0)
        sizer_tone_curve.Add(self.button_reset_tone, 0, 0, 0)
        sizer_tone.Add(sizer_tone_curve, 0, wx.EXPAND, 0)
        sizer_tone.Add(self.curve_panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_tone)
        sizer_tone.Fit(self)
        self.Layout()
        # end wxGlade

    def update_in_gui_thread(self):
        self.on_update_tone()
        try:
            self.Refresh(True)
            self.Update()
        except RuntimeError:
            pass

    def on_tone_panel_paint(self, event=None):
        try:
            wx.BufferedPaintDC(self.curve_panel, self._tone_panel_buffer)
        except RuntimeError:
            pass

    def on_curve_mouse_move(self, event):
        if self.curve_panel.HasCapture():
            pos = event.GetPosition()
            try:
                v = 255 - pos[1]
                if self.op["type"] == "point":
                    current_x = pos[0]
                    if 0 <= current_x <= 255:
                        self.op["values"][pos[0]] = (pos[0], v)
                else:
                    self.op["values"][self.point] = (pos[0], v)
                self.node.update(self.context)
                self.update_in_gui_thread()
            except (KeyError, IndexError):
                pass

    def on_curve_mouse_left_down(self, event):
        if not self.curve_panel.HasCapture():
            self.curve_panel.CaptureMouse()
        distance = float("inf")
        pos = event.GetPosition()
        if self.op["type"] == "point":
            v = 255 - pos[1]
            self.point = pos[0]
            self.op["values"][pos[0]] = (pos[0], v)
            self.update_in_gui_thread()
        else:
            for i, q in enumerate(self.op["values"]):
                dx = pos[0] - q[0]
                dy = (255 - pos[1]) - q[1]
                d = dx * dx + dy * dy
                if d < distance:
                    distance = d
                    self.point = i

    def on_curve_mouse_left_up(self, event=None):
        if self.curve_panel.HasCapture():
            self.curve_panel.ReleaseMouse()

    def on_curve_mouse_lost(self, event=None):
        pass

    def on_update_tone(self, event=None):
        if self._tone_panel_buffer is None:
            return
        dc = wx.MemoryDC()
        dc.SelectObject(self._tone_panel_buffer)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.PushState()
        gc.SetBrush(self.graph_brush)
        gc.DrawRectangle(0, 0, *self._tone_panel_buffer.Size)
        gc.SetPen(self.graph_pen)

        tone_values = self.op["values"]
        if self.op["type"] == "spline":
            spline = ImageNode.spline(tone_values)
            starts = [(i, 255 - spline[i]) for i in range(255)]
            ends = [(i, 255 - spline[i]) for i in range(1, 256)]
        else:
            tone_values = [q for q in tone_values if q is not None]
            spline = ImageNode.line(tone_values)
            starts = [(i, 255 - spline[i]) for i in range(255)]
            ends = [(i, 255 - spline[i]) for i in range(1, 256)]
        gc.StrokeLineSegments(starts, ends)
        gc.PopState()
        gc.Destroy()
        del dc

    def on_check_enable_tone(self, event=None):  # wxGlade: RasterWizard.<event_handler>
        self.op["enable"] = self.check_enable_tone.GetValue()
        self.node.update(self.context)

    def on_button_reset_tone(self, event=None):  # wxGlade: RasterWizard.<event_handler>
        self.op["enable"] = self.original_op["enable"]
        self.op["type"] = self.original_op["type"]
        self.op["values"].clear()
        self.op["values"].extend(self.original_op["values"])
        self.node.update(self.context)
        self.on_update_tone()
        self.update_in_gui_thread()


class SharpenPanel(wx.Panel):
    name = _("Sharpen")
    priority = 25

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        if node.operations is None:
            node.operations = list()
        for n in node.operations:
            if n.get("name") == "unsharp_mask":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable_sharpen = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset_sharpen = wx.Button(self, wx.ID_ANY, _("Reset"))
        self.slider_sharpen_percent = wx.Slider(
            self, wx.ID_ANY, 500, 0, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_sharpen_percent = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_sharpen_radius = wx.Slider(
            self, wx.ID_ANY, 20, 0, 50, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_sharpen_radius = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_sharpen_threshold = wx.Slider(
            self, wx.ID_ANY, 6, 0, 50, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_sharpen_threshold = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_enable_sharpen, self.check_enable_sharpen
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_reset_sharpen, self.button_reset_sharpen
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_sharpen_percent, self.slider_sharpen_percent
        )
        self.Bind(wx.EVT_TEXT, self.on_text_sharpen_percent, self.text_sharpen_percent)
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_sharpen_radius, self.slider_sharpen_radius
        )
        self.Bind(wx.EVT_TEXT, self.on_text_sharpen_radius, self.text_sharpen_radius)
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_sharpen_threshold,
            self.slider_sharpen_threshold,
        )
        self.Bind(
            wx.EVT_TEXT, self.on_text_sharpen_threshold, self.text_sharpen_threshold
        )
        # end wxGlade

        op = None
        for n in node.operations:
            if n.get("name") == "unsharp_mask":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable_sharpen.SetValue(op["enable"])
        self.slider_sharpen_percent.SetValue(op["percent"])
        self.slider_sharpen_radius.SetValue(op["radius"])
        self.slider_sharpen_threshold.SetValue(op["threshold"])
        self.text_sharpen_percent.SetValue(str(op["percent"]))
        self.text_sharpen_radius.SetValue(str(op["radius"]))
        self.text_sharpen_threshold.SetValue(str(op["threshold"]))

    def __set_properties(self):
        # begin wxGlade: SharpenPanel.__set_properties
        self.check_enable_sharpen.SetToolTip(_("Enable Sharpen"))
        self.check_enable_sharpen.SetValue(1)
        self.button_reset_sharpen.SetToolTip(_("Sharpen Reset"))
        self.slider_sharpen_percent.SetToolTip(_("Strength of sharpening in percent"))
        self.text_sharpen_percent.SetToolTip(_("amount of sharpening in %"))
        self.slider_sharpen_radius.SetToolTip(
            _("Blur radius for the sharpening operation")
        )
        self.text_sharpen_radius.SetToolTip(_("Sharpen radius amount"))
        self.slider_sharpen_threshold.SetToolTip(
            _("Threshold controls the minimum brighteness change to be sharpened.")
        )
        self.text_sharpen_threshold.SetToolTip(_("Sharpen Threshold Amount"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SharpenPanel.__do_layout
        sizer_sharpen = StaticBoxSizer(self, wx.ID_ANY, _("Sharpen"), wx.VERTICAL)
        sizer_sharpen_threshold = StaticBoxSizer(
            self, wx.ID_ANY, _("Threshold"), wx.HORIZONTAL
        )
        sizer_sharpen_radius = StaticBoxSizer(
            self, wx.ID_ANY, _("Radius"), wx.HORIZONTAL
        )
        sizer_sharpen_percent = StaticBoxSizer(
            self, wx.ID_ANY, _("Percent"), wx.HORIZONTAL
        )
        sizer_sharpen_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sharpen_main.Add(self.check_enable_sharpen, 0, 0, 0)
        sizer_sharpen_main.Add(self.button_reset_sharpen, 0, 0, 0)
        sizer_sharpen.Add(sizer_sharpen_main, 0, wx.EXPAND, 0)
        sizer_sharpen_percent.Add(self.slider_sharpen_percent, 5, wx.EXPAND, 0)
        sizer_sharpen_percent.Add(self.text_sharpen_percent, 1, 0, 0)
        sizer_sharpen.Add(sizer_sharpen_percent, 0, wx.EXPAND, 0)
        sizer_sharpen_radius.Add(self.slider_sharpen_radius, 5, wx.EXPAND, 0)
        sizer_sharpen_radius.Add(self.text_sharpen_radius, 1, 0, 0)
        sizer_sharpen.Add(sizer_sharpen_radius, 0, wx.EXPAND, 0)
        sizer_sharpen_threshold.Add(self.slider_sharpen_threshold, 5, wx.EXPAND, 0)
        sizer_sharpen_threshold.Add(self.text_sharpen_threshold, 1, 0, 0)
        sizer_sharpen.Add(sizer_sharpen_threshold, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_sharpen)
        sizer_sharpen.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable_sharpen(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["enable"] = self.check_enable_sharpen.GetValue()
        self.node.update(self.context)

    def on_button_reset_sharpen(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["percent"] = self.original_op["percent"]
        self.op["radius"] = self.original_op["radius"]
        self.op["threshold"] = self.original_op["threshold"]
        self.slider_sharpen_percent.SetValue(self.op["percent"])
        self.slider_sharpen_radius.SetValue(self.op["radius"])
        self.slider_sharpen_threshold.SetValue(self.op["threshold"])
        self.text_sharpen_percent.SetValue(str(self.op["percent"]))
        self.text_sharpen_radius.SetValue(str(self.op["radius"]))
        self.text_sharpen_threshold.SetValue(str(self.op["threshold"]))
        self.node.update(self.context)

    def on_slider_sharpen_percent(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["percent"] = int(self.slider_sharpen_percent.GetValue())
        self.text_sharpen_percent.SetValue(str(self.op["percent"]))
        self.node.update(self.context)

    def on_text_sharpen_percent(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        pass

    def on_slider_sharpen_radius(self, event):  # wxGlade: RasterWizard.<event_handler>
        self.op["radius"] = int(self.slider_sharpen_radius.GetValue())
        self.text_sharpen_radius.SetValue(str(self.op["radius"]))
        self.node.update(self.context)

    def on_text_sharpen_radius(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        pass

    def on_slider_sharpen_threshold(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["threshold"] = int(self.slider_sharpen_threshold.GetValue())
        self.text_sharpen_threshold.SetValue(str(self.op["threshold"]))
        self.node.update(self.context)

    def on_text_sharpen_threshold(self, event):  # wxGlade: RasterWizard.<event_handler>
        pass


class GammaPanel(wx.Panel):
    name = _("Gamma")
    priority = 30

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "gamma":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable_gamma = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset_gamma = wx.Button(self, wx.ID_ANY, _("Reset"))
        self.slider_gamma_factor = wx.Slider(
            self, wx.ID_ANY, 100, 0, 500, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_gamma_factor = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable_gamma, self.check_enable_gamma)
        self.Bind(wx.EVT_BUTTON, self.on_button_reset_gamma, self.button_reset_gamma)
        self.Bind(wx.EVT_SLIDER, self.on_slider_gamma_factor, self.slider_gamma_factor)
        self.Bind(wx.EVT_TEXT, self.on_text_gamma_factor, self.text_gamma_factor)
        # end wxGlade
        self.last_x = None

        op = None
        for n in node.operations:
            if n.get("name") == "gamma":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.text_gamma_factor.SetValue(str(op["factor"]))
        self.slider_gamma_factor.SetValue(op["factor"] * 100.0)
        self.check_enable_gamma.SetValue(op["enable"])

    def __set_properties(self):
        # begin wxGlade: GammaPanel.__set_properties
        self.check_enable_gamma.SetToolTip(_("Enable Gamma Shift"))
        self.check_enable_gamma.SetValue(1)
        self.button_reset_gamma.SetToolTip(_("Reset Gamma Shift"))
        self.slider_gamma_factor.SetToolTip(_("Gamma factor slider"))
        self.text_gamma_factor.SetToolTip(_("Amount of gamma factor"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: GammaPanel.__do_layout
        sizer_gamma = StaticBoxSizer(self, wx.ID_ANY, _("Gamma"), wx.VERTICAL)
        sizer_gamma_factor = StaticBoxSizer(
            self, wx.ID_ANY, _("Gamma Factor"), wx.HORIZONTAL
        )
        sizer_gamma_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_gamma_main.Add(self.check_enable_gamma, 0, 0, 0)
        sizer_gamma_main.Add(self.button_reset_gamma, 0, 0, 0)
        sizer_gamma.Add(sizer_gamma_main, 0, wx.EXPAND, 0)
        sizer_gamma_factor.Add(self.slider_gamma_factor, 5, wx.EXPAND, 0)
        sizer_gamma_factor.Add(self.text_gamma_factor, 1, 0, 0)
        sizer_gamma.Add(sizer_gamma_factor, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_gamma)
        sizer_gamma.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable_gamma(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["enable"] = self.check_enable_gamma.GetValue()
        self.node.update(self.context)

    def on_button_reset_gamma(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["factor"] = self.original_op["factor"]
        self.slider_gamma_factor.SetValue(self.op["factor"] * 100.0)
        self.text_gamma_factor.SetValue(str(self.op["factor"]))
        self.node.update(self.context)

    def on_slider_gamma_factor(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.op["factor"] = self.slider_gamma_factor.GetValue() / 100.0
        self.text_gamma_factor.SetValue(str(self.op["factor"]))
        self.node.update(self.context)

    def on_text_gamma_factor(self, event=None):  # wxGlade: RasterWizard.<event_handler>
        pass


class EdgePanel(wx.Panel):
    name = _("Edge Enhance")
    priority = 40

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "edge_enhance":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable = wx.CheckBox(self, wx.ID_ANY, _("Enable"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable, self.check_enable)
        # end wxGlade

        op = None
        for n in node.operations:
            if n.get("name") == "edge_enhance":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable.SetLabel(_("Enable {name}").format(name=op["name"]))
        self.check_enable.SetValue(op["enable"])

    def __set_properties(self):
        # begin wxGlade: OutputPanel.__set_properties
        self.check_enable.SetToolTip(_("Enable Operation"))
        self.check_enable.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: OutputPanel.__do_layout
        sizer_output = StaticBoxSizer(self, wx.ID_ANY, _("Enable"), wx.VERTICAL)
        sizer_output.Add(self.check_enable, 0, 0, 0)
        self.SetSizer(sizer_output)
        sizer_output.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable(self, event=None):
        self.op["enable"] = self.check_enable.GetValue()
        self.node.update(self.context)


class AutoContrastPanel(wx.Panel):
    name = _("Auto Contrast")
    priority = 45

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "auto_contrast":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable = wx.CheckBox(self, wx.ID_ANY, _("Enable"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable, self.check_enable)
        # end wxGlade

        op = None
        for n in node.operations:
            if n.get("name") == "auto_contrast":
                op = n
        if op is None:
            raise ValueError
        self.op = op
        self.original_op = deepcopy(op)
        self.check_enable.SetLabel(_("Enable {name}").format(name=op["name"]))
        self.check_enable.SetValue(op["enable"])

    def __set_properties(self):
        # begin wxGlade: OutputPanel.__set_properties
        self.check_enable.SetToolTip(_("Enable Operation"))
        self.check_enable.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: OutputPanel.__do_layout
        sizer_output = StaticBoxSizer(self, wx.ID_ANY, _("Enable"), wx.VERTICAL)
        sizer_output.Add(self.check_enable, 0, 0, 0)
        self.SetSizer(sizer_output)
        sizer_output.Fit(self)
        self.Layout()
        # end wxGlade

    def on_check_enable(self, event=None):
        self.op["enable"] = self.check_enable.GetValue()
        self.node.update(self.context)
