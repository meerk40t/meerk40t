import wx

#from meerk40t.core.elements.element_types import elem_group_nodes, op_nodes
#from meerk40t.core.node.image_raster import ImageRasterNode
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.wxutils import dip_size
from meerk40t.core.units import Angle
from meerk40t.device.devicechoices import get_effect_choices

_ = wx.GetTranslation


class EffectsPanel(wx.Panel):
    """
    EffectsPanel is a panel that should work for all devices (hence in its own directory)
    It allows to define default settings for effects for a device
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.parent = args[0]
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("effects")

        self.data = {}

        for choice in get_effect_choices(self.context):
            self.context.setting(choice["type"], choice["attr"], choice["default"])

        #self.context.setting(str, "effect_hatch_default_distance", "1.0mm")
        #self.context.setting(str, "effect_hatch_default_angle", "0deg")

        #self.context.setting(str, "effect_wobble_default_radius", "0.5mm")
        #self.context.setting(str, "effect_wobble_default_interval", "0.05mm")
        #self.context.setting(str, "effect_wobble_default_speed", "50")

        testsize = dip_size(self, 20, 20)
        imgsize = testsize[1]
        epanel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=get_effect_choices(self.context)
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(epanel, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.parent.add_module_delegate(epanel)

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
