import wx

from meerk40t.gui.icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
    icons8_home_20,
    icons8_return_20,
    icons8_bell_20,
    icons8_stop_gesture_20,
    icons8_close_window_20,
    icons8_timer_20,
    icons8_home_20,
    icons8_return_20,
    icons8_output_20,
    icons8_input_20,
    icons8_system_task_20,
    icons8_scatter_plot_20,
    icons8_file_20,
    icons8_group_objects_20,
    icons8_oval_50,
    icons8_rectangular_50,
    icons8_polyline_50,
    icons8_text_50,
    icons8_image_50,
    icons8_vector_50,
)
from meerk40t.core.element_types import op_nodes, elem_group_nodes, elem_ref_nodes
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel

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
        self.context = context
        self.data = {}
        images = {
            "util wait": icons8_timer_20,
            "util home": icons8_home_20,
            "util goto": icons8_return_20,
            "util origin": icons8_return_20,
            "util output": icons8_output_20,
            "util input": icons8_input_20,
            "util console": icons8_system_task_20,
            "op engrave": icons8_small_beam_20,
            "op cut": icons8_laser_beam_20,
            "op image": icons8_image_20,
            "op raster": icons8_direction_20,
            "op hatch": icons8_diagonal_20,
            "op dots": icons8_scatter_plot_20,
            "file": icons8_file_20,
            "group": icons8_group_objects_20,
            "elem point": icons8_scatter_plot_20,
            "elem ellipse": icons8_oval_50,
            "elem image": icons8_image_50,
            "elem path": icons8_vector_50,
            "elem numpath": icons8_vector_50,
            "elem polyline": icons8_polyline_50,
            "elem rect": icons8_rectangular_50,
            "elem line": icons8_polyline_50,
            "elem text": icons8_text_50,
        }
        omit = ("elem numpath", "elem line")
        self.node_list = list(elem_group_nodes + op_nodes)
        for node in omit:
            try:
                self.node_list.remove(node)
            except ValueError:
                # wasnt in list...
                pass

        choices=[]
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
                default == ""
            self.context.setting(bool, f"formatter_{lbl}_active", False)
            self.context.setting(str, f"formatter_{lbl}", default)
            choices.append(
                {
                    "object": self.context,
                    "attr": f"formatter_{lbl}_active",
                    "label": f"{node}",
                    "type": bool,
                    "icon": image,
                    "tip": _("Do yo want to use a bespoke formatter"),
                    "section": sectname,
                    "subsection": f"_{node}_",
                    "signals": "tree_changed",
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
                    "tip": _("Bespoke formatter for this node-type"),
                    "conditional": (self.context, f"formatter_{lbl}_active"),
                    "section": sectname,
                    "subsection": f"_{node}_",
                    "signals": "tree_changed",
                }
            )
            # We have a pair of checkboxes and textinputs
        patternpanel = ChoicePropertyPanel(self, wx.ID_ANY, context=self.context, choices=choices)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(patternpanel, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()

        self.update_widgets()

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
