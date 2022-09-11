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

        self.context = context

        self.standards = (
            ("Home", "util home", ""),
            ("Origin", "util origin", "0,0"),
            ("Beep", "util console", "beep"),
            ("Interrupt", "util console", 'interrupt "Spooling was interrupted"'),
            ("GoTo", "util goto", "0,0"),
            ("Console", "util console", ""),
        )
        self.prepend_ops = []
        self.append_ops = []
        choices = []
        for entry in self.standards:
            choices.append(_(entry[0]))

        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_before = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("At job start")), wx.VERTICAL
        )
        sizer_after = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("At job end")), wx.VERTICAL
        )
        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        self.btn_add_left = wx.Button(self, wx.ID_ANY, _("<- Add"))

        self.option_list = wx.ListBox(self, wx.ID_ANY, choices=choices, style=wx.LB_SINGLE)
        self.text_param_option = wx.TextCtrl(self, wx.ID_ANY)

        self.btn_add_right = wx.Button(self, wx.ID_ANY, _("<- Add"))


        self.prepend_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.text_param_prepend = wx.TextCtrl(self, wx.ID_ANY)

        self.append_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        self.text_param_append = wx.TextCtrl(self, wx.ID_ANY)
        self.button_del_prepend = wx.Button(self, wx.ID_ANY, _("<- Remove"))
        self.button_up_prepend = wx.Button(self, wx.ID_ANY, "^")
        self.button_down_prepend = wx.Button(self, wx.ID_ANY, "v")

        self.button_del_append = wx.Button(self, wx.ID_ANY, _("Remove ->"))
        self.button_up_append = wx.Button(self, wx.ID_ANY, "^")
        self.button_down_append = wx.Button(self, wx.ID_ANY, "v")

        sizer_param = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Operation parameter:")), wx.HORIZONTAL
        )
        sizer_param.Add(self.text_param_option, 1, wx.EXPAND, 0)

        sizer_middle.Add(self.btn_add_left, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.option_list, 1, wx.EXPAND, 0)
        sizer_middle.Add(sizer_param, 0, wx.EXPAND, 0)
        sizer_middle.Add(self.btn_add_right, 0, wx.EXPAND, 0)

        hsizer_prepend=wx.BoxSizer(wx.HORIZONTAL)
        hsizer_prepend.Add(self.text_param_prepend, 1, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_del_prepend, 0, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_up_prepend, 0, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_down_prepend, 0, wx.EXPAND, 0)

        hsizer_append=wx.BoxSizer(wx.HORIZONTAL)
        hsizer_append.Add(self.text_param_append, 1, wx.EXPAND, 0)
        hsizer_append.Add(self.button_del_append, 0, wx.EXPAND, 0)
        hsizer_append.Add(self.button_up_append, 0, wx.EXPAND, 0)
        hsizer_append.Add(self.button_down_append, 0, wx.EXPAND, 0)

        sizer_before.Add(self.prepend_list, 1, wx.EXPAND, 0)
        sizer_before.Add(hsizer_prepend, 0, wx.EXPAND, 0)

        sizer_after.Add(self.append_list, 1, wx.EXPAND, 0)
        sizer_after.Add(hsizer_append, 0, wx.EXPAND, 0)

        sizer_jobs = wx.BoxSizer(wx.VERTICAL)
        sizer_jobs.Add(sizer_before, 1, wx.EXPAND, 0)
        sizer_jobs.Add(sizer_after, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_jobs, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_middle, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.init_settings()
        self.update_widgets()

    def save_data(self):
        prefix = "prepend"
        str_count = f"{prefix}_op_count"
        for idx, entry in enumerate(self.prepend_ops):
            attr1 = f"{prefix}_op_{idx:2d}"
            attr2 = f"{prefix}_op_param_{idx:2d}"
            self.context.setting(str, attr1, entry[0])
            self.context.setting(str, attr2, entry[1])
            setattr(self.context, attr1, entry[0])
            setattr(self.context, attr2, entry[0])
        setattr(self.context, str_count, len(self.prepend_ops))
        prefix = "append"
        str_count = f"{prefix}_op_count"
        for idx, entry in enumerate(self.append_ops):
            attr1 = f"{prefix}_op_{idx:2d}"
            attr2 = f"{prefix}_op_param_{idx:2d}"
            self.context.setting(str, attr1, entry[0])
            self.context.setting(str, attr2, entry[1])
            setattr(self.context, attr1, entry[0])
            setattr(self.context, attr2, entry[0])
        setattr(self.context, str_count, len(self.append_ops))


    def init_settings(self):
        for prefix in ("prepend", "append"):
            str_count = f"{prefix}_op_count"
            self.context.setting(int, str_count, 0)
            value = getattr(self.context, str_count, 0)
            if value>0:
                for idx in range(value):
                    attr1 = f"{prefix}_op_{idx:2d}"
                    attr2 = f"{prefix}_op_param_{idx:2d}"
                    self.context.setting(str, attr1, "")
                    self.context.setting(str, attr2, "")

    def update_widgets(self):
        # Validate and set all choices
        self.prepend_ops = []
        self.append_ops = []
        prefix = "prepend"
        str_count = f"{prefix}_op_count"
        count = getattr(self.context, str_count, 0)
        choices = []
        for idx in range(count):
            entry = ["", ""]
            attr1 = f"{prefix}_op_{idx:2d}"
            attr2 = f"{prefix}_op_param_{idx:2d}"
            entry[0] = getattr(self.context, attr1, "")
            entry[1] = getattr(self.context, attr2, "")
            self.prepend_ops.append(entry)
            choices.append(entry[0])
        self.prepend_list.Clear()
        self.prepend_list.Set(choices)

        prefix = "append"
        str_count = f"{prefix}_op_count"
        count = getattr(self.context, str_count, 0)
        choices = []
        for idx in range(count):
            entry = ["", ""]
            attr1 = f"{prefix}_op_{idx:2d}"
            attr2 = f"{prefix}_op_param_{idx:2d}"
            entry[0] = getattr(self.context, attr1, "")
            entry[1] = getattr(self.context, attr2, "")
            self.append_ops.append(entry)
            choices.append(entry[0])
        self.append_list.Clear()
        self.append_list.Set(choices)

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()
