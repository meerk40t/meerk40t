import wx

from ..icons import icons8_image_50
from ..mwindow import MWindow
from ..wxutils import ScrolledPanel, TextCtrl
from .attributes import IdPanel, PositionSizePanel

_ = wx.GetTranslation

class CropPanel(wx.Panel):
    name = _("Crop")
    priority = 5

    @staticmethod
    def accepts(node):
        if node.type != "elem image":
            return False
        for n in node.operations:
            if n.get("name") == "crop":
                return True
        return False

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.node = node

        self.check_enable_crop = wx.CheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset = wx.Button(self, wx.ID_ANY, _("Reset"))

        self.label_info = wx.StaticText(self, wx.ID_ANY, "--")

        self.slider_left = wx.Slider(self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.slider_right = wx.Slider(self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.slider_top = wx.Slider(self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.slider_bottom = wx.Slider(self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.text_left = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_right = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_top = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_bottom = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_reset, self.button_reset)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable_crop, self.check_enable_crop)
        self.Bind(wx.EVT_SLIDER, self.on_slider_left, self.slider_left)
        self.Bind(wx.EVT_SLIDER, self.on_slider_right, self.slider_right)
        self.Bind(wx.EVT_SLIDER, self.on_slider_top, self.slider_top)
        self.Bind(wx.EVT_SLIDER, self.on_slider_bottom, self.slider_bottom)

        flag = False
        self.button_reset.Enable(flag)
        self.slider_left.Enable(flag)
        self.slider_right.Enable(flag)
        self.slider_top.Enable(flag)
        self.slider_bottom.Enable(flag)

        self.set_widgets(node)

    def set_widgets(self, node):
        if self.node is None:
            self.label_info.SetLabel("")
            self.Hide()
            return
        else:
            self.Show()
        self._no_update = True
        self.node = node
        self.op = None
        self._width, self._height = self.node.image.size
        self._bounds = [0, 0, self._width, self._height]
        flag = False
        for n in node.operations:
            if n.get("name") == "crop":
                self.op = n
                break
        self._width, self._height = self.node.image.size
        self.label_info.SetLabel(f"{self._width} x {self._height} px")
        if self.op is not None:
            flag = self.op["enable"]
            self._bounds = self.op["bounds"]
            if self._bounds is None:
                self._bounds = [0, 0, self._width, self._height]
                self.op["bounds"] = self._bounds

        self.set_slider_limits("lrtb", False)

        self.check_enable_crop.SetValue(flag)
        self.cropleft = self._bounds[0]
        self.cropright = self._bounds[2]
        self.croptop = self._bounds[1]
        self.cropbottom = self._bounds[3]
        self._no_update = False

    def __set_properties(self):
        self.slider_left.SetToolTip(_("How many pixels do you want to crop from the left?"))
        self.slider_right.SetToolTip(_("How many pixels do you want to crop from the right?"))
        self.slider_top.SetToolTip(_("How many pixels do you want to crop from the top?"))
        self.slider_bottom.SetToolTip(_("How many pixels do you want to crop from the bottom?"))

    def __do_layout(self):
        # begin wxGlade: ContrastPanel.__do_layout
        sizer_main = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Image-Dimensions")), wx.VERTICAL
        )
        sizer_info = wx.BoxSizer(wx.HORIZONTAL)
        sizer_info.Add(self.check_enable_crop, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_info.Add(self.button_reset, 0, wx.EXPAND, 0)
        sizer_info.Add(self.label_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_left = wx.BoxSizer(wx.HORIZONTAL)
        sizer_right = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bottom = wx.BoxSizer(wx.HORIZONTAL)

        lbl_left = wx.StaticText(self, wx.ID_ANY, _("Left"))
        lbl_left.SetMinSize((60, -1))
        lbl_right = wx.StaticText(self, wx.ID_ANY, _("Right"))
        lbl_right.SetMinSize((60, -1))
        lbl_bottom = wx.StaticText(self, wx.ID_ANY, _("Bottom"))
        lbl_bottom.SetMinSize((60, -1))
        lbl_top = wx.StaticText(self, wx.ID_ANY, _("Top"))
        lbl_top.SetMinSize((60, -1))

        self.text_left.SetMaxSize((60, -1))
        self.text_right.SetMaxSize((60, -1))
        self.text_top.SetMaxSize((60, -1))
        self.text_bottom.SetMaxSize((60, -1))

        sizer_left.Add(lbl_left, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_left.Add(self.slider_left, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_left.Add(self.text_left, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_right.Add(lbl_right, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_right.Add(self.slider_right, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_right.Add(self.text_right, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_top.Add(lbl_top, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_top.Add(self.slider_top, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_top.Add(self.text_top, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_bottom.Add(lbl_bottom, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_bottom.Add(self.slider_bottom, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_bottom.Add(self.text_bottom, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_main.Add(sizer_info, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_left, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_right, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_top, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_bottom, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def on_button_reset(self, event):
        if self.node is None:
            return
        w, h = self.node.image.size
        self._bounds = [0, 0, w, h]
        self.op["bounds"] = self._bounds
        self.set_slider_limits("lrtb")
        self.node.update(self.context)

    def on_check_enable_crop(self, event=None):
        flag = self.check_enable_crop.GetValue()
        if flag:
            if self.op is None:
                w, h = self.node.image.size
                self._width = w
                self._height = h
                self.op = {"name": "crop", "enable": True, "bounds": [0, 0, w, h]}
                self.node.operations.append(self.op)
                self.set_slider_limits("lrtb", False)
                last = self._no_update
                self._no_update = True
                self.cropleft = 0
                self.copright = w
                self.croptop = 0
                self.cropbottom = h
                self._no_update = last
        else:
            if self.op is not None:
                self.op["enable"] = flag
        if self.op is not None and not self._no_update:
            self.node.update(self.context)
        self.button_reset.Enable(flag)
        self.slider_left.Enable(flag)
        self.slider_right.Enable(flag)
        self.slider_top.Enable(flag)
        self.slider_bottom.Enable(flag)

    def on_slider_left(self, event=None):
        self.cropleft = self.slider_left.GetValue()

    def on_slider_right(self, event=None):
        self.cropright = self.slider_right.GetValue()

    def on_slider_top(self, event=None):
        self.croptop = self.slider_top.GetValue()

    def on_slider_bottom(self, event=None):
        self.cropbottom = self.slider_bottom.GetValue()

    def set_slider_limits(self, pattern, constraint=True):
        if "l" in pattern:
            value = self._bounds[2]
            self.slider_left.SetMin(0)
            self.slider_left.SetMax(value - 1 if constraint else self._width)
            if self._bounds[0] != self.slider_left.GetValue():
                self.slider_left.SetValue(self._bounds[0])
                dvalue = self._bounds[0]
                if dvalue==0:
                    self.text_left.SetValue(f"---")
                else:
                    self.text_left.SetValue(f"> {dvalue} px")
        if "r" in pattern:
            value = self._bounds[0]
            self.slider_right.SetMin(value + 1 if constraint else 0)
            self.slider_right.SetMax(self._width)
            if self._bounds[2] != self.slider_right.GetValue():
                self.slider_right.SetValue(self._bounds[2])
                dvalue = self._width - self._bounds[2]
                if dvalue==0:
                    self.text_right.SetValue(f"---")
                else:
                    self.text_right.SetValue(f"{dvalue} px <")
        if "t" in pattern:
            value = self._bounds[3]
            self.slider_top.SetMin(0)
            self.slider_top.SetMax(value - 1 if constraint else self._height)
            if self._bounds[1] != self.slider_top.GetValue():
                self.slider_top.SetValue(self._bounds[1])
                dvalue = self._bounds[1]
                if dvalue==0:
                    self.text_top.SetValue(f"---")
                else:
                    self.text_top.SetValue(f"> {dvalue} px")
        if "b" in pattern:
            value = self._bounds[1]
            self.slider_bottom.SetMin(value + 1 if constraint else 0)
            self.slider_bottom.SetMax(self._height)
            if self._bounds[3] != self.slider_bottom.GetValue():
                self.slider_bottom.SetValue(self._bounds[3])
                dvalue = self._height - self._bounds[3]
                if dvalue==0:
                    self.text_bottom.SetValue(f"---")
                else:
                    self.text_bottom.SetValue(f"{dvalue} px <")

    @property
    def cropleft(self):
        if self._bounds is None:
            return None
        else:
            return self._bounds[0]

    @cropleft.setter
    def cropleft(self, value):
        # print(f"Set left to: {value}")
        self._bounds[0] = value
        if self.slider_left.GetValue() != value:
            self.slider_left.SetValue(value)
        if value==0:
            self.text_left.SetValue(f"---")
        else:
            self.text_left.SetValue(f"> {value} px")
        # We need to adjust the boundaries of the right slider.
        self.set_slider_limits("r")
        if self.op is not None:
            self.op["bounds"][0] = value
            if not self._no_update:
                self.node.update(self.context)

    @property
    def cropright(self):
        if self._bounds is None:
            return None
        else:
            return self._bounds[2]

    @cropright.setter
    def cropright(self, value):
        # print(f"Set right to: {value}")
        self._bounds[2] = value
        if self.slider_right.GetValue() != value:
            self.slider_right.SetValue(value)
        dvalue = self._width - value
        if dvalue==0:
            self.text_right.SetValue(f"---")
        else:
            self.text_right.SetValue(f"{dvalue} px <")
        # We need to adjust the boundaries of the left slider.
        self.set_slider_limits("l")
        if self.op is not None:
            self.op["bounds"][2] = value
            if not self._no_update:
                self.node.update(self.context)

    @property
    def croptop(self):
        if self._bounds is None:
            return None
        else:
            return self._bounds[1]

    @croptop.setter
    def croptop(self, value):
        # print(f"Set top to: {value}")
        self._bounds[1] = value
        if self.slider_top.GetValue() != value:
            self.slider_top.SetValue(value)
        if value==0:
            self.text_top.SetValue(f"---")
        else:
            self.text_top.SetValue(f"> {value} px")
        # We need to adjust the boundaries of the bottom slider.
        self.set_slider_limits("b")
        if self.op is not None:
            self.op["bounds"][1] = value
            if not self._no_update:
                self.node.update(self.context)

    @property
    def cropbottom(self):
        if self._bounds is None:
            return None
        else:
            return self._bounds[3]

    @cropbottom.setter
    def cropbottom(self, value):
        self._bounds[3] = value
        if self.slider_bottom.GetValue() != value:
            self.slider_bottom.SetValue(value)
        # We need to adjust the boundaries of the top slider.
        self.set_slider_limits("t")
        if self.op is not None:
            self.op["bounds"][3] = value
            if not self._no_update:
                self.node.update(self.context)

class ImageModificationPanel(ScrolledPanel):
    name = _("Modification")
    priority = 90

    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node
        self.scripts = []
        choices = []
        choices.append(_("Set to None"))
        for entry in list(self.context.match("raster_script/.*", suffix=True)):
            self.scripts.append(entry)
            choices.append(_("Apply {entry}").format(entry=entry))
        self.combo_scripts = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self.combo_scripts.SetSelection(0)
        self.button_apply = wx.Button(self, wx.ID_ANY, _("Apply Script"))
        self.list_operations = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL)

        self._do_layout()
        self._do_logic()
        self.set_widgets(node)


    def _do_layout(self):
        self.list_operations.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_operations.AppendColumn(_("Action"), format=wx.LIST_FORMAT_LEFT, width=65)
        self.list_operations.AppendColumn(_("Active"), format=wx.LIST_FORMAT_LEFT, width=25)
        self.list_operations.AppendColumn(_("Parameters"), format=wx.LIST_FORMAT_LEFT, width=95)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_script = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("RasterWizard")), wx.HORIZONTAL
        )

        sizer_script.Add(self.combo_scripts, 1, wx.EXPAND, 0)
        sizer_script.Add(self.button_apply, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_script, 0, wx.EXPAND, 0)
        sizer_main.Add(self.list_operations, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()

    def _do_logic(self):
        self.button_apply.Bind(wx.EVT_BUTTON, self.on_apply_replace)
        self.button_apply.Bind(wx.EVT_RIGHT_DOWN, self.on_apply_append)
        self.list_operations.Bind(wx.EVT_RIGHT_DOWN, self.on_list_menu)

    @staticmethod
    def accepts(node):
        if node.type == "elem image":
            return True
        return False

    def set_widgets(self, node=None):
        self.node = node
        if node is None:
            return
        self.fill_operations()

    def fill_operations(self):
        self.list_operations.DeleteAllItems()
        idx = 0
        for op in self.node.operations:
            idx += 1
            list_id = self.list_operations.InsertItem(self.list_operations.GetItemCount(), f"#{idx}")
            self.list_operations.SetItem(list_id, 1, op["name"])
            self.list_operations.SetItem(list_id, 2, "x" if op["enable"] else "-")
            self.list_operations.SetItem(list_id, 3, str(op))

    def apply_script(self, index, addition):
        if index == 0:
            self.node.operations = []
            self.update_node()
        else:
            if index < 1 or index > len(self.scripts):
                return
            script = self.scripts[index - 1]
            raster_script = self.context.lookup(f"raster_script/{script}")
            if not addition:
                self.node.operations = []
            for entry in raster_script:
                self.node.operations.append(entry)
            self.update_node()

    def update_node(self):
        self.node.update(self.context.elements)
        self.context.signal("element_property_update", self.node)
        self.context.signal("selected", self.node)

    def on_apply_replace(self, event):
        idx = self.combo_scripts.GetSelection()
        if idx>=0:
            self.apply_script(idx, False)

    def on_apply_append(self, event):
        idx = self.combo_scripts.GetSelection()
        if idx>=0:
            self.apply_script(idx, True)

    def on_list_menu(self, event):
        def on_delete(index):
            def check(event):
                self.node.operations.pop(index)
                self.update_node()
            return check

        def on_enable(index):
            def check(event):
                self.node.operations[index]["enable"] = not self.node.operations[index]["enable"]
                self.update_node()
            return check

        def on_op_insert(index, op):
            def check(event):
                self.node.operations.insert(index, op)
                self.update_node()
            return check

        def on_op_append(index, op):
            def check(event):
                self.node.operations.append(op)
                self.update_node()
            return check

        index = self.list_operations.GetFirstSelected()

        possible_ops = [
            {"name": "crop", "enable": True, "bounds": None},
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            },
            {"name": "auto_contrast", "enable": True, "cutoff": 3},
            {"name": "contrast", "enable": True, "contrast": 25, "brightness": 25},
            {"name": "unsharp_mask", "enable": True, "percent": 500, "radius": 4, "threshold": 0,},
            {
                "name": "tone",
                "type": "spline",
                "enable": True,
                "values": [[0, 0], [100, 150], [255, 255]],
            },
            {"name": "gamma", "enable": True, "factor": 3.5},
            {"name": "edge_enhance", "enable": False},
            {
                "name": "halftone",
                "enable": True,
                "black": True,
                "sample": 10,
                "angle": 22,
                "oversample": 2,
            },
            {"name": "dither", "enable": True, "type": "Floyd-Steinberg"},
        ]
        devmode = self.context.root.setting(bool, "developer_mode", False)
        menu = wx.Menu()
        if index>=0:
            # Edit-Part
            menuitem = menu.Append(wx.ID_ANY, _("Delete item"), _("Will delete the current entry"))
            self.Bind(wx.EVT_MENU, on_delete(index), id=menuitem.GetId())

            menuitem = menu.Append(wx.ID_ANY, _("Enable"), _("Toggles enable-status of operation"), kind=wx.ITEM_CHECK)
            menuitem.Check(self.node.operations[index]["enable"])
            self.Bind(wx.EVT_MENU, on_enable(index), id=menuitem.GetId())
            if devmode:
                menu.AppendSeparator()
                for op in possible_ops:
                    menuitem = menu.Append(wx.ID_ANY, _("Insert {op}").format(op=op["name"]), _("Will insert this operation before the current entry"))
                    self.Bind(wx.EVT_MENU, on_op_insert(index, op), id=menuitem.GetId())
                menu.AppendSeparator()
        if devmode:
            for op in possible_ops:
                menuitem = menu.Append(wx.ID_ANY, _("Append {op}").format(op=op["name"]), _("Will append this operation to the end of the list"))
                self.Bind(wx.EVT_MENU, on_op_append(index, op), id=menuitem.GetId())

        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def pane_show(self):
        self.fill_operations()

    def pane_active(self):
        self.fill_operations()

class ImageVectorisationPanel(ScrolledPanel):
    name = _("Vectorisation")
    priority = 95

    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        self.set_widgets(node)

    @staticmethod
    def accepts(node):
        return False
        if node.type == "elem image":
            return True
        return False

    def set_widgets(self, node=None):
        self.node = node
        if node is None:
            return


class ImagePropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node
        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )

        self.text_dpi = TextCtrl(
            self,
            wx.ID_ANY,
            "500",
            style=wx.TE_PROCESS_ENTER,
            check="float",
            limited=True,
        )

        self.panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )

        self.panel_crop = CropPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.check_enable_dither = wx.CheckBox(self, wx.ID_ANY, _("Dither"))
        self.choices = [
            "Floyd-Steinberg",
            "Atkinson",
            "Jarvis-Judice-Ninke",
            "Stucki",
            "Burkes",
            "Sierra3",
            "Sierra2",
            "Sierra-2-4a",
        ]
        self.combo_dither = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.choices,
            style=wx.CB_DROPDOWN,
        )

        self.check_invert_grayscale = wx.CheckBox(self, wx.ID_ANY, _("Invert"))
        self.slider_grayscale_red = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_red = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.slider_grayscale_green = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_green = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_grayscale_blue = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_blue = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_grayscale_lightness = wx.Slider(
            self, wx.ID_ANY, 500, 0, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_lightness = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_enable_dither, self.check_enable_dither
        )
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_dither_type, self.combo_dither)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_dither_type, self.combo_dither)

        self.text_dpi.SetActionRoutine(self.on_text_dpi)

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_invert_grayscale, self.check_invert_grayscale
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_lightness,
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_grayscale_component, self.slider_grayscale_red
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_green,
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_blue,
        )
        # self.check_enable_grayscale.SetValue(op["enable"])
        self.check_invert_grayscale.SetValue(node.invert)

        self.slider_grayscale_red.SetValue(int(node.red * 500.0))
        self.text_grayscale_red.SetValue(str(node.red))

        self.slider_grayscale_green.SetValue(int(node.green * 500.0))
        self.text_grayscale_green.SetValue(str(node.green))

        self.slider_grayscale_blue.SetValue(int(node.blue * 500.0))
        self.text_grayscale_blue.SetValue(str(node.blue))

        self.slider_grayscale_lightness.SetValue(int(node.lightness * 500.0))
        self.text_grayscale_lightness.SetValue(str(node.lightness))
        self.set_widgets()

    @staticmethod
    def accepts(node):
        if node.type == "elem image":
            return True
        return False

    def set_widgets(self, node=None):
        if node is None:
            node = self.node
        self.panel_id.set_widgets(node)
        self.panel_xy.set_widgets(node)
        self.panel_crop.set_widgets(node)
        self.node = node
        if node is None:
            return

        self.text_dpi.SetValue(str(node.dpi))
        self.check_enable_dither.SetValue(node.dither)
        self.combo_dither.SetValue(node.dither_type)

    def __set_properties(self):
        self.check_enable_dither.SetToolTip(_("Enable Dither"))
        self.check_enable_dither.SetValue(1)
        self.combo_dither.SetToolTip(_("Select dither algorithm to use"))
        self.combo_dither.SetSelection(0)
        self.check_invert_grayscale.SetToolTip(_("Invert Grayscale"))
        self.slider_grayscale_red.SetToolTip(_("Red component amount"))
        self.text_grayscale_red.SetToolTip(_("Red Factor"))
        self.slider_grayscale_green.SetToolTip(_("Green component control"))
        self.text_grayscale_green.SetToolTip(_("Green Factor"))
        self.slider_grayscale_blue.SetToolTip(_("Blue component control"))
        self.text_grayscale_blue.SetToolTip(_("Blue Factor"))
        self.slider_grayscale_lightness.SetToolTip(_("Lightness control"))
        self.text_grayscale_lightness.SetToolTip(_("Lightness"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ImageProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_dim = wx.BoxSizer(wx.HORIZONTAL)
        sizer_xy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(self.panel_id, 0, wx.EXPAND, 0)
        sizer_main.Add(self.panel_crop, 0, wx.EXPAND, 0)


        sizer_dpi_dither = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dpi = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("DPI:")), wx.HORIZONTAL
        )
        self.text_dpi.SetToolTip(_("Dots Per Inch"))
        sizer_dpi.Add(self.text_dpi, 1, wx.EXPAND, 0)

        sizer_dpi_dither.Add(sizer_dpi, 1, wx.EXPAND, 0)

        sizer_dither = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Dither")), wx.HORIZONTAL
        )
        sizer_dither.Add(self.check_enable_dither, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_dither.Add(self.combo_dither, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dpi_dither.Add(sizer_dither, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_dpi_dither, 0, wx.EXPAND, 0)

        # -----

        sizer_rg = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grayscale = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Grayscale")), wx.VERTICAL
        )
        sizer_grayscale_lightness = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Lightness")), wx.HORIZONTAL
        )
        sizer_grayscale_blue = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Blue")), wx.HORIZONTAL
        )
        sizer_grayscale_green = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Green")), wx.HORIZONTAL
        )
        sizer_grayscale_red = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Red")), wx.HORIZONTAL
        )
        sizer_grayscale.Add(self.check_invert_grayscale, 0, 0, 0)
        sizer_grayscale_red.Add(self.slider_grayscale_red, 1, wx.EXPAND, 0)
        sizer_grayscale_red.Add(self.text_grayscale_red, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_red, 1, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.slider_grayscale_green, 1, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.text_grayscale_green, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_green, 1, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.slider_grayscale_blue, 1, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.text_grayscale_blue, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_blue, 1, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.slider_grayscale_lightness, 1, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.text_grayscale_lightness, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_lightness, 1, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_rg, 5, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_bl, 5, wx.EXPAND, 0)

        self.text_grayscale_red.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_green.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_blue.SetMaxSize(wx.Size(70, -1))
        self.text_grayscale_lightness.SetMaxSize(wx.Size(70, -1))

        sizer_main.Add(sizer_grayscale, 0, wx.EXPAND, 0)

        sizer_main.Add(self.panel_xy, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_text_dpi(self):
        new_step = float(self.text_dpi.GetValue())
        self.node.dpi = new_step

    def on_check_enable_dither(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.node.dither = self.check_enable_dither.GetValue()
        self.node.update(self.context)
        self.context.signal("element_property_reload", self.node)

    def on_combo_dither_type(self, event=None):  # wxGlade: RasterWizard.<event_handler>
        self.node.dither_type = self.choices[self.combo_dither.GetSelection()]
        self.node.update(self.context)
        self.context.signal("element_property_reload", self.node)

    def on_check_invert_grayscale(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.node.invert = self.check_invert_grayscale.GetValue()
        self.node.update(self.context)
        self.context.signal("element_property_reload", self.node)

    def on_slider_grayscale_component(
        self, event=None
    ):  # wxGlade: GrayscalePanel.<event_handler>
        self.node.red = float(int(self.slider_grayscale_red.GetValue()) / 500.0)
        self.text_grayscale_red.SetValue(str(self.node.red))

        self.node.green = float(int(self.slider_grayscale_green.GetValue()) / 500.0)
        self.text_grayscale_green.SetValue(str(self.node.green))

        self.node.blue = float(int(self.slider_grayscale_blue.GetValue()) / 500.0)
        self.text_grayscale_blue.SetValue(str(self.node.blue))

        self.node.lightness = float(
            int(self.slider_grayscale_lightness.GetValue()) / 500.0
        )
        self.text_grayscale_lightness.SetValue(str(self.node.lightness))
        self.node.update(self.context)
        self.context.signal("element_property_reload", self.node)


# class ImageProperty(MWindow):
#     def __init__(self, *args, node=None, **kwds):
#         super().__init__(276, 218, *args, **kwds)
#         self.panels = []
#         main_sizer = wx.BoxSizer(wx.VERTICAL)
#         panel_main = ImagePropertyPanel(
#             self, wx.ID_ANY, context=self.context, node=node
#         )
#         panel_modify = ImageModificationPanel(
#             self, wx.ID_ANY, context=self.context, node=node
#         )
#         panel_vector = ImageVectorisationPanel(
#             self, wx.ID_ANY, context=self.context, node=node
#         )
#         notebook_main = wx.aui.AuiNotebook(
#             self,
#             -1,
#             style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
#             | wx.aui.AUI_NB_SCROLL_BUTTONS
#             | wx.aui.AUI_NB_TAB_SPLIT
#             | wx.aui.AUI_NB_TAB_MOVE,
#         )
#         notebook_main.AddPage(panel_main, _("Properties"))
#         notebook_main.AddPage(panel_modify, _("Modification"))
#         notebook_main.AddPage(panel_vector, _("Vectorisation"))

#         self.panels.append(panel_main)
#         self.panels.append(panel_modify)
#         self.panels.append(panel_vector)
#         for panel in self.panels:
#             self.add_module_delegate(panel)
#         # begin wxGlade: ImageProperty.__set_properties
#         _icon = wx.NullIcon
#         _icon.CopyFromBitmap(icons8_image_50.GetBitmap())
#         self.SetIcon(_icon)
#         self.SetTitle(_("Image Properties"))
#         main_sizer.Add(notebook_main, 1, wx.EXPAND, 0)
#         self.SetSizer(main_sizer)
#         self.Layout()

#     def restore(self, *args, node=None, **kwds):
#         for panel in self.panels:
#             panel.set_widgets(node)

#     def window_preserve(self):
#         return False

#     def window_menu(self):
#         return False
