import threading

import wx

from meerk40t.core.units import Length
from meerk40t.gui.icons import (
    get_default_icon_size,
    icons8_connected,
    icons8_disconnected,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import TextCtrl, dip_size, wxButton
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class NewlyInformationPanel(wx.ScrolledWindow):
    """NewlyInformationPanel - Displays key information from the NewlyController connection instance
    **Technical Purpose:**
    Provides real-time display of connection status, device information, and controller state.
    Shows connection details, current position, mode, and settings from self.context.device.connection.
    **End-User Perspective:**
    This panel shows detailed information about the laser controller connection and current state."""

    def __init__(self, *args, context=None, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("newlyinformation")

        # Information display widgets
        self.lbl_connection_status = wx.StaticText(
            self, wx.ID_ANY, _("Connection Status:")
        )
        self.txt_connection_status = wx.StaticText(self, wx.ID_ANY, _("Disconnected"))

        self.lbl_connection_type = wx.StaticText(self, wx.ID_ANY, _("Verbose:"))
        self.txt_connection_type = wx.StaticText(self, wx.ID_ANY, "None")

        self.lbl_device_info = wx.StaticText(self, wx.ID_ANY, _("Device Info:"))
        self.txt_device_info = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_machine_index = wx.StaticText(self, wx.ID_ANY, _("Machine Index:"))
        self.txt_machine_index = wx.StaticText(self, wx.ID_ANY, "0")

        self.lbl_current_position = wx.StaticText(
            self, wx.ID_ANY, _("Current Position:")
        )
        self.txt_current_position = wx.StaticText(self, wx.ID_ANY, "0.0, 0.0")

        self.lbl_current_mode = wx.StaticText(self, wx.ID_ANY, _("Current Mode:"))
        self.txt_current_mode = wx.StaticText(self, wx.ID_ANY, "init")

        self.lbl_current_speed = wx.StaticText(self, wx.ID_ANY, _("Current Speed:"))
        self.txt_current_speed = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_current_power = wx.StaticText(self, wx.ID_ANY, _("Current Power:"))
        self.txt_current_power = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_pwm_frequency = wx.StaticText(self, wx.ID_ANY, _("PWM Frequency:"))
        self.txt_pwm_frequency = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_relative_mode = wx.StaticText(self, wx.ID_ANY, _("Relative Mode:"))
        self.txt_relative_mode = wx.StaticText(self, wx.ID_ANY, "True")

        self.lbl_command_buffer = wx.StaticText(self, wx.ID_ANY, _("Command Buffer:"))
        self.txt_command_buffer = wx.StaticText(self, wx.ID_ANY, _("0 commands"))

        self.lbl_connection_details = wx.StaticText(
            self, wx.ID_ANY, _("Connection Details:")
        )
        self.txt_connection_details = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_device_enumeration = wx.StaticText(
            self, wx.ID_ANY, _("Device Enumeration:")
        )
        self.txt_device_enumeration = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_backend_status = wx.StaticText(self, wx.ID_ANY, _("Backend Status:"))
        self.txt_backend_status = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_controller_status = wx.StaticText(
            self, wx.ID_ANY, _("Controller Status:")
        )
        self.txt_controller_status = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.lbl_mode_details = wx.StaticText(self, wx.ID_ANY, _("Mode Details:"))
        self.txt_mode_details = wx.StaticText(self, wx.ID_ANY, _("N/A"))

        self.__set_properties()
        self.__do_layout()

        # Initial update
        self.update_information()

    def __set_properties(self):
        # Set font for information labels
        info_font = wx.Font(
            9,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )

        # Style the information display texts
        labels = [
            self.lbl_connection_status,
            self.lbl_connection_type,
            self.lbl_device_info,
            self.lbl_current_position,
            self.lbl_current_mode,
            self.lbl_current_speed,
            self.lbl_current_power,
            self.lbl_relative_mode,
        ]
        for label in labels:
            label.SetFont(info_font)

        values = [
            self.txt_connection_status,
            self.txt_connection_type,
            self.txt_device_info,
            self.txt_current_position,
            self.txt_current_mode,
            self.txt_current_speed,
            self.txt_current_power,
            self.txt_relative_mode,
        ]
        for value in values:
            value.SetFont(info_font)

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # Connection status section
        sizer_connection = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Connection")), wx.VERTICAL
        )
        grid_connection = wx.FlexGridSizer(2, 2, 5, 10)
        grid_connection.Add(self.lbl_connection_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_connection.Add(self.txt_connection_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_connection.Add(self.lbl_connection_type, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_connection.Add(self.txt_connection_type, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_connection.Add(grid_connection, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_connection, 0, wx.EXPAND | wx.ALL, 5)

        # Device info section
        sizer_device = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Device")), wx.VERTICAL
        )
        grid_device = wx.FlexGridSizer(2, 2, 5, 10)
        grid_device.Add(self.lbl_device_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_device.Add(self.txt_device_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_device.Add(self.lbl_machine_index, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_device.Add(self.txt_machine_index, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_device.Add(grid_device, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_device, 0, wx.EXPAND | wx.ALL, 5)

        # Position and mode section
        sizer_position = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Position & Mode")), wx.VERTICAL
        )
        grid_position = wx.FlexGridSizer(2, 2, 5, 10)
        grid_position.Add(self.lbl_current_position, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_position.Add(self.txt_current_position, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_position.Add(self.lbl_current_mode, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_position.Add(self.txt_current_mode, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_position.Add(grid_position, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_position, 0, wx.EXPAND | wx.ALL, 5)

        # Settings section
        sizer_settings = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Settings")), wx.VERTICAL
        )
        grid_settings = wx.FlexGridSizer(4, 2, 5, 10)
        grid_settings.Add(self.lbl_current_speed, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.txt_current_speed, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.lbl_current_power, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.txt_current_power, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.lbl_pwm_frequency, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.txt_pwm_frequency, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.lbl_relative_mode, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_settings.Add(self.txt_relative_mode, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_settings.Add(grid_settings, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_settings, 0, wx.EXPAND | wx.ALL, 5)

        # Command buffer section
        sizer_buffer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Command Buffer")), wx.VERTICAL
        )
        grid_buffer = wx.FlexGridSizer(1, 2, 5, 10)
        grid_buffer.Add(self.lbl_command_buffer, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_buffer.Add(self.txt_command_buffer, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_buffer.Add(grid_buffer, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_buffer, 0, wx.EXPAND | wx.ALL, 5)

        # Connection details section
        sizer_details = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Connection Details")), wx.VERTICAL
        )
        grid_details = wx.FlexGridSizer(1, 2, 5, 10)
        grid_details.Add(self.lbl_connection_details, 0, wx.ALIGN_TOP, 0)
        grid_details.Add(self.txt_connection_details, 0, wx.ALIGN_TOP, 0)
        sizer_details.Add(grid_details, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_details, 0, wx.EXPAND | wx.ALL, 5)

        # Device enumeration section
        sizer_enumeration = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Device Enumeration")), wx.VERTICAL
        )
        grid_enumeration = wx.FlexGridSizer(1, 2, 5, 10)
        grid_enumeration.Add(self.lbl_device_enumeration, 0, wx.ALIGN_TOP, 0)
        grid_enumeration.Add(self.txt_device_enumeration, 0, wx.ALIGN_TOP, 0)
        sizer_enumeration.Add(grid_enumeration, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_enumeration, 0, wx.EXPAND | wx.ALL, 5)

        # Backend status section
        sizer_backend = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Backend Status")), wx.VERTICAL
        )
        grid_backend = wx.FlexGridSizer(1, 2, 5, 10)
        grid_backend.Add(self.lbl_backend_status, 0, wx.ALIGN_TOP, 0)
        grid_backend.Add(self.txt_backend_status, 0, wx.ALIGN_TOP, 0)
        sizer_backend.Add(grid_backend, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_backend, 0, wx.EXPAND | wx.ALL, 5)

        # Controller status section
        sizer_controller = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Controller Status")), wx.VERTICAL
        )
        grid_controller = wx.FlexGridSizer(1, 2, 5, 10)
        grid_controller.Add(self.lbl_controller_status, 0, wx.ALIGN_TOP, 0)
        grid_controller.Add(self.txt_controller_status, 0, wx.ALIGN_TOP, 0)
        sizer_controller.Add(grid_controller, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_controller, 0, wx.EXPAND | wx.ALL, 5)

        # Mode details section
        sizer_mode = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Mode Details")), wx.VERTICAL
        )
        grid_mode = wx.FlexGridSizer(1, 2, 5, 10)
        grid_mode.Add(self.lbl_mode_details, 0, wx.ALIGN_TOP, 0)
        grid_mode.Add(self.txt_mode_details, 0, wx.ALIGN_TOP, 0)
        sizer_mode.Add(grid_mode, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_mode, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def update_information(self):
        """Update all displayed information from the controller connection."""
        try:
            controller = self.context.device.driver.connection  # .connection
            connection = controller.connection

            # Connection status
            connected = (
                controller.connected if hasattr(controller, "connected") else False
            )
            self.txt_connection_status.SetLabel(
                _("Connected") if connected else _("Disconnected")
            )

            # Connection type
            self.txt_connection_type.SetLabel(
                controller.status if hasattr(controller, "status") else _("Unknown")
            )
            # Device info and machine index
            device_info = _("N/A")
            machine_index = "0"
            if hasattr(connection, "bus") and hasattr(connection, "address"):
                try:
                    bus = connection.bus(0)
                    address = connection.address(0)
                    device_info = f"Bus {bus}, Address {address}"
                except Exception:
                    device_info = _("N/A")
            elif self.context.device.mock:
                device_info = _("Mock Device")

            if hasattr(controller, "_machine_index"):
                machine_index = str(getattr(controller, "_machine_index", 0))
            self.txt_device_info.SetLabel(device_info)
            self.txt_machine_index.SetLabel(machine_index)

            # Current position
            if hasattr(controller, "_last_x") and hasattr(controller, "_last_y"):
                pos_x = getattr(controller, "_last_x", 0)
                pos_y = getattr(controller, "_last_y", 0)
                self.txt_current_position.SetLabel(
                    f"{Length(pos_x, digits=1).length_mm}, {Length(pos_y, digits=1).length_mm}"
                )
            else:
                self.txt_current_position.SetLabel(_("0.0, 0.0"))

            # Current mode
            if hasattr(controller, "_set_mode"):
                mode = controller._set_mode
                self.txt_current_mode.SetLabel(str(mode))
            else:
                self.txt_current_mode.SetLabel(_("init"))

            # Current speed
            if hasattr(controller, "_set_speed"):
                speed = controller._set_speed
                self.txt_current_speed.SetLabel(
                    str(speed) if speed is not None else _("N/A")
                )
            else:
                self.txt_current_speed.SetLabel(_("N/A"))

            # Current power
            if hasattr(controller, "_set_power"):
                power = controller._set_power
                self.txt_current_power.SetLabel(
                    str(power) if power is not None else _("N/A")
                )
            else:
                self.txt_current_power.SetLabel(_("N/A"))

            # PWM frequency
            if hasattr(controller, "_pwm_frequency"):
                pwm_freq = getattr(controller, "_pwm_frequency", None)
                self.txt_pwm_frequency.SetLabel(
                    str(pwm_freq) if pwm_freq is not None else _("N/A")
                )
            else:
                self.txt_pwm_frequency.SetLabel(_("N/A"))

            # Relative mode
            if hasattr(controller, "_relative"):
                relative = getattr(controller, "_relative", True)
                self.txt_relative_mode.SetLabel(str(relative))
            else:
                self.txt_relative_mode.SetLabel(_("True"))

            # Command buffer
            if hasattr(controller, "_command_buffer"):
                buffer_len = len(getattr(controller, "_command_buffer", []))
                self.txt_command_buffer.SetLabel(f"{buffer_len} commands")
            else:
                self.txt_command_buffer.SetLabel(_("0 commands"))

            # Connection details
            details = []
            if hasattr(controller, "is_open"):
                details.append(f"Open: {controller.is_open()}")

            if hasattr(controller, "_is_opening"):
                details.append(f"Opening: {getattr(controller, '_is_opening', False)}")

            if hasattr(controller, "backend_error_code"):
                error_code = getattr(controller, "backend_error_code", None)
                if error_code is not None:
                    details.append(f"Backend Error: {error_code}")
                else:
                    details.append("Backend Error: None")

            if hasattr(controller, "timeout"):
                details.append(f"Timeout: {getattr(controller, 'timeout', 'N/A')}ms")

            self.txt_connection_details.SetLabel(
                "\n".join(details) if details else _("N/A")
            )

            # Device enumeration
            enumeration = []
            if hasattr(controller, "devices"):
                device_count = len(getattr(controller, "devices", {}))
                enumeration.append(f"Devices: {device_count}")
                if device_count > 0:
                    for idx, device in controller.devices.items():
                        if device:
                            try:
                                bus = controller.bus(idx)
                                address = controller.address(idx)
                                enumeration.append(
                                    f"Dev {idx}: Bus {bus}, Addr {address}"
                                )
                            except (AttributeError, KeyError, IndexError):
                                enumeration.append(f"Dev {idx}: Connected")

            if hasattr(controller, "interface"):
                interface_count = len(getattr(controller, "interface", {}))
                enumeration.append(f"Interfaces: {interface_count}")

            self.txt_device_enumeration.SetLabel(
                "\n".join(enumeration) if enumeration else _("No devices")
            )

            # Backend status
            backend_info = []
            if hasattr(controller, "backend_error_code"):
                error_code = getattr(controller, "backend_error_code", None)
                if error_code is not None:
                    backend_info.append(f"Error Code: {error_code}")
                    # Try to provide more descriptive error info
                    if hasattr(controller, "backend_error_code"):
                        if error_code == 1:  # LIBUSB_ERROR_ACCESS
                            backend_info.append("Access denied (permissions)")
                        elif error_code == -5:  # LIBUSB_ERROR_NOT_FOUND
                            backend_info.append("Device not found")
                        else:
                            backend_info.append("USB backend error")
                else:
                    backend_info.append("No backend errors")

            if hasattr(controller, "timeout"):
                backend_info.append(f"USB Timeout: {controller.timeout}ms")

            self.txt_backend_status.SetLabel(
                "\n".join(backend_info) if backend_info else _("N/A")
            )

            # Controller status
            controller_info = []
            if hasattr(controller, "is_shutdown"):
                controller_info.append(
                    f"Shutdown: {getattr(controller, 'is_shutdown', False)}"
                )

            if hasattr(controller, "_realtime"):
                controller_info.append(
                    f"Realtime: {getattr(controller, '_realtime', False)}"
                )

            if hasattr(controller, "paused"):
                controller_info.append(
                    f"Paused: {getattr(controller, 'paused', False)}"
                )

            if hasattr(controller, "_disable_connect"):
                controller_info.append(
                    f"Auto-connect disabled: {getattr(controller, '_disable_connect', False)}"
                )

            if hasattr(controller, "_abort_open"):
                controller_info.append(
                    f"Abort requested: {getattr(controller, '_abort_open', False)}"
                )

            self.txt_controller_status.SetLabel(
                "\n".join(controller_info) if controller_info else _("N/A")
            )

            # Mode details
            mode_info = []
            if hasattr(controller, "mode"):
                mode_info.append(f"Current Mode: {controller.mode}")

            if hasattr(controller, "_mode"):
                mode_info.append(f"Committed Mode: {controller._mode}")

            # Show current settings if available
            if hasattr(controller, "_speed") and controller._speed is not None:
                mode_info.append(f"Speed: {controller._speed}")

            if hasattr(controller, "_power") and controller._power is not None:
                mode_info.append(f"Power: {controller._power}")

            if (
                hasattr(controller, "_pwm_frequency")
                and controller._pwm_frequency is not None
            ):
                mode_info.append(f"PWM Freq: {controller._pwm_frequency}")

            if hasattr(controller, "_relative") and controller._relative is not None:
                mode_info.append(f"Relative: {controller._relative}")

            self.txt_mode_details.SetLabel(
                "\n".join(mode_info) if mode_info else _("No mode info")
            )

        except AttributeError:
            # If controller is not available, show defaults
            self.txt_connection_status.SetLabel(_("Disconnected"))
            self.txt_connection_type.SetLabel(_("None"))
            self.txt_device_info.SetLabel(_("N/A"))
            self.txt_machine_index.SetLabel(_("0"))
            self.txt_current_position.SetLabel(_("0.0, 0.0"))
            self.txt_current_mode.SetLabel(_("init"))
            self.txt_current_speed.SetLabel(_("N/A"))
            self.txt_current_power.SetLabel(_("N/A"))
            self.txt_pwm_frequency.SetLabel(_("N/A"))
            self.txt_relative_mode.SetLabel(_("True"))
            self.txt_command_buffer.SetLabel(_("0 commands"))
            self.txt_connection_details.SetLabel(_("N/A"))
            self.txt_device_enumeration.SetLabel(_("No devices"))
            self.txt_backend_status.SetLabel(_("N/A"))
            self.txt_controller_status.SetLabel(_("N/A"))
            self.txt_mode_details.SetLabel(_("No mode info"))

        self.Layout()

    @signal_listener("pipe;usb_status")
    def on_connection_update(self, origin=None, status=None):
        """Update information when connection status changes."""
        wx.CallAfter(self.update_information)

    @signal_listener("driver;position")
    def on_position_update(self, origin, pos):
        """Update information when position changes."""
        wx.CallAfter(self.update_information)

    @signal_listener("newly_controller_update")
    def on_controller_update(self, origin):
        """Update information when controller state changes."""
        wx.CallAfter(self.update_information)

    def pane_show(self):
        """Called when the panel becomes visible."""
        self.update_information()

    def pane_hide(self):
        """Called when the panel becomes hidden."""
        pass


class NewlyControllerPanel(wx.ScrolledWindow):
    """NewlyControllerPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for newlycontroller functionality. Features button controls for user interaction. Integrates with newly_controller_update, pipe;usb_status for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for newlycontroller functionality. Key controls include "Connection" (button)."""

    """NewlyControllerPanel - User interface panel for laser cutting operations"""

    def __init__(self, *args, context=None, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.ScrolledWindow.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("newlycontroller")

        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.button_device_connect = wxButton(self, wx.ID_ANY, _("Connection"))
        self.service = self.context.device
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self.text_usb_log = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.text_usb_log.SetFont(font)

        self.__set_properties()
        self.__do_layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_start_connection, self.button_device_connect
        )
        # end wxGlade
        self.max = 0
        self.state = None

    def __set_properties(self):
        self.button_device_connect.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_device_connect.SetForegroundColour(wx.BLACK)
        self.button_device_connect.SetFont(
            wx.Font(
                12,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                False,
                "Segoe UI",
            )
        )
        self.button_device_connect.SetToolTip(
            _("Force connection/disconnection from the device.")
        )
        self.button_device_connect.SetBitmap(
            icons8_disconnected.GetBitmap(
                use_theme=False, resize=get_default_icon_size(self.context)
            )
        )
        # end wxGlade

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        connection_controller = wx.BoxSizer(wx.VERTICAL)
        connection_controller.Add(self.button_device_connect, 0, wx.EXPAND, 0)
        sizer_1.Add(connection_controller, 0, wx.EXPAND, 0)
        static_line_2 = wx.StaticLine(self, wx.ID_ANY)
        static_line_2.SetMinSize(dip_size(self, 483, 5))
        sizer_1.Add(static_line_2, 0, wx.EXPAND, 0)
        sizer_1.Add(self.text_usb_log, 5, wx.EXPAND, 0)
        hspacer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_clear = wxButton(self, wx.ID_ANY, _("Clear Log"))
        hspacer.Add(self.btn_clear, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.btn_clear.Bind(wx.EVT_BUTTON, lambda evt: self.text_usb_log.Clear())
        self.info_label = wx.StaticText(self, wx.ID_ANY, "")
        hspacer.Add(self.info_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 0)
        sizer_1.Add(hspacer, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def update_text(self, text):
        with self._buffer_lock:
            self._buffer.append(f"{text}\n")
        self.context.signal("newly_controller_update")

    @signal_listener("driver;position")
    def on_device_update(self, origin, pos):
        if len(pos) < 4:
            return
        self.info_label.SetLabel(
            f"{Length(pos[2], digits=1).length_mm}, {Length(pos[3], digits=1).length_mm}"
        )

    @signal_listener("newly_controller_update")
    def update_text_gui(self, origin):
        with self._buffer_lock:
            buffer = "".join(self._buffer)
            self._buffer.clear()
        self.text_usb_log.AppendText(buffer)

    def set_button_connected(self):
        self.button_device_connect.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_device_connect.SetBitmap(
            icons8_connected.GetBitmap(
                use_theme=False, resize=get_default_icon_size(self.context)
            )
        )
        self.button_device_connect.Enable()

    def set_button_disconnected(self):
        self.button_device_connect.SetBackgroundColour(wx.Colour(223, 223, 0))
        self.button_device_connect.SetBitmap(
            icons8_disconnected.GetBitmap(
                use_theme=False, resize=get_default_icon_size(self.context)
            )
        )
        self.button_device_connect.Enable()

    @signal_listener("pipe;usb_status")
    def on_usb_update(self, origin=None, status=None):
        if status is None:
            status = "Unknown"
        try:
            connected = self.service.driver.connected
        except AttributeError:
            return
        try:
            if isinstance(status, bytes):
                status = status.decode("unicode-escape")
            label = (
                f'{_("Connected")}: {_(status)}'
                if connected
                else f'{_("Disconnected")}: {_(status)}'
            )
            self.button_device_connect.SetLabel(label)
            if connected:
                self.set_button_connected()
            else:
                self.set_button_disconnected()
        except RuntimeError:
            pass

    def on_button_start_connection(self, event):  # wxGlade: Controller.<event_handler>
        try:
            connected = self.service.driver.connected
        except AttributeError:
            return
        try:
            if self.service.driver.connection.is_connecting:
                self.service.driver.connection.abort_connect()
                self.service.driver.connection.set_disable_connect(False)
                return
        except AttributeError:
            pass

        if connected:
            self.context("usb_disconnect\n")
            self.service.driver.connection.set_disable_connect(False)
        else:
            self.service.driver.connection.set_disable_connect(False)
            self.context("usb_connect\n")

    def pane_show(self):
        self._channel_watching = f"{self.service.safe_label}/usb"
        self.context.channel(self._channel_watching).watch(self.update_text)
        try:
            connected = self.service.driver.connected
            if connected:
                self.set_button_connected()
            else:
                self.set_button_disconnected()
        except RuntimeError:
            pass

    def pane_hide(self):
        self.context.channel(self._channel_watching).unwatch(self.update_text)


class NewlyController(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(
            800, 600, *args, **kwds
        )  # Increased size for side-by-side layout

        # Create main horizontal sizer
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create controller panel (left side)
        self.controller_panel = NewlyControllerPanel(
            self, wx.ID_ANY, context=self.context
        )

        # Create information panel (right side)
        self.info_panel = NewlyInformationPanel(self, wx.ID_ANY, context=self.context)

        # Add panels to main sizer
        main_sizer.Add(self.controller_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(
            self.info_panel, 0, wx.EXPAND | wx.ALL, 5
        )  # 0 proportion so it takes minimum space

        self.sizer.Add(main_sizer, 1, wx.EXPAND, 0)

        # Add both panels as module delegates
        self.add_module_delegate(self.controller_panel)
        self.add_module_delegate(self.info_panel)

        self.SetTitle(_("Newly-Controller"))
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected.GetBitmap())
        self.SetIcon(_icon)
        self.Layout()
        self.restore_aspect()

    def window_open(self):
        self.controller_panel.pane_show()
        self.info_panel.pane_show()

    def window_close(self):
        self.controller_panel.pane_hide()
        self.info_panel.pane_hide()

    @staticmethod
    def submenu():
        # Hint for translation: _("Device-Control"), _("Newly-Controller")
        return "Device-Control", "Newly-Controller"

    @staticmethod
    def helptext():
        return _("Display the device controller window")
