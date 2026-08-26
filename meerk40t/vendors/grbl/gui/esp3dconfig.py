"""
GRBL ESP3D Configuration Panel

GUI panel for configuring ESP3D upload settings for network-connected GRBL devices.
"""
import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer

_ = wx.GetTranslation


class ESP3DConfigPanel(ScrolledPanel):
    """
    Configuration panel for ESP3D upload settings.
    
    Provides GUI controls for configuring ESP3D-WEBUI connection parameters
    including host, port, authentication, and upload settings.
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("esp3dconfig")

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # ESP3D Settings
        self.panel_esp3d_settings = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="esp3d"
        )
        sizer_main.Add(self.panel_esp3d_settings, 1, wx.EXPAND, 0)

        # Test Connection Button
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_buttons, 0, wx.EXPAND | wx.ALL, 5)

        self.btn_test_connection = wx.Button(self, wx.ID_ANY, _("Test Connection"))
        self.btn_test_connection.SetToolTip(
            _("Test connection to ESP3D device and display SD card information")
        )
        sizer_buttons.Add(self.btn_test_connection, 0, wx.ALL, 5)

        self.btn_list_files = wx.Button(self, wx.ID_ANY, _("List Files"))
        self.btn_list_files.SetToolTip(
            _("List files on ESP3D SD card")
        )
        sizer_buttons.Add(self.btn_list_files, 0, wx.ALL, 5)

        # Status text
        sizer_status = StaticBoxSizer(self, wx.ID_ANY, _("Status"), wx.VERTICAL)
        sizer_main.Add(sizer_status, 0, wx.EXPAND | wx.ALL, 5)

        self.text_status = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self.text_status.SetMinSize((400, 100))
        sizer_status.Add(self.text_status, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_test_connection, self.btn_test_connection)
        self.Bind(wx.EVT_BUTTON, self.on_list_files, self.btn_list_files)

    def on_test_connection(self, event):
        """Handle test connection button click."""
        self.text_status.SetValue(_("Testing connection...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                self.text_status.AppendText(
                    _("Install with: pip install requests\n")
                )
                return

            # Connection test works regardless of esp3d_enabled setting
            if not hasattr(self.context, "esp3d_host") or not self.context.esp3d_host:
                self.text_status.AppendText(
                    _("Error: ESP3D host not configured.\n")
                )
                return

            username = self.context.esp3d_username if self.context.esp3d_username else None
            password = self.context.esp3d_password if self.context.esp3d_password else None

            # Use short timeout for connection test (5 seconds)
            with ESP3DConnection(
                self.context.esp3d_host,
                self.context.esp3d_port,
                username,
                password,
                timeout=5
            ) as esp3d:
                result = esp3d.test_connection()
                if result["success"]:
                    self.text_status.AppendText(_("✓ Connection successful!\n"))
                    
                    # Try to get SD info
                    try:
                        sd_info = esp3d.get_sd_info()
                        total_mb = sd_info["total"] / (1024 * 1024)
                        used_mb = sd_info["used"] / (1024 * 1024)
                        free_mb = sd_info["free"] / (1024 * 1024)
                        self.text_status.AppendText(
                            _("SD Card: {used:.2f} MB / {total:.2f} MB used ({occupation}%)\n").format(used=used_mb, total=total_mb, occupation=sd_info['occupation'])
                        )
                        self.text_status.AppendText(
                            _("Free space: {free:.2f} MB\n").format(free=free_mb)
                        )
                    except ESP3DUploadError as e:
                        self.text_status.AppendText(
                            _("Warning: Could not get SD info: {error}\n").format(error=e)
                        )
                else:
                    self.text_status.AppendText(
                        _("✗ Connection failed: {message}\n").format(message=result['message'])
                    )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("✗ Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("✗ Unexpected error: {error}\n").format(error=e))

    def on_list_files(self, event):
        """Handle list files button click."""
        self.text_status.SetValue(_("Listing files...\n"))
        wx.Yield()

        try:
            from ..esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE

            if not REQUESTS_AVAILABLE:
                self.text_status.AppendText(
                    _("Error: 'requests' library not installed.\n")
                )
                return

            if not hasattr(self.context, "esp3d_enabled") or not self.context.esp3d_enabled:
                self.text_status.AppendText(
                    _("ESP3D upload is not enabled. Enable in settings.\n")
                )
                return

            username = self.context.esp3d_username if self.context.esp3d_username else None
            password = self.context.esp3d_password if self.context.esp3d_password else None

            with ESP3DConnection(
                self.context.esp3d_host,
                self.context.esp3d_port,
                username,
                password,
            ) as esp3d:
                sd_info = esp3d.get_sd_info()
                files = sd_info.get("files", [])

                if not files:
                    self.text_status.AppendText(_("SD card is empty\n"))
                    return

                self.text_status.AppendText(_("Files on ESP3D SD card:\n\n"))
                for f in files:
                    name = f.get("name", "")
                    size = f.get("size", "-1")
                    time = f.get("time", "")

                    if size == "-1":
                        # Directory
                        self.text_status.AppendText(_("  [DIR]  {name}\n").format(name=name))
                    else:
                        # File
                        time_str = f"  ({time})" if time else ""
                        self.text_status.AppendText(
                            _("  {name:30s} {size:>10s}{time_str}\n").format(name=name, size=size, time_str=time_str)
                        )

                self.text_status.AppendText("\n")
                total_mb = sd_info["total"] / (1024 * 1024)
                used_mb = sd_info["used"] / (1024 * 1024)
                self.text_status.AppendText(
                    _("Used: {used:.2f} MB / {total:.2f} MB ({occupation}%)\n").format(used=used_mb, total=total_mb, occupation=sd_info['occupation'])
                )

        except ESP3DUploadError as e:
            self.text_status.AppendText(_("Error: {error}\n").format(error=e))
        except Exception as e:
            self.text_status.AppendText(_("Unexpected error: {error}\n").format(error=e))

    def pane_show(self):
        """Called when panel is shown."""
        pass

    def pane_hide(self):
        """Called when panel is hidden."""
        pass
