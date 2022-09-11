import wx

from meerk40t.gui.icons import (
    icons8_diagonal_20,
    icons8_direction_20,
    icons8_image_20,
    icons8_laser_beam_20,
    icons8_scatter_plot_20,
    icons8_small_beam_20,
)
from meerk40t.gui.wxutils import TextCtrl

_ = wx.GetTranslation


class DefaultActionPanel(wx.Panel):
    """
    DefaultActions is a panel that should work for all devices (hence in its own directory)
    It allows to define operations that should be executed at the beginning and the end of a job
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.standards = (
            ("Home", "util home", ""),
            ("Origin", "util origin", "0,0"),
            ("Beep", "util console", "beep"),
            ("Interrupt", "util console", 'interrupt "Spooling was interrupted"'),
            ("GoTo", "util goto", "0,0"),
        )
        self.choices = [
            {
                "attr": "prehome",
                "default": False,
                "type": bool,
                "submenu": "Before",
                "label": "Home",
                "tip": "Automatically add a home command before all jobs",
            },
            {
                "attr": "prephysicalhome",
                "default": False,
                "type": bool,
                "submenu": "Before",
                "label": "Physical Home",
                "tip": "Automatically add a physical home command before all jobs",
            },
            {
                "attr": "autohome",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Home",
                "tip": "Automatically add a home command after all jobs",
            },
            {
                "attr": "autophysicalhome",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Physical Home",
                "tip": "Automatically add a physical home command before all jobs",
            },
            {
                "attr": "autoorigin",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Return to Origin",
                "tip": "Automatically return to origin after a job",
            },
            {
                "attr": "postunlock",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Unlock",
                "tip": "Automatically unlock the rail after all jobs",
            },
            {
                "attr": "autobeep",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Beep",
                "tip": "Automatically add a beep after all jobs",
            },
            {
                "attr": "autointerrupt",
                "default": False,
                "type": bool,
                "submenu": "After",
                "label": "Interrupt",
                "tip": "Automatically add an interrupt after all jobs",
            },
        ]
        self.context = context
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_before = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("At job start")), wx.VERTICAL
        )
        sizer_after = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("At job end")), wx.VERTICAL
        )
        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        self.btn_del_left = wx.Button(self, wx.ID_ANY, _("<- Remove"))
        self.btn_add_left = wx.Button(self, wx.ID_ANY, _("<- Add"))
        self.option_list = wx.ListBox(self, wx.ID_ANY, choices=["A", "B", "C"], style=wx.LB_SINGLE)
        self.btn_add_right = wx.Button(self, wx.ID_ANY, _("Add ->"))
        self.btn_del_right = wx.Button(self, wx.ID_ANY, _("Remove ->"))
        self.text_param = wx.TextCtrl(self, wx.ID_ANY)

        sizer_param = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Operation parameter:")), wx.HORIZONTAL
        )
        sizer_param.Add(self.text_param, 1, wx.EXPAND, 0)
        sizer_middle.Add(self.btn_del_left, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.btn_add_left, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.option_list, 1, wx.EXPAND, 0)
        sizer_middle.Add(sizer_param, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.btn_add_right, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.btn_del_right, 0, wx.EXPAND, 0)
        for choice in self.choices:
            mylabel = choice["label"]
            tip = choice["tip"]
            key = choice["attr"]
            submenu = choice["submenu"]
            if submenu == "Before":
                check1 = wx.CheckBox(self, wx.ID_ANY, _(mylabel))
                check1.SetToolTip(_(tip))
                # Add a specific info
                check1._key = key
                check1.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
                choice["control"] = check1
                sizer_before.Add(check1, 0, wx.EXPAND, 0)
            elif submenu == "After":
                check2 = wx.CheckBox(self, wx.ID_ANY, _(mylabel))
                check2.SetToolTip(_(tip))
                check2._key = key
                check2.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
                choice["control"] = check2
                sizer_after.Add(check2, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_before, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_middle, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(sizer_after, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        self.update_widgets()

    def on_checkbox(self, event):
        ctrl = event.GetEventObject()
        key = ctrl._key
        value = ctrl.GetValue()
        # print(f"set {key} to {value}")
        setattr(self.context, key, value)

    def update_widgets(self):
        # Validate and set all choices
        for choice in self.choices:
            key = choice["attr"]
            default_value = choice["default"]
            self.context.setting(bool, key, default_value)
            value = getattr(self.context, key, None)
            # print(f"read {key} = {value}")
            if value is None:
                setattr(self.context, key, default_value)
                value = default_value
            value = bool(value)
            ctrl = choice["control"]
            ctrl.SetValue(value)

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()
