import wx

from meerk40t.gui.wxutils import ScrolledPanel
from meerk40t.kernel import Context

_ = wx.GetTranslation

import wx.lib.mixins.listctrl as listmix


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    """TextEditMixin allows any column to be edited."""

    # ----------------------------------------------------------------------
    def __init__(
        self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)


class ChoiceChart(ScrolledPanel):
    def __init__(
        self,
        *args,
        context: Context = None,
        choices=None,
        scrolling=True,
        entries_per_column=None,
        **kwds,
    ):
        self._detached = False
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.listeners = list()
        self.entries_per_column = entries_per_column
        if choices is None:
            return
        if isinstance(choices, str):
            tempchoices = self.context.lookup("choices", choices)
            # we need to create an independent copy of the lookup, otherwise
            # any amendments to choices like injector will affect the original
            choices = []
            for c in tempchoices:
                choices.append(c)
            if choices is None:
                return
        for c in choices:
            needs_dynamic_call = c.get("dynamic")
            if needs_dynamic_call:
                # Calls dynamic function to update this dictionary before production
                needs_dynamic_call(c)
        # Let's see whether we have a section and a page property...
        for c in choices:
            try:
                dummy = c["subsection"]
            except KeyError:
                c["subsection"] = ""
            try:
                dummy = c["section"]
            except KeyError:
                c["section"] = ""
            try:
                dummy = c["page"]
            except KeyError:
                c["page"] = ""
            try:
                dummy = c["priority"]
            except KeyError:
                c["priority"] = "ZZZZZZZZ"
        self.choices = choices
        if len(self.choices) == 0:
            return
        sizer_very_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_very_main.Add(sizer_main, 1, wx.EXPAND, 0)
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
                # if obj lacks attr, default must have been assigned.
                try:
                    data = c["default"]
                except KeyError:
                    # This choice is in error.
                    continue
            data_style = c.get("style", None)
            data_type = type(data)
            data_type = c.get("type", data_type)
            label = c.get("label", attr)  # Undefined label is the attr
            if data_type == list and data_style == "chart":
                chart = EditableListCtrl(
                    self,
                    wx.ID_ANY,
                    style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
                )
                columns = c.get("columns", [])
                for column in columns:
                    chart.AppendColumn(
                        column.get("label", ""),
                        format=wx.LIST_FORMAT_LEFT,
                        width=column.get("width", 150),
                    )
                for dataline in data:
                    row_id = chart.InsertItem(
                        chart.GetItemCount(), dataline.get("speed", 0)
                    )
                    for column_id, column in enumerate(columns):
                        c_attr = column.get("attr")
                        chart.SetItem(row_id, column_id, str(dataline.get(c_attr, "")))

                def on_chart_start(columns, param, ctrl, obj):
                    def chart_start(event=None):
                        for column in columns:
                            if column.get("editable", False):
                                event.Allow()
                            else:
                                event.Veto()

                    return chart_start

                chart.Bind(
                    wx.EVT_LIST_BEGIN_LABEL_EDIT,
                    on_chart_start(columns, attr, chart, obj),
                )

                def on_chart_stop(columns, param, ctrl, obj):
                    def chart_stop(event=None):
                        row_id = event.GetIndex()  # Get the current row
                        col_id = event.GetColumn()  # Get the current column
                        new_data = event.GetLabel()  # Get the changed data
                        ctrl.SetItem(row_id, col_id, new_data)
                        column = columns[col_id]
                        c_attr = column.get("attr")
                        c_type = column.get("type")
                        values = getattr(obj, attr)
                        values[row_id][c_attr] = c_type(new_data)
                        self.context.signal(param, values, row_id, attr)

                    return chart_stop

                chart.Bind(
                    wx.EVT_LIST_END_LABEL_EDIT, on_chart_stop(columns, attr, chart, obj)
                )
                sizer_main.Add(chart, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_very_main)
        sizer_very_main.Fit(self)
        # Make sure stuff gets scrolled if necessary by default
        if scrolling:
            self.SetupScrolling()
        self._detached = False

    def module_close(self, *args, **kwargs):
        self.pane_hide()

    def pane_hide(self):
        if not self._detached:
            for attr, listener in self.listeners:
                self.context.unlisten(attr, listener)
            self._detached = True

    def pane_show(self):
        pass
