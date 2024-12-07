import wx

from meerk40t.core.elements.element_types import elem_group_nodes, op_nodes
from meerk40t.core.node.image_raster import ImageRasterNode
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    EmptyIcon,
    icon_console,
    icon_distort,
    icon_effect_hatch,
    icon_effect_wobble,
    icon_external,
    icon_internal,
    icon_mk_ellipse,
    icon_mk_polyline,
    icon_mk_rectangular,
    icon_points,
    icon_return,
    icon_timer,
    icons8_direction,
    icons8_file,
    icons8_group_objects,
    icons8_home_filled,
    icons8_image,
    icons8_laser_beam,
    icons8_laserbeam_weak,
    icons8_text,
    icons8_vector,
)
from meerk40t.gui.wxutils import dip_size

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
        self.context.themes.set_window_colors(self)
        self.SetHelpText("formatter")

        self.data = {}
        images = {
            "util wait": icon_timer,
            "util home": icons8_home_filled,
            "util goto": icon_return,
            "util output": icon_external,
            "util input": icon_internal,
            "util console": icon_console,
            "op engrave": icons8_laserbeam_weak,
            "op cut": icons8_laser_beam,
            "op image": icons8_image,
            "op raster": icons8_direction,
            "op dots": icon_points,
            "effect hatch": icon_effect_hatch,
            "effect wobble": icon_effect_wobble,
            "effect warp": icon_distort,
            "file": icons8_file,
            "group": icons8_group_objects,
            "elem point": icon_points,
            "elem ellipse": icon_mk_ellipse,
            "elem image": icons8_image,
            "elem path": icons8_vector,
            "elem polyline": icon_mk_polyline,
            "elem rect": icon_mk_rectangular,
            "elem line": icon_mk_polyline,
            "elem text": icons8_text,
            # "image raster": icons8_image,
            "place current": icons8_home_filled,
            "place point": icons8_home_filled,
        }
        omit = ("elem line",)
        self.node_list = list(elem_group_nodes + op_nodes)
        for node in omit:
            try:
                self.node_list.remove(node)
            except ValueError:
                # wasn't in list...
                pass

        self.context.setting(bool, "use_percent_for_power_display", False)
        self.context.setting(bool, "use_mm_min_for_speed_display", False)
        choices = [
            {
                "attr": "use_percent_for_power_display",
                "object": self.context,
                "default": False,
                "type": bool,
                "label": _("Show power as %"),
                "tip": _(
                    "Active: Full power will be shown as 100%"
                    + "\n"
                    + "Inactive: Full power will be shown as 1000 ppi"
                ),
                "subsection": "_10_General",
                "signals": ("rebuild_tree", "power_percent"),
            },
            {
                "attr": "use_mm_min_for_speed_display",
                "object": self.context,
                "default": False,
                "type": bool,
                "label": _("Show speed in mm/min"),
                "tip": _(
                    "Active: Speed will be shown in mm/min"
                    + "\n"
                    + "Inactive: Speed will be shown in mm/s"
                ),
                "subsection": "_10_General",
                "signals": ("rebuild_tree", "speed_min"),
            },
        ]
        testsize = dip_size(self, 20, 20)
        imgsize = testsize[1] * self.context.root.bitmap_correction_scale
        for node in self.node_list:
            if node in images:
                image = images[node].GetBitmap(
                    resize=imgsize, buffer=2, noadjustment=True
                )
            else:
                # print (f"Did not find {node}")
                continue
                # image = EmptyIcon(size=imgsize, color=None, msg="??").GetBitmap()
            if node.startswith("effect"):
                sectname = "Elements (Effects)"
            elif node in elem_group_nodes:
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
                    "signals": ("reset_formatter", "rebuild_tree"),
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
                    "signals": ("reset_formatter", "rebuild_tree"),
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

        # Get dictionary with all nodetypes
        from meerk40t.core.node.bootstrap import bootstrap

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
                elif nodetype in ("elem image", "image raster"):
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
