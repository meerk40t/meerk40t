import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.kernel import Context
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class WizardPanel(wx.Panel):
    """
    WizardPanel is a generic panel set that presents wizard pages to be answered in order.
    """

    def __init__(self, *args, context: Context = None, choices=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        if choices is None:
            return
        if isinstance(choices, str):
            choices = self.context.lookup("choices", choices)
            if choices is None:
                return
        self.choices = choices
        self.choice_index = 0
        self.set_panel()

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

    def set_panel(self):
        choice = self.choices[self.choice_index]
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        for i, c in enumerate(self.choices):
            try:
                attr = c["attr"]
                obj = c["object"]
            except KeyError:
                continue

            # get default value
            if hasattr(obj, attr):
                data = getattr(obj, attr)
            else:
                # if obj can lack attr, default must have been assigned.
                try:
                    data = c["default"]
                except KeyError:
                    continue

            data_type = type(data)
            try:
                # if type is explicitly given, use that to define data_type.
                data_type = c["type"]
            except KeyError:
                pass

            try:
                # Get label
                label = c["label"]
            except KeyError:
                # Undefined label is the attr
                label = attr

            if data_type == bool:
                control = wx.CheckBox(self, label=label)
                control.SetValue(data)

                def on_checkbox_check(param, ctrl, obj):
                    def check(event=None):
                        v = ctrl.GetValue()
                        setattr(obj, param, v)

                    return check

                control.Bind(wx.EVT_CHECKBOX, on_checkbox_check(attr, control, obj))
                sizer_main.Add(control, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float):
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.TextCtrl(self, -1)
                control.SetValue(str(data))
                control_sizer.Add(control)

                def on_textbox_text(param, ctrl, obj):
                    def text(event=None):
                        v = ctrl.GetValue()
                        try:
                            setattr(obj, param, data_type(v))
                        except ValueError:
                            # If cannot cast to data_type, pass
                            pass

                    return text

                control.Bind(wx.EVT_TEXT, on_textbox_text(attr, control, obj))
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            elif data_type == Color:
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.Button(self, -1)

                def set_color(color: Color):
                    control.SetLabel(str(color.hex))
                    control.SetBackgroundColour(wx.Colour(swizzlecolor(color)))
                    control.color = color

                def on_button_color(param, ctrl, obj):
                    def click(event=None):
                        color_data = wx.ColourData()
                        color_data.SetColour(wx.Colour(swizzlecolor(ctrl.color)))
                        dlg = wx.ColourDialog(self, color_data)
                        if dlg.ShowModal() == wx.ID_OK:
                            color_data = dlg.GetColourData()
                            data = Color(
                                swizzlecolor(color_data.GetColour().GetRGB()), 1.0
                            )
                            set_color(data)
                            try:
                                setattr(obj, param, data_type(data))
                            except ValueError:
                                # If cannot cast to data_type, pass
                                pass

                    return click

                set_color(data)
                control_sizer.Add(control)

                control.Bind(wx.EVT_BUTTON, on_button_color(attr, control, obj))
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue
            try:
                # Set the tool tip if 'tip' is available
                control.SetToolTip(c["tip"])
            except KeyError:
                pass


class TreeSelectionPanel(wx.Panel):
    def __init__(self, choice: dict, *args, **kwds):
        # begin wxGlade: LayerType.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)

        main_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, selection_text), wx.VERTICAL
        )

        self.selected_tree = wx.TreeCtrl(self, wx.ID_ANY)
        main_sizer.Add(self.controller_tree, 7, wx.EXPAND, 0)

        self.SetSizer(main_sizer)

        self.Layout()

        self.Bind(
            wx.EVT_TREE_ITEM_ACTIVATED,
            self.on_tree_laser_activated,
            self.controller_tree,
        )
        # end wxGlade

    def on_selected_tree_activated(self, event):  # wxGlade: LayerType.<event_handler>
        print("Event handler 'on_tree_laser_activated' not implemented!")
        event.Skip()


class TextboxSelectionPanel(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: NetworkPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)

        sizer_6 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Network Address"), wx.VERTICAL
        )

        sizer_7 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "What is the network address for the laser?"),
            wx.HORIZONTAL,
        )
        sizer_6.Add(sizer_7, 1, wx.EXPAND, 0)

        self.text_network_address = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_7.Add(self.text_network_address, 1, 0, 0)

        self.SetSizer(sizer_6)

        self.Layout()

        self.Bind(
            wx.EVT_TEXT_ENTER, self.on_text_network_address, self.text_network_address
        )
        # end wxGlade

    def on_text_network_address(self, event):  # wxGlade: NetworkPanel.<event_handler>
        print("Event handler 'on_text_network_address' not implemented!")
        event.Skip()
