import wx

from meerk40t.kernel import signal_listener
from meerk40t.core.units import Length
from meerk40t.gui.icons import icons8_hinges_50
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.svgelements import Color, Path, Point, Matrix

_ = wx.GetTranslation

"""
TODO:
a) get rid of row / col range limitation and iterate until boundary exceeds frame
b) Fix circle arc invocation
c) Create proper bowlingpin shape
d) Proper clipping
e) Save presets per patterntype / or allow save / load of patternset
f) Labels for additional parameters?!

"""
class LivingHinges:
    """
    This class generates a predefined pattern in a *rectangular* area
    """

    def __init__(self, xpos, ypos, width, height):
        self.pattern = None
        self.start_x = xpos
        self.start_y = ypos
        self.width = width
        self.height = height
        # We set it off somewhat...
        self.gap = 0
        self.x0 = width * self.gap
        self.y0 = height * self.gap
        self.x1 = width * (1 - self.gap)
        self.y1 = height * (1 - self.gap)
        self.param_a = 0.7
        self.param_b = 0.7
        # Requires recalculation
        self.path = None
        self.pattern = []
        self.cutshape = ""
        self.set_cell_values(10, 10)
        self.set_padding_values(5, 5)
        self.set_predefined_pattern("line")

    def get_patterns(self):
        yield "line"
        yield "fishbone"
        yield "diagonal"
        yield "diamond1"
        yield "diamond2"
        yield "cross"
        yield "bezier"
        yield "wave"
        yield "bowlingpin"
        yield "beehive"
        yield "fabric"
        yield "brackets"
        yield "circle"

    def set_predefined_pattern(self, cutshape):
        # The pattern needs to be defined within a 0,0  - 1,1 rectangle
        #
        additional_parameter = False
        self.cutshape = cutshape
        self.pattern = []
        if cutshape == "line":
            self.pattern.append(("M", 0, 0.5))
            self.pattern.append(("L", 1, 0.5))
        elif cutshape == "fishbone":
            self.pattern.append(("M", 0, 1))
            self.pattern.append(("L", 0.5, 0))
            self.pattern.append(("M", 0.5, 0))
            self.pattern.append(("L", 1, 1))
        elif cutshape == "diagonal":
            self.pattern.append(("M", 0, 1))
            self.pattern.append(("L", 1, 0))
        elif cutshape == "diamond1":
            self.pattern.append(("M", 0, 0.5))
            self.pattern.append(("L", 0.5, 0))
            self.pattern.append(("L", 1, 0.5))
            self.pattern.append(("L", 0.5, 1))
            self.pattern.append(("L", 0, 0.5))
        elif cutshape == "diamond2":
            self.pattern.append(("M", 0, 0))
            self.pattern.append(("L", 0.5, 0.4))
            self.pattern.append(("L", 1, 0))
            self.pattern.append(("M", 0, 1))
            self.pattern.append(("L", 0.5, 0.6))
            self.pattern.append(("L", 1, 1))
        elif cutshape == "cross":
            # Pattern: cross
            self.pattern.append(("M", 0.0, 0.25))
            self.pattern.append(("L", 0.25, 0.50))
            self.pattern.append(("L", 0.0, 0.75))
            self.pattern.append(("M", 0.25, 0.50))
            self.pattern.append(("L", 0.75, 0.50))
            self.pattern.append(("M", 1, 0.25))
            self.pattern.append(("L", 0.75, 0.50))
            self.pattern.append(("L", 1, 0.75))
        elif cutshape == "fabric":
            self.pattern.append(("M", 0.25, 0.25))
            self.pattern.append(("L", 0, 0.25))
            self.pattern.append(("L", 0, 0))
            self.pattern.append(("L", 0.5, 0))
            self.pattern.append(("L", 0.5, 1))
            self.pattern.append(("L", 1, 1))
            self.pattern.append(("L", 1, 0.75))
            self.pattern.append(("L", 0.75, 0.75))

            self.pattern.append(("M", 0.75, 0.25))
            self.pattern.append(("L", 0.75, 0))
            self.pattern.append(("L", 1, 0))
            self.pattern.append(("L", 1, 0.5))
            self.pattern.append(("L", 0, 0.5))
            self.pattern.append(("L", 0, 1))
            self.pattern.append(("L", 0.25, 1))
            self.pattern.append(("L", 0.25, 0.75))

        elif cutshape == "beehive":
            dx = self.param_a / 5.0 * 0.5
            dy = self.param_b / 5.0 * 0.5
            # top
            self.pattern.append(("M", 0, 0.5 - dy))
            self.pattern.append(("L", dx, dy))
            self.pattern.append(("L", 1 - dx, dy))
            self.pattern.append(("L", 1, 0.5 - dy))
            # inner
            self.pattern.append(("M", 0, 0.5))
            self.pattern.append(("L", dx, 2 * dy))
            self.pattern.append(("L", 1 - dx, 2 * dy))
            self.pattern.append(("L", 1, 0.5))
            self.pattern.append(("L", 1 - dx, 1 - 2 * dy))
            self.pattern.append(("L", dx, 1 - 2 * dy))
            self.pattern.append(("L", 0, 0.5))
            # bottom
            self.pattern.append(("M", 0, 0.5 + dy))
            self.pattern.append(("L", dx, 1 - dy))
            self.pattern.append(("L", 1 - dx, 1 - dy))
            self.pattern.append(("L", 1, 0.5 + dy))

            additional_parameter = True

        elif cutshape == "bowlingpin":
            self.pattern.append(("M", 0.0, 0.25))
            self.pattern.append(("L", 0.25, 0.25))
            ctrl_x = 0.5 + self.param_a
            ctrl_y = 0.25 + self.param_b
            self.pattern.append(("Q", ctrl_x, ctrl_y, 0.5, 0.5))
            ctrl_x = 0.5 - self.param_a
            ctrl_y = 0.75 - self.param_b
            self.pattern.append(("Q", ctrl_x, ctrl_y, 0.75, 0.75))
            self.pattern.append(("L", 1, 0.75))
            additional_parameter = True
        elif cutshape == "wave":
            self.pattern.append(("M", 0.0, 0.25))
            self.pattern.append(("L", 0.25, 0.25))
            ctrl_x = 0.5 + self.param_a
            ctrl_y = 0.25 + self.param_b
            self.pattern.append(("Q", ctrl_x, ctrl_y, 0.5, 0.5))
            ctrl_x = 0.5 - self.param_a
            ctrl_y = 0.75 - self.param_b
            self.pattern.append(("Q", ctrl_x, ctrl_y, 0.75, 0.75))
            self.pattern.append(("L", 1, 0.75))
            additional_parameter = True
        elif cutshape == "bezier":
            # Pattern: wavy
            anchor_tip = (
                self.param_a
            )  # distance factor from anchor to place control point
            anchor_center = self.param_b
            self.pattern.append(("M", 0, 0))
            self.pattern.append(
                ("C", 1 * anchor_tip, 0, 1 / 2 - (1 * anchor_center), 1, 1 / 2, 1)
            )
            self.pattern.append(
                ("C", 1 / 2 + (1 * anchor_center), 1, 1 * (1 - anchor_tip), 0, 1, 0)
            )
            additional_parameter = True
        elif cutshape == "brackets":
            additional_parameter = True
            p_a = self.param_a
            p_b = self.param_b
            self.pattern.append(("M", 0.0, 0.5))
            self.pattern.append(("C", 0.0, p_a, 1.0, p_b, 1.0, 0.5))
            self.pattern.append(("C", 1.0, 1 - p_a, 0.0, 1 - p_b, 0.0, 0.5))
        elif cutshape == "circle":
            # concentric circles
            additional_parameter = True
            amount = int(abs(10 * self.param_a)) + 1  # (1 to 50)
            gap = abs(self.param_b)
            dx = 0.5 / amount
            cx = 0.5
            cy = 0.5
            rotation = 0
            sweep = 0
            arc = 0
            for i in range(amount):
                # A move-to command to the point cx+rx,cy;
                # arc to cx,cy+ry;
                # arc to cx-rx,cy;
                # arc to cx,cy-ry;
                # arc with a segment-completing close path operation.
                radius = i * dx

                self.pattern.append(("M", cx + radius, cy))
                self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx, cy + radius))
                self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx - radius, cy))
                self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx, cy - radius))
                self.pattern.append(("A", cx, cy, rotation, arc, sweep, cx + radius, cy))

        self.path = None
        return additional_parameter

    def make_outline(self, x0, y0, x1, y1):
        # Draw a rectangle
        pt0 = Point(x0, y0)
        pt1 = Point(x1, y0)
        pt2 = Point(x1, y1)
        pt3 = Point(x0, y1)

        self.path.move(pt0)
        self.path.line(pt1)
        self.path.line(pt2)
        self.path.line(pt3)
        self.path.line(pt0)

    def draw_trace(self, offset_x, offset_y, width, height):
        # Draw the pattern
        # The extents of the cell will be at (offset_x, offset_y)
        # in the upper-left corner and (width, height) in the bottom-right corner

        def create_point(x, y):
            return Point(x * width + offset_x, y * height + offset_y)

        def inside(x, y):
            outside = (
                x < 0
                or x > self.width
                or y < 0
                or y > self.height
            )
            return not outside

        # self.path.move(offset_x, offset_y)
        # print (f"After initial move: {str(self.path)}")
        current_x = 0
        current_y = 0
        s_left = self.start_x
        s_right = s_left + self.width
        s_top = self.start_y
        s_bottom = s_top + self.height
        for entry in self.pattern:
            old_x = current_x
            old_y = current_y
            key = entry[0].lower()
            if key == "m":
                endpoint = create_point(entry[1], entry[2])
                self.path.move(endpoint)
                current_x = entry[1]
                current_y = entry[2]
            elif key == "h":
                current_x += entry[1]
                dx = entry[1]
                if inside(current_x, current_y):
                    self.path.horizontal(dx, relative=True)
            elif key == "v":
                current_y += entry[1]
                dy = entry[1]
                if inside(current_x, current_y):
                    self.path.vertical(dy, relative=True)
            elif key == "l":
                # Line to...
                current_x = entry[1]
                current_y = entry[2]
                endpoint = create_point(entry[1], entry[2])
                if inside(current_x, current_y):
                    self.path.line(endpoint)
            elif key == "a":
                current_x = entry[6]
                current_y = entry[7]
                rx = entry[1]
                ry = entry[2]
                rotation = entry[3]
                arc = entry[4]
                sweep = entry[5]
                endpoint = create_point(current_x, current_y)
                if inside(current_x, current_y):
                    self.path.arc(rx, ry, rotation, arc, sweep, endpoint)
            elif key == "c":
                current_x = entry[5]
                current_y = entry[6]
                control1 = create_point(entry[1], entry[2])
                control2 = create_point(entry[3], entry[4])
                endpoint = create_point(entry[5], entry[6])
                if inside(current_x, current_y):
                    self.path.cubic(control1, control2, endpoint)
            elif key == "q":
                current_x = entry[3]
                current_y = entry[4]
                control1 = create_point(entry[1], entry[2])
                endpoint = create_point(entry[3], entry[4])
                if inside(current_x, current_y):
                    self.path.quad(control1, endpoint)

    def set_hinge_area(self, hinge_left, hinge_top, hinge_width, hinge_height):
        self.start_x = hinge_left
        self.start_y = hinge_top
        self.width = hinge_width
        self.height = hinge_height
        self.x0 = hinge_width * self.gap
        self.y0 = hinge_height * self.gap
        self.x1 = hinge_width * (1 - self.gap)
        self.y1 = hinge_height * (1 - self.gap)
        # Requires recalculation
        self.path = None

    def set_cell_values(self, percentage_x, percentage_y):
        self.cell_width_percentage = percentage_x
        self.cell_height_percentage = percentage_y
        # Requires recalculation
        self.path = None

    def set_padding_values(self, padding_x, padding_y):
        self.cell_padding_h_percentage = padding_x
        self.cell_padding_v_percentage = padding_y
        # Requires recalculation
        self.path = None

    def set_additional_parameters(self, param_a, param_b):
        self.param_a = param_a
        self.param_b = param_b
        # Make sure pattern is updated with additional parameter
        __ = self.set_predefined_pattern(self.cutshape)

    def generate(self, show_outline=False, force=False):
        if self.path is not None and not force:
            # No need to recalculate...
            return

        self.cell_width = self.width * self.cell_width_percentage / 100
        self.cell_height = self.height * self.cell_height_percentage / 100
        self.cell_padding_h = self.cell_width * self.cell_padding_h_percentage / 100
        self.cell_padding_v = self.cell_height * self.cell_padding_v_percentage / 100
        self.path = Path(stroke=Color("red"), stroke_width=500)

        if show_outline:
            self.make_outline(self.x0, self.y0, self.x1, self.y1)

        #  Determine rows and columns of cuts to create
        #  will round down so add 1 and trim later
        cols = (
            int(
                ((self.x1 - self.x0) + self.cell_width)
                / (self.cell_width + (2 * self.cell_padding_h))
            )
            + 1
        )
        rows = (
            int(
                ((self.y1 - self.y0) + self.cell_height)
                / (self.cell_height + (2 * self.cell_padding_v))
            )
            + 1
        )

        # print (f"Area: {self.width:.1f}, {self.height:.1f}, Cell: {self.cell_width:.1f}, {self.cell_height:.1f}")
        # print (f"Rows: {rows}, Cols={cols}")
        # print (f"Ratios: {self.cell_width_percentage}, {self.cell_height_percentage}")
        # print (f"Padding: {self.cell_padding_h_percentage}, {self.cell_padding_v_percentage}")
        for col in range(cols):
            top_left_x = self.x0 - (self.cell_width / 2)
            x_offset = col * (self.cell_width + (2 * self.cell_padding_h))
            x_current = top_left_x + x_offset
            for row in range(rows):
                top_left_y = self.y0
                y_offset = row * (self.cell_height + (2 * self.cell_padding_v)) + (
                    (self.cell_height + (2 * self.cell_padding_v)) / 2
                ) * (col % 2)
                y_current = top_left_y + y_offset

                if x_current < self.x1 and y_current < self.y1:
                    # Don't call draw if outside of hinge area
                    self.draw_trace(
                        x_current,
                        y_current,
                        self.cell_width,
                        self.cell_height,
                    )
                    if show_outline:
                        self.make_outline(
                            x_current,
                            y_current,
                            x_current + self.cell_width,
                            y_current + self.cell_height,
                        )
        self.path.transform *= Matrix.translate(self.start_x, self.start_y)


class HingePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.renderer = LaserRender(context)
        self.in_event = False
        self.text_origin_x = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_origin_y = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_width = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_height = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_style = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN
        )
        self.slider_width = wx.Slider(
            self,
            wx.ID_ANY,
            20,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_height = wx.Slider(
            self,
            wx.ID_ANY,
            20,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_offset_x = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            -49,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_offset_y = wx.Slider(
            self,
            wx.ID_ANY,
            0,
            -49,
            50,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
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

        self.hinge_generator = LivingHinges(
            0, 0, float(Length("5cm")), float(Length("5cm"))
        )

        #  self.check_debug_outline = wx.CheckBox(self, wx.ID_ANY, "Show outline")

        self.patterns = list(self.hinge_generator.get_patterns())
        self.combo_style.Set(self.patterns)
        self.combo_style.SetSelection(0)
        # self.check_debug_outline.SetValue(True)
        self._set_layout()
        self._set_logic()

        self._setup_settings()
        self._restore_settings()

        self.Layout()

    def _set_logic(self):
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_paint)
        self.button_close.Bind(wx.EVT_BUTTON, self.on_button_close)
        self.button_generate.Bind(wx.EVT_BUTTON, self.on_button_generate)
        self.text_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_x.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_origin_y.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_width.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_height.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_x.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_offset_y.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_a.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.slider_param_b.Bind(wx.EVT_SLIDER, self.on_option_update)
        self.combo_style.Bind(wx.EVT_COMBOBOX, self.on_option_update)
        # self.check_debug_outline.Bind(wx.EVT_CHECKBOX, self.on_option_update)

    def _set_layout(self):
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_left = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(main_left, 1, wx.EXPAND, 0)

        vsizer_dimension = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Dimension")), wx.VERTICAL
        )
        main_left.Add(vsizer_dimension, 0, wx.EXPAND, 0)

        hsizer_originx = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_originx, 0, wx.EXPAND, 0)

        label_x = wx.StaticText(self, wx.ID_ANY, _("X:"))
        label_x.SetMinSize((90, -1))
        hsizer_originx.Add(label_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_origin_x.SetToolTip(_("X-Coordinate of the hinge area"))
        hsizer_originx.Add(self.text_origin_x, 0, 0, 0)

        hsizer_originy = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_originy, 0, wx.EXPAND, 0)

        label_y = wx.StaticText(self, wx.ID_ANY, _("Y:"))
        label_y.SetMinSize((90, -1))
        hsizer_originy.Add(label_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_origin_y.SetToolTip(_("Y-Coordinate of the hinge area"))
        hsizer_originy.Add(self.text_origin_y, 0, 0, 0)

        hsizer_width = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_width, 0, wx.EXPAND, 0)

        label_width = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        label_width.SetMinSize((90, -1))
        hsizer_width.Add(label_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_width.SetToolTip(_("Width of the hinge area"))
        hsizer_width.Add(self.text_width, 0, 0, 0)

        hsizer_height = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_height, 0, wx.EXPAND, 0)

        label_height = wx.StaticText(self, wx.ID_ANY, _("Height:"))
        label_height.SetMinSize((90, -1))
        hsizer_height.Add(label_height, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_height.SetToolTip(_("Height of the hinge area"))
        hsizer_height.Add(self.text_height, 0, 0, 0)

        vsizer_options = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Options")), wx.VERTICAL
        )
        main_left.Add(vsizer_options, 0, wx.EXPAND, 0)

        hsizer_pattern = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_pattern, 0, wx.EXPAND, 0)

        label_pattern = wx.StaticText(self, wx.ID_ANY, _("Pattern:"))
        label_pattern.SetMinSize((90, -1))
        hsizer_pattern.Add(label_pattern, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.combo_style.SetToolTip(_("Choose the hinge pattern"))
        hsizer_pattern.Add(self.combo_style, 1, wx.EXPAND, 0)

        hsizer_cellwidth = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellwidth, 1, wx.EXPAND, 0)

        label_cell_width = wx.StaticText(self, wx.ID_ANY, _("Cell-Width:"))
        label_cell_width.SetMinSize((90, -1))
        hsizer_cellwidth.Add(label_cell_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
        )
        hsizer_cellwidth.Add(self.slider_width, 1, wx.EXPAND, 0)

        hsizer_cellheight = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellheight, 1, wx.EXPAND, 0)

        label_cell_height = wx.StaticText(self, wx.ID_ANY, _("Cell-Height:"))
        label_cell_height.SetMinSize((90, -1))
        hsizer_cellheight.Add(label_cell_height, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_height.SetToolTip(
            _("Select the ratio of the cell height compared to the overall height")
        )
        hsizer_cellheight.Add(self.slider_height, 1, wx.EXPAND, 0)

        hsizer_offsetx = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsetx, 1, wx.EXPAND, 0)

        label_offset_x = wx.StaticText(self, wx.ID_ANY, _("Offset X:"))
        label_offset_x.SetMinSize((90, -1))
        hsizer_offsetx.Add(label_offset_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_x.SetToolTip(
            _("Select the offset of one pattern in X-direction")
        )
        hsizer_offsetx.Add(self.slider_offset_x, 1, wx.EXPAND, 0)

        hsizer_offsety = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_offsety, 0, wx.EXPAND, 0)

        label_offset_y = wx.StaticText(self, wx.ID_ANY, _("Offset Y:"))
        label_offset_y.SetMinSize((90, -1))
        hsizer_offsety.Add(label_offset_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_y.SetToolTip(
            _("Select the offset of one pattern in X-direction")
        )
        hsizer_offsety.Add(self.slider_offset_y, 1, wx.EXPAND, 0)

        self.slider_param_a.SetToolTip(_("Change the shape appearance"))
        self.slider_param_b.SetToolTip(_("Change the shape appearance"))
        hsizer_param_a = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_param_a.Add(self.slider_param_a, 1, wx.EXPAND, 0)
        hsizer_param_a.Add(self.slider_param_b, 1, wx.EXPAND, 0)
        vsizer_options.Add(hsizer_param_a, 0, wx.EXPAND, 0)
        # main_left.Add(self.check_debug_outline, 0, wx.EXPAND, 0)

        hsizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        main_left.Add(hsizer_buttons, 0, wx.EXPAND, 0)

        self.button_generate = wx.Button(self, wx.ID_ANY, _("Generate"))
        self.button_generate.SetToolTip(_("Generates the hinge"))
        hsizer_buttons.Add(self.button_generate, 2, 0, 0)

        self.button_close = wx.Button(self, wx.ID_ANY, _("Close"))
        hsizer_buttons.Add(self.button_close, 1, 0, 0)

        main_right = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Preview"), wx.VERTICAL
        )
        main_sizer.Add(main_right, 2, wx.EXPAND, 0)

        self.panel_preview = wx.Panel(self, wx.ID_ANY)
        main_right.Add(self.panel_preview, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

    def on_paint(self, event):
        # Create paint DC
        dc = wx.PaintDC(self.panel_preview)

        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            wd, ht = self.panel_preview.GetSize()
            ratio = min(
                wd / self.hinge_generator.width, ht / self.hinge_generator.height
            )
            matrix = gc.CreateMatrix(a=ratio, b=0, c=0, d=ratio, tx=0, ty=0)
            gc.SetTransform(matrix)
            # Draw the hinge area:
            gc.SetPen(wx.BLUE_PEN)
            gc.DrawRectangle(
                0, 0, self.hinge_generator.width, self.hinge_generator.height
            )
            # flag = self.check_debug_outline.GetValue()
            flag = False
            self.hinge_generator.generate(flag)
            gc.SetPen(wx.RED_PEN)
            gcpath = self.renderer.make_path(gc, self.hinge_generator.path)
            gc.StrokePath(gcpath)

    def on_button_close(self, event):
        self.context("window toggle Hingetool\n")

    def on_button_generate(self, event):
        self.hinge_generator.generate(show_outline=False)
        node = self.context.elements.elem_branch.add(
            path=abs(self.hinge_generator.path),
            stroke_width=500,
            color=Color("red"),
            type="elem path",
        )
        self.context.signal("classify_new", node)
        self.context.signal("refresh_scene")

    def on_option_update(self, event):
        if self.in_event:
            return
        self.in_event = True
        flag = True
        idx = self.combo_style.GetSelection()
        if idx < 0:
            idx = 0
        style = self.patterns[idx]
        self.context.hinge_type = style
        try:
            wd = float(Length(self.text_width.GetValue()))
            if wd > 0:
                self.context.hinge_width = self.text_width.GetValue()
        except ValueError:
            wd = 0
            flag = False
        try:
            ht = float(Length(self.text_height.GetValue()))
            if ht > 0:
                self.context.hinge_height = self.text_height.GetValue()
        except ValueError:
            ht = 0
            flag = False
        cell_x = self.slider_width.GetValue()
        cell_y = self.slider_height.GetValue()
        self.context.hinge_cells_x = cell_x
        self.context.hinge_cells_y = cell_y
        offset_x = self.slider_offset_x.GetValue()
        offset_y = self.slider_offset_y.GetValue()
        self.context.hinge_padding_x = offset_x
        self.context.hinge_padding_y = offset_y

        p_a = self.slider_param_a.GetValue() / 10.0
        p_b = self.slider_param_b.GetValue() / 10.0
        self.context.hinge_param_a = p_a
        self.context.hinge_param_b = p_b
        # Restore settings will call the LivingHinge class
        self._restore_settings()
        self.panel_preview.Refresh()
        self.in_event = False

    def _setup_settings(self):
        self.context.setting(str, "hinge_type", "line")
        self.context.setting(str, "hinge_origin_x", "0cm")
        self.context.setting(str, "hinge_origin_y", "0cm")
        self.context.setting(str, "hinge_width", "5cm")
        self.context.setting(str, "hinge_height", "5cm")
        self.context.setting(int, "hinge_cells_x", 20)
        self.context.setting(int, "hinge_cells_y", 20)
        self.context.setting(int, "hinge_padding_x", 10)
        self.context.setting(int, "hinge_padding_y", 10)
        self.context.setting(float, "hinge_param_a", 0.7)
        self.context.setting(float, "hinge_param_b", 0.7)

    def _restore_settings(self):
        if self.context.hinge_type not in self.patterns:
            self.context.hinge_type = self.patterns[0]
        flag = self.hinge_generator.set_predefined_pattern(self.context.hinge_type)
        x = float(Length(self.context.hinge_origin_x))
        y = float(Length(self.context.hinge_origin_y))
        wd = float(Length(self.context.hinge_width))
        ht = float(Length(self.context.hinge_height))
        self.hinge_generator.set_hinge_area(x, y, wd, ht)
        self.hinge_generator.set_cell_values(
            self.context.hinge_cells_x, self.context.hinge_cells_y
        )
        self.hinge_generator.set_padding_values(
            self.context.hinge_padding_x, self.context.hinge_padding_y
        )
        self.hinge_generator.set_additional_parameters(
            self.context.hinge_param_a, self.context.hinge_param_b
        )
        self.slider_param_a.Enable(flag)
        self.slider_param_b.Enable(flag)
        self.slider_param_a.Show(flag)
        self.slider_param_b.Show(flag)
        if self.combo_style.GetSelection() != self.patterns.index(
            self.context.hinge_type
        ):
            self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        if self.text_origin_x.GetValue() != self.context.hinge_origin_x:
            self.text_origin_x.ChangeValue(self.context.hinge_origin_x)
        if self.text_origin_y.GetValue() != self.context.hinge_origin_y:
            self.text_origin_y.ChangeValue(self.context.hinge_origin_y)
        if self.text_width.GetValue() != self.context.hinge_width:
            self.text_width.ChangeValue(self.context.hinge_width)
        if self.text_height.GetValue() != self.context.hinge_height:
            self.text_height.ChangeValue(self.context.hinge_height)
        if self.slider_width.GetValue() != self.context.hinge_cells_x:
            self.slider_width.SetValue(self.context.hinge_cells_x)
        if self.slider_height.GetValue() != self.context.hinge_cells_y:
            self.slider_height.SetValue(self.context.hinge_cells_y)
        if self.slider_offset_x.GetValue() != self.context.hinge_padding_x:
            self.slider_offset_x.SetValue(self.context.hinge_padding_x)
        if self.slider_offset_y.GetValue() != self.context.hinge_padding_y:
            self.slider_offset_y.SetValue(self.context.hinge_padding_y)
        if self.slider_param_a.GetValue() != int(10 * self.context.hinge_param_a):
            self.slider_param_a.SetValue(int(10 * self.context.hinge_param_a))
        if self.slider_param_b.GetValue() != int(10 * self.context.hinge_param_b):
            self.slider_param_b.SetValue(int(10 * self.context.hinge_param_b))
        flag = wd > 0 and ht > 0
        self.button_generate.Enable(flag)
        self.Layout()

    def pane_show(self):
        bounds = self.context.elements._emphasized_bounds
        if bounds is not None:
            units = self.context.units_name
            start_x = bounds[0]
            start_y = bounds[1]
            wd = bounds[2] - bounds[0]
            ht = bounds[3] - bounds[1]
            self.text_origin_x.ChangeValue(
                Length(amount=start_x, digits=2, preferred_units=units).preferred_length
            )
            self.text_origin_y.ChangeValue(
                Length(amount=start_y, digits=2, preferred_units=units).preferred_length
            )
            self.text_width.ChangeValue(
                Length(amount=wd, digits=2, preferred_units=units).preferred_length
            )
            self.text_height.ChangeValue(
                Length(amount=ht, digits=2, preferred_units=units).preferred_length
            )
            self.hinge_generator.set_hinge_area(start_x, start_y, wd, ht)


class LivingHingeTool(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 360, submenu="Laser-Tools", *args, **kwds)
        self.panel_template = HingePanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.add_module_delegate(self.panel_template)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_hinges_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Living Hinges"))
        self.Layout()

    def window_open(self):
        self.panel_template.pane_show()

    def window_close(self):
        pass

    @signal_listener("emphasized")
    def on_emphasized_elements_changed(self, origin, *args):
        self.panel_template.pane_show()

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Living-Hinges")
