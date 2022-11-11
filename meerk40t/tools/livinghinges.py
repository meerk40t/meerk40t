import wx
from wx import aui

from meerk40t.core.units import Length
from meerk40t.gui.icons import icons8_hinges_50
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl
from meerk40t.svgelements import Color, Path, Point

_ = wx.GetTranslation


class Generator:
    """A generic generator, subclassed for each different lattice style."""

    def __init__(self, x, y, width, height, stroke_width, e_length, p_spacing):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.stroke_width = stroke_width
        self.e_length = e_length
        self.e_height = 0  # Provided by sub-classes.
        self.p_spacing = p_spacing
        self.fixed_commands = ""

    def draw_one(self, x, y):
        return "M %f,%f %s" % (x, y, self.fixed_commands)

    def generate(self):
        # Round width/height to integer number of patterns.
        self.e_length = self.width / max(round(self.width / self.e_length), 1.0)
        self.e_height = self.height / max(round(self.height / self.e_height), 1.0)
        self.prerender()
        path_command = ""
        y = self.y
        while y < self.y + self.height:
            x = self.x
            while x < self.x + self.width:
                path_command = "%s %s " % (path_command, self.draw_one(x, y))
                x += self.e_length
            y += self.e_height


class StraightLatticeGenerator(Generator):
    def __init__(self, *args, **kwargs):
        super(StraightLatticeGenerator, self).__init__(*args)
        self.link_gap = kwargs["link_gap"]
        self.e_height = 2 * self.p_spacing
        self.name = "straight"

    def prerender(self):
        self.e_height = 2 * self.p_spacing
        w = self.e_length
        lg = self.link_gap

        if lg < 0.1:
            # Single line for 0 height gap.
            self.fixed_commands = " m %f,%f h %f m %f,%f h %f m %f,%f h %f" % (
                0,
                self.e_height / 2,
                w * 2 / 5,
                0 - w / 5,
                0 - self.e_height / 2,
                w * 3 / 5,
                0 - w / 5,
                self.e_height / 2,
                w * 2 / 5,
            )
        else:
            self.fixed_commands = (
                " m %f,%f h %f v %f h %f"
                " m %f,%f h %f v %f h %f v %f"
                " m %f,%f h %f v %f h %f "
            ) % (
                0,
                self.e_height / 2,
                w * 2 / 5,
                lg,
                0 - w * 2 / 5,
                w / 8,
                0 - lg - self.e_height / 2,
                w * 3 / 4,
                lg,
                0 - w * 3 / 4,
                0 - lg,
                w * 7 / 8,
                lg + self.e_height / 2,
                0 - w * 2 / 5,
                0 - lg,
                w * 2 / 5,
            )


class DiamondLatticeGenerator(Generator):
    def __init__(self, *args, **kwargs):
        super(DiamondLatticeGenerator, self).__init__(*args)
        self.e_height = self.p_spacing
        self.diamond_curve = kwargs["diamond_curve"]
        self.name = "diamond"

    def prerender(self):
        h = self.e_height
        w = self.e_length
        # Diamond curve
        dc = 0 - self.diamond_curve
        # Horiz handle length.
        hhl = abs(dc * w * 0.2)
        # Endpoint horiz handle length
        ehhl = hhl if dc > 0 else 0
        # Vert handle length
        vhl = abs(dc * h / 8) if dc < 0 else 0
        # Left
        self.fixed_commands = " m %f,%f c %f,%f %f,%f %f,%f c %f,%f %f,%f %f,%f " % (
            0,
            h / 4,
            hhl,
            0,
            w * 0.4 - ehhl,
            h / 4 - vhl,
            w * 0.4,
            h / 4,
            0 - ehhl,
            vhl,
            0 - (w * 0.4 - hhl),
            h / 4,
            0 - w * 0.4,
            h / 4,
        )

        # Bottom
        self.fixed_commands = "%s m %f,%f c %f,%f %f,%f %f,%f s %f,%f %f,%f " % (
            self.fixed_commands,
            w * 0.1,
            h / 4,
            ehhl,
            0 - vhl,
            w * 0.4 - hhl,
            0 - h / 4,
            w * 0.4,
            0 - h / 4,
            w * 0.4 - ehhl,
            h / 4 - vhl,
            w * 0.4,
            h / 4,
        )

        # Top
        self.fixed_commands = "%s m %f,%f c %f,%f %f,%f %f,%f s %f,%f %f,%f " % (
            self.fixed_commands,
            0 - w * 0.8,
            0 - h,
            ehhl,
            vhl,
            w * 0.4 - hhl,
            h / 4,
            w * 0.4,
            h / 4,
            w * 0.4 - ehhl,
            0 - h / 4 + vhl,
            w * 0.4,
            0 - h / 4,
        )

        # Right
        self.fixed_commands = "%s m %f,%f c %f,%f %f,%f %f,%f c %f,%f %f,%f %f,%f " % (
            self.fixed_commands,
            w * 0.1,
            h * 0.75,
            0 - hhl,
            0,
            (0 - w * 0.4) + ehhl,
            0 - h / 4 + vhl,
            0 - w * 0.4,
            0 - h / 4,
            ehhl,
            0 - vhl,
            w * 0.4 - hhl,
            0 - h / 4,
            w * 0.4,
            0 - h / 4,
        )

    def draw_one(self, x, y):
        return "M %f,%f %s" % (x, y, self.fixed_commands)


class CrossLatticeGenerator(Generator):
    def __init__(self, *args):
        super(CrossLatticeGenerator, self).__init__(*args)
        self.e_height = self.p_spacing
        self.name = "cross"

    def prerender(self):
        l = self.e_length
        h = self.e_height
        self.fixed_commands = (
            "m %f,%f l %f,%f l %f,%f m %f,%f l %f,%f"
            "m %f,%f l %f,%f l %f,%f l %f,%f "
            "m %f,%f l %f,%f l %f,%f l %f,%f "
            "m %f,%f l %f,%f l %f,%f m %f,%f l %f,%f"
        ) % (
            # Left
            0,
            h * 0.5,
            l * 0.2,
            0,
            l * 0.2,
            0 - h * 0.3,
            0 - l * 0.2,
            h * 0.3,
            l * 0.2,
            h * 0.3,
            # Top
            0 - l * 0.3,
            0 - h * 0.5,
            l * 0.2,
            0 - h * 0.3,
            l * 0.4,
            0,
            l * 0.2,
            h * 0.3,
            # Bottom
            0,
            h * 0.4,
            0 - l * 0.2,
            h * 0.3,
            0 - l * 0.4,
            0,
            0 - l * 0.2,
            0 - h * 0.3,
            # Right
            l * 0.5,
            0 - h * 0.5,
            l * 0.2,
            h * 0.3,
            0 - l * 0.2,
            h * 0.3,
            l * 0.2,
            0 - h * 0.3,
            l * 0.2,
            0,
        )


class WavyLatticeGenerator(Generator):
    def __init__(self, *args, **kwargs):
        super(WavyLatticeGenerator, self).__init__(*args)
        self.e_height = self.p_spacing
        self.name = "wavy"

    def prerender(self):
        h = self.e_height
        w = self.e_length
        self.fixed_commands = (
            " m %f,%f h %f c %f,%f %f,%f %f,%f h %f "
            "m %f,%f h %f c %f,%f %f,%f %f,%f h %f "
        ) % (
            0,
            h,  # Start of element (left)
            w * 0.1,  # Short horiz line.
            w * 0.1,
            0,  # Control 1
            w * 3 / 40,
            0 - h / 2,  # Control 2
            w * 0.2,
            0 - h / 2,  # Curve top.
            w * 0.175,  # Top horiz line.
            0 - w * 0.1,
            0 - h / 2,  # Move to higher line.
            w * 0.3,  # Long higher horiz line.
            w / 5,
            0,  # Control 1
            w / 10,
            h,  # Control 2
            w * 0.25,
            h,  # Curve down.
            w * 0.075,  # End horiz line.
        )


class LivingHinges:
    """
    This class generates a predefined pattern in a *rectangular* area
    """

    def __init__(self, width, height):
        self.pattern = None
        self.cols = 0
        self.rows = 0
        self.width = width
        self.height = height
        # We set it off somewhat...
        self.x0 = width / 4
        self.y0 = height / 4
        self.x1 = width * 3 / 4
        self.y1 = height * 3 / 4
        self.cell_width_percentage = 10
        self.cell_height_percentage = 5
        self.cell_width = self.width * self.cell_width_percentage / 100
        self.cell_height = self.height * self.cell_height_percentage / 100
        self.cell_offset_h_percentage = 2
        self.cell_offset_v_percentage = 2
        self.cell_padding_h = self.width * self.cell_offset_h_percentage / 100
        self.cell_padding_v = self.height * self.cell_offset_v_percentage / 100
        self.pattern = []
        self.set_predefined_pattern("line")
        self.path = None

    def get_patterns(self):
        yield "line"
        yield "fishbone"
        yield "diagonal"
        yield "diamond"
        yield "cross"
        yield "wavy"

    def set_predefined_pattern(self, cutshape):
        # The pattern needs to be defined within a 0,0  - 1,1 rectangle
        #
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
        elif cutshape == "diamond":
            self.pattern.append(("M", 0, 0.5))
            self.pattern.append(("L", 0.5, 0))
            self.pattern.append(("L", 1, 0.5))
            self.pattern.append(("L", 0.5, 1))
            self.pattern.append(("L", 0, 0.5))
        elif cutshape == "cross":
            self.pattern.append(("M", 0.00, 0.50))
            self.pattern.append(("L", 0.20, 0.00))
            self.pattern.append(("L", 0.20, -0.30))
            self.pattern.append(("M", -0.20, 0.30))
            self.pattern.append(("L", 0.20, 0.30))
            self.pattern.append(("M", -0.30, -0.50))
            self.pattern.append(("L", 0.20, -0.30))
            self.pattern.append(("L", 0.40, 0.00))
            self.pattern.append(("L", 0.20, 0.30))
            self.pattern.append(("M", 0.00, 0.40))
            self.pattern.append(("L", -0.20, 0.30))
            self.pattern.append(("L", -0.40, 0.00))
            self.pattern.append(("L", -0.20, -0.30))
            self.pattern.append(("M", 0.50, -0.50))
            self.pattern.append(("L", 0.20, 0.30))
            self.pattern.append(("L", -0.20, 0.30))
            self.pattern.append(("M", 0.20, -0.30))
            self.pattern.append(("L", 0.20, 0.00))

        elif cutshape == "wavy":
            pass

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

    def draw_trace(self, x0, y0, x1, y1):
        # Draw the pattern
        # move the matrix so that dimensions here can be relative, the extents of the cell will be (0,0)
        # in the upper-left corner and (cellWidth,cellHeight) in the bottom-right corner

        def create_point(x, y):
            return Point(x * width + offset_x, y * height + offset_y)

        self.path.move(x0, y0)
        offset_x = x0
        offset_y = y0
        width = x1 - x0
        height = y1 - y0
        for entry in self.pattern:
            if entry[0] == "M":
                endpoint = create_point(entry[1], entry[2])
                self.path.move(endpoint)
            elif entry[0] == "L":
                # Line to...
                endpoint = create_point(entry[1], entry[2])
                self.path.line(endpoint)
            elif entry[0] == "C":
                control1 = create_point(entry[1], entry[2])
                control2 = create_point(entry[3], entry[4])
                endpoint = create_point(entry[5], entry[6])
                self.path.cubic(control1, control2, endpoint)
            elif entry[0] == "Q":
                control1 = create_point(entry[1], entry[2])
                endpoint = create_point(entry[3], entry[4])
                self.path.cubic(control1, endpoint)

    def generate(self, show_outline=False):
        self.path = Path(stroke=Color("red"), stroke_width=500)
        self.cell_width = self.width * self.cell_width_percentage / 100
        self.cell_height = self.height * self.cell_height_percentage / 100
        self.cell_padding_h = self.width * self.cell_offset_h_percentage / 100
        self.cell_padding_v = self.height * self.cell_offset_v_percentage / 100

        if show_outline:
            self.make_outline(self.x0, self.y0, self.x1, self.y1)

        #  Determine rows and columns of cuts to create
        #  will round down so add 1 and trim later
        self.cols = (
            int(
                ((self.x1 - self.x0) + self.cell_width)
                / (self.cell_width + (2 * self.cell_padding_h))
            )
            + 1
        )
        self.rows = (
            int(
                ((self.y1 - self.y0) + self.cell_height)
                / (self.cell_height + (2 * self.cell_padding_v))
            )
            + 1
        )

        for col in range(self.cols):
            for row in range(self.rows):

                # logic for X and Y is to find upper-left corner of upper-left cell
                # and then use col- and row-based offsets
                top_left_x = self.x0 - (self.cell_width / 2)
                x_offset = col * (self.cell_width + (2 * self.cell_padding_h))
                x_current = top_left_x + x_offset

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


class HingePanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.renderer = LaserRender(context)
        self.text_width = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_height = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_style = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.slider_width = wx.Slider(
            self,
            wx.ID_ANY,
            1,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_height = wx.Slider(
            self,
            wx.ID_ANY,
            1,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_offset_x = wx.Slider(
            self,
            wx.ID_ANY,
            1,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )
        self.slider_offset_y = wx.Slider(
            self,
            wx.ID_ANY,
            1,
            1,
            100,
            style=wx.SL_HORIZONTAL | wx.SL_VALUE_LABEL,
        )

        self.hinge_generator = LivingHinges(
            float(Length("5cm")),
            float(Length("5cm"))
        )
        self.patterns = list(self.hinge_generator.get_patterns())
        self.combo_style.Set(self.patterns)
        self._set_layout()
        self._set_logic()

        self._setup_settings()
        self._restore_settings(False)

        self.Layout()

    def _set_logic(self):
        self.panel_preview.Bind(wx.EVT_PAINT, self.on_paint)
        self.button_close.Bind(wx.EVT_BUTTON, self.on_button_close)
        self.button_generate.Bind(wx.EVT_BUTTON, self.on_button_generate)
        self.text_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.text_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_width.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_height.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_offset_x.Bind(wx.EVT_TEXT, self.on_option_update)
        self.slider_offset_y.Bind(wx.EVT_TEXT, self.on_option_update)

    def _set_layout(self):
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_left = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(main_left, 1, wx.EXPAND, 0)

        vsizer_dimension = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Dimension")), wx.VERTICAL
        )
        main_left.Add(vsizer_dimension, 0, wx.EXPAND, 0)

        hsizer_width = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_width, 1, wx.EXPAND, 0)

        label_width = wx.StaticText(self, wx.ID_ANY, _("Width:"))
        label_width.SetMinSize((90, -1))
        hsizer_width.Add(label_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_width.SetToolTip(_("Width of the hinge area"))
        hsizer_width.Add(self.text_width, 0, 0, 0)

        hsizer_height = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_dimension.Add(hsizer_height, 1, wx.EXPAND, 0)

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
        vsizer_options.Add(hsizer_pattern, 1, wx.EXPAND, 0)

        label_pattern = wx.StaticText(self, wx.ID_ANY, _("Pattern:"))
        label_pattern.SetMinSize((90, -1))
        hsizer_pattern.Add(label_pattern, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.combo_style.SetToolTip(_("Choose the  hinge pattern"))
        hsizer_pattern.Add(self.combo_style, 1, 0, 0)

        hsizer_cellwidth = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellwidth, 1, wx.EXPAND, 0)

        label_cell_width = wx.StaticText(
            self, wx.ID_ANY, _("Cell-Width:")
        )
        label_cell_width.SetMinSize((90, -1))
        hsizer_cellwidth.Add(label_cell_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_width.SetToolTip(
            _("Select the ratio of the cell width compared to the overall width")
        )
        hsizer_cellwidth.Add(self.slider_width, 1, wx.EXPAND, 0)

        hsizer_cellheight = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_options.Add(hsizer_cellheight, 1, wx.EXPAND, 0)

        label_cell_height = wx.StaticText(
            self, wx.ID_ANY, _("Cell-Height:")
        )
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
        vsizer_options.Add(hsizer_offsety, 1, wx.EXPAND, 0)

        label_offset_y = wx.StaticText(self, wx.ID_ANY, _("Offset Y:"))
        label_offset_y.SetMinSize((90, -1))
        hsizer_offsety.Add(label_offset_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_offset_y.SetToolTip(
            _("Select the offset of one pattern in X-direction")
        )
        hsizer_offsety.Add(self.slider_offset_y, 1, wx.EXPAND, 0)

        hsizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        main_left.Add(hsizer_buttons, 1, wx.EXPAND, 0)

        self.button_generate = wx.Button(self, wx.ID_ANY, _("Generate"))
        self.button_generate.SetToolTip(_("Generates the hinge"))
        hsizer_buttons.Add(self.button_generate, 2, 0, 0)

        self.button_close = wx.Button(self, wx.ID_ANY, _("Close"))
        hsizer_buttons.Add(self.button_close, 1, 0, 0)

        main_right = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Preview"), wx.VERTICAL
        )
        main_sizer.Add(main_right, 1, wx.EXPAND, 0)

        self.panel_preview = wx.Panel(self, wx.ID_ANY)
        main_right.Add(self.panel_preview, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

    def on_paint(self, event):
        # Create paint DC
        dc = wx.PaintDC(self.panel_preview)

        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            self.hinge_generator.generate(True)
            # make a path that contains a circle and some lines
            gc.SetPen(wx.RED_PEN)
            gcpath = self.renderer.make_path(gc, self.hinge_generator.path)
            # gcpath = gc.CreatePath()
            # gcpath.AddCircle(50.0, 50.0, 50.0)
            # gcpath.MoveToPoint(0.0, 50.0)
            # gcpath.AddLineToPoint(100.0, 50.0)
            # gcpath.MoveToPoint(50.0, 0.0)
            # gcpath.AddLineToPoint(50.0, 100.0)
            # gcpath.CloseSubpath()
            # gcpath.AddRectangle(25.0, 25.0, 50.0, 50.0)

            gc.StrokePath(gcpath)

    def on_button_close(self, event):
        self.context("window toggle Hingetool\n")

    def on_button_generate(self, event):
        # self.context.signal("")
        return

    def on_option_update(self, event):
        flag = True
        idx = self.combo_style.GetSelection()
        if idx < 0: idx = 0
        style = self.patterns[idx]
        self.context.hinge_type = style
        try:
            wd = float(Length(self.text_width.GetValue()))
            if wd > 0:
                self.context.hinge_width = self.text_width.GetValue()
        except ValueError:
            flag = False
        try:
            ht = float(Length(self.text_height.GetValue()))
            if ht > 0:
                self.context.hinge_height = self.text_height.GetValue()
        except ValueError:
            flag = False
        cell_x = self.slider_width.GetValue()
        self.context.hinge_cells_x = cell_x
        cell_y = self.slider_width.GetValue() / 100.0
        self.context.hinge_cells_y = cell_y
        offset_x = self.slider_offset_x.GetValue()
        self.context.hinge_offset_x = offset_x
        offset_y = self.slider_offset_y.GetValue()
        self.context.hinge_offset_y = offset_y

        self._restore_settings(True)
        self.panel_preview.Refresh()
        self.button_generate.Enable(flag)

    def _setup_settings(self):
        self.context.setting(str, "hinge_type", "line")
        self.context.setting(str, "hinge_width", "5cm")
        self.context.setting(str, "hinge_height", "5cm")
        self.context.setting(int, "hinge_cells_x", 20)
        self.context.setting(int, "hinge_cells_y", 20)
        self.context.setting(int, "hinge_offset_x", 10)
        self.context.setting(int, "hinge_offset_y", 10)

    def _restore_settings(self, just_internal=False):
        if self.context.hinge_type not in self.patterns:
            self.context.hinge_type = self.patterns[0]
        self.hinge_generator.width = float(Length(self.context.hinge_width))
        self.hinge_generator.height = float(Length(self.context.hinge_height))
        self.hinge_generator.set_predefined_pattern(self.context.hinge_type)
        self.hinge_generator.cell_width_percentage = self.context.hinge_cells_x
        self.hinge_generator.cell_height_percentage = self.context.hinge_cells_y
        self.hinge_generator.cell_offset_h_percentage = self.context.hinge_offset_x
        self.hinge_generator.cell_offset_v_percentage = self.context.hinge_offset_y
        if just_internal:
            return
        self.combo_style.SetSelection(self.patterns.index(self.context.hinge_type))
        self.text_width.SetValue(self.context.hinge_width)
        self.text_height.SetValue(self.context.hinge_height)
        self.slider_width.SetValue(self.context.hinge_cells_x)
        self.slider_height.SetValue(self.context.hinge_cells_y)
        self.slider_offset_x.SetValue(self.context.hinge_offset_x)
        self.slider_offset_y.SetValue(self.context.hinge_offset_y)

    def pane_show(self):
        bounds = self.context.elements._emphasized_bounds
        if bounds is not None:
            units = self.context.units_name
            wd = bounds[2] - bounds[0]
            ht = bounds[3] - bounds[1]
            self.text_width.SetValue(Length(amount=wd, digits=2, preferred_units=units).preferred_length)
            self.text_height.SetValue(Length(amount=ht, digits=2, preferred_units=units).preferred_length)

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

    @staticmethod
    def submenu():
        return ("Laser-Tools", "Living-Hinges")
