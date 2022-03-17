import os
import sys
from meerk40t.core.spoolers import Spooler
from meerk40t.core.units import ViewPort
from meerk40t.kernel import Service

from meerk40t.svgelements import Point, Path, SVGImage, Polygon, Shape, Angle, Matrix

import balor
from balor.Cal import Cal
from balor.command_list import CommandList
from balormk.BalorDriver import BalorDriver

import numpy as np
import scipy
import scipy.interpolate

from balormk.gui import gui
from balormk.pathtools import EulerianFill


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        return [gui.plugin]
    if lifecycle == "register":
        kernel.register("provider/device/balor", BalorDevice)
    elif lifecycle == "preboot":
        suffix = "balor"
        for d in kernel.settings.derivable(suffix):
            kernel.root(
                "service device start -p {path} {suffix}\n".format(
                    path=d, suffix=suffix
                )
            )


class BalorDevice(Service, ViewPort):
    """
    The BalorDevice is a MeerK40t service for the device type. It should be the main method of interacting with
    the rest of meerk40t. It defines how the scene should look and contains a spooler which meerk40t will give jobs
    to. This class additionally defines commands which exist as console commands while this service is activated.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "balor"

        _ = kernel.translation

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "balor-device",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
            },
            {
                "attr": "calfile_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable Calibration File"),
                "tip": _("Use calibration file?"),
            },
            {
                "attr": "calfile",
                "object": self,
                "default": None,
                "type": str,
                "label": _("Calibration File"),
                "tip": _("Provide a calibration file for the machine"),
            },
            {
                "attr": "corfile_enabled",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Enable Correction File"),
                "tip": _("Use correction file?"),
            },
            {
                "attr": "corfile",
                "object": self,
                "default": None,
                "type": str,
                "label": _("Correction File"),
                "tip": _("Provide a correction file for the machine"),
            },
            {
                "attr": "lens_size",
                "object": self,
                "default": "110mm",
                "type": float,
                "label": _("Width"),
                "tip": _("Lens Size"),
            },
            {
                "attr": "redlight_offset_x",
                "object": self,
                "default": "0mm",
                "type": float,
                "label": _("Redlight X Offset"),
                "tip": _("Offset the redlight positions by this amount in x"),
            },
            {
                "attr": "redlight_offset_y",
                "object": self,
                "default": "0mm",
                "type": float,
                "label": _("Redlight Y Offset"),
                "tip": _("Offset the redlight positions by this amount in y"),
            },
            {
                "attr": "mock",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Run mock-usb backend"),
                "tip": _(
                    "This starts connects to fake software laser rather than real one for debugging."
                ),
            },
            {
                "attr": "machine_index",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Machine index to select"),
                "tip": _(
                    "Which machine should we connect to? -- Leave at 0 if you have 1 machine."
                ),
            },
        ]
        self.register_choices("balor", choices)

        choices = [
            {
                "attr": "travel_speed",
                "object": self,
                "default": 2000.0,
                "type": float,
                "label": _("Travel Speed"),
                "tip": _("How fast do we travel when not cutting?"),
            },
            {
                "attr": "laser_power",
                "object": self,
                "default": 50.0,
                "type": float,
                "label": _("Laser Power"),
                "tip": _("How what power level do we cut at?"),
            },
            {
                "attr": "cut_speed",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Cut Speed"),
                "tip": _("How fast do we cut?"),
            },
            {
                "attr": "q_switch_frequency",
                "object": self,
                "default": 30.0,
                "type": float,
                "label": _("Q Switch Frequency"),
                "tip": _("QSwitch Frequency value"),
            },
            {
                "attr": "delay_laser_on",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser On Delay"),
                "tip": _("Delay for the start of the laser"),
            },
            {
                "attr": "delay_laser_off",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Laser Off Delay"),
                "tip": _("Delay amount for the end of the laser"),
            },
            {
                "attr": "delay_polygon",
                "object": self,
                "default": 100.0,
                "type": float,
                "label": _("Polygon Delay"),
                "tip": _("Delay amount between different points in the path travel."),
            },
        ]
        self.register_choices("balor-global", choices)

        choices = [
            {
                "attr": "first_pulse_killer",
                "object": self,
                "default": 200,
                "type": int,
                "label": _("First Pulse Killer"),
                "tip": _("Unknown"),
            },
            {
                "attr": "pwm_half_period",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Half Period"),
                "tip": _("Unknown"),
            },
            {
                "attr": "pwm_pulse_width",
                "object": self,
                "default": 125,
                "type": int,
                "label": _("PWM Pulse Width"),
                "tip": _("Unknown"),
            },
            {
                "attr": "standby_param_1",
                "object": self,
                "default": 2000,
                "type": int,
                "label": _("Standby Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "standby_param_2",
                "object": self,
                "default": 20,
                "type": int,
                "label": _("Standby Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "timing_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Timing Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "delay_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Delay Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "laser_mode",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("Laser Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "control_mode",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Control Mode"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p1",
                "object": self,
                "default": 0xFFB,
                "type": int,
                "label": _("First Pulse Killer, Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p2",
                "object": self,
                "default": 1,
                "type": int,
                "label": _("First Pulse Killer, Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p3",
                "object": self,
                "default": 409,
                "type": int,
                "label": _("First Pulse Killer, Parameter 3"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fpk2_p4",
                "object": self,
                "default": 100,
                "type": int,
                "label": _("First Pulse Killer, Parameter 4"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p1",
                "object": self,
                "default": 0,
                "type": int,
                "label": _("Fly Res, Parameter 1"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p2",
                "object": self,
                "default": 99,
                "type": int,
                "label": _("Fly Res, Parameter 2"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p3",
                "object": self,
                "default": 1000,
                "type": int,
                "label": _("Fly Res, Parameter 3"),
                "tip": _("Unknown"),
            },
            {
                "attr": "fly_res_p4",
                "object": self,
                "default": 25,
                "type": int,
                "label": _("Fly Res, Parameter 4"),
                "tip": _("Unknown"),
            },
        ]
        self.register_choices("balor-extra", choices)

        self.state = 0

        ViewPort.__init__(
            self,
            self.lens_size,
            self.lens_size,
            origin_x=0.5,
            origin_y=0.5,
            flip_y=True,
        )
        self.spooler = Spooler(self)
        self.driver = BalorDriver(self)
        self.spooler.driver = self.driver

        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device", "balor"),
            output_type="spooler",
        )
        def spool(
            command, channel, _, data=None, data_type=None, remainder=None, **kwgs
        ):
            """
            Registers the spool command for the Balor driver.
            """
            spooler = self.spooler
            if data is not None:
                if data_type == "balor":
                    spooler.job(("balor_job", data))
                    return "spooler", spooler
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler on device %s:" % str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))

            return "spooler", spooler

        @self.console_option(
            "travel_speed", "t", type=float, help="Set the travel speed."
        )
        @self.console_option("power", "p", type=float, help="Set the power level")
        @self.console_option(
            "frequency", "q", type=float, help="Set the device's qswitch frequency"
        )
        @self.console_option(
            "cut_speed", "s", type=float, help="Set the cut speed of the device"
        )
        @self.console_option("power", "p", type=float, help="Set the power level")
        @self.console_option(
            "laser_on_delay", "n", type=float, help="Sets the device's laser on delay"
        )
        @self.console_option(
            "laser_off_delay", "f", type=float, help="Sets the device's laser off delay"
        )
        @self.console_option(
            "polygon_delay",
            "n",
            type=float,
            help="Sets the device's laser polygon delay",
        )
        @self.console_option(
            "quantization",
            "Q",
            type=int,
            default=500,
            help="Number of line segments to break this path into",
        )
        @self.console_command(
            "mark",
            input_type="elements",
            output_type="balor",
            help=_("runs mark on path."),
        )
        def mark(
            command,
            channel,
            _,
            data=None,
            travel_speed=None,
            power=None,
            frequency=None,
            cut_speed=None,
            laser_on_delay=None,
            laser_off_delay=None,
            polygon_delay=None,
            quantization=500,
            **kwgs
        ):
            """
            Mark takes in element types from element* or circle or hull and applies the mark settings, and outputs
            a Balor job type. These could be spooled, looped, debugged or whatever else might be wanted/needed.
            """
            channel("Creating mark job out of elements.")
            paths = data
            from balor.Cal import Cal

            cal = None
            if self.calibration_file is not None:
                try:
                    cal = Cal(self.calibration_file)
                except TypeError:
                    pass
            job = CommandList(cal=cal)
            job.set_mark_settings(
                travel_speed=self.travel_speed
                if travel_speed is None
                else travel_speed,
                power=self.laser_power if power is None else power,
                frequency=self.q_switch_frequency if frequency is None else frequency,
                cut_speed=self.cut_speed if cut_speed is None else cut_speed,
                laser_on_delay=self.delay_laser_on
                if laser_on_delay is None
                else laser_on_delay,
                laser_off_delay=self.delay_laser_off
                if laser_off_delay is None
                else laser_off_delay,
                polygon_delay=self.delay_polygon
                if polygon_delay is None
                else polygon_delay,
            )
            job.laser_control(True)
            for e in paths:
                if isinstance(e, Shape):
                    if not isinstance(e, Path):
                        e = Path(e)
                    e = abs(e)
                else:
                    continue
                x, y = e.point(0)
                x *= self.get_native_scale_x
                y *= self.get_native_scale_y
                job.goto(x, y)
                for i in range(1, quantization + 1):
                    x, y = e.point(i / float(quantization))
                    x *= self.get_native_scale_x
                    y *= self.get_native_scale_y
                    job.mark(x, y)
            return "balor", job

        @self.console_option(
            "speed",
            "s",
            type=bool,
            action="store_true",
            help="Run this light job at slow speed for the parts that would have been cuts.",
        )
        @self.console_option(
            "travel_speed", "t", type=float, help="Set the travel speed."
        )
        @self.console_option(
            "simulation_speed",
            "m",
            type=float,
            help="sets the simulation speed for this operation",
        )
        @self.console_option(
            "quantization",
            "Q",
            type=int,
            default=500,
            help="Number of line segments to break this path into",
        )
        @self.console_command(
            "light",
            input_type="elements",
            output_type="balor",
            help=_("runs light on events."),
        )
        def light(
            command,
            channel,
            _,
            speed=False,
            travel_speed=None,
            simulation_speed=None,
            quantization=500,
            data=None,
            **kwgs
        ):
            channel("Creating light job out of elements.")
            paths = data
            cal = None
            if self.calibration_file is not None:
                try:
                    cal = Cal(self.calibration_file)
                except TypeError:
                    pass
            job = CommandList(cal=cal)
            if travel_speed is None:
                travel_speed = self.travel_speed
            if simulation_speed is None:
                simulation_speed = self.cut_speed
            else:
                # If we set a sim-speed we should go at that speed
                speed = True
            job.set_travel_speed(travel_speed)

            for e in paths:
                if isinstance(e, Shape):
                    if not isinstance(e, Path):
                        e = Path(e)
                    e = abs(e)
                else:
                    continue
                x, y = e.point(0)
                x *= self.get_native_scale_x
                y *= self.get_native_scale_y
                job.light(x, y, False, jump_delay=200)
                if speed:
                    job.set_travel_speed(simulation_speed)
                for i in range(1, quantization + 1):
                    x, y = e.point(i / float(quantization))
                    x *= self.get_native_scale_x
                    y *= self.get_native_scale_y
                    # if i == quantization:
                    #     job.light(x, y, True, calibration=50)
                    # else:
                    job.light(x, y, True, jump_delay=0)
                if speed:
                    job.set_travel_speed(travel_speed)
            job.light_off()
            return "balor", job

        @self.console_command(
            "stop",
            help=_("stops the idle running job"),
            input_type=(None),
        )
        def stoplight(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Stopping idle job")
            self.spooler.set_idle(None)
            self.driver.connection.abort()

        @self.console_command(
            "estop",
            help=_("stops the current job, deletes the spooler"),
            input_type=(None),
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Stopping idle job")
            self.spooler.set_idle(None)
            self.spooler.clear_queue()
            self.driver.connection.abort()

        @self.console_command(
            "pause",
            help=_("Pauses the currently running job"),
        )
        def pause(command, channel, _, data=None, remainder=None, **kwgs):
            if self.driver.paused:
                channel("Resuming current job")
            else:
                channel("Pausing current job")
            self.driver.pause()

        @self.console_command(
            "resume",
            help=_("Resume the currently running job"),
        )
        def resume(command, channel, _, data=None, remainder=None, **kwgs):
            channel("Resume the current job")
            self.driver.resume()

        @self.console_command(
            "usb_connect",
            help=_("connect usb"),
        )
        def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.connect()

        @self.console_command(
            "usb_disconnect",
            help=_("connect usb"),
        )
        def usb_connect(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.disconnect()

        @self.console_command(
            "print",
            help=_("print balor info about generated job"),
            input_type="balor",
            output_type="balor",
        )
        def balor_print(command, channel, _, data=None, remainder=None, **kwgs):
            for d in data:
                print(d)
            return "balor", data

        @self.console_argument("filename", type=str, default="balor.png")
        @self.console_command(
            "png",
            help=_("save image of balor write data"),
            input_type="balor",
            output_type="balor",
        )
        def balor_png(command, channel, _, data=None, filename="balor.png", **kwargs):
            from PIL import Image, ImageDraw

            data.scale_x = 1.0
            data.scale_y = 1.0
            data.size = "decagalvo"
            im = Image.new("RGB", (0xFFF, 0xFFF), color=0)
            data.plot(ImageDraw.Draw(im), 0xFFF)
            im.save(filename, format="png")
            return "balor", data

        @self.console_command(
            "debug",
            help=_("debug balor job block"),
            input_type="balor",
            output_type="balor",
        )
        def balor_debug(command, channel, _, data=None, **kwargs):
            c = CommandList()
            for packet in data.packet_generator():
                c.add_packet(packet)
            for operation in c:
                print(operation.text_debug(show_tracking=True))
            return "balor", data

        @self.console_argument("filename", type=str, default="balor.bin")
        @self.console_command(
            "save",
            help=_("print balor info about generated job"),
            input_type="balor",
            output_type="balor",
        )
        def balor_save(
            command, channel, _, data=None, filename="balor.bin", remainder=None, **kwgs
        ):
            with open(filename, "wb") as f:
                for d in data:
                    f.write(d)
            channel("Saved file {filename} to disk.".format(filename=filename))
            return "balor", data

        @self.console_argument(
            "repeats", help="Number of times to duplicate the job", default=1
        )
        @self.console_command(
            "duplicate",
            help=_("loop the selected job forever"),
            input_type="balor",
            output_type="balor",
        )
        def balor_dup(
            command, channel, _, data=None, repeats=1, remainder=None, **kwgs
        ):
            data.duplicate(1, None, repeats)
            channel("Job duplicated")
            return "balor", data

        @self.console_command(
            "loop",
            help=_("loop the selected job forever"),
            input_type="balor",
            output_type="balor",
        )
        def balor_loop(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.connect_if_needed()
            channel("Looping job: {job}".format(job=str(data)))
            self.spooler.set_idle(("light", data))
            return "balor", data

        @self.console_argument("x", type=float, default=0.0)
        @self.console_argument("y", type=float, default=0.0)
        @self.console_command(
            "goto",
            help=_("send laser a goto command"),
        )
        def balor_goto(command, channel, _, x=None, y=None, remainder=None, **kwgs):
            if x is not None and y is not None:
                rx = int(0x8000 + x) & 0xFFFF
                ry = int(0x8000 + y) & 0xFFFF
                self.driver.connect_if_needed()
                self.driver.connection.set_xy(rx, ry)

        @self.console_argument("off", type=str)
        @self.console_command(
            "red",
            help=_("Turns redlight on/off"),
        )
        def balor_on(command, channel, _, off=None, remainder=None, **kwgs):
            if off == "off":
                self.driver.connect_if_needed()
                reply = self.driver.connection.light_off()
                self.driver.redlight_preferred = False
                channel("Turning off redlight.")
            else:
                self.driver.connect_if_needed()
                reply = self.driver.connection.light_on()
                channel("Turning on redlight.")
                self.driver.redlight_preferred = True

        @self.console_command(
            "status",
            help=_("Sends status check"),
        )
        def balor_status(command, channel, _, remainder=None, **kwgs):
            self.driver.connect_if_needed()
            reply = self.driver.connection.read_port()
            channel("Command replied: {reply}".format(reply=str(reply)))
            for index, b in enumerate(reply):
                channel(
                    "Bit {index}: {bits}".format(
                        index="{0:x}".format(index), bits="{0:b}".format(b)
                    )
                )

        @self.console_command(
            "lstatus",
            help=_("Checks the list status."),
        )
        def balor_status(command, channel, _, remainder=None, **kwgs):
            self.driver.connect_if_needed()
            reply = self.driver.connection.raw_get_list_status()
            channel("Command replied: {reply}".format(reply=str(reply)))
            for index, b in enumerate(reply):
                channel(
                    "Bit {index}: {bits}".format(
                        index="{0:x}".format(index), bits="{0:b}".format(b)
                    )
                )

        @self.console_command(
            "serial_number",
            help=_("Checks the serial number."),
        )
        def balor_serial(command, channel, _, remainder=None, **kwgs):
            self.driver.connect_if_needed()
            reply = self.driver.connection.raw_get_serial_no()
            channel("Command replied: {reply}".format(reply=str(reply)))
            for index, b in enumerate(reply):
                channel(
                    "Bit {index}: {bits}".format(
                        index="{0:x}".format(index), bits="{0:b}".format(b)
                    )
                )

        @self.console_argument("filename", type=str, default=None)
        @self.console_command(
            "calibrate",
            help=_("set the calibration file"),
        )
        def set_calfile(command, channel, _, filename=None, remainder=None, **kwgs):
            if filename is None:
                calfile = self.calfile
                if calfile is None:
                    channel("No calibration file set.")
                else:
                    channel(
                        "Calibration file is set to: {file}".format(file=self.calfile)
                    )
                    from os.path import exists

                    if exists(calfile):
                        channel("Calibration file exists!")
                        cal = balor.Cal.Cal(calfile)
                        if cal.enabled:
                            channel("Calibration file successfully loads.")
                        else:
                            channel("Calibration file does not load.")
                    else:
                        channel("WARNING: Calibration file does not exist.")
            else:
                from os.path import exists

                if exists(filename):
                    self.calfile = filename
                else:
                    channel(
                        "The file at {filename} does not exist.".format(
                            filename=os.path.realpath(filename)
                        )
                    )
                    channel("Calibration file was not set.")

        @self.console_argument("filename", type=str, default=None)
        @self.console_command(
            "correction",
            help=_("set the correction file"),
        )
        def set_corfile(command, channel, _, filename=None, remainder=None, **kwgs):
            if filename is None:
                file = self.corfile
                if file is None:
                    channel("No correction file set.")
                else:
                    channel(
                        "Correction file is set to: {file}".format(file=self.corfile)
                    )
                    from os.path import exists

                    if exists(file):
                        channel("Correction file exists!")
                        cal = balor.Cal.Cal(file)
                        if cal.enabled:
                            channel("Correction file successfully loads.")
                        else:
                            channel("Correction file does not load.")
                    else:
                        channel("WARNING: Correction file does not exist.")
            else:
                from os.path import exists

                if exists(filename):
                    self.corfile = filename
                else:
                    channel(
                        "The file at {filename} does not exist.".format(
                            filename=os.path.realpath(filename)
                        )
                    )
                    channel("Correction file was not set.")

        @self.console_command(
            "position",
            help=_("give the position of the selection box in galvos"),
        )
        def galvo_pos(command, channel, _, data=None, args=tuple(), **kwargs):
            """
            Draws an outline of the current shape.
            """
            bounds = self.elements.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            cal = balor.Cal.Cal(self.calibration_file)

            x0 = bounds[0] * self.get_native_scale_x
            y0 = bounds[1] * self.get_native_scale_y
            x1 = bounds[2] * self.get_native_scale_x
            y1 = bounds[3] * self.get_native_scale_y
            width = (bounds[2] - bounds[0]) * self.get_native_scale_x
            height = (bounds[3] - bounds[1]) * self.get_native_scale_y
            cx, cy = cal.interpolate(x0, y0)
            mx, my = cal.interpolate(x1, y1)
            channel(
                "Top Right: ({cx}, {cy}). Lower, Left: ({mx},{my})".format(
                    cx=cx, cy=cy, mx=mx, my=my
                )
            )

        @self.console_argument("lens_size", type=str, default=None)
        @self.console_command(
            "lens",
            help=_("give the galvo position of the selection"),
        )
        def galvo_lens(
            command, channel, _, data=None, lens_size=None, args=tuple(), **kwargs
        ):
            """
            Sets lens size.
            """
            if lens_size is None:
                raise SyntaxError
            self.bedwidth = lens_size
            self.bedheight = lens_size

            channel(
                "Set Bed Size : ({sx}, {sy}).".format(
                    sx=self.bedwidth, sy=self.bedheight
                )
            )

            self.signal("bed_size")

        @self.console_command(
            "box",
            help=_("outline the current selected elements"),
            output_type="elements",
        )
        def element_outline(command, channel, _, data=None, args=tuple(), **kwargs):
            """
            Draws an outline of the current shape.
            """
            bounds = self.elements.selected_area()
            if bounds is None:
                channel(_("Nothing Selected"))
                return
            xmin, ymin, xmax, ymax = bounds
            channel("Element bounds: {bounds}".format(bounds=str(bounds)))
            points = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
                (xmin, ymin),
            ]
            return "elements", [Polygon(*points)]

        @self.console_command(
            "hull",
            help=_("convex hull of the current selected elements"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_outline(command, channel, _, data=None, args=tuple(), **kwargs):
            """
            Draws an outline of the current shape.
            """
            if data is None:
                data = list(self.elements.elems(emphasized=True))
            pts = []
            for obj in data:
                if isinstance(obj, Shape):
                    if not isinstance(obj, Path):
                        obj = Path(obj)
                    epath = abs(obj)
                    pts += [q for q in epath.as_points()]
                elif isinstance(obj, SVGImage):
                    bounds = obj.bbox()
                    pts += [
                        (bounds[0], bounds[1]),
                        (bounds[0], bounds[3]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                    ]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                channel(_("No elements bounds to trace."))
                return
            hull.append(hull[0])  # loop
            return "elements", [Polygon(*hull)]

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

        @self.console_option(
            "quantization",
            "q",
            default=500,
            type=int,
            help="Number of segments to break each path into.",
        )
        @self.console_command(
            "ants",
            help=_("Marching ants of the given element path."),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def element_ants(
            command, channel, _, data=None, quantization=500, args=tuple(), **kwargs
        ):
            """
            Draws an outline of the current shape.
            """
            if data is None:
                data = list(self.elements.elems(emphasized=True))
            points_list = []
            points = list()
            for e in data:
                if isinstance(e, Shape):
                    if not isinstance(e, Path):
                        e = Path(e)
                    e = abs(e)
                else:
                    continue
                for i in range(0, quantization + 1):
                    x, y = e.point(i / float(quantization))
                    points.append((x, y))
                points_list.append(list(ant_points(points, int(quantization / 10))))
            return "elements", [Polygon(*p) for p in points_list]

        @self.console_option(
            "raster-x-res",
            help="X resolution (in mm) of the laser.",
            default=0.15,
            type=float,
        )
        @self.console_option(
            "raster-y-res",
            help="X resolution (in mm) of the laser.",
            default=0.15,
            type=float,
        )
        @self.console_option(
            "x",
            "xoffs",
            help="Specify an x offset for the image (mm.)",
            default=0.0,
            type=float,
        )
        @self.console_option(
            "y",
            "yoffs",
            help="Specify an y offset for the image (mm.)",
            default=0.0,
            type=float,
        )
        @self.console_option(
            "d", "dither", help="Configure dithering", default=0.1, type=float
        )
        @self.console_option(
            "s",
            "scale",
            help="Pixels per mm (default 23.62 px/mm - 600 DPI)",
            default=23.622047,
            type=float,
        )
        @self.console_option(
            "t",
            "threshold",
            help="Greyscale threshold for burning (default 0.5, negative inverts)",
            default=0.5,
            type=float,
        )
        @self.console_option(
            "g",
            "grayscale",
            help="Greyscale rastering (power, speed, q_switch_frequency, passes)",
            default=False,
            type=bool,
        )
        @self.console_option(
            "grayscale-min",
            help="Minimum (black=1) value of the gray scale",
            default=None,
            type=float,
        )
        @self.console_option(
            "grayscale-max",
            help="Maximum (white=255) value of the gray scale",
            default=None,
            type=float,
        )
        @self.console_command("balor-raster", input_type="image", output_type="balor")
        def balor_raster(
            command,
            channel,
            _,
            data=None,
            raster_x_res=0.15,
            raster_y_res=0.15,
            xoffs=0.0,
            yoffs=0.0,
            dither=0.1,
            scale=23.622047,
            threshold=0.5,
            grayscale=False,
            grayscale_min=None,
            grayscale_max=None,
            **kwgs
        ):
            # def raster_render(self, job, cal, in_file, out_file, args):
            if len(data) == 0:
                channel("No image selected.")
                return
            in_file = data[0].image
            width = in_file.size[0] / scale
            height = in_file.size[1] / scale
            x0, y0 = xoffs, yoffs

            invert = False
            if threshold < 0:
                invert = True
                threshold *= -1.0
            dither = 0
            passes = 1
            if grayscale:
                gsmin = grayscale_min
                gsmax = grayscale_max
                gsslope = (gsmax - gsmin) / 256.0
            cal = None
            if self.calibration_file is not None:
                try:
                    cal = Cal(self.calibration_file)
                except TypeError:
                    pass
            job = CommandList(cal=cal)

            img = scipy.interpolate.RectBivariateSpline(
                np.linspace(y0, y0 + height, in_file.size[1]),
                np.linspace(x0, x0 + width, in_file.size[0]),
                np.asarray(in_file),
            )

            dither = 0
            job.set_mark_settings(
                travel_speed=self.travel_speed,
                power=self.laser_power,
                frequency=self.q_switch_frequency,
                cut_speed=self.cut_speed,
                laser_on_delay=self.delay_laser_on,
                laser_off_delay=self.delay_laser_off,
                polygon_delay=self.delay_polygon,
            )
            y = y0
            count = 0
            burning = False
            old_y = y0
            while y < y0 + height:
                x = x0
                job.goto(x, y)
                old_x = x0
                while x < x0 + width:
                    px = img(y, x)[0][0]
                    if invert:
                        px = 255.0 - px

                    if grayscale:
                        if px > 0:
                            gsval = gsmin + gsslope * px
                            if grayscale == "power":
                                job.set_power(gsval)
                            elif grayscale == "speed":
                                job.set_cut_speed(gsval)
                            elif grayscale == "q_switch_frequency":
                                job.set_frequency(gsval)
                            elif grayscale == "passes":
                                passes = int(round(gsval))
                                # Would probably be better to do this over the course of multiple
                                # rasters for heat disappation during 2.5D engraving
                            # pp = int(round((int(px)/255) * args.laser_power * 40.95))
                            # job.change_settings(q_switch_period, pp, cut_speed)

                            if not burning:
                                job.laser_control(True)  # laser turn on
                            i = passes
                            while i > 1:
                                job.mark(x, y)
                                job.mark(old_x, old_y)
                                i -= 2
                            job.mark(x, y)
                            burning = True

                        else:
                            if burning:
                                # laser turn off
                                job.laser_control(False)
                            job.goto(x, y)
                            burning = False
                    else:

                        if px + dither > threshold:
                            if not burning:
                                job.laser_control(True)  # laser turn on
                            job.mark(x, y)
                            burning = True
                            dither = 0.0
                        else:
                            if burning:
                                # laser turn off
                                job.laser_control(False)
                            job.goto(x, y)
                            dither += abs(px + dither - threshold) * dither
                            burning = False
                    old_x = x
                    x += raster_x_res
                if burning:
                    # laser turn off
                    job.laser_control(False)
                    burning = False

                old_y = y
                y += raster_y_res
                count += 1
                if not (count % 20):
                    print("\ty = %.3f" % y, file=sys.stderr)

            return "balor", job

        @self.console_option(
            "travel_speed", "t", type=float, help="Set the travel speed."
        )
        @self.console_option("power", "p", type=float, help="Set the power level")
        @self.console_option(
            "frequency", "q", type=float, help="Set the device's qswitch frequency"
        )
        @self.console_option(
            "cut_speed", "s", type=float, help="Set the cut speed of the device"
        )
        @self.console_option("power", "p", type=float, help="Set the power level")
        @self.console_option(
            "laser_on_delay", "n", type=float, help="Sets the device's laser on delay"
        )
        @self.console_option(
            "laser_off_delay", "f", type=float, help="Sets the device's laser off delay"
        )
        @self.console_option(
            "polygon_delay",
            "n",
            type=float,
            help="Sets the device's laser polygon delay",
        )
        @self.console_option(
            "angle", "a", type=Angle.parse, default=0, help=_("Angle of the fill")
        )
        @self.console_option(
            "distance", "d", type=str, default="1mm", help=_("distance between rungs")
        )
        @self.console_command(
            "hatch",
            help=_("hatch <angle> <distance>"),
            output_type="balor",
        )
        def hatch(
            command,
            channel,
            _,
            angle=None,
            distance=None,
            travel_speed=None,
            power=None,
            frequency=None,
            cut_speed=None,
            laser_on_delay=None,
            laser_off_delay=None,
            polygon_delay=None,
            **kwargs
        ):
            from balor.Cal import Cal

            cal = None
            if self.calibration_file is not None:
                try:
                    cal = Cal(self.calibration_file)
                except TypeError:
                    pass
            job = CommandList(cal=cal)
            job.set_mark_settings(
                travel_speed=self.travel_speed
                if travel_speed is None
                else travel_speed,
                power=self.laser_power if power is None else power,
                frequency=self.q_switch_frequency if frequency is None else frequency,
                cut_speed=self.cut_speed if cut_speed is None else cut_speed,
                laser_on_delay=self.delay_laser_on
                if laser_on_delay is None
                else laser_on_delay,
                laser_off_delay=self.delay_laser_off
                if laser_off_delay is None
                else laser_off_delay,
                polygon_delay=self.delay_polygon
                if polygon_delay is None
                else polygon_delay,
            )
            job.light_on()
            elements = self.elements
            channel(_("Hatch Filling"))
            if distance is not None:
                distance = self.length(distance, -1, as_float=True)
                distance *= self.get_native_scale_x
            else:
                distance = self.length("1mm", -1, as_float=True)
                distance *= self.get_native_scale_x

            efill = EulerianFill(distance)
            for element in elements.elems(emphasized=True):
                if not isinstance(element, Shape):
                    continue
                e = abs(Path(element))
                e *= Matrix.scale(self.get_native_scale_x, self.get_native_scale_y)
                if angle is not None:
                    e *= Matrix.rotate(angle)

                pts = [abs(e).point(i / 100.0, error=1e-4) for i in range(101)]
                efill += pts

            points = efill.get_fill()

            def split(points):
                pos = 0
                for i, pts in enumerate(points):
                    if pts is None:
                        yield points[pos : i - 1]
                        pos = i + 1
                if pos != len(points):
                    yield points[pos : len(points)]

            for s in split(points):
                for p in s:
                    if p.value == "RUNG":
                        job.mark(p.x, p.y)
                    if p.value == "EDGE":
                        job.goto(p.x, p.y)
            return "balor", job

    @property
    def current(self):
        """
        @return: the location in nm for the current known x value.
        """
        # return float(self.driver.native_x / self.width) * 0xFFF
        return self.device_to_scene_position(
            self.driver.native_x,
            self.driver.native_y,
        )

    @property
    def current_x(self):
        """
        @return: the location in nm for the current known y value.
        """
        return self.current[0]

    @property
    def current_y(self):
        """
        @return: the location in nm for the current known y value.
        """
        return self.current[1]

    @property
    def get_native_scale_x(self):
        """
        Native x goes from 0x0000 to 0xFFFF with 0x8000 being zero.
        :return:
        """
        unit_size = self.unit_width
        galvo_range = 0xFFFF
        unit_per_galvo = unit_size / galvo_range
        return 1.0 / unit_per_galvo

    @property
    def get_native_scale_y(self):
        unit_size = self.unit_height
        galvo_range = 0xFFFF
        unit_per_galvo = unit_size / galvo_range
        return 1.0 / unit_per_galvo

    @property
    def calibration_file(self):
        if self.calfile_enabled:
            return self.calfile
        else:
            return None
