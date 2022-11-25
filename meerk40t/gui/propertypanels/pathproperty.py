from copy import copy

import wx

from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.gui.icons import icons8_vector_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.propertypanels.attributes import (
    ColorPanel,
    IdPanel,
    LinePropPanel,
    PositionSizePanel,
    StrokeWidthPanel,
)
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class PathPropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.setting(
            bool, "_auto_classify", self.context.elements.classify_on_color
        )
        self.node = node
        self.panels = []
        # Id at top in all cases...
        panel_id = IdPanel(self, id=wx.ID_ANY, context=self.context, node=self.node)
        self.panels.append(panel_id)

        for property_class in self.context.lookup_all("path_attributes/.*"):
            panel = property_class(
                self, id=wx.ID_ANY, context=self.context, node=self.node
            )
            self.panels.append(panel)

        panel_stroke = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Stroke:",
            attribute="stroke",
            callback=self.callback_color,
            node=self.node,
        )
        self.panels.append(panel_stroke)
        panel_fill = ColorPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            label="Fill:",
            attribute="fill",
            callback=self.callback_color,
            node=self.node,
        )
        self.panels.append(panel_fill)
        # Next one is a placeholder...
        self.panels.append(None)

        panel_width = StrokeWidthPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_width)
        panel_line = LinePropPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_line)
        panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.panels.append(panel_xy)

        # Property display
        self.lbl_info_points = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.lbl_info_length = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.lbl_info_area = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.btn_info_get = wx.Button(self, wx.ID_ANY, _("Retrieve"))
        self.check_classify = wx.CheckBox(
            self, wx.ID_ANY, _("Immediately classify after colour change")
        )
        self.check_classify.SetValue(self.context._auto_classify)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_btn_get_infos, self.btn_info_get)

    @staticmethod
    def accepts(node):
        if node.type == "elem text":
            return False
        elif node.type.startswith("elem"):
            return True
        return False

    def covered_area(self, nodes):
        area_with_stroke = 0
        area_without_stroke = 0
        make_raster = self.context.root.lookup("render-op/make_raster")
        if nodes is None or len(nodes) == 0 or not make_raster:
            return 0, 0
        ratio = 0
        dpi = 300
        dots_per_units = dpi / UNITS_PER_INCH
        _mm = float(Length("1mm"))
        data = []
        for node in nodes:
            e = copy(node)
            if hasattr(e, "fill"):
                e.fill = Color("black")
            data.append(e)

        for with_stroke in (True, False):
            no_stroke = True
            for e in data:
                if hasattr(e, "stroke"):
                    no_stroke = False
                    e.stroke = Color("black")
                    if not with_stroke:
                        e.stroke_width = 1
                    e.altered()

            if with_stroke:
                bounds = Node.union_bounds(data, attr="paint_bounds")
            else:
                bounds = Node.union_bounds(data)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            new_width = int(width * dots_per_units)
            new_height = int(height * dots_per_units)
            # print(f"Width: {width:.0f} -> {new_width}")
            # print(f"Height: {height:.0f} -> {new_height}")
            keep_ratio = True
            ratio = 0

            all_pixel = new_height * new_width
            if all_pixel > 0:
                image = make_raster(
                    data,
                    bounds=bounds,
                    width=new_width,
                    height=new_height,
                    keep_ratio=keep_ratio,
                )
                white_pixel = sum(
                    image.point(lambda x: 255 if x else 0)
                    .convert("L")
                    .point(bool)
                    .getdata()
                )
                black_pixel = all_pixel - white_pixel
                # print(
                #     f"Mode: {with_stroke}, pixels: {all_pixel}, white={white_pixel}, black={black_pixel}"
                # )
                ratio = black_pixel / all_pixel
                area = (
                    ratio
                    * (bounds[2] - bounds[0])
                    * (bounds[3] - bounds[1])
                    / (_mm * _mm)
                )
                if with_stroke:
                    area_with_stroke = area
                else:
                    area_without_stroke = area
                if no_stroke:
                    # No sense of doing it again
                    if area_without_stroke == 0:
                        area_without_stroke = area_with_stroke
                    break

        # print(f"Area, with: {area_with_stroke:.0f}, without: {area_without_stroke:.0f}")
        return area_with_stroke, area_without_stroke

    def on_btn_get_infos(self, event):
        def closed_path(path):
            p1 = path.first_point
            p2 = path.current_point
            # print (p1, p2)
            # print (type(p1).__name__, type(p2).__name__)
            return p1 == p2

        def calc_points(node):
            from meerk40t.svgelements import (
                Arc,
                Close,
                CubicBezier,
                Line,
                Move,
                QuadraticBezier,
            )

            result = 0
            if hasattr(node, "as_path"):
                path = node.as_path()
                target = []
                first_point = path.first_point
                if first_point is not None:
                    pt = (first_point[0], first_point[1], 0)
                    target.append(pt)
                for e in path:
                    if isinstance(e, Move):
                        pt = (e.end[0], e.end[1], 0)
                        if pt not in target:
                            target.append(pt)
                    elif isinstance(e, Line):
                        pt = (e.end[0], e.end[1], 0)
                        if pt not in target:
                            target.append(pt)
                    elif isinstance(e, Close):
                        pass
                    elif isinstance(e, QuadraticBezier):
                        pt = (e.end[0], e.end[1], 0)
                        if pt not in target:
                            target.append(pt)
                    elif isinstance(e, CubicBezier):
                        pt = (e.end[0], e.end[1], 0)
                        if pt not in target:
                            target.append(pt)
                    elif isinstance(e, Arc):
                        pt = (e.end[0], e.end[1], 0)
                        if pt not in target:
                            target.append(pt)
                result = len(target)
            elif hasattr(node, "bounds"):
                result = 4
            return result

        elements = self.context.elements
        _mm = float(Length("1mm"))
        total_area = 0
        total_length = 0
        if hasattr(self.node, "as_path"):
            path = self.node.as_path()
            total_length = path.length()
        else:
            total_length = 0
        total_area, second_area = self.covered_area([self.node])

        total_length = total_length / _mm
        points = calc_points(self.node)

        self.lbl_info_area.SetValue(f"{total_area:.0f} mm² ({second_area:.0f} mm²)")
        self.lbl_info_length.SetValue(f"{total_length:.1f} mm")
        self.lbl_info_points.SetValue(f"{points:d}")

    def set_widgets(self, node):
        for panel in self.panels:
            if panel is not None:
                panel.set_widgets(node)

        if node is not None:
            self.node = node
        self.lbl_info_area.SetValue("")
        self.lbl_info_length.SetValue("")
        self.lbl_info_points.SetValue("")

        self.Refresh()

    def __set_properties(self):
        return

    def __do_layout(self):
        # begin wxGlade: PathProperty.__do_layout
        sizer_v_main = wx.BoxSizer(wx.VERTICAL)

        sizer_h_infos = wx.BoxSizer(wx.HORIZONTAL)
        sizer_info1 = StaticBoxSizer(self, wx.ID_ANY, _("Points"), wx.VERTICAL)
        sizer_info1.Add(self.lbl_info_points, 1, wx.EXPAND, 0)

        sizer_info2 = StaticBoxSizer(self, wx.ID_ANY, _("Length"), wx.VERTICAL)
        sizer_info2.Add(self.lbl_info_length, 1, wx.EXPAND, 0)

        sizer_info3 = StaticBoxSizer(
            self, wx.ID_ANY, _("Area (w/wo stroke)"), wx.VERTICAL
        )
        sizer_info3.Add(self.lbl_info_area, 1, wx.EXPAND, 0)

        sizer_h_infos.Add(sizer_info1, 0, wx.EXPAND, 0)
        sizer_h_infos.Add(sizer_info2, 0, wx.EXPAND, 0)
        sizer_h_infos.Add(sizer_info3, 1, wx.EXPAND, 0)
        sizer_h_infos.Add(self.btn_info_get, 0, wx.EXPAND, 0)

        for panel in self.panels:
            if panel is None:
                sizer_v_main.Add(self.check_classify, 0, wx.EXPAND, 0)
            else:
                sizer_v_main.Add(panel, 0, wx.EXPAND, 0)

        sizer_v_main.Add(sizer_h_infos, 0, wx.EXPAND, 0)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_classify, self.check_classify)
        self.SetSizer(sizer_v_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_check_classify(self, event):
        self.context._auto_classify = self.check_classify.GetValue()

    def update_label(self):
        return

    def callback_color(self):
        self.node.altered()
        self.update_label()
        self.Refresh()
        if self.check_classify.GetValue():
            mynode = self.node
            wasemph = self.node.emphasized
            self.context("declassify\nclassify\n")
            self.context.elements.signal("tree_changed")
            self.context.elements.signal("element_property_update", self.node)
            mynode.emphasized = wasemph
            self.set_widgets(mynode)


class PathProperty(MWindow):
    def __init__(self, *args, node=None, **kwds):
        super().__init__(288, 303, *args, **kwds)

        self.panel = PathPropertyPanel(self, wx.ID_ANY, context=self.context, node=node)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_vector_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: PathProperty.__set_properties
        self.SetTitle(_("Path Properties"))

    def restore(self, *args, node=None, **kwds):
        self.panel.set_widgets(node)

    def window_preserve(self):
        return False

    def window_menu(self):
        return False
