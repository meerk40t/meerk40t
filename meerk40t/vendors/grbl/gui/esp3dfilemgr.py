import wx
from wx import aui

from meerk40t.gui.wxutils import wxButton

_ = wx.GetTranslation


def register_panel_esp3d_files(window, context):
    """Register ESP3D file manager panel."""
    panel = ESP3DFileManagerPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(400, 300)
        .FloatingSize(500, 600)
        .Caption(_("ESP3D Files"))
        .Name("esp3d_files")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 400
    pane.control = panel
    panel.pane_aui = pane
    pane.submenu = "_10_" + _("Laser")
    pane.helptext = _("Manage files on ESP3D SD card")

    window.on_pane_create(pane)
    context.register("pane/esp3d_files", pane)


class ESP3DFileManagerPanel(wx.Panel):
    """
    File manager panel for ESP3D SD card files.

    Uses a dropdown to pick which SD file to run (Execute asks for confirmation).
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.pane_aui = None
        self._file_names = []
        if self.context is not None:
            self.context.themes.set_window_colors(self)
        self.SetHelpText("esp3dfilemgr")

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        list_label = wx.StaticText(self, wx.ID_ANY, _("Select file to run:"))
        sizer_main.Add(list_label, 0, wx.ALL, 5)

        self.choice_files = wx.Choice(self, wx.ID_ANY, choices=[])
        self.choice_files.SetMinSize((-1, 28))
        sizer_main.Add(self.choice_files, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        self.label_selected = wx.StaticText(self, wx.ID_ANY, _("Selected: (none)"))
        sizer_main.Add(self.label_selected, 0, wx.ALL, 5)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_refresh = wxButton(self, wx.ID_ANY, _("Refresh"))
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        sizer_buttons.Add(self.btn_refresh, 0, wx.ALL, 5)

        self.btn_execute = wxButton(self, wx.ID_ANY, _("Execute"))
        self.btn_execute.Bind(wx.EVT_BUTTON, self.on_execute)
        self.btn_execute.Enable(False)
        sizer_buttons.Add(self.btn_execute, 0, wx.ALL, 5)

        self.btn_delete = wxButton(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_delete.Enable(False)
        sizer_buttons.Add(self.btn_delete, 0, wx.ALL, 5)

        self.btn_clear_all = wxButton(self, wx.ID_ANY, _("Clear All"))
        self.btn_clear_all.Bind(wx.EVT_BUTTON, self.on_clear_all)
        sizer_buttons.Add(self.btn_clear_all, 0, wx.ALL, 5)

        sizer_main.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.text_status = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.text_status.SetMinSize((-1, 150))
        sizer_main.Add(self.text_status, 0, wx.EXPAND | wx.ALL, 5)

        self.label_sd_info = wx.StaticText(self, wx.ID_ANY, "")
        sizer_main.Add(self.label_sd_info, 0, wx.ALL, 5)

        self.SetSizer(sizer_main)
        self.Layout()

        self.choice_files.Bind(wx.EVT_CHOICE, self.on_file_selected)

    def _device(self):
        device = self.context
        if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
            device = self.context.kernel.device
        return device

    def on_file_selected(self, event):
        filename = self.get_selected_filename()
        has_sel = filename is not None
        self.btn_execute.Enable(has_sel)
        self.btn_delete.Enable(has_sel)
        if filename:
            self.label_selected.SetLabel(_("Selected: {name}").format(name=filename))
        else:
            self.label_selected.SetLabel(_("Selected: (none)"))

    def get_selected_filename(self):
        index = self.choice_files.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        if 0 <= index < len(self._file_names):
            return self._file_names[index]
        return None

    def _populate_file_list(self, files):
        """Fill dropdown and status log from SD card JSON."""
        from ..esp3d_upload import normalize_sd_file_entry

        self._file_names = []
        labels = []
        self.choice_files.Clear()
        self.text_status.AppendText(_("Files on SD card:\n"))

        for raw in files:
            f = normalize_sd_file_entry(raw)
            if f["is_dir"]:
                continue
            name = f["name"]
            size = f["size"]
            self._file_names.append(name)
            label = f"{name}  ({size})"
            labels.append(label)
            self.text_status.AppendText(f"  {label}\n")

        if labels:
            self.choice_files.AppendItems(labels)
            self.choice_files.SetSelection(0)
            self.on_file_selected(None)
        else:
            self.btn_execute.Enable(False)
            self.btn_delete.Enable(False)
            self.label_selected.SetLabel(_("Selected: (none)"))

        self.text_status.AppendText("\n")
        return len(self._file_names)

    def on_refresh(self, event):
        """Refresh file list."""
        self.text_status.SetValue(_("Refreshing file list...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import (
                ESP3DConnection,
                ESP3DUploadError,
                REQUESTS_AVAILABLE,
            )

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            device = self._device()

            if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                self.text_status.AppendText(
                    _(
                        "Error: ESP3D upload is not enabled.\n"
                        "Configuration → Device → ESP3D Upload → Enable.\n"
                    )
                )
                return

            if not hasattr(device, "esp3d_host") or not device.esp3d_host:
                self.text_status.AppendText(
                    _("Error: ESP3D host not configured.\n")
                )
                return

            username = device.esp3d_username if device.esp3d_username else None
            password = device.esp3d_password if device.esp3d_password else None

            with ESP3DConnection(
                device.esp3d_host,
                device.esp3d_port,
                username,
                password,
                timeout=5,
            ) as esp3d:
                sd_info = esp3d.get_sd_info()
                files = sd_info.get("files", [])

                file_count = self._populate_file_list(files)

                total_mb = sd_info["total"] / (1024 * 1024)
                used_mb = sd_info["used"] / (1024 * 1024)
                free_mb = sd_info["free"] / (1024 * 1024)
                occupation = sd_info["occupation"]

                self.label_sd_info.SetLabel(
                    _(
                        "SD Card: {used:.2f} MB / {total:.2f} MB used ({occupation}%) - Free: {free:.2f} MB"
                    ).format(
                        used=used_mb,
                        total=total_mb,
                        occupation=occupation,
                        free=free_mb,
                    )
                )

                self.text_status.AppendText(
                    _("✓ Found {count} file(s)\n").format(count=file_count)
                )
                if file_count:
                    self.text_status.AppendText(
                        _(
                            "Pick a file from the dropdown, then click Execute.\n"
                            "Old SD files may need re-upload (esp3d_upload_run) for M3 + LF.\n"
                        )
                    )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_execute(self, event):
        """Execute selected file."""
        filename = self.get_selected_filename()
        if not filename:
            wx.MessageBox(
                _("Choose a file from the dropdown first."),
                _("ESP3D Files"),
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        dlg = wx.MessageDialog(
            self,
            _(
                "Run this file on the laser?\n\n{filename}\n\n"
                "Home first ($HY then $HX).\n\n"
                "If this file was uploaded before today, delete it and use "
                "Console → esp3d_upload_run -e instead (LF lines + M3 laser)."
            ).format(filename=filename),
            _("Confirm Execute"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if dlg.ShowModal() != wx.ID_YES:
            dlg.Destroy()
            return
        dlg.Destroy()

        self.text_status.SetValue(_("Executing {filename}...\n").format(filename=filename))
        wx.Yield()

        try:
            from ..esp3d_upload import (
                ESP3DConnection,
                ESP3DUploadError,
                REQUESTS_AVAILABLE,
            )

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            device = self._device()

            if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                self.text_status.AppendText(
                    _("ESP3D upload is not enabled. Enable in settings.\n")
                )
                return

            if not hasattr(device, "esp3d_host") or not device.esp3d_host:
                self.text_status.AppendText(
                    _("ESP3D host not configured. Set in device settings.\n")
                )
                return

            username = device.esp3d_username if device.esp3d_username else None
            password = device.esp3d_password if device.esp3d_password else None

            with ESP3DConnection(
                device.esp3d_host,
                device.esp3d_port,
                username,
                password,
                timeout=10,
            ) as esp3d:
                result = esp3d.execute_file(filename)
                if result["success"]:
                    self.text_status.AppendText(_("✓ {message}\n").format(
                        message=result.get("message", _("File execution started"))
                    ))
                else:
                    self.text_status.AppendText(
                        _("✗ {message}\n").format(
                            message=result.get("message", _("Execution failed"))
                        )
                    )
                    self.text_status.AppendText(
                        _(
                            "Fix: Console → esp3d_upload_run -e (fresh LF + M3 file), "
                            "or Clear All old files first.\n"
                        )
                    )
                resp = result.get("response")
                if resp:
                    self.text_status.AppendText(
                        _("Board: {resp}\n").format(resp=resp[:200])
                    )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_delete(self, event):
        """Delete selected file."""
        filename = self.get_selected_filename()
        if not filename:
            return

        dlg = wx.MessageDialog(
            self,
            _("Delete file '{filename}'?").format(filename=filename),
            _("Confirm Delete"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result != wx.ID_YES:
            return

        self.text_status.SetValue(_("Deleting {filename}...\n").format(filename=filename))
        wx.Yield()

        try:
            from ..esp3d_upload import (
                ESP3DConnection,
                ESP3DUploadError,
                REQUESTS_AVAILABLE,
            )

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            device = self._device()

            if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                self.text_status.AppendText(
                    _("ESP3D upload is not enabled. Enable in settings.\n")
                )
                return

            if not hasattr(device, "esp3d_host") or not device.esp3d_host:
                self.text_status.AppendText(
                    _("ESP3D host not configured. Set in device settings.\n")
                )
                return

            username = device.esp3d_username if device.esp3d_username else None
            password = device.esp3d_password if device.esp3d_password else None

            with ESP3DConnection(
                device.esp3d_host,
                device.esp3d_port,
                username,
                password,
                timeout=5,
            ) as esp3d:
                result = esp3d.delete_file(filename, device.esp3d_path)
                if result["success"]:
                    self.text_status.AppendText(
                        _("✓ File deleted: {filename}\n").format(filename=filename)
                    )
                    self.on_refresh(None)
                else:
                    self.text_status.AppendText(
                        _("✗ Delete failed: {message}\n").format(
                            message=result.get("message", "Unknown error")
                        )
                    )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_clear_all(self, event):
        """Delete all files on SD card."""
        file_count = len(self._file_names)

        if file_count == 0:
            wx.MessageBox(
                _("No files to delete"),
                _("Clear All"),
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        dlg = wx.MessageDialog(
            self,
            _(
                "Delete ALL {count} file(s) from SD card?\n\nThis cannot be undone!"
            ).format(count=file_count),
            _("Confirm Clear All"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result != wx.ID_YES:
            return

        self.text_status.SetValue(_("Deleting all files...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import (
                ESP3DConnection,
                ESP3DUploadError,
                REQUESTS_AVAILABLE,
                normalize_sd_file_entry,
            )

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            device = self._device()

            if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                self.text_status.AppendText(
                    _("ESP3D upload is not enabled. Enable in settings.\n")
                )
                return

            if not hasattr(device, "esp3d_host") or not device.esp3d_host:
                self.text_status.AppendText(
                    _("ESP3D host not configured. Set in device settings.\n")
                )
                return

            username = device.esp3d_username if device.esp3d_username else None
            password = device.esp3d_password if device.esp3d_password else None

            with ESP3DConnection(
                device.esp3d_host,
                device.esp3d_port,
                username,
                password,
                timeout=5,
            ) as esp3d:
                sd_info = esp3d.get_sd_info()
                files = sd_info.get("files", [])

                deleted = 0
                failed = 0

                for raw in files:
                    f = normalize_sd_file_entry(raw)
                    name = f["name"]
                    if f["is_dir"]:
                        continue

                    try:
                        result = esp3d.delete_file(name, device.esp3d_path)
                        if result["success"]:
                            deleted += 1
                            self.text_status.AppendText(_("  ✓ {name}\n").format(name=name))
                        else:
                            failed += 1
                            self.text_status.AppendText(
                                _("  ✗ {name}: {message}\n").format(
                                    name=name,
                                    message=result.get("message", "Unknown error"),
                                )
                            )
                    except ESP3DUploadError as e:
                        failed += 1
                        self.text_status.AppendText(
                            _("  ✗ {name}: {error}\n").format(name=name, error=e)
                        )

                    wx.Yield()

                self.text_status.AppendText("\n")
                self.text_status.AppendText(
                    _("Deleted: {deleted}, Failed: {failed}\n").format(
                        deleted=deleted, failed=failed
                    )
                )

                self.on_refresh(None)

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def pane_show(self):
        """Refresh when the pane is opened."""
        if not self._file_names:
            self.on_refresh(None)

    def pane_hide(self):
        """Called when panel is hidden."""
        return
