import os
import re
import struct
import time

from usb.core import NoBackendError

from meerk40t.balormk.driver import BalorDriver
from meerk40t.balormk.livelightjob import LiveLightJob
from meerk40t.core.laserjob import LaserJob
from meerk40t.kernel import CommandSyntaxError
from meerk40t.tools.geomstr import Geomstr


def plugin(service, lifecycle):
    if lifecycle == "service":
        return "provider/device/balor"
    if lifecycle != "added":
        return

    _ = service._

    ########################
    # LIGHT JOBS COMMANDS
    ########################

    @service.console_option(
        "travel_speed", "t", type=float, help="Set the travel speed."
    )
    @service.console_option(
        "jump_delay",
        "d",
        type=float,
        default=200.0,
        help="Sets the jump delay for light travel moves",
    )
    @service.console_option(
        "simulation_speed",
        "m",
        type=float,
        help="sets the simulation speed for this operation",
    )
    @service.console_option(
        "quantization",
        "Q",
        type=int,
        default=500,
        help="Number of line segments to break this path into",
    )
    @service.console_command(
        ("light", "light-simulate"),
        input_type="geometry",
        help=_("runs light on events."),
    )
    def light(
        command,
        channel,
        _,
        travel_speed=None,
        jump_delay=200,
        simulation_speed=None,
        quantization=500,
        data=None,
        **kwgs,
    ):
        """
        Creates a shape based light job for use with the Galvo driver
        """
        if data is None:
            channel("Nothing sent")
            return
        service.job = LiveLightJob(
            service,
            mode="geometry",
            geometry=data,
            travel_speed=travel_speed,
            jump_delay=jump_delay,
            quantization=quantization,
            listen=False,
        )
        if command != "light":
            service.job.set_travel_speed(simulation_speed)
        service.spooler.send(service.job)

    @service.console_command("select-light", help=_("Execute selection light idle job"))
    def select_light(**kwargs):
        """
        Start a live bounds job.
        """
        # Live Bounds Job.
        if service.job is not None:
            service.job.stop()
        service.job = LiveLightJob(service, mode="bounds")
        service.spooler.send(service.job)

    @service.console_command("full-light", help=_("Execute full light idle job"))
    def full_light(**kwargs):
        if service.job is not None:
            service.job.stop()
        service.job = LiveLightJob(service)
        service.spooler.send(service.job)

    # @service.console_command(
    #     "regmark-light", help=_("Execute regmark live light idle job")
    # )
    # def reg_light(**kwargs):
    #     if service.job is not None:
    #         service.job.stop()
    #     service.job = LiveLightJob(service, mode="regmarks")
    #     service.spooler.send(service.job)

    @service.console_command("hull-light", help=_("Execute convex hull light idle job"))
    def hull_light(**kwargs):
        if service.job is not None:
            service.job.stop()
        service.job = LiveLightJob(service, mode="hull")
        service.spooler.send(service.job)

    @service.console_command(
        "stop",
        help=_("stops the idle running job"),
    )
    def stoplight(command, channel, _, data=None, remainder=None, **kwgs):
        if service.job is None:
            channel("No job is currently set")
            return
        channel("Stopping idle job")
        service.job.stop()

    @service.console_option(
        "count",
        "c",
        default=256,
        type=int,
        help="Number of instances of boxes to draw.",
    )
    @service.console_command(
        "box",
        help=_("outline the current selected elements"),
        output_type="geometry",
    )
    def shapes_selected(
        command, channel, _, count=256, data=None, args=tuple(), **kwargs
    ):
        """
        Draws an outline of the current shape.
        """
        bounds = service.elements.selected_area()
        if bounds is None:
            channel(_("Nothing Selected"))
            return
        xmin, ymin, xmax, ymax = bounds
        channel(_("Element bounds: {bounds}").format(bounds=str(bounds)))
        geometry = Geomstr.rect(xmin, ymin, xmax - xmin, ymax - ymin)
        if count > 1:
            geometry.copies(count)
        return "geometry", geometry

    @service.console_command(
        "hull",
        help=_("convex hull of the current selected elements"),
        input_type=(None, "elements"),
        output_type="geometry",
    )
    def shapes_hull(channel, _, data=None, **kwargs):
        """
        Draws an outline of the current shape.
        """
        if data is None:
            data = list(service.elements.elems(emphasized=True))
        g = Geomstr()
        for e in data:
            if hasattr(e, "as_image"):
                bounds = e.bounds
                g.append(
                    Geomstr.rect(
                        bounds[0],
                        bounds[1],
                        bounds[2] - bounds[0],
                        bounds[3] - bounds[1],
                    )
                )
            elif e.type == "elem text":
                continue  # We can't outline text.
            else:
                g.append(e.as_geometry())
        hull = Geomstr.hull(g)
        if len(hull) == 0:
            channel(_("No elements bounds to trace."))
            return
        return "geometry", hull

    def ant_points(points, steps):
        points = list(points)
        movement = 1 + int(steps / 10)
        forward_steps = steps + movement
        pos = 0
        size = len(points)
        cycles = int(size / movement) + 1
        for cycle in range(cycles):
            for f in range(pos, pos + forward_steps, 1):
                index = f % size
                point = points[index]
                yield point
            pos += forward_steps
            for f in range(pos, pos - steps, -1):
                index = f % size
                point = points[index]
                yield point
            pos -= steps

    @service.console_option(
        "quantization",
        "q",
        default=50,
        type=int,
        help="Number of segments to break each path into.",
    )
    @service.console_command(
        "ants",
        help=_("Marching ants of the given element path."),
        input_type=(None, "elements"),
        output_type="geometry",
    )
    def element_ants(command, channel, _, data=None, quantization=50, **kwargs):
        """
        Draws an outline of the current shape.
        """
        if data is None:
            data = list(service.elements.elems(emphasized=True))
        geom = Geomstr()
        for e in data:
            try:
                path = e.as_geometry()
            except AttributeError:
                continue
            ants = list(
                ant_points(
                    path.as_equal_interpolated_points(distance=quantization),
                    int(quantization / 2),
                )
            )
            geom.polyline(ants)
            geom.end()
        return "geometry", geom

    ########################
    # LASER CONTROL COMMANDS
    ########################

    @service.console_command(
        "estop",
        help=_("stops the current job, deletes the spooler"),
        input_type=None,
    )
    def estop(command, channel, _, data=None, remainder=None, **kwgs):
        channel("Stopping Job")
        if service.job is not None:
            service.job.stop()
        service.spooler.clear_queue()
        service.driver.set_abort()
        try:
            channel("Resetting controller.")
            service.driver.reset()
            service.signal("pause")
        except ConnectionRefusedError:
            pass

    @service.console_command(
        "pause",
        help=_("Pauses the currently running job"),
    )
    def pause(command, channel, _, data=None, remainder=None, **kwgs):
        if service.driver.paused:
            channel("Resuming current job")
        else:
            channel("Pausing current job")
        try:
            service.driver.pause()
        except ConnectionRefusedError:
            channel(_("Could not contact Galvo laser."))
        service.signal("pause")

    @service.console_command(
        "resume",
        help=_("Resume the currently running job"),
    )
    def resume(command, channel, _, data=None, remainder=None, **kwgs):
        channel("Resume the current job")
        try:
            service.driver.resume()
        except ConnectionRefusedError:
            channel(_("Could not contact Galvo laser."))
        service.signal("pause")

    @service.console_option(
        "idonotlovemyhouse",
        type=bool,
        action="store_true",
        help=_("override one second laser fire pulse duration"),
    )
    @service.console_argument("time", type=float, help=_("laser fire pulse duration"))
    @service.console_command(
        "pulse",
        help=_("pulse <time>: Pulse the laser in place."),
    )
    def pulse(command, channel, _, time=None, idonotlovemyhouse=False, **kwargs):
        if time is None:
            channel(_("Must specify a pulse time in milliseconds."))
            return
        if time > 1000.0:
            channel(
                _('"{time}ms" exceeds 1 second limit to fire a standing laser.').format(
                    time=time
                )
            )
            try:
                if not idonotlovemyhouse:
                    return
            except IndexError:
                return
        if service.spooler.is_idle:
            service.spooler.command("pulse", time)
            channel(_("Pulse laser for {time} milliseconds").format(time=time))
        else:
            channel(_("Pulse laser failed: Busy"))
        return

    ########################
    # USB COMMANDS
    ########################

    @service.console_command(
        "usb_connect",
        help=_("connect usb"),
    )
    def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
        service.spooler.command("connect", priority=1)

    @service.console_command(
        "usb_disconnect",
        help=_("connect usb"),
    )
    def usb_disconnect(command, channel, _, data=None, remainder=None, **kwgs):
        service.spooler.command("disconnect", priority=1)

    @service.console_command("usb_abort", help=_("Stops USB retries"))
    def usb_abort(command, channel, _, **kwargs):
        service.spooler.command("abort_retry", priority=1)

    ########################
    # PROJECT IO COMMANDS
    ########################

    @service.console_argument("filename", type=str)
    @service.console_command("save_job", help=_("save job export"), input_type="plan")
    def galvo_save(channel, _, filename, data=None, **kwargs):
        if filename is None:
            raise CommandSyntaxError
        try:
            with open(filename, "w") as f:
                driver = BalorDriver(service, force_mock=True)
                job = LaserJob(filename, list(data.plan), driver=driver)
                from meerk40t.balormk.controller import list_command_lookup

                def write(index, cmd):
                    cmds = [
                        struct.unpack("<6H", cmd[i : i + 12])
                        for i in range(0, len(cmd), 12)
                    ]
                    for v in cmds:
                        if v[0] >= 0x8000:
                            f.write(
                                f"{list_command_lookup.get(v[0], f'{v[0]:04x}').ljust(20)} "
                                f"{v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}\n"
                            )
                            if v[0] == 0x8002:
                                break

                try:
                    driver.connection.connect_if_needed()
                except (ConnectionRefusedError, NoBackendError):
                    channel("Could not connect to Galvo")
                    return
                driver.connection.connection.write = write
                job.execute()

        except (PermissionError, OSError):
            channel(_("Could not save: {filename}").format(filename=filename))

    @service.console_option(
        "default",
        "d",
        help=_("Allow default list commands to persist within the raw command"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "raw",
        "r",
        help=_("Data is explicitly little-ended hex from a data capture"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "binary_in",
        "b",
        help=_("Read data is explicitly in binary"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "binary_out",
        "B",
        help=_("Write data should be explicitly in binary"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "short",
        "s",
        help=_("Export data is assumed short command only"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "hard",
        "h",
        help=_("Do not send regular list protocol commands"),
        type=bool,
        action="store_true",
    )
    @service.console_option(
        "trim",
        "t",
        help=_("Trim the first number of characters"),
        type=int,
    )
    @service.console_option(
        "input", "i", type=str, default=None, help="input data for given file"
    )
    @service.console_option(
        "output", "o", type=str, default=None, help="output data to given file"
    )
    @service.console_command(
        "raw",
        help=_("sends raw galvo list command exactly as composed"),
    )
    def galvo_raw(
        channel,
        _,
        default=False,
        raw=False,
        binary_in=False,
        binary_out=False,
        short=False,
        hard=False,
        trim=0,
        input=None,
        output=None,
        remainder=None,
        **kwgs,
    ):
        """
        Raw for galvo performs raw actions and sends these commands directly to the laser.
        There are methods for reading and writing raw info from files in order to send that
        data. You can also use shorthand commands.
        """
        from meerk40t.balormk.controller import (
            list_command_lookup,
            single_command_lookup,
        )

        # Establish reverse lookup for string commands to binary command.
        reverse_lookup = {}
        for k in list_command_lookup:
            command_string = list_command_lookup[k]
            reverse_lookup[command_string] = k
            reverse_lookup[command_string.lower()[4:]] = k

        for k in single_command_lookup:
            command_string = single_command_lookup[k]
            reverse_lookup[command_string] = k
            reverse_lookup[command_string.lower()] = k

        if remainder is None and input is None:
            # "raw" was typed without any data or input file, so we list the permitted commands
            channel("Permitted List Commands:")
            for k in list_command_lookup:
                command_string = list_command_lookup[k]
                channel(f"{command_string.lower()[4:]} aka {k:04x}")
            channel("----------------------------")

            channel("Permitted Short Commands:")
            for k in single_command_lookup:
                command_string = single_command_lookup[k]
                channel(f"{command_string.lower()} aka {k:04x}")
            return

        if input is not None:
            # We were given an input file. We load that data, in either binary plain text.
            from os.path import exists

            if exists(input):
                channel(f"Loading data from: {input}")
                try:
                    if binary_in:
                        with open(input, "br") as f:
                            remainder = f.read().hex()
                    else:
                        with open(input) as f:
                            remainder = f.read()
                except OSError:
                    channel("File could not be read.")
            else:
                channel(f"The file at {os.path.realpath(input)} does not exist.")
                return

        cmds = None
        if raw or binary_in:
            # Our data is 6 values int16le
            if trim:
                # Used to cut off raw header data
                remainder = remainder[trim:]
            try:
                cmds = [
                    struct.unpack("<6H", bytearray.fromhex(remainder[i : i + 24]))
                    for i in range(0, len(remainder), 24)
                ]
                cmds = [
                    f"{v[0]:04x} {v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}"
                    for v in cmds
                ]
            except (struct.error, ValueError) as e:
                channel(f"Data was declared raw but could not parse because '{e}'")

        if cmds is None:
            cmds = list(re.split(r"[,\n\r]", remainder))

        raw_commands = list()

        # Compile commands.
        for cmd_i, cmd in enumerate(cmds):
            cmd = cmd.strip()
            if not cmd:
                continue

            values = [0] * 6
            byte_i = 0
            split_bytes = [b for b in cmd.split(" ") if b.strip()]
            if len(split_bytes) > 6:
                channel(
                    f"Invalid command line {cmd_i}: {split_bytes} has more than six entries."
                )
                return
            for b in split_bytes:
                v = None
                convert = reverse_lookup.get(b)
                if convert is not None:
                    v = int(convert)
                else:
                    try:
                        p = struct.unpack(">H", bytearray.fromhex(b))
                        v = p[0]
                    except (ValueError, struct.error):
                        pass
                if not isinstance(v, int):
                    channel(f'Compile error. Line #{cmd_i + 1} value "{b}"')
                    return
                values[byte_i] = v
                byte_i += 1
            raw_commands.append(values)

        if output is not None:
            # Output to file
            channel(f"Writing data to: {output}")
            try:
                if binary_out:
                    with open(output, "wb") as f:
                        for v in raw_commands:
                            b_data = struct.pack("<6H", *v)
                            f.write(b_data)
                else:
                    lines = []
                    for v in raw_commands:
                        lines.append(
                            f"{list_command_lookup.get(v[0], f'{v[0]:04x}').ljust(20)} "
                            f"{v[1]:04x} {v[2]:04x} {v[3]:04x} {v[4]:04x} {v[5]:04x}\n"
                        )
                    with open(output, "w") as f:
                        f.writelines(lines)
            except OSError:
                channel("File could not be written.")
            return  # If we output to file, we do not output to device.

        # OUTPUT TO DEVICE
        if hard:
            # Hard raw mode, disable any control values being sent.
            service.driver.connection.raw_mode()
            if not default:
                service.driver.connection.raw_clear()
            for v in raw_commands:
                command = v[0]
                if command >= 0x8000:
                    service.driver.connection._list_write(*v)
                else:
                    service.driver.connection._list_end()
                    service.driver.connection._command(*v)
            return

        if short:
            # Short mode only sending pure shorts.
            for v in raw_commands:
                service.driver.connection.raw_write(*v)
            return

        # Hybrid mode. Sending list and short commands using the right mode changes.
        service.driver.connection.rapid_mode()
        service.driver.connection.program_mode()
        if not default:
            service.driver.connection.raw_clear()
        for v in raw_commands:
            command = v[0]
            if command >= 0x8000:
                service.driver.connection.program_mode()
                service.driver.connection._list_write(*v)
            else:
                service.driver.connection.rapid_mode()
                service.driver.connection._command(*v)
        service.driver.connection.rapid_mode()

    ########################
    # CONTROLLER COMMANDS
    ########################

    @service.console_argument("x", type=float, default=0.0)
    @service.console_argument("y", type=float, default=0.0)
    @service.console_command(
        "goto",
        help=_("send laser a goto command"),
    )
    def galvo_goto(command, channel, _, x=None, y=None, remainder=None, **kwgs):
        if x is not None and y is not None:
            rx = int(0x8000 + x) & 0xFFFF
            ry = int(0x8000 + y) & 0xFFFF
            service.driver.connection.set_xy(rx, ry)

    @service.console_option("minspeed", "n", type=int, default=100)
    @service.console_option("maxspeed", "x", type=int, default=5000)
    @service.console_option("acc_time", "a", type=int, default=100)
    @service.console_argument("position", type=int, default=0)
    @service.console_command(
        "rotary_to",
        help=_("Send laser rotary command info."),
        all_arguments_required=True,
    )
    def galvo_rotary(
        command, channel, _, position, minspeed, maxspeed, acc_time, **kwgs
    ):
        service.driver.connection.set_axis_motion_param(
            minspeed & 0xFFFF, maxspeed & 0xFFFF
        )
        service.driver.connection.set_axis_origin_param(acc_time)  # Unsure why 100.
        pos = position if position >= 0 else -position + 0x80000000
        p1 = (pos >> 16) & 0xFFFF
        p0 = pos & 0xFFFF
        service.driver.connection.move_axis_to(p0, p1)
        service.driver.connection.wait_axis()

    @service.console_option("minspeed", "n", type=int, default=100)
    @service.console_option("maxspeed", "x", type=int, default=5000)
    @service.console_option("acc_time", "a", type=int, default=100)
    @service.console_argument(
        "delta_rotary", type=int, default=0, help="relative amount"
    )
    @service.console_command(
        "rotary_relative",
        help=_("Advance the rotary by the given amount"),
        all_arguments_required=True,
    )
    def galvo_rotary_advance(
        command, channel, _, delta_rotary, minspeed, maxspeed, acc_time, **kwgs
    ):
        pos_args = service.driver.connection.get_axis_pos()
        current = pos_args[1] | pos_args[2] << 16
        if current > 0x80000000:
            current = -current + 0x80000000
        position = current + delta_rotary

        service.driver.connection.set_axis_motion_param(
            minspeed & 0xFFFF, maxspeed & 0xFFFF
        )
        service.driver.connection.set_axis_origin_param(acc_time)  # Unsure why 100.
        pos = position if position >= 0 else -position + 0x80000000
        p1 = (pos >> 16) & 0xFFFF
        p0 = pos & 0xFFFF
        service.driver.connection.move_axis_to(p0, p1)
        service.driver.connection.wait_axis()

    @service.console_option("axis_index", "i", type=int, default=0)
    @service.console_command(
        "rotary_pos",
        help=_("Check the rotary position"),
    )
    def galvo_rotary_pos(command, channel, _, axis_index=0, **kwgs):
        pos_args = service.driver.connection.get_axis_pos(axis_index)
        if pos_args is None:
            channel("Not connected, cannot get axis pos.")
            return
        current = pos_args[1] | pos_args[2] << 16
        if current > 0x80000000:
            current = -current + 0x80000000
        channel(f"Rotary Position: {current}")

    @service.console_argument("off", type=str)
    @service.console_command(
        "red",
        help=_("Turns redlight on/off"),
    )
    def galvo_on(command, channel, _, off=None, remainder=None, **kwgs):
        try:
            if off == "off":
                service.driver.connection.light_off()
                service.driver.connection.write_port()
                service.redlight_preferred = False
                channel("Turning off redlight.")
                service.signal("red_dot", False)
            else:
                service.driver.connection.light_on()
                service.driver.connection.write_port()
                channel("Turning on redlight.")
                service.redlight_preferred = True
                service.signal("red_dot", True)
        except ConnectionRefusedError:
            service.signal(
                "warning",
                _("Connection was aborted. Manual connection required."),
                _("Not Connected"),
            )
            channel("Could not alter redlight. Connection is aborted.")

    @service.console_argument(
        "filename", type=str, default=None, help="filename or none"
    )
    @service.console_option(
        "default", "d", type=bool, action="store_true", help="restore to default"
    )
    @service.console_command(
        "force_correction",
        help=_("Resets the galvo laser"),
    )
    def force_correction(
        command, channel, _, filename=None, default=False, remainder=None, **kwgs
    ):
        if default:
            filename = service.corfile
            channel(f"Using default corfile: {filename}")
        if filename is None:
            service.driver.connection.write_correction_file(None)
            channel("Force set corrections to blank.")
        else:
            from os.path import exists

            if exists(filename):
                channel(f"Force set corrections: {filename}")
                service.driver.connection.write_correction_file(filename)
            else:
                channel(f"The file at {os.path.realpath(filename)} does not exist.")

    @service.console_command(
        "softreboot",
        help=_("Resets the galvo laser"),
    )
    def galvo_reset(command, channel, _, remainder=None, **kwgs):
        service.driver.connection.init_laser()
        channel(f"Soft reboot: {service.label}")

    @service.console_option(
        "duration", "d", type=float, help=_("time to set/unset the port")
    )
    @service.console_argument("off", type=str)
    @service.console_argument("bit", type=int)
    @service.console_command(
        "port",
        help=_("Turns port on or off, eg. port off 8"),
        all_arguments_required=True,
    )
    def galvo_port(command, channel, _, off, bit=None, duration=None, **kwgs):
        off = off == "off"
        if off:
            service.driver.connection.port_off(bit)
            service.driver.connection.write_port()
            channel(f"Turning off bit {bit}")
        else:
            service.driver.connection.port_on(bit)
            service.driver.connection.write_port()
            channel(f"Turning on bit {bit}")
        if duration is not None:
            if off:
                service(f".timer 1 {duration} port on {bit}")
            else:
                service(f".timer 1 {duration} port off {bit}")

    @service.console_command(
        "status",
        help=_("Sends status check"),
    )
    def galvo_status(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_version()
        if reply is None:
            channel("Not connected, cannot get serial number.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "lstatus",
        help=_("Checks the list status."),
    )
    def galvo_liststatus(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_list_status()
        if reply is None:
            channel("Not connected, cannot get serial number.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "mark_time",
        help=_("Checks the Mark Time."),
    )
    def galvo_mark_time(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_mark_time()
        if reply is None:
            channel("Not connected, cannot get mark time.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "mark_count",
        help=_("Checks the Mark Count."),
    )
    def galvo_mark_count(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_mark_count()
        if reply is None:
            channel("Not connected, cannot get mark count.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "axis_pos",
        help=_("Checks the Axis Position."),
    )
    def galvo_axis_pos(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_axis_pos()
        if reply is None:
            channel("Not connected, cannot get axis position.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "user_data",
        help=_("Checks the User Data."),
    )
    def galvo_user_data(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_user_data()
        if reply is None:
            channel("Not connected, cannot get user data.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "position_xy",
        help=_("Checks the Position XY"),
    )
    def galvo_position_xy(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_position_xy()
        if reply is None:
            channel("Not connected, cannot get position xy.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "fly_speed",
        help=_("Checks the Fly Speed."),
    )
    def galvo_fly_speed(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_fly_speed()
        if reply is None:
            channel("Not connected, cannot get fly speed.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "fly_wait_count",
        help=_("Checks the fiber config extend"),
    )
    def galvo_fly_wait_count(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_fly_wait_count()
        if reply is None:
            channel("Not connected, cannot get fly weight count.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "fiber_st_mo_ap",
        help=_("Checks the fiber st mo ap"),
    )
    def galvo_fiber_st_mo_ap(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_fiber_st_mo_ap()
        if reply is None:
            channel("Not connected, cannot get fiber_st_mo_ap.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    def from_binary(p: str):
        if p.startswith("0b"):
            p = p[2:]
        for c in p:
            if c not in ("0", "1", "x", "X"):
                raise ValueError("Not valid binary")
        return p.lower()

    @service.console_argument(
        "input",
        help=_("input binary to wait for. Use 'x' for any bit."),
        type=from_binary,
        nargs="*",
    )
    @service.console_option(
        "debug", "d", action="store_true", type=bool, help="debug output"
    )
    @service.console_command("wait_for_input", all_arguments_required=True, hidden=True)
    def wait_for_input(channel, input, debug=False, **kwargs):
        """
        Wait for input is intended as a spooler command. It will halt the calling thread (spooler thread) until the
        matching input is matched. Unimportant bits or bytes can be denoted with `x` for example:
        `wait_for_input x x x 1xxxx` would wait for a 1 on the 5th bit of the 4th word.

        Omitted values are assumed to be unimportant.
        """
        input_unmatched = True
        while input_unmatched:
            reply = service.driver.connection.read_port()
            input_unmatched = False
            word = 0
            for a, b in zip(reply, input):
                a = bin(a)
                if debug:
                    channel(f"input check: {a} match {b} in word #{word}")
                word += 1
                for i in range(-1, -len(a), -1):
                    try:
                        ac = a[i]
                        bc = b[i]
                    except IndexError:
                        # Assume remaining bits are no-care.
                        break
                    if bc in "x":
                        # This is a no-care bit.
                        continue
                    if ac != bc:
                        if debug:
                            channel(f"Fail at {~i} because {ac} != {bc}")
                        # We care, and they weren't equal
                        time.sleep(0.1)
                        input_unmatched = True
                        break
            if not input_unmatched:
                if debug:
                    channel("Input matched.")
                return  # We exited

    @service.console_command(
        "read_port",
        help=_("Checks the read_port"),
    )
    def galvo_read_port(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.read_port()
        if reply is None:
            channel("Not connected, cannot get read port.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "input_port",
        help=_("Checks the input_port"),
    )
    def galvo_input_port(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_input_port()
        if reply is None:
            channel("Not connected, cannot get input port.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "clear_lock_input_port",
        help=_("clear the input_port"),
    )
    def galvo_clear_input_port(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.clear_lock_input_port()
        if reply is None:
            channel("Not connected, cannot get input port.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "enable_lock_input_port",
        help=_("clear the input_port"),
    )
    def galvo_enable_lock_input_port(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.enable_lock_input_port()
        if reply is None:
            channel("Not connected, cannot get input port.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "disable_lock_input_port",
        help=_("clear the input_port"),
    )
    def galvo_disable_lock_input_port(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.disable_lock_input_port()
        if reply is None:
            channel("Not connected, cannot get input port.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "fiber_config_extend",
        help=_("Checks the fiber config extend"),
    )
    def galvo_fiber_config_extend(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_fiber_config_extend()
        if reply is None:
            channel("Not connected, cannot get fiber config extend.")
            return
        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_command(
        "serial_number",
        help=_("Checks the serial number."),
    )
    def galvo_serial(command, channel, _, remainder=None, **kwgs):
        reply = service.driver.connection.get_serial_number()
        if reply is None:
            channel("Not connected, cannot get serial number.")
            return

        channel(f"Command replied: {reply}")
        for index, b in enumerate(reply):
            channel(f"Bit {index}: 0x{b:04x} 0b{b:016b}")

    @service.console_argument("filename", type=str, default=None)
    @service.console_command(
        "correction",
        help=_("set the correction file"),
    )
    def set_corfile(command, channel, _, filename=None, remainder=None, **kwgs):
        if filename is None:
            file = service.corfile
            if file is None:
                channel("No correction file set.")
            else:
                channel(f"Correction file is set to: {service.corfile}")
                from os.path import exists

                if exists(file):
                    channel("Correction file exists!")
                else:
                    channel("WARNING: Correction file does not exist.")
        else:
            from os.path import exists

            if exists(filename):
                service.corfile = filename
                service.signal("corfile", filename)
            else:
                channel(f"The file at {os.path.realpath(filename)} does not exist.")
                channel("Correction file was not set.")

    @service.console_command(
        "position",
        help=_("give the position of the selection box in galvos"),
    )
    def galvo_pos(command, channel, _, data=None, args=tuple(), **kwargs):
        """
        Draws an outline of the current shape.
        """
        bounds = service.elements.selected_area()
        if bounds is None:
            channel(_("Nothing Selected"))
            return
        x0, y0 = service.view.position(bounds[0], bounds[1])
        x1, y1 = service.view.position(bounds[2], bounds[3])
        channel(
            f"Top,Right: ({x0:.02f}, {y0:.02f}). Lower, Left: ({x1:.02f},{y1:.02f})"
        )

    @service.console_argument("lens_size", type=str, default=None)
    @service.console_command(
        "lens",
        help=_("set the lens size"),
    )
    def galvo_lens(
        command, channel, _, data=None, lens_size=None, args=tuple(), **kwargs
    ):
        """
        Sets lens size.
        """
        if lens_size is None:
            raise SyntaxError
        service.lens_size = lens_size
        service.width = lens_size
        service.height = lens_size
        service.signal("lens_size", (service.lens_size, service.lens_size))
        channel(f"Set Bed Size : ({service.lens_size}, {service.lens_size}).")

    @service.console_argument("filename", type=str)
    @service.console_command(
        "clone_init",
        help=_("Initializes a galvo clone board from specified file."),
    )
    def codes_update(channel, filename, **kwargs):
        import platform

        from meerk40t.balormk.clone_loader import load_sys

        kernel = service.kernel

        service.setting(str, "clone_sys", "chunks")
        if filename is not None:
            service.clone_sys = filename
        if service.clone_sys == "chunks":
            from meerk40t.balormk.clone_loader import load_chunks

            load_chunks(channel=channel)
            return

        # Check for file in local directory
        p = service.clone_sys
        if os.path.exists(p):
            load_sys(p, channel=channel)
            return

        # Check for file in the meerk40t directory (safe_path)
        directory = kernel.os_information["WORKDIR"]
        p = os.path.join(directory, service.clone_sys)
        if os.path.exists(p):
            load_sys(p, channel=channel)
            return

        if platform.system() != "Windows":
            return

        # In windows, check the system32/drivers directory.
        system32 = os.path.join(
            os.environ["SystemRoot"],
            "SysNative" if platform.architecture()[0] == "32bit" else "System32",
        )
        p = os.path.join(system32, "drivers", service.clone_sys)
        if os.path.exists(p):
            load_sys(p, channel=channel)
            return

        channel(f"{service.clone_sys} file was not found.")
