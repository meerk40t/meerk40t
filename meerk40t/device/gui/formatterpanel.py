import wx

from meerk40t.core.elements.element_types import elem_group_nodes, op_nodes
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_file_20,
    icons8_group_objects_20,
    icons8_home_20,
    icons8_home_location_20,
    icons8_image_20,
    icons8_image_50,
    icons8_input_20,
    icons8_laser_beam_20,
    icons8_output_20,
    icons8_oval_50,
    icons8_polyline_50,
    icons8_rectangular_50,
    icons8_return_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
    icons8_system_task_20,
    icons8_text_50,
    icons8_timer_20,
    icons8_vector_50,
)

_ = wx.GetTranslation


class FormatterPanel(wx.Panel):
    """
    FormtterPanel is a panel that should work for all devices (hence in its own directory)
    It allows to define default formatting strings per operation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.data = {}
        images = {
            "util wait": icons8_timer_20,
            "util home": icons8_home_20,
            "util goto": icons8_return_20,
            "util output": icons8_output_20,
            "util input": icons8_input_20,
            "util console": icons8_system_task_20,
            "op engrave": icons8_small_beam_20,
            "op cut": icons8_laser_beam_20,
            "op image": icons8_image_20,
            "op raster": icons8_direction_20,
            "op hatch": icons8_diagonal_20,
            "op dots": icons8_scatter_plot_20,
            "effect hatch": icons8_diagonal_20,
            "file": icons8_file_20,
            "group": icons8_group_objects_20,
            "elem point": icons8_scatter_plot_20,
            "elem ellipse": icons8_oval_50,
            "elem image": icons8_image_50,
            "elem path": icons8_vector_50,
            "elem polyline": icons8_polyline_50,
            "elem rect": icons8_rectangular_50,
            "elem line": icons8_polyline_50,
            "elem text": icons8_text_50,
            "place current": icons8_home_location_20,
            "place point": icons8_home_location_20,
        }
        omit = ("elem line",)
        self.node_list = list(elem_group_nodes + op_nodes)
        for node in omit:
            try:
                self.node_list.remove(node)
            except ValueError:
                # wasnt in list...
                pass

        self.context.setting(bool, "use_percent_for_power_display", False)
        choices = [
            {
                "attr": "use_percent_for_power_display",
                "object": self.context,
                "default": False,
                "type": bool,
                "label": _("Display power as a percentage"),
                "tip": _("Active: Full power will be shown as 100%" + "\n" +
                         "Inactive: Full power will be shown as 1000 ppi"),
                "subsection": "_10_General",
                "signals": ("rebuild_tree", "power_percent"),
            },
        ]
        for node in self.node_list:
            imgsize = 20
            if node in images:
                image = images[node].GetBitmap(resize=imgsize, noadjustment=True)
            else:
                image = wx.Bitmap(8, imgsize, imgsize)
            if node in elem_group_nodes:
                sectname = "Elements"
            elif node in elem_group_nodes:
                sectname = "Grouping + Files"
            elif node.startswith("util"):
                sectname = "Operations (Special)"
            elif node in op_nodes:
                sectname = "Operations"
            else:
                sectname = ""
            lbl = node.replace(" ", "_")
            default = self.context.elements.lookup(f"format/{node}")
            if default is None:
                default = ""
            self.context.setting(bool, f"formatter_{lbl}_active", False)
            self.context.setting(str, f"formatter_{lbl}", default)
            # We have a pair of a checkbox and a textinput
            available = self.get_node_patterns(node)
            choices.append(
                {
                    "object": self.context,
                    "attr": f"formatter_{lbl}_active",
                    "label": f"{node}",
                    "type": bool,
                    "icon": image,
                    "tip": _("Do yo want to use a bespoke formatter?"),
                    "section": sectname,
                    "subsection": f"_{node}_",
                    "signals": "rebuild_tree",
                }
            )
            choices.append(
                {
                    "object": self.context,
                    "attr": f"formatter_{lbl}",
                    "label": "",
                    "type": str,
                    "weight": 2,
                    "width": 250,
                    "tip": _("Bespoke formatter for this node-type") + available,
                    "conditional": (self.context, f"formatter_{lbl}_active"),
                    "section": sectname,
                    "subsection": f"_{node}_",
                    "signals": "rebuild_tree",
                }
            )
            # tree_changed does not suffice
        patternpanel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(patternpanel, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.parent.add_module_delegate(patternpanel)

        self.update_widgets()

    def get_node_patterns(self, nodetype):
        from PIL import Image

        from meerk40t.core.node.elem_ellipse import EllipseNode
        from meerk40t.core.node.elem_image import ImageNode
        from meerk40t.core.node.elem_line import LineNode
        from meerk40t.core.node.elem_path import PathNode
        from meerk40t.core.node.elem_point import PointNode
        from meerk40t.core.node.elem_polyline import PolylineNode
        from meerk40t.core.node.elem_rect import RectNode
        from meerk40t.core.node.elem_text import TextNode
        from meerk40t.core.node.filenode import FileNode
        from meerk40t.core.node.groupnode import GroupNode
        from meerk40t.core.node.op_cut import CutOpNode
        from meerk40t.core.node.op_dots import DotsOpNode
        from meerk40t.core.node.op_engrave import EngraveOpNode
        from meerk40t.core.node.op_hatch import HatchOpNode
        from meerk40t.core.node.op_image import ImageOpNode
        from meerk40t.core.node.op_raster import RasterOpNode
        from meerk40t.core.node.refnode import ReferenceNode
        from meerk40t.core.node.util_console import ConsoleOperation
        from meerk40t.core.node.util_goto import GotoOperation
        from meerk40t.core.node.util_home import HomeOperation
        from meerk40t.core.node.util_input import InputOperation
        from meerk40t.core.node.util_output import OutputOperation
        from meerk40t.core.node.util_wait import WaitOperation

        bootstrap = {
            "op cut": CutOpNode,
            "op engrave": EngraveOpNode,
            "op raster": RasterOpNode,
            "op image": ImageOpNode,
            "op dots": DotsOpNode,
            "op hatch": HatchOpNode,
            "util console": ConsoleOperation,
            "util wait": WaitOperation,
            "util home": HomeOperation,
            "util goto": GotoOperation,
            "util input": InputOperation,
            "util output": OutputOperation,
            "group": GroupNode,
            "elem ellipse": EllipseNode,
            "elem line": LineNode,
            "elem rect": RectNode,
            "elem path": PathNode,
            "elem point": PointNode,
            "elem polyline": PolylineNode,
            "elem image": ImageNode,
            "elem text": TextNode,
            "reference": ReferenceNode,
            "file": FileNode,
        }
        node = None
        available = ""
        if nodetype in bootstrap:
            # print (f"Try to get an instance of {nodetype}")
            if nodetype.startswith("elem"):
                if nodetype == "elem rect":
                    node = bootstrap[nodetype](x=0, y=0, width=10, height=10)
                elif nodetype == "elem ellipse":
                    node = bootstrap[nodetype](cx=0, cy=0, rx=10, ry=10)
                elif nodetype == "elem path":
                    node = bootstrap[nodetype]()
                elif nodetype == "elem image":
                    # Let's use an arbitrary image
                    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
                    node = bootstrap[nodetype](image=image)
                elif nodetype == "elem polyline":
                    node = bootstrap[nodetype]()
                else:
                    node = bootstrap[nodetype]()
            else:
                node = bootstrap[nodetype]()

        if node is not None:
            mymap = node.default_map()
            for entry in mymap:
                if available != "":
                    available += ", "
                available += "{" + entry + "}"
            available = "\n" + available

        return available

    def on_checkbox_check(self, entry, isMax):
        def check(event=None):
            event.Skip()

        return check

    def on_text_formatter(self, textctrl, entry, isMax):
        def check(event=None):
            return

        return check

    def update_settings(self, operation, attribute, minmax, active, value):
        return

    def update_widgets(self):
        return

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()
