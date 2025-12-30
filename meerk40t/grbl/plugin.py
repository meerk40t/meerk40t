"""
GRBL Device Plugin

Registers the required files to run the GRBL device.
"""
from meerk40t.grbl.control import GRBLControl, greet
from meerk40t.grbl.device import GRBLDevice, GRBLDriver
from meerk40t.grbl.emulator import GRBLEmulator
from meerk40t.grbl.gcodejob import GcodeJob
from meerk40t.grbl.interpreter import GRBLInterpreter
from meerk40t.grbl.loader import GCodeLoader


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import serial  # pylint: disable=unused-import
            from serial import SerialException  # pylint: disable=unused-import
        except ImportError:
            print("GRBL plugin could not load because pyserial is not installed.")
            return True
    elif lifecycle == "register":
        _ = kernel.translation

        kernel.register("provider/device/grbl", GRBLDevice)
        kernel.register("provider/friendly/grbl", ("GRBL-Diode-Laser", 2))
        kernel.register(
            "dev_info/grbl-generic",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Generic (GRBL-Controller)"),
                "extended_info": _("Generic GRBL Laser Device."),
                "priority": 17,
                "family": _("Generic Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Grbl",
                    },
                    {
                        "attr": "source",
                        "default": "generic",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-fluidnc",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("GRBL-FluidNC (FluidNC-Controller)"),
                "extended_info": _(
                    "Any of a variety of ESP32 based FluidNC drivers that implement GRBL as a protocol"
                ),
                "priority": 20,
                "family": _("Generic"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "FluidNC",
                    },
                    {
                        "attr": "source",
                        "default": "generic",
                    },
                    {
                        "attr": "flavor",
                        "default": "fluidnc",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-k40",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("K40 CO2 (GRBL-Controller)"),
                "extended_info": _("K40 laser with a modified GRBL laser controller."),
                "priority": 18,
                "family": _("K-Series CO2-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "GRBL-K40-CO2",
                    },
                    {
                        "attr": "has_endstops",
                        "default": True,
                    },
                    {
                        "attr": "bedwidth",
                        "default": "235mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "235mm",
                    },
                    {
                        "attr": "source",
                        "default": "co2",
                    },
                    {
                        "attr": "require_validator",
                        "default": True,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-diode",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Diode-Laser (GRBL-Controller)"),
                "extended_info": _(
                    "Any of a variety of inexpensive GRBL based diode lasers."
                ),
                "priority": 19,
                "family": _("Generic"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Grbl-Diode",
                    },
                    {
                        "attr": "has_endstops",
                        "default": False,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-ortur",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Ortur Laser Master 2 (GRBL)"),
                "extended_info": _("Ortur-branded self-assembled grbl diode lasers"),
                "priority": 21,
                "family": _("Ortur Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Ortur-LM2",
                    },
                    {
                        "attr": "has_endstops",
                        "default": True,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                    {"attr": "bedheight", "default": "430mm"},
                    {"attr": "bedwidth", "default": "400mm"},
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-longer-ray5",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Longer Ray5 (GRBL)"),
                "extended_info": _(
                    "Longer-branded 5w/10w/20w grbl diode laser.\nMake sure you verify your bed size! This machine has several upgrade kits."
                ),
                "priority": 21,
                "family": _("Longer Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Longer-Ray5",
                    },
                    {
                        "attr": "has_endstops",
                        "default": False,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                    {"attr": "bedheight", "default": "450mm"},
                    {"attr": "bedwidth", "default": "450mm"},
                ],
            },
        )
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("spoolerjob/grbl", GcodeJob)
        kernel.register("interpreter/grbl", GRBLInterpreter)
        kernel.register("emulator/grbl", GRBLEmulator)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("watch server channels"),
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current grblserver"),
        )
        @kernel.console_command(
            "grblcontrol",
            help=_("activate the grblserver."),
            hidden=True,
        )
        def grblserver(
            command,
            channel,
            _,
            port=23,
            verbose=False,
            quit=False,
            remainder=None,
            **kwargs,
        ):
            """
            The grblserver emulation methods provide a simulation of a grbl device.
            this emulates a grbl devices in order to be compatible with software that
            controls that type of device.
            """
            if remainder and remainder.lower() in ("stop", "quit"):
                quit = True
            root = kernel.root
            grblcontrol = root.device.lookup("grblcontrol")
            if grblcontrol is None:
                if quit:
                    channel(_("No control instance to stop."))
                    return
                grblcontrol = GRBLControl(root)
                root.device.register("grblcontrol", grblcontrol)
                grblcontrol.start(port, verbose)
            if quit:
                grblcontrol.quit()
                root.device.unregister("grblcontrol")

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_command(
            "grblmock", help=_("starts a grblmock server on port 23 (telnet)")
        )
        def server_console(command, channel, _, port=23, **kwargs):
            root = kernel.root

            try:
                root.open_as("module/TCPServer", "grblmock", port=port)
                tcp_recv_channel = root.channel("grblmock/recv", pure=True)
                tcp_send_channel = root.channel("grblmock/send", pure=True)
                tcp_send_channel.greet = greet

                def everything_ok(line):
                    for c in line:
                        if c == ord("\n") or c == ord("\r"):
                            tcp_send_channel("ok\r\n")
                        if c == ord("?"):
                            x = 0
                            y = 0
                            z = 0
                            f = 0
                            s = 0
                            status = (
                                f"<Idle|MPos:{x:.3f},{y:.3f},{z:.3f}|FS:{f},{s}>\r\n"
                            )
                            tcp_send_channel(status)

                tcp_send_channel.watch(print)
                tcp_recv_channel.watch(print)
                tcp_recv_channel.watch(everything_ok)
            except (OSError, ValueError):
                channel(_("Server failed on port: {port}").format(port=port))
            return

    elif lifecycle == "preboot":
        prefix = "grbl"
        for d in kernel.section_startswith(prefix):
            kernel.root(f"service device start -p {d} {prefix}\n")

    elif lifecycle == "postboot":
        _ = kernel.translation

        def init_esp3d_commands(kernel):
            """Initialize ESP3D upload commands."""
            
            @kernel.console_command(
                "esp3d_config",
                help=_("Configure or test ESP3D connection"),
                input_type=(None, "device"),
            )
            def esp3d_config(command, channel, _, data=None, **kwargs):
                """Configure ESP3D settings or test connection."""
                from .esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE
                
                if not REQUESTS_AVAILABLE:
                    channel(_("Error: 'requests' library not installed."))
                    channel(_("Install with: pip install requests"))
                    return
                
                device = data
                if device is None:
                    device = kernel.device
                if device is None:
                    channel(_("No device selected"))
                    return
                
                if not hasattr(device, "esp3d_enabled"):
                    channel(_("This device does not support ESP3D upload"))
                    return
                
                args = command.split()
                if len(args) > 1:
                    action = args[1].lower()
                    
                    if action == "test":
                        # Test connection
                        if not device.esp3d_enabled:
                            channel(_("ESP3D upload is not enabled. Enable in device settings."))
                            return
                        
                        channel(_("Testing ESP3D connection..."))
                        try:
                            username = device.esp3d_username if device.esp3d_username else None
                            password = device.esp3d_password if device.esp3d_password else None
                            
                            with ESP3DConnection(
                                device.esp3d_host,
                                device.esp3d_port,
                                username,
                                password
                            ) as esp3d:
                                result = esp3d.test_connection()
                                if result["success"]:
                                    channel(_("✓ Connection successful!"))
                                    # Try to get SD info
                                    try:
                                        sd_info = esp3d.get_sd_info()
                                        total_mb = sd_info["total"] / (1024 * 1024)
                                        used_mb = sd_info["used"] / (1024 * 1024)
                                        free_mb = sd_info["free"] / (1024 * 1024)
                                        channel(_(f"SD Card: {used_mb:.2f} MB / {total_mb:.2f} MB used ({sd_info['occupation']}%)"))
                                        channel(_(f"Free space: {free_mb:.2f} MB"))
                                    except ESP3DUploadError as e:
                                        channel(_(f"Warning: Could not get SD info: {e}"))
                                else:
                                    channel(_(f"✗ Connection failed: {result['message']}"))
                        except ESP3DUploadError as e:
                            channel(_(f"✗ Error: {e}"))
                        return
                    
                    elif action == "set":
                        # Set configuration parameters
                        if len(args) < 4:
                            channel(_("Usage: esp3d_config set <parameter> <value>"))
                            channel(_("Parameters: host, port, path, username, password, enabled, cleanup"))
                            return
                        
                        param = args[2].lower()
                        value = " ".join(args[3:])
                        
                        if param == "host":
                            device.esp3d_host = value
                            channel(_(f"ESP3D host set to: {value}"))
                        elif param == "port":
                            try:
                                device.esp3d_port = int(value)
                                channel(_(f"ESP3D port set to: {value}"))
                            except ValueError:
                                channel(_("Error: Port must be a number"))
                        elif param == "path":
                            device.esp3d_path = value
                            channel(_(f"ESP3D path set to: {value}"))
                        elif param == "username":
                            device.esp3d_username = value
                            channel(_(f"ESP3D username set to: {value}"))
                        elif param == "password":
                            device.esp3d_password = value
                            channel(_("ESP3D password set"))
                        elif param == "enabled":
                            device.esp3d_enabled = value.lower() in ("true", "1", "yes", "on")
                            channel(_(f"ESP3D upload enabled: {device.esp3d_enabled}"))
                        elif param == "cleanup":
                            device.esp3d_cleanup = value.lower() in ("true", "1", "yes", "on")
                            channel(_(f"ESP3D cleanup enabled: {device.esp3d_cleanup}"))
                        else:
                            channel(_(f"Unknown parameter: {param}"))
                        return
                
                # Show current configuration
                channel(_("ESP3D Configuration:"))
                channel(_(f"  Enabled: {device.esp3d_enabled}"))
                channel(_(f"  Host: {device.esp3d_host}"))
                channel(_(f"  Port: {device.esp3d_port}"))
                channel(_(f"  Path: {device.esp3d_path}"))
                channel(_(f"  Username: {device.esp3d_username if device.esp3d_username else '(not set)'}"))
                channel(_(f"  Password: {'***' if device.esp3d_password else '(not set)'}"))
                channel(_(f"  Cleanup: {device.esp3d_cleanup}"))
                channel(_(""))
                channel(_("Commands:"))
                channel(_("  esp3d_config test - Test connection"))
                channel(_("  esp3d_config set <parameter> <value> - Set configuration"))

            @kernel.console_command(
                "esp3d_list",
                help=_("List files on ESP3D SD card"),
                input_type=(None, "device"),
            )
            def esp3d_list(command, channel, _, data=None, **kwargs):
                """List files on ESP3D SD card."""
                from .esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE
                
                if not REQUESTS_AVAILABLE:
                    channel(_("Error: 'requests' library not installed."))
                    return
                
                device = data
                if device is None:
                    device = kernel.device
                if device is None:
                    channel(_("No device selected"))
                    return
                
                if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                    channel(_("ESP3D upload is not enabled"))
                    return
                
                try:
                    username = device.esp3d_username if device.esp3d_username else None
                    password = device.esp3d_password if device.esp3d_password else None
                    
                    with ESP3DConnection(
                        device.esp3d_host,
                        device.esp3d_port,
                        username,
                        password
                    ) as esp3d:
                        sd_info = esp3d.get_sd_info()
                        files = sd_info.get("files", [])
                        
                        if not files:
                            channel(_("SD card is empty"))
                            return
                        
                        channel(_("Files on ESP3D SD card:"))
                        channel(_(""))
                        for f in files:
                            name = f.get("name", "")
                            size = f.get("size", "-1")
                            time = f.get("time", "")
                            
                            if size == "-1":
                                # Directory
                                channel(_(f"  [DIR]  {name}"))
                            else:
                                # File
                                time_str = f"  ({time})" if time else ""
                                channel(_(f"  {name:30s} {size:>10s}{time_str}"))
                        
                        channel(_(""))
                        total_mb = sd_info["total"] / (1024 * 1024)
                        used_mb = sd_info["used"] / (1024 * 1024)
                        channel(_(f"Used: {used_mb:.2f} MB / {total_mb:.2f} MB ({sd_info['occupation']}%)"))
                        
                except ESP3DUploadError as e:
                    channel(_(f"Error: {e}"))

            @kernel.console_option(
                "filename", "f", type=str, help=_("Custom filename (8.3 format recommended)")
            )
            @kernel.console_option(
                "execute", "e", type=bool, action="store_true", help=_("Execute file after upload")
            )
            @kernel.console_command(
                "esp3d_upload_run",
                help=_("Generate G-code, upload to ESP3D SD card, and optionally execute"),
                input_type=(None, "device"),
            )
            def esp3d_upload_run(command, channel, _, data=None, filename=None, execute=False, **kwargs):
                """Upload current job to ESP3D and optionally execute."""
                import os
                import tempfile
                from .esp3d_upload import (
                    ESP3DConnection, 
                    ESP3DUploadError, 
                    generate_8_3_filename,
                    validate_filename_8_3,
                    REQUESTS_AVAILABLE
                )
                
                if not REQUESTS_AVAILABLE:
                    channel(_("Error: 'requests' library not installed."))
                    channel(_("Install with: pip install requests"))
                    return
                
                device = data
                if device is None:
                    device = kernel.device
                if device is None:
                    channel(_("No device selected"))
                    return
                
                if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                    channel(_("ESP3D upload is not enabled. Enable in device settings."))
                    return
                
                # Generate filename
                if filename:
                    if not validate_filename_8_3(filename):
                        channel(_("Warning: Filename doesn't follow 8.3 convention. This may cause issues."))
                    remote_filename = filename
                else:
                    remote_filename = generate_8_3_filename("file", "gc")
                    channel(_(f"Generated filename: {remote_filename}"))
                
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix=".gc", prefix="meerk40t_esp3d_")
                
                try:
                    os.close(temp_fd)  # Close the file descriptor
                    
                    # Generate G-code
                    channel(_("Generating G-code..."))
                    kernel.console(f"plan copy preprocess validate blob preopt optimize save_job {temp_path}\n")
                    
                    # Check if file was created and has content
                    if not os.path.exists(temp_path):
                        channel(_("Error: G-code generation failed - file not created"))
                        return
                    
                    file_size = os.path.getsize(temp_path)
                    if file_size == 0:
                        channel(_("Error: G-code generation failed - empty file"))
                        os.remove(temp_path)
                        return
                    
                    channel(_(f"Generated {file_size} bytes of G-code"))
                    
                    # Upload to ESP3D
                    channel(_(f"Uploading to {device.esp3d_host}:{device.esp3d_port}..."))
                    
                    username = device.esp3d_username if device.esp3d_username else None
                    password = device.esp3d_password if device.esp3d_password else None
                    
                    with ESP3DConnection(
                        device.esp3d_host,
                        device.esp3d_port,
                        username,
                        password
                    ) as esp3d:
                        result = esp3d.upload_file(
                            temp_path,
                            remote_filename,
                            device.esp3d_path
                        )
                        
                        if result["success"]:
                            channel(_(f"✓ Upload successful: {remote_filename}"))
                            
                            # Execute if requested
                            if execute:
                                channel(_("Executing file on device..."))
                                exec_result = esp3d.execute_file(remote_filename)
                                if exec_result["success"]:
                                    channel(_("✓ File execution started"))
                                else:
                                    channel(_(f"✗ Execution failed: {exec_result.get('message', 'Unknown error')}"))
                        else:
                            channel(_(f"✗ Upload failed: {result.get('message', 'Unknown error')}"))
                    
                except ESP3DUploadError as e:
                    channel(_(f"✗ Error: {e}"))
                except Exception as e:
                    channel(_(f"✗ Unexpected error: {e}"))
                finally:
                    # Cleanup local file if requested
                    if device.esp3d_cleanup and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                            channel(_("Local file cleaned up"))
                        except OSError:
                            channel(_("Warning: Could not delete local temporary file"))

            @kernel.console_command(
                "esp3d_run_file",
                help=_("Execute a file from ESP3D SD card"),
                input_type=(None, "device"),
            )
            def esp3d_run_file(command, channel, _, data=None, remainder=None, **kwargs):
                """Execute an existing file on ESP3D SD card."""
                from .esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE
                
                if not REQUESTS_AVAILABLE:
                    channel(_("Error: 'requests' library not installed."))
                    return
                
                device = data
                if device is None:
                    device = kernel.device
                if device is None:
                    channel(_("No device selected"))
                    return
                
                if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                    channel(_("ESP3D upload is not enabled"))
                    return
                
                if not remainder:
                    channel(_("Usage: esp3d_run_file <filename>"))
                    return
                
                filename = remainder.strip()
                
                try:
                    username = device.esp3d_username if device.esp3d_username else None
                    password = device.esp3d_password if device.esp3d_password else None
                    
                    with ESP3DConnection(
                        device.esp3d_host,
                        device.esp3d_port,
                        username,
                        password
                    ) as esp3d:
                        channel(_(f"Executing {filename} on device..."))
                        result = esp3d.execute_file(filename)
                        if result["success"]:
                            channel(_("✓ File execution started"))
                        else:
                            channel(_(f"✗ Execution failed: {result.get('message', 'Unknown error')}"))
                        
                except ESP3DUploadError as e:
                    channel(_(f"Error: {e}"))

            @kernel.console_command(
                "esp3d_delete",
                help=_("Delete a file from ESP3D SD card"),
                input_type=(None, "device"),
            )
            def esp3d_delete(command, channel, _, data=None, remainder=None, **kwargs):
                """Delete a file from ESP3D SD card."""
                from .esp3d_upload import ESP3DConnection, ESP3DUploadError, REQUESTS_AVAILABLE
                
                if not REQUESTS_AVAILABLE:
                    channel(_("Error: 'requests' library not installed."))
                    return
                
                device = data
                if device is None:
                    device = kernel.device
                if device is None:
                    channel(_("No device selected"))
                    return
                
                if not hasattr(device, "esp3d_enabled") or not device.esp3d_enabled:
                    channel(_("ESP3D upload is not enabled"))
                    return
                
                if not remainder:
                    channel(_("Usage: esp3d_delete <filename>"))
                    return
                
                filename = remainder.strip()
                
                try:
                    username = device.esp3d_username if device.esp3d_username else None
                    password = device.esp3d_password if device.esp3d_password else None
                    
                    with ESP3DConnection(
                        device.esp3d_host,
                        device.esp3d_port,
                        username,
                        password
                    ) as esp3d:
                        result = esp3d.delete_file(filename, device.esp3d_path)
                        if result["success"]:
                            channel(_(f"✓ File deleted: {filename}"))
                        else:
                            channel(_(f"✗ Delete failed: {result.get('message', 'Unknown error')}"))
                        
                except ESP3DUploadError as e:
                    channel(_(f"Error: {e}"))

        init_esp3d_commands(kernel)
