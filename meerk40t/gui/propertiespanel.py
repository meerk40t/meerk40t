import wx

from meerk40t.kernel import Context

_ = wx.GetTranslation


class PropertiesPanel(wx.Panel):
    """
    PropertiesPanel is a generic panel that simply presents a simple list of properties to be viewed and edited.
    """

    def __init__(self, *args, context: Context = None, choices=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        if choices is None:
            return
        if isinstance(choices, str):
            try:
                choices = self.context.registered["choices/%s" % choices]
            except KeyError:
                return
        self.choices = choices
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        for i, c in enumerate(self.choices):
            if isinstance(c, tuple):
                # If c is tuple
                dict_c = dict()
                try:
                    dict_c['object'] = c[0]
                    dict_c['attr'] = c[1]
                    dict_c['default'] = c[2]
                    dict_c['label'] = c[3]
                    dict_c['tip'] = c[4]
                except IndexError:
                    pass
                c = dict_c
            try:
                attr = c['attr']
                obj = c['object']
            except KeyError:
                continue

            # get default value
            if hasattr(obj, attr):
                data = getattr(obj, attr)
            else:
                # if obj can lack attr, default must have been assigned.
                try:
                    data = c['default']
                except KeyError:
                    continue

            data_type = type(data)
            try:
                # if type is explicitly given, use that to define data_type.
                data_type = c['type']
            except KeyError:
                pass

            try:
                # Get label
                label = c['label']
            except KeyError:
                # Undefined label is the attr
                label = attr

            if data_type == bool:
                control = wx.CheckBox(self, label=label)
                control.SetValue(data)

                def on_checkbox_check(param, ctrl):
                    def check(event=None):
                        v = ctrl.GetValue()
                        setattr(obj, param, v)

                    return check

                control.Bind(wx.EVT_CHECKBOX, on_checkbox_check(attr, control))
                sizer_main.Add(control, 0, wx.EXPAND, 0)
            elif data_type in (str, int, float):
                control_sizer = wx.StaticBoxSizer(
                    wx.StaticBox(self, wx.ID_ANY, label), wx.HORIZONTAL
                )
                control = wx.TextCtrl(self, -1)
                control.SetValue(str(data))
                control_sizer.Add(control)

                def on_textbox_text(param, ctrl):
                    def check(event=None):
                        v = ctrl.GetValue()
                        try:
                            setattr(obj, param, data_type(v))
                        except ValueError:
                            # If cannot cast to data_type, pass
                            pass

                    return check

                control.Bind(wx.EVT_TEXT, on_textbox_text(attr, control))
                sizer_main.Add(control_sizer, 0, wx.EXPAND, 0)
            else:
                # Requires a registered data_type
                continue
            try:
                # Set the tool tip if 'tip' is available
                control.SetToolTip(c['tip'])
            except KeyError:
                pass

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
