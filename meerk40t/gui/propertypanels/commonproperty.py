"""
A small pane to display and amend common properties of emphasized elements
"""
import wx
from wx import aui

from meerk40t.gui.wxutils import StaticBoxSizer
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.svgelements import Color

_ = wx.GetTranslation

UNDEF = "_undefined_"
NONEQ = "_different_"


def set_value(context, nodes, attributes, value):
    changed = list()
    if isinstance(attributes, str):
        attributes = [attributes]
    requires_classify = False
    requires_update = False
    property_ops = []
    for attrib in attributes:
        if attrib in ("stroke", "fill"):
            requires_classify = True
        if attrib in ("mkalign", "mktext", "mkfontsize", "mkfont"):
            requires_update = True
            property_ops = [p for p in context.kernel.lookup_all("path_updater/.*")]

    for e in nodes:
        for attrib in attributes:
            if hasattr(e, attrib):
                setattr(e, attrib, value)
                if e.type == "elem path" and requires_update:
                    for p in property_ops:
                        p(context.kernel.root, e)

                changed.append(e)
    if len(changed):
        context.signal("element_property_update", changed)
        if requires_classify:
            context.elements.classify(changed)
        context.signal("refresh_scene", "Scene")


class PropertyColor(StaticBoxSizer):
    def __init__(self, parent, *args, **kwds):
        self.parent = parent
        self.nodes = list()
        self.common_stroke = UNDEF
        self.common_fill = UNDEF
        # kwds["orientation"] = wx.HORIZONTAL
        super().__init__(parent, wx.ID_ANY, _("Color"), wx.HORIZONTAL)
        self.color_list = (
            None,
            Color("black"),
            Color("white"),
            Color(red=255, green=0, blue=0),
            Color(red=0, green=255, blue=0),
            Color(red=0, green=0, blue=255),
            Color(red=255, green=255, blue=0),
            Color(red=255, green=0, blue=255),
            Color(red=0, green=255, blue=255),
        )
        choices = (
            _("Transp."),
            _("Black"),
            _("White"),
            _("Red"),
            _("Green"),
            _("Blue"),
            _("Yellow"),
            _("Magenta"),
            _("Cyan"),
        )
        self.col_stroke = wx.ComboBox(
            self.parent, wx.ID_ANY, choices=choices, style=wx.CB_READONLY | wx.CB_SIMPLE
        )
        self.col_stroke.SetBackgroundColour(wx.Colour(0, 0, 0))
        COLOR_TOOLTIP = _("Change/View the {type}-color of the selected elements.")
        self.col_stroke.SetToolTip(COLOR_TOOLTIP.format(type=_("stroke")))

        self.col_fill = wx.ComboBox(
            self.parent, wx.ID_ANY, choices=choices, style=wx.CB_READONLY | wx.CB_SIMPLE
        )
        self.col_fill.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.col_fill.SetToolTip(COLOR_TOOLTIP.format(type=_("fill")))
        self.Add(self.col_stroke, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.col_fill, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_stroke, self.col_stroke)
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_fill, self.col_fill)
        self.set_widgets(None)

    def set_control_color(self, ctrl, color):
        def color_distance(c1, c2):
            from math import sqrt

            red_mean = int((c1.red + c2.red) / 2.0)
            r = c1.red - c2.red
            g = c1.green - c2.green
            b = c1.blue - c2.blue
            distance_sq = (
                (((512 + red_mean) * r * r) >> 8)
                + (4 * g * g)
                + (((767 - red_mean) * b * b) >> 8)
            )
            return sqrt(distance_sq)

        if color is None:
            bgc = wx.SystemSettings().GetColour(wx.SYS_COLOUR_LISTBOX)
            fgc = wx.SystemSettings().GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
        else:
            if isinstance(color, Color):
                bgc = wx.Colour(swizzlecolor(color))
            else:
                bgc = color
            d1 = color_distance(bgc, wx.BLACK)
            d2 = color_distance(bgc, wx.WHITE)
            if d1 < d2:
                fgc = wx.WHITE
            else:
                fgc = wx.BLACK
        ctrl.SetBackgroundColour(bgc)
        ctrl.SetForegroundColour(fgc)

    def on_stroke(self, event):
        idx = self.col_stroke.GetSelection()
        if idx < 0:
            return
        color = self.color_list[idx]
        self.set_control_color(self.col_stroke, color)
        set_value(self.parent.context, self.nodes, "stroke", color)

    def on_fill(self, event):
        idx = self.col_fill.GetSelection()
        if idx < 0:
            return
        color = self.color_list[idx]
        self.set_control_color(self.col_fill, color)
        set_value(self.parent.context, self.nodes, "fill", color)

    def color_index(self, color):
        # The naiive self.color_list.index() fails as colors are not hashable?!
        if color is None:
            return 0
        if not isinstance(color, Color):
            return -1
        cval = color.rgb
        for idx, std_col in enumerate(self.color_list):
            if std_col is None:
                continue
            if std_col.rgb == cval:
                return idx
        return -1

    def set_widgets(self, nodes):
        has_fill = False
        has_stroke = False
        self.common_stroke = UNDEF
        self.common_fill = UNDEF
        self.nodes.clear()
        if nodes is None:
            nodes = []

        for e in nodes:
            f1 = hasattr(e, "stroke")
            f2 = hasattr(e, "fill")
            if f1 or f2:
                self.nodes.append(e)
            if f1:
                has_stroke = True
                p = getattr(e, "stroke", None)
                if self.common_stroke == UNDEF:
                    self.common_stroke = p
                elif self.common_stroke == NONEQ:
                    pass
                else:
                    if p != self.common_stroke:
                        self.common_stroke = NONEQ
            if f2:
                has_fill = True
                p = getattr(e, "fill", None)
                if self.common_fill == UNDEF:
                    self.common_fill = p
                elif self.common_fill == NONEQ:
                    pass
                else:
                    if p != self.common_fill:
                        self.common_fill = NONEQ
        idx = self.color_index(self.common_stroke)
        if idx < 0:
            col = None
        else:
            col = self.color_list[idx]
        self.set_control_color(self.col_stroke, col)
        self.col_stroke.SetSelection(idx)
        self.col_stroke.Refresh()
        idx = self.color_index(self.common_fill)
        if idx < 0:
            col = None
        else:
            col = self.color_list[idx]
        self.set_control_color(self.col_fill, col)
        self.col_fill.SetSelection(idx)
        self.col_fill.Refresh()
        if has_fill or has_stroke:
            self.ShowItems(True)
            self.col_fill.Show(has_fill)
            self.col_stroke.Show(has_stroke)
            self.Layout()
        else:
            self.ShowItems(False)


class PropertyFont(StaticBoxSizer):
    def __init__(self, parent, *args, **kwds):
        self.parent = parent
        self.nodes = list()
        self.common_font = UNDEF
        self.common_align = UNDEF
        # kwds["orientation"] = wx.HORIZONTAL
        super().__init__(parent, wx.ID_ANY, _("Font-Properties"), wx.HORIZONTAL)

        self.font_list = []
        self.font_facename = wx.ComboBox(
            self.parent, wx.ID_ANY, style=wx.CB_READONLY | wx.CB_SIMPLE
        )
        self.font_facename.SetBackgroundColour(wx.Colour(0, 0, 0))
        ttip = _("Change/View the font of the selected elements.")
        self.font_facename.SetToolTip(ttip)

        self.anchor_list = ("start", "middle", "end")
        choices = (
            _("Left"),
            _("Center"),
            _("Right"),
        )
        self.font_anchor = wx.ComboBox(
            self.parent, wx.ID_ANY, choices=choices, style=wx.CB_READONLY | wx.CB_SIMPLE
        )
        self.font_anchor.SetToolTip(
            _("Sets the text alignment for the selected elements")
        )
        self.Add(self.font_facename, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Add(self.font_anchor, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.parent.Bind(wx.EVT_COMBOBOX, self.on_facename, self.font_facename)
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_anchor, self.font_anchor)
        self.set_widgets(None)

    def on_facename(self, event):
        idx = self.font_facename.GetSelection()
        if idx < 0:
            return
        facename = self.font_list[idx]
        t_list = []
        p_list = []
        for e in self.nodes:
            if e.type == "elem text":
                t_list.append(e)
            else:
                p_list.append(e)
        attributes = "font_family"
        set_value(self.parent.context, t_list, attributes, facename)
        fontname = self.parent.context.fonts.face_to_full_name(facename)
        if fontname is None:
            return
        fontname = self.parent.context.fonts.short_name(fontname)
        attributes = "mkfont"
        set_value(self.parent.context, p_list, attributes, fontname)

    def on_anchor(self, event):
        idx = self.font_anchor.GetSelection()
        if idx < 0:
            return
        anchor = self.anchor_list[idx]
        attributes = ("anchor", "mkalign")
        set_value(self.parent.context, self.nodes, attributes, anchor)

    def set_widgets(self, nodes):
        if nodes is not None:
            p = self.parent.context.fonts.available_fonts()
            self.font_list = [info[1] for info in p]
            self.font_facename.SetItems(self.font_list)

        has_font = False
        self.common_font = UNDEF
        self.common_anchor = UNDEF
        self.nodes.clear()
        if nodes is None:
            nodes = []

        for e in nodes:
            if not (
                e.type == "elem text"
                or (e.type == "elem path" and hasattr(e, "mkfont"))
            ):
                continue
            has_font = True
            self.nodes.append(e)
            anchor = "start"
            if hasattr(e, "mkalign"):
                anchor = getattr(e, "mkalign", "start")
            elif hasattr(e, "anchor"):
                anchor = getattr(e, "anchor", "start")
            face = None
            if hasattr(e, "mkfont"):
                fname = getattr(e, "mkfont", "")
                if fname:
                    # We need to translate that into the facename
                    info = self.parent.context.fonts._get_full_info(fname)
                    if info is not None:
                        face = info[1]
            elif hasattr(e, "wxfont"):
                face = e.wxfont.GetFaceName()

            if face:
                if self.common_font == UNDEF:
                    self.common_font = face
                elif self.common_font == NONEQ:
                    pass
                else:
                    if face != self.common_font:
                        self.common_font = NONEQ
            if self.common_anchor == UNDEF:
                self.common_anchor = anchor
            elif self.common_anchor == NONEQ:
                pass
            else:
                if anchor != self.common_anchor:
                    self.common_anchor = NONEQ

        idx = -1
        try:
            idx = self.anchor_list.index(self.common_anchor)
        except ValueError:
            pass
        self.font_anchor.SetSelection(idx)

        idx = -1
        try:
            idx = self.font_list.index(self.common_font)
        except ValueError:
            pass
        self.font_facename.SetSelection(idx)

        if has_font:
            self.ShowItems(True)
            self.font_facename.Show(has_font)
            self.font_anchor.Show(True)
            self.Layout()
        else:
            self.ShowItems(False)


class PropertyHolder(wx.Panel):
    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.registered_handlers = list()
        self.registered_handlers.append(PropertyColor(self))
        self.registered_handlers.append(PropertyFont(self))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        for handler in self.registered_handlers:
            main_sizer.Add(handler, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Layout()

        # Untranslated, will be done outside
        # _("Common properties")
        self.name = "Common properties"

    def set_widgets(self, node):
        self.Freeze()
        nodes = list(self.context.elements.elems(emphasized=True))
        for handler in self.registered_handlers:
            handler.set_widgets(nodes)
        self.Layout()
        self.Thaw()

    def pane_active(self):
        self.Show(True)

    def pane_deactive(self):
        self.Show(False)
