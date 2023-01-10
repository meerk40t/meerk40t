"""
dialogoptions.py contains a GUI element to query options
for a GRBL import / blob conversion
"""

import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel

_ = wx.GetTranslation


class DialogOptions:
    def __init__(
        self,
        context,
        choices=None,
        scrolling=True,
        constraint=None,
        entries_per_column=None,
        injector=None,
        reset_on_cancel=True,
        **kwds,
    ):
        self.context = context
        self.choices = choices
        self.reset_on_cancel = reset_on_cancel
        self.scrolling = scrolling
        self.constraint = constraint
        self.entries_per_column = entries_per_column
        self.injector = injector

    def dialog_options(self, title=None, intro=None):
        if self.choices is None:
            return False
        stored_values = []
        cancelled = True
        can_restore = False
        if title is None:
            title = _("Input required")

        if not isinstance(self.choices, str) and self.reset_on_cancel:
            can_restore = True
            for entry in self.choices:
                if "attr" in entry and "object" in entry:
                    waspresent = bool(hasattr(entry["object"], entry["attr"]))
                    if waspresent:
                        value = getattr(entry["object"], entry["attr"])
                    else:
                        value = None
                    stored_values.append(
                        (entry["object"], entry["attr"], waspresent, value)
                    )
        parentid = self.context.gui if hasattr(self.context, "gui") else None
        parent_win = wx.Dialog(parentid, wx.ID_ANY, title=title)
        cpanel = ChoicePropertyPanel(
            parent_win,
            context=self.context,
            choices=self.choices,
            scrolling=self.scrolling,
            constraint=self.constraint,
            entries_per_column=self.entries_per_column,
            injector=self.injector,
        )
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        if intro is not None and intro != "":
            intro_label = wx.StaticText(parent_win, id=wx.ID_ANY, label=intro)
            sizer_main.Add(intro_label, 0, wx.EXPAND, 0)
        sizer_main.Add(cpanel, 1, wx.EXPAND, 0)
        sizer_button = wx.BoxSizer(wx.HORIZONTAL)
        self.button_apply = wx.Button(parent_win, wx.ID_OK, _("OK"))
        self.button_cancel = wx.Button(parent_win, wx.ID_CANCEL, _("Cancel"))
        sizer_button.Add(self.button_apply, 0, wx.EXPAND, 0)
        sizer_button.Add(self.button_cancel, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_button, 0, wx.EXPAND, 0)
        parent_win.SetSizer(sizer_main)
        parent_win.SetAffirmativeId(self.button_apply.GetId())
        parent_win.SetEscapeId(self.button_cancel.GetId())
        parent_win.Layout()
        if parent_win.ShowModal() == wx.ID_OK:
            cancelled = False
        parent_win.Destroy()

        if cancelled:
            if can_restore:
                for entry in stored_values:
                    e_object = entry[0]
                    e_attr = entry[1]
                    waspresent = bool(entry[2])
                    value = entry[3]
                    try:
                        if waspresent:
                            value = setattr(e_object, e_attr, value)
                        else:
                            # Was not there, so remove it
                            delattr(e_object, e_attr)
                    except (ValueError, AttributeError):
                        pass

            return False
        else:
            return True
