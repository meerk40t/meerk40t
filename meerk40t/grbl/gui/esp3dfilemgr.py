import wx
from wx import aui
from datetime import datetime

from meerk40t.gui.icons import icons8_delete, icons8_save
from meerk40t.gui.wxutils import ScrolledPanel, wxButton

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
    
    Provides GUI controls for listing, executing, and deleting files
    on the ESP3D SD card.
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.pane_aui = None
        if self.context is not None:
            self.context.themes.set_window_colors(self)
        self.SetHelpText("esp3dfilemgr")

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # File list
        list_label = wx.StaticText(self, wx.ID_ANY, _("Files on ESP3D SD Card:"))
        sizer_main.Add(list_label, 0, wx.ALL, 5)

        self.list_files = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        self.list_files.InsertColumn(0, _("Filename"), width=200)
        self.list_files.InsertColumn(1, _("Size"), width=100)
        self.list_files.InsertColumn(2, _("Date/Time"), width=150)
        sizer_main.Add(self.list_files, 1, wx.EXPAND | wx.ALL, 5)

        # Buttons
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

        # Status text
        self.text_status = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.text_status.SetMinSize((-1, 150))
        sizer_main.Add(self.text_status, 0, wx.EXPAND | wx.ALL, 5)

        # SD card info
        self.label_sd_info = wx.StaticText(self, wx.ID_ANY, "")
        sizer_main.Add(self.label_sd_info, 0, wx.ALL, 5)

        self.SetSizer(sizer_main)
        self.Layout()

        # List selection handler
        self.list_files.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_file_selected)
        self.list_files.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_file_deselected)

    def on_file_selected(self, event):
        """Enable buttons when file is selected."""
        self.btn_execute.Enable(True)
        self.btn_delete.Enable(True)

    def on_file_deselected(self, event):
        """Disable buttons when no file is selected."""
        self.btn_execute.Enable(False)
        self.btn_delete.Enable(False)

    def get_selected_filename(self):
        """Get the currently selected filename."""
        index = self.list_files.GetFirstSelected()
        if index != -1:
            return self.list_files.GetItemText(index, 0)
        return None

    def on_refresh(self, event):
        """Refresh file list."""
        self.text_status.SetValue(_("Refreshing file list...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            # Get device - context might be device itself or have kernel.device
            device = self.context
            if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
                device = self.context.kernel.device

            if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                self.text_status.AppendText(
                    _("Error: ESP3D upload is not enabled.\n")
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
                timeout=5
            ) as esp3d:
                sd_info = esp3d.get_sd_info()
                files = sd_info.get("files", [])

                # Clear list
                self.list_files.DeleteAllItems()

                # Add files
                for f in files:
                    name = f.get("name", "")
                    size = f.get("size", "-1")
                    time = f.get("time", "")

                    # Skip directories
                    if size == "-1":
                        continue

                    # Format time according to locale
                    formatted_time = time
                    if time:
                        try:
                            # ESP3D returns time in format like "2024-12-30 15:30:45"
                            # Parse and reformat according to locale
                            dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
                            formatted_time = dt.strftime("%x %X")  # Locale's date and time representation
                        except (ValueError, AttributeError):
                            # If parsing fails, keep original format
                            formatted_time = time

                    index = self.list_files.InsertItem(self.list_files.GetItemCount(), name)
                    self.list_files.SetItem(index, 1, size)
                    self.list_files.SetItem(index, 2, formatted_time)

                # Update SD info
                total_mb = sd_info["total"] / (1024 * 1024)
                used_mb = sd_info["used"] / (1024 * 1024)
                free_mb = sd_info["free"] / (1024 * 1024)
                occupation = sd_info["occupation"]

                self.label_sd_info.SetLabel(
                    _("SD Card: {used:.2f} MB / {total:.2f} MB used ({occupation}%) - Free: {free:.2f} MB").format(
                        used=used_mb,
                        total=total_mb,
                        occupation=occupation,
                        free=free_mb
                    )
                )

                file_count = self.list_files.GetItemCount()
                self.text_status.AppendText(
                    _("✓ Found {count} file(s)\n").format(count=file_count)
                )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_execute(self, event):
        """Execute selected file."""
        filename = self.get_selected_filename()
        if not filename:
            return

        self.text_status.SetValue(_("Executing {filename}...\n").format(filename=filename))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            # Get device - context might be device itself or have kernel.device
            device = self.context
            if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
                device = self.context.kernel.device

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
                timeout=5
            ) as esp3d:
                result = esp3d.execute_file(filename)
                if result["success"]:
                    self.text_status.AppendText(_("✓ File execution started\n"))
                else:
                    self.text_status.AppendText(
                        _("✗ Execution failed: {message}\n").format(message=result.get('message', 'Unknown error'))
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

        # Confirm deletion
        dlg = wx.MessageDialog(
            self,
            _("Delete file '{filename}'?").format(filename=filename),
            _("Confirm Delete"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result != wx.ID_YES:
            return

        self.text_status.SetValue(_("Deleting {filename}...\n").format(filename=filename))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            # Get device - context might be device itself or have kernel.device
            device = self.context
            if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
                device = self.context.kernel.device

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
                timeout=5
            ) as esp3d:
                result = esp3d.delete_file(filename, device.esp3d_path)
                if result["success"]:
                    self.text_status.AppendText(_("✓ File deleted: {filename}\n").format(filename=filename))
                    # Refresh list
                    self.on_refresh(None)
                else:
                    self.text_status.AppendText(
                        _("✗ Delete failed: {message}\n").format(message=result.get('message', 'Unknown error'))
                    )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_clear_all(self, event):
        """Delete all files on SD card."""
        file_count = self.list_files.GetItemCount()
        
        if file_count == 0:
            wx.MessageBox(
                _("No files to delete"),
                _("Clear All"),
                wx.OK | wx.ICON_INFORMATION
            )
            return

        # Confirm deletion
        dlg = wx.MessageDialog(
            self,
            _("Delete ALL {count} file(s) from SD card?\n\nThis cannot be undone!").format(count=file_count),
            _("Confirm Clear All"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result != wx.ID_YES:
            return

        self.text_status.SetValue(_("Deleting all files...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            # Get device - context might be device itself or have kernel.device
            device = self.context
            if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
                device = self.context.kernel.device

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
            if hasattr(self.context, "kernel") and hasattr(self.context.kernel, "device"):
                device = self.context.kernel.device

            username = device.esp3d_username if device.esp3d_username else None
            password = device.esp3d_password if device.esp3d_password else None

            with ESP3DConnection(
                device.esp3d_host,
                device.esp3d_port,
                username,
                password,
                timeout=5
            ) as esp3d:
                # Get list of files
                sd_info = esp3d.get_sd_info()
                files = sd_info.get("files", [])

                deleted = 0
                failed = 0

                for f in files:
                    name = f.get("name", "")
                    size = f.get("size", "-1")

                    # Skip directories
                    if size == "-1":
                        continue

                    try:
                        result = esp3d.delete_file(name, device.esp3d_path)
                        if result["success"]:
                            deleted += 1
                            self.text_status.AppendText(_("  ✓ {name}\n").format(name=name))
                        else:
                            failed += 1
                            self.text_status.AppendText(
                                _("  ✗ {name}: {message}\n").format(name=name, message=result.get('message', 'Unknown error'))
                            )
                    except ESP3DUploadError as e:
                        failed += 1
                        self.text_status.AppendText(_("  ✗ {name}: {error}\n").format(name=name, error=e))

                    wx.Yield()

                self.text_status.AppendText("\n")
                self.text_status.AppendText(_("Deleted: {deleted}, Failed: {failed}\n").format(deleted=deleted, failed=failed))

                # Refresh list
                self.on_refresh(None)

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def pane_show(self):
        """Called when panel is shown."""
        pass

    def pane_hide(self):
        """Called when panel is hidden."""
        pass
