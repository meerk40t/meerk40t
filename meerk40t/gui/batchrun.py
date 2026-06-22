"""
CSV Batch Run — batch personalization using wordlist CSV columns.

Import a CSV, preview each row against text elements using {variable} placeholders,
run jobs row-by-row, optionally auto-advance after each completed spooler job.
"""

import os

import wx

from meerk40t.core.wordlist import IDX_DATA_START, IDX_POSITION, IDX_TYPE, TYPE_CSV
from meerk40t.gui.icons import icons8_curly_brackets, icons8_gas_industry
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl, dip_size, wxButton, wxCheckBox, wxStaticText
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def csv_column_keys(wordlist):
    """Return normalized keys for CSV-backed wordlist columns."""
    return [
        skey
        for skey, entry in wordlist.content.items()
        if entry[IDX_TYPE] == TYPE_CSV and skey not in wordlist.prohibited
    ]


def csv_row_count(wordlist):
    """Number of data rows across CSV columns (uses the longest column)."""
    count = 0
    for skey in csv_column_keys(wordlist):
        entry = wordlist.content[skey]
        rows = len(entry) - IDX_DATA_START
        if rows > count:
            count = rows
    return count


def current_csv_row(wordlist):
    """Zero-based row index from the first CSV column, or 0 if none loaded."""
    keys = csv_column_keys(wordlist)
    if not keys:
        return 0
    return max(0, wordlist.content[keys[0]][IDX_POSITION] - IDX_DATA_START)


def set_csv_row(elements, row_index):
    """Set all CSV columns to the same row and refresh the scene."""
    wlist = elements.mywordlist
    for skey in csv_column_keys(wlist):
        wlist.set_index(skey, row_index)
    elements.refresh_signal()
    elements.signal("wordlist")


def collect_text_previews(elements):
    """Return lines describing text elements with variables translated for the current row."""
    lines = []
    for node in elements.elems():
        if node.type != "elem text":
            continue
        raw = getattr(node, "text", None) or ""
        if not raw:
            continue
        if "{" not in raw:
            continue
        translated = elements.wordlist_translate(raw, elemnode=node, increment=False)
        lines.append(f"{node.display_label()}: {translated}")
    return lines


class BatchRunWindow(MWindow):
    """Run repeated jobs from CSV wordlist rows with preview and optional auto-advance."""

    def __init__(self, *args, **kwds):
        super().__init__(520, 560, *args, **kwds)
        self._batch_chain = False

        self.wlist = self.context.elements.mywordlist

        csv_box = StaticBoxSizer(self, wx.ID_ANY, _("CSV data"), wx.VERTICAL)
        row_file = wx.BoxSizer(wx.HORIZONTAL)
        row_file.Add(wxStaticText(self, wx.ID_ANY, _("File")), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_csv = TextCtrl(self, wx.ID_ANY, "")
        row_file.Add(self.txt_csv, 1, wx.EXPAND | wx.LEFT, 4)
        self.btn_browse = wxButton(self, wx.ID_ANY, "...")
        self.btn_browse.SetMinSize(dip_size(self, 28, 28))
        row_file.Add(self.btn_browse, 0, wx.LEFT, 4)
        self.btn_import = wxButton(self, wx.ID_ANY, _("Import"))
        row_file.Add(self.btn_import, 0, wx.LEFT, 4)
        csv_box.Add(row_file, 0, wx.EXPAND, 0)

        header_row = wx.BoxSizer(wx.HORIZONTAL)
        self.rbox_header = wx.RadioBox(
            self,
            wx.ID_ANY,
            _("First row"),
            choices=(_("Auto"), _("Data"), _("Headers")),
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        header_row.Add(self.rbox_header, 1, wx.EXPAND, 0)
        csv_box.Add(header_row, 0, wx.EXPAND | wx.TOP, 6)
        self.sizer.Add(csv_box, 0, wx.EXPAND | wx.ALL, 6)

        row_box = StaticBoxSizer(self, wx.ID_ANY, _("Row"), wx.VERTICAL)
        nav = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_prev = wxButton(self, wx.ID_ANY, _("Prev"))
        self.btn_next = wxButton(self, wx.ID_ANY, _("Next"))
        self.spin_row = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=1, initial=1)
        self.lbl_row_status = wxStaticText(self, wx.ID_ANY, _("Row 0 / 0"))
        nav.Add(self.btn_prev, 0, wx.RIGHT, 4)
        nav.Add(self.btn_next, 0, wx.RIGHT, 8)
        nav.Add(wxStaticText(self, wx.ID_ANY, _("Go to")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        nav.Add(self.spin_row, 0, wx.RIGHT, 8)
        nav.Add(self.lbl_row_status, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        row_box.Add(nav, 0, wx.EXPAND, 0)

        self.check_auto = wxCheckBox(
            self,
            wx.ID_ANY,
            _("After each job completes, run the next row automatically"),
        )
        row_box.Add(self.check_auto, 0, wx.TOP, 6)
        self.sizer.Add(row_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        preview_box = StaticBoxSizer(self, wx.ID_ANY, _("Preview (text with {variables})"), wx.VERTICAL)
        self.txt_preview = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.txt_preview.SetMinSize(dip_size(self, -1, 160))
        preview_box.Add(self.txt_preview, 1, wx.EXPAND, 0)
        self.sizer.Add(preview_box, 1, wx.EXPAND | wx.ALL, 6)

        cols_box = StaticBoxSizer(self, wx.ID_ANY, _("Current row values"), wx.VERTICAL)
        self.txt_columns = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.txt_columns.SetMinSize(dip_size(self, -1, 80))
        cols_box.Add(self.txt_columns, 1, wx.EXPAND, 0)
        self.sizer.Add(cols_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_apply = wxButton(self, wx.ID_ANY, _("Apply row to design"))
        self.btn_run = wxButton(self, wx.ID_ANY, _("Run current row"))
        self.btn_run_all = wxButton(self, wx.ID_ANY, _("Run all rows"))
        self.btn_stop = wxButton(self, wx.ID_ANY, _("Stop batch"))
        self.btn_stop.Enable(False)
        actions.Add(self.btn_apply, 0, wx.RIGHT, 4)
        actions.Add(self.btn_run, 0, wx.RIGHT, 4)
        actions.Add(self.btn_run_all, 0, wx.RIGHT, 4)
        actions.Add(self.btn_stop, 0, wx.RIGHT, 4)
        self.sizer.Add(actions, 0, wx.EXPAND | wx.ALL, 6)

        self.lbl_status = wxStaticText(self, wx.ID_ANY, "")
        self.sizer.Add(self.lbl_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.Layout()

        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
        self.btn_prev.Bind(wx.EVT_BUTTON, self.on_prev)
        self.btn_next.Bind(wx.EVT_BUTTON, self.on_next)
        self.spin_row.Bind(wx.EVT_SPINCTRL, self.on_spin_row)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply)
        self.btn_run.Bind(wx.EVT_BUTTON, self.on_run_current)
        self.btn_run_all.Bind(wx.EVT_BUTTON, self.on_run_all)
        self.btn_stop.Bind(wx.EVT_BUTTON, self.on_stop_batch)

        icon = wx.NullIcon
        icon.CopyFromBitmap(icons8_curly_brackets.GetBitmap())
        self.SetIcon(icon)
        self.SetTitle(_("CSV Batch Run"))
        self.restore_aspect()
        self.refresh_ui()

    def _header_mode(self):
        sel = self.rbox_header.GetSelection()
        if sel == 1:
            return False
        if sel == 2:
            return True
        return None

    def set_status(self, msg):
        self.lbl_status.SetLabel(msg)

    def refresh_ui(self):
        total = csv_row_count(self.wlist)
        row = current_csv_row(self.wlist)
        if total <= 0:
            row = 0
            self.spin_row.SetRange(1, 1)
            self.spin_row.SetValue(1)
            self.lbl_row_status.SetLabel(_("No CSV loaded"))
            self.btn_prev.Enable(False)
            self.btn_next.Enable(False)
            self.btn_run.Enable(False)
            self.btn_run_all.Enable(False)
            self.btn_apply.Enable(False)
        else:
            self.spin_row.SetRange(1, total)
            self.spin_row.SetValue(row + 1)
            self.lbl_row_status.SetLabel(
                _("Row {current} of {total}").format(current=row + 1, total=total)
            )
            self.btn_prev.Enable(row > 0)
            self.btn_next.Enable(row < total - 1)
            self.btn_run.Enable(True)
            self.btn_run_all.Enable(True)
            self.btn_apply.Enable(True)
        self._refresh_previews(row, total)

    def _refresh_previews(self, row, total):
        if total <= 0:
            self.txt_preview.SetValue(_("Import a CSV with column headers matching your {variables}."))
            self.txt_columns.SetValue("")
            return

        previews = collect_text_previews(self.context.elements)
        if previews:
            self.txt_preview.SetValue("\n".join(previews))
        else:
            self.txt_preview.SetValue(
                _(
                    "No text elements with {variables} found.\n"
                    "Add text like Hello {name} and ensure CSV columns match."
                )
            )

        col_lines = []
        for skey in sorted(csv_column_keys(self.wlist)):
            entry = self.wlist.content[skey]
            idx = entry[IDX_POSITION]
            if idx < len(entry):
                col_lines.append(f"{skey} = {entry[idx]}")
        self.txt_columns.SetValue("\n".join(col_lines))

    def go_to_row(self, row_index):
        total = csv_row_count(self.wlist)
        if total <= 0:
            return
        row_index = max(0, min(row_index, total - 1))
        set_csv_row(self.context.elements, row_index)
        self.refresh_ui()

    def on_browse(self, event=None):
        with wx.FileDialog(
            self,
            message=_("Choose a CSV file"),
            wildcard="CSV (*.csv)|*.csv|Text (*.txt)|*.txt|All (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.txt_csv.SetValue(dlg.GetPath())

    def on_import(self, event=None):
        path = self.txt_csv.GetValue().strip()
        if not path or not os.path.exists(path):
            self.set_status(_("Choose a valid CSV file first."))
            return
        rows, cols, headers = self.wlist.load_csv_file(path, force_header=self._header_mode())
        if self.wlist.has_load_warnings():
            channel = self.context.kernel.root.channel("console")
            channel(_("CSV import warnings:"))
            for warning in self.wlist.get_load_warnings():
                channel("  " + warning)
        self.context.elements.signal("wordlist_modified")
        self._batch_chain = False
        self.go_to_row(0)
        self.set_status(
            _("Imported {cols} columns, {rows} rows.").format(cols=cols, rows=rows)
        )

    def on_prev(self, event=None):
        self.go_to_row(current_csv_row(self.wlist) - 1)

    def on_next(self, event=None):
        self.go_to_row(current_csv_row(self.wlist) + 1)

    def on_spin_row(self, event=None):
        self.go_to_row(self.spin_row.GetValue() - 1)

    def on_apply(self, event=None):
        row = current_csv_row(self.wlist)
        set_csv_row(self.context.elements, row)
        self.set_status(_("Applied row {row} to the design.").format(row=row + 1))

    def _spool_job(self):
        context = self.context.kernel.root
        kernel = self.context.kernel
        hold = context.setting(bool, "laserpane_hold", False)
        prefer_threaded = context.setting(bool, "prefer_threaded_mode", True)
        prefix = "threaded " if prefer_threaded else ""
        opt = kernel.planner.do_optimization
        last_plan = kernel.planner.get_last_plan()
        if last_plan is not None and hold:
            context(f"plan{last_plan} spool\n")
        else:
            new_plan = kernel.planner.get_free_plan()
            if opt:
                context(
                    f"{prefix}plan{new_plan} clear copy preprocess validate blob preopt optimize spool\n"
                )
            else:
                context(
                    f"{prefix}plan{new_plan} clear copy preprocess validate blob spool\n"
                )
        if context.auto_spooler:
            context("window open JobSpooler\n")

    def on_run_current(self, event=None):
        total = csv_row_count(self.wlist)
        if total <= 0:
            self.set_status(_("Import a CSV first."))
            return
        row = current_csv_row(self.wlist)
        set_csv_row(self.context.elements, row)
        self._batch_chain = False
        self._spool_job()
        self.set_status(_("Running row {row} of {total}.").format(row=row + 1, total=total))

    def on_run_all(self, event=None):
        total = csv_row_count(self.wlist)
        if total <= 0:
            self.set_status(_("Import a CSV first."))
            return
        self._batch_chain = True
        self.check_auto.SetValue(True)
        self.btn_stop.Enable(True)
        self.go_to_row(0)
        self._spool_job()
        self.set_status(_("Batch started at row 1 of {total}.").format(total=total))

    def on_stop_batch(self, event=None):
        self._batch_chain = False
        self.btn_stop.Enable(False)
        self.set_status(_("Batch stopped."))

    def _continue_batch_if_needed(self):
        if not self._batch_chain or not self.check_auto.GetValue():
            self.btn_stop.Enable(False)
            return
        total = csv_row_count(self.wlist)
        next_row = current_csv_row(self.wlist) + 1
        if next_row >= total:
            self._batch_chain = False
            self.btn_stop.Enable(False)
            self.set_status(_("Batch complete — {total} rows processed.").format(total=total))
            return
        self.go_to_row(next_row)
        self._spool_job()
        self.set_status(
            _("Batch continuing — row {row} of {total}.").format(row=next_row + 1, total=total)
        )

    @signal_listener("spooler;aborted")
    def on_spooler_aborted(self, origin, *args):
        self._batch_chain = False
        self.btn_stop.Enable(False)
        self.set_status(_("Batch stopped — job was aborted."))

    @signal_listener("spooler;completed")
    def on_spooler_completed(self, origin, *args):
        if not self._batch_chain:
            return
        if getattr(self.context.device.spooler, "_user_aborted", False):
            return
        self._continue_batch_if_needed()

    @signal_listener("wordlist")
    @signal_listener("wordlist_modified")
    def on_wordlist_changed(self, origin, *args):
        self.refresh_ui()

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/preparation/BatchRun",
            {
                "label": _("CSV Batch"),
                "icon": icons8_gas_industry,
                "tip": _("Run jobs from CSV wordlist rows"),
                "help": "batchrun",
                "action": lambda v: kernel.console("window toggle BatchRun\n"),
            },
        )
        kernel.register(
            "button/config/BatchRun",
            {
                "label": _("CSV Batch Run"),
                "icon": icons8_curly_brackets,
                "tip": _("Batch personalization from CSV"),
                "help": "batchrun",
                "action": lambda v: kernel.console("window toggle BatchRun\n"),
            },
        )

    def window_open(self):
        self.refresh_ui()

    def window_close(self):
        self._batch_chain = False

    @staticmethod
    def submenu():
        return "Editing", "Variables + Wordlists", True

    @staticmethod
    def helptext():
        return _("Import CSV data and run repeated jobs with {variable} text substitution")
