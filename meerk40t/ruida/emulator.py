"""
Ruida Emulator

The emulator allows us to listen for connections that send ruida data, we emulate that a ruida controller and turn
the received data into laser commands to be executed by the local driver.
"""

import os
from typing import Tuple, Union

from meerk40t.kernel import get_safe_path

from ..core.units import UNITS_PER_MM, UNITS_PER_uM
from .exceptions import RuidaCommandError
from .rdjob import (
    RDJob,
    abscoord,
    decode14,
    decodeu35,
    encode32,
    parse_commands,
    parse_filenumber,
    parse_mem,
    swizzles_lut,
)


class RuidaEmulator:
    def __init__(self, device, units_to_device_matrix):
        self.device = device
        self.units_to_device_matrix = units_to_device_matrix

        self.saving = False

        self.filename = None
        self.filestream = None

        self.color = None

        self.magic = 0x88  # 0x11 for the 634XG
        # Should automatically shift encoding if wrong.

        # self.magic = 0x38
        self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)

        self.channel = None

        self.program_mode = False
        self.reply = None
        self.realtime = None

        self.process_commands = True
        self.parse_lasercode = True
        self.swizzle_mode = True

        self.scale = UNITS_PER_uM

        self.job = RDJob(
            driver=device.driver,
            priority=0,
            channel=self._channel,
            units_to_device_matrix=units_to_device_matrix,
        )
        self.z = 0.0
        self.u = 0.0

        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0

    @property
    def x(self):
        return self.device.current[0]

    @property
    def y(self):
        return self.device.current[1]

    def __repr__(self):
        return f"RuidaEmulator(@{hex(id(self))})"

    def msg_reply(self, response, desc="ACK"):
        if self.swizzle_mode:
            if self.reply:
                self.reply(self.swizzle(response))
        else:
            if self.realtime:
                self.realtime(response)
        if self.channel:
            self.channel(f"<-- {response.hex()}\t({desc})")

    def _set_magic(self, magic):
        self.magic = magic
        self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)
        if self.channel:
            self.channel(f"Setting magic to 0x{self.magic:02x}")

    def checksum_write(self, sent_data):
        """
        This is `write` with a checksum and swizzling. This is how the 50200 packets arrive and need to be processed.

        @param sent_data: Packet data.
        @return:
        """
        self.swizzle_mode = True
        if len(sent_data) < 2:
            return  # Cannot contain a checksum.
        data = sent_data[2:1472]
        checksum_check = (sent_data[0] & 0xFF) << 8 | sent_data[1] & 0xFF
        checksum_sum = sum(data) & 0xFFFF
        if len(sent_data) > 3:
            if self.magic != 0x88 and sent_data[2] == 0xD4:
                self._set_magic(0x88)
            if self.magic != 0x11 and sent_data[2] == 0x4B:
                self._set_magic(0x11)
        if checksum_check == checksum_sum:
            response = b"\xCC"
            self.msg_reply(response, desc="Checksum match")
        else:
            response = b"\xCF"
            self.msg_reply(
                response, desc=f"Checksum Fail ({checksum_sum} != {checksum_check})"
            )
            if self.channel:
                self.channel("--> " + str(data.hex()))
            return
        self.write(data)

    def realtime_write(self, bytes_to_write):
        """
        Real time commands are replied to and sent in realtime. For Ruida devices these are sent along udp 50207.

        @param bytes_to_write:
        @return: bytes to write.
        """
        self.swizzle_mode = False
        self.msg_reply(b"\xCC")  # Clear ACK.
        self.write(bytes_to_write, unswizzle=False)

    def write(self, data, unswizzle=True):
        """
        Procedural commands sent in large data chunks. This can be through USB or UDP or a loaded file. These are
        expected to be unswizzled with the swizzle_mode set for the reply. Write will parse out the individual commands
        and send those to the command routine.

        @param data:
        @param unswizzle: Whether the given data should be unswizzled
        @return:
        """
        packet = self.unswizzle(data) if unswizzle else data
        for array in parse_commands(packet):
            try:
                if not self._process_realtime(array):
                    self.job.write_command(array)
                    self.device.spooler.send(self.job, prevent_duplicate=True)
            except (RuidaCommandError, IndexError):
                if self.channel:
                    self.channel(f"Process Failure: {str(bytes(array).hex())}")

    def _channel(self, text):
        if self.channel:
            self.channel(text)

    def _describe(self, array, desc):
        if self.channel:
            self.channel(f"--> {str(bytes(array).hex())}\t({desc})")

    def _respond(self, respond, desc=None):
        if respond is not None:
            self.msg_reply(respond, desc=desc)

    def _process_realtime(self, array):
        """
        Test whether the given command is realtime or interfacing code. Should return True if the job does not deal
        with the given command type.

        @param array:
        @return: If realtime or machine interfacing code.
        """
        if array[0] < 0x80:
            if self.channel:
                self.channel(f"NOT A COMMAND: {array[0]}")
            raise RuidaCommandError
        elif array[0] == 0xA5:
            # Interface key values. These are de facto realtime. Only seen in android app. UDP: 50207
            key = None
            if array[1] == 0x50:
                key = "Down"
            elif array[1] == 0x51:
                key = "Up"
            if array[1] == 0x53:
                if array[2] == 0x00:
                    self._describe(array, "Interface Frame")
            else:
                if array[2] == 0x02:
                    self._describe(array, f"Interface +X {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_right(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_right(False)
                        except AttributeError:
                            pass
                elif array[2] == 0x01:
                    self._describe(array, f"Interface -X {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_left(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_left(False)
                        except AttributeError:
                            pass
                if array[2] == 0x03:
                    self._describe(array, f"Interface +Y {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_top(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_top(False)
                        except AttributeError:
                            pass
                elif array[2] == 0x04:
                    self._describe(array, f"Interface -Y {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_bottom(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_bottom(False)
                        except AttributeError:
                            pass
                if array[2] == 0x0A:
                    self._describe(array, f"Interface +Z {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_plus_z(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_plus_z(False)
                        except AttributeError:
                            pass
                elif array[2] == 0x0B:
                    self._describe(array, f"Interface -Z {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_minus_z(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_minus_z(False)
                        except AttributeError:
                            pass
                if array[2] == 0x0C:
                    self._describe(array, f"Interface +U {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_plus_u(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_plus_u(False)
                        except AttributeError:
                            pass
                elif array[2] == 0x0D:
                    self._describe(array, f"Interface -U {key}")
                    if key == "Down":
                        try:
                            self.device.driver.move_minus_u(True)
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.move_minus_u(False)
                        except AttributeError:
                            pass
                elif array[2] == 0x05:
                    self._describe(array, f"Interface Pulse {key}")
                    if key == "Down":
                        try:
                            self.device.driver.laser_on()
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.laser_off()
                        except AttributeError:
                            pass
                elif array[2] == 0x11:
                    self._describe(array, "Interface Speed")
                elif array[2] == 0x06:
                    self._describe(array, "Interface Start/Pause")
                    try:
                        self.device.driver.pause()
                    except AttributeError:
                        pass
                elif array[2] == 0x09:
                    self._describe(array, "Interface Stop")
                    try:
                        self.device.driver.reset()
                    except AttributeError:
                        pass
                elif array[2] == 0x5A:
                    self._describe(array, "Interface Reset")
                elif array[2] == 0x0F:
                    self._describe(array, "Interface Trace On/Off")
                elif array[2] == 0x07:
                    self._describe(array, "Interface ESC")
                elif array[2] == 0x12:
                    self._describe(array, "Interface Laser Gate")
                elif array[2] == 0x08:
                    self._describe(array, "Interface Origin")
                    try:
                        self.device.driver.move_abs(0, 0)
                    except AttributeError:
                        pass
            return True
        elif array[0] == 0xCC:
            self._describe(array, "ACK from machine")
            return True
        elif array[0] == 0xCD:
            self._describe(array, "ERR from machine")
            return True
        elif array[0] == 0xCE:
            self._describe(array, "Keep Alive")
            return True
        elif array[0] == 0xD7:
            # END OF FILE.
            self.filename = None
            self.program_mode = False
            self._describe(array, "End Of File")
            return False
        elif array[0] == 0xD8:
            if array[1] == 0x00:
                self._describe(array, "Start Process")
                self.program_mode = True
                return False
            elif array[1] == 0x01:
                self._describe(array, "Stop Process")
                try:
                    self.device.driver.reset()
                    self.device.driver.home()
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x02:
                self._describe(array, "Pause Process")
                try:
                    self.device.driver.pause()
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x03:
                self._describe(array, "Restore Process")
                try:
                    self.device.driver.resume()
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x2C:
                self._describe(array, "Home Z")
                return True
            elif array[1] == 0x2D:
                self._describe(array, "Home U")
                return True
            elif array[1] == 0x2A:
                self._describe(array, "Home XY")
                try:
                    self.device.driver.home()
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x2E:
                self._describe(array, "FocusZ")
                return True
            elif array[1] == 0x20:
                self._describe(array, "KeyDown -X +Left")
                try:
                    self.device.driver.move_left(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x21:
                self._describe(array, "KeyDown +X +Right")
                try:
                    self.device.driver.move_right(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x22:
                self._describe(array, "KeyDown +Y +Top")
                try:
                    self.device.driver.move_top(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x23:
                self._describe(array, "KeyDown -Y +Bottom")
                try:
                    self.device.driver.move_down(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x24:
                self._describe(array, "KeyDown +Z")
                try:
                    self.device.driver.move_plus_z(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x25:
                self._describe(array, "KeyDown -Z")
                try:
                    self.device.driver.move_minus_z(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x26:
                self._describe(array, "KeyDown +U")
                try:
                    self.device.driver.move_plus_u(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x27:
                self._describe(array, "KeyDown -U")
                try:
                    self.device.driver.move_minus_u(True)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x28:
                self._describe(array, "KeyDown 0x21")
                return True
            elif array[1] == 0x30:
                self._describe(array, "KeyUp -X +Left")
                try:
                    self.device.driver.move_left(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x31:
                self._describe(array, "KeyUp +X +Right")
                try:
                    self.device.driver.move_right(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x32:
                self._describe(array, "KeyUp +Y +Top")
                try:
                    self.device.driver.move_top(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x33:
                self._describe(array, "KeyUp -Y +Bottom")
                try:
                    self.device.driver.move_down(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x34:
                self._describe(array, "KeyUp +Z")
                try:
                    self.device.driver.move_plus_z(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x35:
                try:
                    self.device.driver.move_minus_z(False)
                except AttributeError:
                    pass
                self._describe(array, "KeyUp -Z")
                return True
            elif array[1] == 0x36:
                self._describe(array, "KeyUp +U")
                try:
                    self.device.driver.move_plus_u(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x37:
                self._describe(array, "KeyUp -U")
                try:
                    self.device.driver.move_minus_u(False)
                except AttributeError:
                    pass
                return True
            elif array[1] == 0x38:
                self._describe(array, "KeyUp 0x20")
                return True
            elif array[1] == 0x39:
                self._describe(array, "Home A")
                return True
            elif array[1] == 0x3A:
                self._describe(array, "Home B")
                return True
            elif array[1] == 0x3B:
                self._describe(array, "Home C")
                return True
            elif array[1] == 0x3C:
                self._describe(array, "Home D")
                return True
            elif array[1] == 0x40:
                self._describe(array, "KeyDown 0x18")
                return True
            elif array[1] == 0x41:
                self._describe(array, "KeyDown 0x19")
                return True
            elif array[1] == 0x42:
                self._describe(array, "KeyDown 0x1A")
                return True
            elif array[1] == 0x43:
                self._describe(array, "KeyDown 0x1B")
                return True
            elif array[1] == 0x44:
                self._describe(array, "KeyDown 0x1C")
                return True
            elif array[1] == 0x45:
                self._describe(array, "KeyDown 0x1D")
                return True
            elif array[1] == 0x46:
                self._describe(array, "KeyDown 0x1E")
                return True
            elif array[1] == 0x47:
                self._describe(array, "KeyDown 0x1F")
                return True
            elif array[1] == 0x48:
                self._describe(array, "KeyUp 0x08")
                return True
            elif array[1] == 0x49:
                self._describe(array, "KeyUp 0x09")
                return True
            elif array[1] == 0x4A:
                self._describe(array, "KeyUp 0x0A")
                return True
            elif array[1] == 0x4B:
                self._describe(array, "KeyUp 0x0B")
                return True
            elif array[1] == 0x4C:
                self._describe(array, "KeyUp 0x0C")
                return True
            elif array[1] == 0x4D:
                self._describe(array, "KeyUp 0x0D")
                return True
            elif array[1] == 0x4E:
                self._describe(array, "KeyUp 0x0E")
                return True
            elif array[1] == 0x4F:
                self._describe(array, "KeyUp 0x0F")
                return True
            elif array[1] == 0x51:
                self._describe(array, "Inhale On/Off")
                return True
        elif array[0] == 0xD9:
            if len(array) == 1:
                self._describe(array, "Unknown Directional Setting")
            else:
                options = array[2]
                if options == 0x03:
                    param = "Light"
                elif options == 0x02:
                    param = ""
                elif options == 0x01:
                    param = "Light/Origin"
                else:  # options == 0x00:
                    param = "Origin"

                if array[1] == 0x00 or array[1] == 0x50:
                    coord = abscoord(array[3:8]) * self.scale
                    self._describe(
                        array, f"Move {param} X: {coord} ({self.x},{self.y})"
                    )
                    try:
                        self.device.driver.move_abs(self.x + coord, self.y)
                    except AttributeError:
                        pass
                elif array[1] == 0x01 or array[1] == 0x51:
                    coord = abscoord(array[3:8]) * self.scale
                    self._describe(
                        array, f"Move {param} Y: {coord} ({self.x},{self.y})"
                    )
                    try:
                        self.device.driver.move_abs(self.x, self.y + coord)
                    except AttributeError:
                        pass
                elif array[1] == 0x02 or array[1] == 0x52:
                    coord = abscoord(array[3:8])
                    self._describe(
                        array, f"Move {param} Z: {coord} ({self.x},{self.y})"
                    )
                    try:
                        self.device.driver.axis("z", coord)
                    except AttributeError:
                        pass
                elif array[1] == 0x03 or array[1] == 0x53:
                    coord = abscoord(array[3:8])
                    self._describe(
                        array, f"Move {param} U: {coord} ({self.x},{self.y})"
                    )
                    try:
                        self.device.driver.axis("u", self.u)
                    except AttributeError:
                        pass
                elif array[1] == 0x0F:
                    self._describe(array, "Feed Axis Move")
                elif array[1] == 0x10 or array[1] == 0x60:
                    x = abscoord(array[3:8]) * self.scale
                    y = abscoord(array[8:13]) * self.scale
                    self._describe(array, f"Move {param} XY ({x}, {y})")
                    if "Origin" in param:
                        try:
                            self.device.driver.move_abs(
                                f"{x / UNITS_PER_MM}mm",
                                f"{y / UNITS_PER_MM}mm",
                            )
                        except AttributeError:
                            pass
                    else:
                        try:
                            self.device.driver.home()
                        except AttributeError:
                            pass
                elif array[1] == 0x30 or array[1] == 0x70:
                    x = abscoord(array[3:8])
                    y = abscoord(array[8:13])
                    self.u = abscoord(array[13 : 13 + 5])
                    self._describe(
                        array,
                        f"Move {param} XYU: {x * UNITS_PER_uM} ({y * UNITS_PER_uM},{self.u * UNITS_PER_uM})",
                    )
                    try:
                        self.device.driver.move_abs(x * UNITS_PER_uM, y * UNITS_PER_uM)
                        self.device.driver.axis("u", self.u * UNITS_PER_uM)
                    except AttributeError:
                        pass
            return True
        elif array[0] == 0xDA:
            # DA commands are usually memory or system processing commands.

            mem = parse_mem(array[2:4])
            name, v = self.mem_lookup(mem)
            if array[1] == 0x00:
                if name is None:
                    name = "Unmapped"
                self._describe(
                    array,
                    f"Get {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name})",
                )
                if isinstance(v, int):
                    v = int(v)
                    vencode = encode32(v)
                    self._respond(
                        b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode),
                        desc=f"Respond {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {v} (0x{v:08x})",
                    )
                else:
                    vencode = v
                    self._respond(
                        b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode),
                        desc=f"Respond {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {str(vencode)}",
                    )
            elif array[1] == 0x01:
                value0 = array[4:9]
                value1 = array[9:14]
                v0 = decodeu35(value0)
                v1 = decodeu35(value1)
                self._describe(
                    array,
                    f"Set {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {v0} (0x{v0:08x}) {v1} (0x{v1:08x})",
                )
                # MEM SET. This is sometimes inside files to set things like declared filesize
                return False
            elif array[1] == 0x04:
                self._describe(array, "OEM On/Off, CardIO On/OFF")
            elif array[1] == 0x05 or array[1] == 0x54:
                self._describe(array, "Read Run Info")
                self._respond(b"\xda\x05" + b"\x00" * 20, desc="Read Run Response")
            elif array[1] == 0x06 or array[1] == 0x52:
                self._describe(array, "Unknown/System Time.")
            elif array[1] == 0x10 or array[1] == 0x53:
                self._describe(array, "Set System Time")
            elif array[1] == 0x30:
                # Property requested with select document, upload button "fresh property"
                filenumber = parse_filenumber(array[2:4])
                self._describe(array, f"Upload Info 0x30 Document {filenumber}")
                # Response Unverified
                self._respond(
                    b"\xda\x30" + b"\x00" * 20, desc="Upload Info Response 0x30"
                )
            elif array[1] == 0x31:
                # Property requested with select document, upload button "fresh property"
                filenumber = parse_filenumber(array[2:4])
                self._describe(array, f"Upload Info 0x31 Document {filenumber}")
                # Response Unverified
                self._respond(
                    b"\xda\x31" + b"\x00" * 20, desc="Upload Info Response 0x31"
                )
            elif array[1] == 0x60:
                # len: 14
                v = decode14(array[2:4])
                self._describe(array, f"RD-FUNCTION-UNK1 {v}")
            return True
        elif array[0] == 0xE5:  # 0xE502
            if len(array) == 1:
                self._describe(array, "Lightburn Swizzle Modulation E5")
                return True
            if array[1] == 0x00:
                # RDWorks File Upload
                filenumber = array[2]
                self._describe(array, f"Document Page Number {filenumber}")
                # Response Unverified
                self._respond(b"\xe5\x00" + b"\x00" * 20, desc="Document Page Response")
            if array[1] == 0x02:
                # len 3
                self._describe(array, "Document Data End")
            if array[1] == 0x03:
                self._describe(array, "Is TblCor Usable")
            if array[1] == 0x04:
                # Something check in data chunk write
                pass
            return True
        elif array[0] == 0xE7:
            # File Layout commands
            if array[1] == 0x01:
                self.filename = ""
                for a in array[2:]:
                    if a == 0x00:
                        break
                    self.filename += chr(a)
                self._describe(array, f"Filename: {self.filename}")
                # self._respond(b"\xe8\x02", desc="File Packet Ack")  # RESPONSE UNKNOWN
                if self.saving:
                    self.filestream = open(get_safe_path(f"{self.filename}.rd"), "wb")
                return True
        elif array[0] == 0xE8:
            # FILE INTERACTIONS
            if array[1] == 0x00:
                # e8 00 00 00 00 00
                v1 = parse_filenumber(array[2:4])
                v2 = parse_filenumber(array[4:6])
                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                if v1 == 0:
                    for f in files:
                        os.remove(f)
                    self._describe(array, "Delete All Documents")
                else:
                    name = files[v1 - 1]
                    os.remove(name)
                    self._describe(array, f"Delete Document {v1} {v2}")
            elif array[1] == 0x01:
                filenumber = parse_filenumber(array[2:4])
                self._describe(array, f"Document Name {filenumber}")
                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                name = files[filenumber - 1]
                name = os.path.split(name)[-1]
                name = name.split(".")[0]
                name = name.upper()[:8]
                self._respond(
                    bytes(array[:4]) + bytes(name, "utf8") + b"\00",
                    f"Document {filenumber} Named: {name}",
                )
            elif array[1] == 0x02:
                self.saving = True
                self._describe(array, "File transfer")
            elif array[1] == 0x03:
                filenumber = parse_filenumber(array[2:4])

                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                name = files[filenumber - 1]
                try:
                    with open(name, "rb") as f:
                        self.write(f.read())
                except OSError:
                    pass
                self._describe(array, f"Start Select Document {filenumber}")
            elif array[1] == 0x04:
                filenumber = parse_filenumber(array[2:4])
                self._describe(array, f"Calculate Document Time {filenumber}")
            return True
        return False

    def mem_lookup(self, mem) -> Tuple[str, Union[int, bytes]]:
        if mem == 0x0002:
            return "Laser Info", 0  #
        if mem == 0x0003:
            return "Machine Def", 0  #
        if mem == 0x0004:
            return "IOEnable", 0  # 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, bits
        if mem == 0x0005:
            return "G0 Velocity", 200000  # 200 mm/s
        if mem == 0x000B:
            return "Eng Facula", 800  # 80%
        if mem == 0x000C:
            return "Home Velocity", 20000  # 20mm/s
        if mem == 0x000E:
            return "Eng Vert Velocity", 100000  # 100 mm/s
        if mem == 0x0010:
            return "System Control Mode", 0
        if mem == 0x0011:
            return "Laser PWM Frequency 1", 0
        if mem == 0x0012:
            return "Laser Min Power 1", 0
        if mem == 0x0013:
            return "Laser Max Power 1", 0
        if mem == 0x0016:
            return "Laser Attenuation", 0
        if mem == 0x0017:
            return "Laser PWM Frequency 2", 0
        if mem == 0x0018:
            return "Laser Min Power 2", 0
        if mem == 0x0019:
            return "Laser Max Power 2", 0
        if mem == 0x001A:
            return "Laser Standby Frequency 1", 0
        if mem == 0x001B:
            return "Laser Standby Pulse 1", 0
        if mem == 0x001C:
            return "Laser Standby Frequency 2", 0
        if mem == 0x001D:
            return "Laser Standby Pulse 2", 0
        if mem == 0x001E:
            return "Auto Type Space", 0
        if mem == 0x001F:
            return "TriColor", 0
        if mem == 0x0020:
            return "Axis Control Para 1", 0x4000  # True
        if mem == 0x0021:
            return "Axis Precision 1", 0
        if mem == 0x0023:
            return "Axis Max Velocity 1", 0
        if mem == 0x0024:
            return "Axis Start Velocity 1", 0
        if mem == 0x0025:
            return "Axis Max Acc 1", 0
        if mem == 0x0026:
            return "Axis Range 1, Get Frame X", 320000
        if mem == 0x0027:
            return "Axis Btn Start Velocity 1", 0
        if mem == 0x0028:
            return "Axis Btn Acc 1", 0
        if mem == 0x0029:
            return "Axis Estp Acc 1", 0
        if mem == 0x002A:
            return "Axis Home Offset 1", 0
        if mem == 0x002B:
            return "Axis Backlash 1", 0  # 0mm

        if mem == 0x0030:
            return "Axis Control Para 2", 0x4000  # True
        if mem == 0x0031:
            return "Axis Precision 2", 0
        if mem == 0x0033:
            return "Axis Max Velocity 2", 0
        if mem == 0x0034:
            return "Axis Start Velocity 2", 0
        if mem == 0x0035:
            return "Axis Max Acc 2", 0
        if mem == 0x0036:
            return "Axis Range 2, Get Frame Y", 220000
        if mem == 0x0037:
            return "Axis Btn Start Velocity 2", 0
        if mem == 0x0038:
            return "Axis Btn Acc 2", 0
        if mem == 0x0039:
            return "Axis Estp Acc 2", 0
        if mem == 0x003A:
            return "Axis Home Offset 2", 0
        if mem == 0x003B:
            return "Axis Backlash 2", 0  # 0 mm

        if mem == 0x0040:
            return "Axis Control Para 3", 0  # False
        if mem == 0x0041:
            return "Axis Precision 3", 0
        if mem == 0x0043:
            return "Axis Max Velocity 3", 0
        if mem == 0x0044:
            return "Axis Start Velocity 3", 0
        if mem == 0x0045:
            return "Axis Max Acc 3", 0
        if mem == 0x0046:
            return "Axis Range 3, Get Frame Z", 0
        if mem == 0x0047:
            return "Axis Btn Start Velocity 3", 0
        if mem == 0x0048:
            return "Axis Btn Acc 3", 0
        if mem == 0x0049:
            return "Axis Estp Acc 3", 0
        if mem == 0x004A:
            return "Axis Home Offset 3", 0
        if mem == 0x004B:
            return "Axis Backlash 3", 0

        if mem == 0x0050:
            return "Axis Control Para 4", 0  # False
        if mem == 0x0051:
            return "Axis Precision 4", 0
        if mem == 0x0053:
            return "Axis Max Velocity 4", 0
        if mem == 0x0054:
            return "Axis Start Velocity 4", 0
        if mem == 0x0055:
            return "Axis Max Acc 4", 0
        if mem == 0x0056:
            return "Axis Range 4, Get Frame U", 0
        if mem == 0x0057:
            return "Axis Btn Start Velocity 4", 0
        if mem == 0x0058:
            return "Axis Btn Acc 4", 0
        if mem == 0x0059:
            return "Axis Estp Acc 4", 0
        if mem == 0x005A:
            return "Axis Home Offset 4", 0
        if mem == 0x005B:
            return "Axis Backlash 4", 0

        if mem == 0x0060:
            return "Machine Type", 0

        if mem == 0x0063:
            return "Laser Min Power 3", 0
        if mem == 0x0064:
            return "Laser Max Power 3", 0
        if mem == 0x0065:
            return "Laser PWM Frequency 3", 0
        if mem == 0x0066:
            return "Laser Standby Frequency 3", 0
        if mem == 0x0067:
            return "Laser Standby Pulse 3", 0

        if mem == 0x0068:
            return "Laser Min Power 4", 0
        if mem == 0x0069:
            return "Laser Max Power 4", 0
        if mem == 0x006A:
            return "Laser PWM Frequency 4", 0
        if mem == 0x006B:
            return "Laser Standby Frequency 4", 0
        if mem == 0x006C:
            return "Laser Standby Pulse 4", 0

        if mem == 0x006D:
            return "Laser Min Power 5", 0
        if mem == 0x006E:
            return "Laser Max Power 5", 0
        if mem == 0x006F:
            return "Laser PWM Frequency 5", 0
        if mem == 0x0070:
            return "Laser Standby Frequency 5", 0
        if mem == 0x0071:
            return "Laser Standby Pulse 5", 0

        if mem == 0x0072:
            return "Laser Min Power 6", 0
        if mem == 0x0073:
            return "Laser Max Power 6", 0
        if mem == 0x0074:
            return "Laser PWM Frequency 6", 0
        if mem == 0x0075:
            return "Laser Standby Frequency 6", 0
        if mem == 0x0076:
            return "Laser Standby Pulse 6", 0
        if mem == 0x0077:
            return "Auto Type Space 2", 0
        if mem == 0x0077:
            return "Auto Type Space 3", 0
        if mem == 0x0078:
            return "Auto Type Space 4", 0
        if mem == 0x0079:
            return "Auto Type Space 5", 0
        if mem == 0x007A:
            return "Auto Type Space 6", 0
        if mem == 0x0080:
            return "RD-UNKNOWN 2", 0
        if mem == 0x0090:
            return "RD-UNKNOWN 3", 0
        if mem == 0x00A0:
            return "RD-UNKNOWN 4", 0
        if mem == 0x00B0:
            return "RD-UNKNOWN 5", 0
        if mem == 0x0C0:
            return "Offset 8 Start", 0
        if mem == 0x0C1:
            return "Offset 8 End", 0
        if mem == 0x00C2:
            return "Offset 9 Start", 0
        if mem == 0x00C3:
            return "Offset 9 End", 0
        if mem == 0x00C4:
            return "Offset 10 Start", 0
        if mem == 0x00C5:
            return "Offset 10 End", 0
        if mem == 0x00C6:
            return "Offset 7 Start", 0
        if mem == 0x0C7:
            return "Offset 7 End", 0

        if mem == 0x00C8:
            return "Axis Home Velocity 1", 0
        if mem == 0x00C9:
            return "Axis Home Velocity 2", 0
        if mem == 0x00CA:
            return "Margin 1", 0
        if mem == 0x00CB:
            return "Margin 2", 0
        if mem == 0x00CC:
            return "Margin 3", 0
        if mem == 0x00CD:
            return "Margin 4", 0
        if mem == 0x00CE:
            return "VWheelRatio", 0
        if mem == 0x00CF:
            return "VPunchRatio", 0
        if mem == 0x00D8:
            return "VSlotRatio", 0
        if mem == 0x00D0:
            return "In Hale Zone", 0
        if mem == 0x00D9:
            return "VSlot Share Home Offset", 0
        if mem == 0x00DA:
            return "VPunch Share Home Offset", 0
        if mem == 0x00E7:
            return "VWheel Share Home Offset", 0
        if mem == 0x0100:
            return "System Settings", 0  # bits 2,2,1,1,1,1,1,1,1,1,1
        if mem == 0x0101:
            return "Turn Velocity", 20000  # 20 m/s
        if mem == 0x0102:
            return "Syn Acc", 3000000  # 3000 mm/s2
        if mem == 0x0103:
            return "G0 Delay", 0  # 0 ms
        if mem == 0x0104:
            return "Scan Step Factor", 0
        if mem == 0x0115:
            return "Dock Point X", 0
        if mem == 0x0116:
            return "Dock Point Y", 0
        if mem == 0x0105:
            return "User Para 5", 0
        if mem == 0x0107:
            return "Feed Delay After", 0  # 0 s
        if mem == 0x0108:
            return "User Key Fast Velocity", 0
        if mem == 0x0109:
            return "Turn Acc", 400000  # 400 mm/s
        if mem == 0x010A:
            return "G0 Acc", 3000000  # 3000 mm/s2
        if mem == 0x010B:
            return "Feed Delay Prior", 0  # 0 ms
        if mem == 0x010C:
            return "Manual Distance", 0
        if mem == 0x010D:
            return "Shut Down Delay", 0
        if mem == 0x010E:
            return "Focus Depth", 5000  # 5mm
        if mem == 0x010F:
            return "Go Scale Blank", 0  # 0 mm
        if mem == 0x0117:
            return "Array Feed Repay", 0  # 0mm
        if mem == 0x0117:
            return "Rotate On Delay", 0
        if mem == 0x0119:
            return "Rotate Off Delay", 0
        if mem == 0x011A:
            return "Acc Ratio", 100  # 100%
        if mem == 0x011B:
            return "Turn Ratio", 100  # 100% (speed factor)
        if mem == 0x011C:
            return "Acc G0 Ratio", 100  # 100%
        if mem == 0x011F:
            return "Rotate Pulse", 0
        if mem == 0x0121:
            return "Rotate D", 0
        if mem == 0x0122:
            return "Eng Facula Replay", 0
        if mem == 0x0124:
            return "X Min Eng Velocity", 10000  # 10mm/s
        if mem == 0x0125:
            return "X Eng Acc", 10000000  # 10000 m/s
        if mem == 0x0126:
            return "User Para 1", 0
        if mem == 0x0128:
            return "Z Home Velocity", 0
        if mem == 0x0129:
            return "Z Work Velocity", 0
        if mem == 0x012A:
            return "Z G0 Velocity", 0
        if mem == 0x012B:
            return "Union Home Distance", 0
        if mem == 0x012C:
            return "U Home Velocity", 0
        if mem == 0x012D:
            return "U Work Velocity", 0  # Axis Dock Position Other
        if mem == 0x012E:
            return "Feed Repay", 0
        if mem == 0x0131:
            return "Manual Fast Speed", 100000  # 100 mm/s
        if mem == 0x0132:
            return "Manual Slow Speed", 10000  # 10 mm/s
        if mem == 0x0134:
            return "Y Minimum Eng Velocity", 10000  # 10mm/s
        if mem == 0x0135:
            return "Y Eng Acc", 3000000  # 3000 mm/s
        if mem == 0x0137:
            return "Eng Acc Ratio", 100  # Engraving factor 100%
        if mem == 0x0138:
            return "Sts Ahead Time", 0
        if mem == 0x0139:
            return "Repeat Delay", 0
        if mem == 0x013B:
            return "User Para 3", 0
        if mem == 0x013D:
            return "User Para 2", 0
        if mem == 0x013F:
            return "User Para 4", 0  # Pressure Monitor Delay
        if mem == 0x0140:
            return "Axis Home Velocity 3", 0
        if mem == 0x0141:
            return "Axis Work Velocity 3", 0
        if mem == 0x0142:
            return "Axis Home Velocity 4", 0
        if mem == 0x0143:
            return "Axis Work Velocity 4", 0
        if mem == 0x0144:
            return "Axis Home Velocity 5", 0
        if mem == 0x0145:
            return "Axis Work Velocity 5", 0
        if mem == 0x0146:
            return "Axis Home Velocity 6", 0
        if mem == 0x0147:
            return "Axis Work Velocity 6", 0
        if mem == 0x0148:
            return "Axis Home Velocity 7", 0
        if mem == 0x0149:
            return "Axis Work Velocity 7", 0
        if mem == 0x014A:
            return "Axis Home Velocity 8", 0
        if mem == 0x014B:
            return "Axis Work Velocity 8", 0
        if mem == 0x014C:
            return "Laser Reset Time", 0
        if mem == 0x014D:
            return "Laser Start Distance", 0
        if mem == 0x014E:
            return "Z Pen Up Pos", 0  # units 0.001
        if mem == 0x014F:
            return "Z Pen Down Pos", 0  # units 0.001
        if mem == 0x0150:
            return "Offset 1 Start", 0
        if mem == 0x0151:
            return "Offset 1 End", 0
        if mem == 0x0152:
            return "Offset 2 Start", 0
        if mem == 0x0153:
            return "Offset 2 End", 0
        if mem == 0x0154:
            return "Offset 3 Start", 0
        if mem == 0x0155:
            return "Offset 3 End", 0
        if mem == 0x0156:
            return "Offset 6 Start", 0
        if mem == 0x0157:
            return "Offset 6 End", 0
        if mem == 0x0158:
            return "Offset 4 Start", 0
        if mem == 0x0159:
            return "Offset 4 End", 0
        if mem == 0x015A:
            return "Offset 5 Start", 0
        if mem == 0x015B:
            return "Offset 5 End", 0
        if mem == 0x15C:
            return "Delay 6 On", 0
        if mem == 0x15D:
            return "Delay 6 Off", 0
        if mem == 0x15E:
            return "Delay 7 On", 0
        if mem == 0x15F:
            return "Delay 7 Off", 0
        if mem == 0x0160:
            return "Inhale On Delay", 0  # Delay 8
        if mem == 0x0161:
            return "Inhale Off Delay", 0  # Delay 8
        if mem == 0x162:
            return "Delay 5 On", 0
        if mem == 0x163:
            return "Delay 5 Off", 0
        if mem == 0x164:
            return "Delay 2 On", 0
        if mem == 0x165:
            return "Delay 2 Off", 0
        if mem == 0x0166:
            return "VSample Distance", 0
        if mem == 0x016D:
            return "VUp Angle", 0
        if mem == 0x016E:
            return "VRotatePulse", 0
        if mem == 0x177:
            return "Delay 9 On", 0
        if mem == 0x178:
            return "Delay 9 Off", 0
        if mem == 0x0169:
            return "Offset 11 Start", 0
        if mem == 0x016A:
            return "Offset 11 End", 0
        if mem == 0x16B:
            return "Tool Up Pos 4", 0
        if mem == 0x16C:
            return "Tool Down Pos 4", 0
        if mem == 0x170:
            return "Delay 1 On", 0
        if mem == 0x171:
            return "VCorner Precision", 0
        if mem == 0x172:
            return "Delay 3 On", 0
        if mem == 0x173:
            return "Delay 4 Off", 0
        if mem == 0x174:
            return "Delay 4 On", 0
        if mem == 0x175:
            return "Delay 1 Off", 0
        if mem == 0x176:
            return "Delay 3 Off", 0
        if mem == 0x0177:
            return "Idle Long Distance", 0
        if mem == 0x178:
            return "Tool Up Pos 3", 0
        if mem == 0x179:
            return "Tool Down Pos 3", 0
        if mem == 0x17A:
            return "Tool Up Pos 2", 0
        if mem == 0x17B:
            return "Tool Down Pos 2", 0
        if mem == 0x017C:
            return "Punch Rotate Delay", 0
        if mem == 0x017D:
            return "VSlot Angle", 0
        if mem == 0x017F:
            return "Tool Up Delay", 0
        if mem == 0x017E:
            return "VTool Rotate Limit", 0
        if mem == 0x0180:
            return "Card Language", 0
        if 0x181 <= mem <= 0x187:
            return f"PC Lock {mem - 0x181}", 0
        if mem == 0x0188:
            return "User Key Slow Velocity", 0
        if mem == 0x0189:
            return "MachineID 2", 0
        if mem == 0x018A:
            return "MachineID 3", 0
        if mem == 0x018B:
            return "MachineID 4", 0
        if mem == 0x018C:
            return "Blow On Delay", 0
        if mem == 0x018D:
            return "Blow Off Delay", 0
        if mem == 0x018F:
            return "User Para 6, Blower", 0
        if mem == 0x0190:
            return "Jet Time", 0
        if mem == 0x0190:
            return "Color Mark Head Max Distance", 0
        if mem == 0x0191:
            return "Color Mark Head Distance", 0
        if mem == 0x0192:
            return "Color Mark Mark Distance", 0
        if mem == 0x0193:
            return "Color Mark Camera Distance", 0  # JetOffset = 0x193 to 0x194
        if mem == 0x0194:
            return "Color Mark Sensor Offset2", 0
        if mem == 0x0195:
            return "Cylinder Down Delay", 0
        if mem == 0x0196:
            return "Cylinder Up Delay", 0
        if mem == 0x0197:
            return "Press Down Delay", 0
        if mem == 0x0198:
            return "Press Up Delay", 0
        if mem == 0x0199:
            return "Drop Position Start", 0
        if mem == 0x019A:
            return "Drop Position End", 0
        if mem == 0x019B:
            return "Drop Interval", 0
        if mem == 0x019C:
            return "Drop Time", 0
        if mem == 0x019D:
            return "Sharpen Delay On", 0
        if mem == 0x019E:
            return "Sharpen Delay Off", 0
        if mem == 0x019F:
            return "Sharpen Time Limit", 0
        if mem == 0x01A0:
            return "Sharpen Travel Limit", 0
        if mem == 0x01A1:
            return "Work End Time", 0
        if mem == 0x01A2:
            return "Color Mark Offset", 0
        if mem == 0x01A3:
            return "Color Mark Count", 0
        if mem == 0x01A4:
            return "Wheel Press Compensation", 0  # Protect IO Status
        if mem == 0x01A5:
            return "Color Mark Filter Length", 0
        if mem == 0x01A6:
            return "VBlow Back On Delay", 0
        if mem == 0x01A7:
            return "VBlow Back Off Delay", 0
        if mem == 0x01AC:
            return "Y U Safe Distance", 0
        if mem == 0x01AD:
            return "Y U Home Distance", 0
        if mem == 0x01AE:
            return "VTool Preset Position X", 0
        if mem == 0x01AF:
            return "VTool Preset Position Y", 0
        if mem == 0x01B1:
            return "VTool Preset Compensation", 0
        if mem == 0x01B2:
            return "VTool Preset Cur Depth", 0
        if mem == 0x0200:
            # 22 ok, 23 paused. 21 running.
            pos, state, minor = self.device.driver.status()
            if state == "idle":
                return "Machine Status", 22
            if state == "hold":
                return "Machine Status", 23
            if state == "busy":
                return "Machine Status", 21
            return "Machine Status", 22
        if mem == 0x0201:
            return "Total Open Time (s)", 0
        if mem == 0x0202:
            return "Total Work Time (s)", 0
        if mem == 0x0203:
            return "Total Work Number", 0
        if mem == 0x0205:
            from glob import glob
            from os.path import join, realpath

            files = [name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))]
            v = len(files)
            return "Total Doc Number", v
        if mem == 0x0206:
            from os.path import realpath
            from shutil import disk_usage

            total, used, free = disk_usage(realpath(get_safe_path(".")))
            v = min(total, 100000000)  # Max 100 megs.
            return "Flash Space", v
        if mem == 0x0207:
            from os.path import realpath
            from shutil import disk_usage

            total, used, free = disk_usage(realpath(get_safe_path(".")))
            v = min(free, 100000000)  # Max 100 megs.
            return "Flash Space", v
        if mem == 0x0208:
            return "Previous Work Time", 0
        if mem == 0x0211:
            return "Total Laser Work Time", 0
        if mem == 0x0212:
            return "File Custom Flag / Feed Info", 0
        if mem == 0x0217:
            return "Total Laser Work Time 2", 0
        if mem == 0x0218:
            # OEM PULSE ENERGY
            return "Total Laser Work Time 3", 0
        if mem == 0x0219:
            # OEM SET CURRENT
            return "Total Laser Work Time 4", 0
        if mem == 0x021A:
            # OEM SET FREQUENCY
            return "Total Laser Work Time 5", 0
        if mem == 0x021F:
            return "Ring Number", 0
        if mem == 0x0221:
            pos, state, minor = self.device.driver.status()
            x, y = self.units_to_device_matrix.point_in_inverse_space(pos)
            x /= UNITS_PER_uM
            return "Axis Preferred Position 1, Pos X", int(x)
        if mem == 0x0223:
            return "X Total Travel (m)", 0
        if mem == 0x0224:
            return "Position Point 0", 0
        if mem == 0x0231:
            pos, state, minor = self.device.driver.status()
            x, y = self.units_to_device_matrix.point_in_inverse_space(pos)
            y /= UNITS_PER_uM
            return "Axis Preferred Position 2, Pos Y", int(y)
        if mem == 0x0233:
            return "Y Total Travel (m)", 0
        if mem == 0x0234:
            return "Position Point 1", 0
        if mem == 0x0241:
            pos, state, minor = self.device.driver.status()
            if len(pos) >= 3:
                z = pos[2]
            else:
                z = self.job.z
            return "Axis Preferred Position 3, Pos Z", int(z)
        if mem == 0x0243:
            return "Z Total Travel (m)", 0
        if mem == 0x0251:
            return "Axis Preferred Position 4, Pos U", int(self.job.u)
        if mem == 0x0253:
            return "U Total Travel (m)", 0
        if mem == 0x025A:
            return "Axis Preferred Position 5, Pos A", int(self.job.a)
        if mem == 0x025B:
            return "Axis Preferred Position 6, Pos B", int(self.job.b)
        if mem == 0x025C:
            return "Axis Preferred Position 7, Pos C", int(self.job.c)
        if mem == 0x025D:
            return "Axis Preferred Position 8, Pos D", int(self.job.d)
        if mem == 0x0260:
            return "DocumentWorkNum", 0
        if 0x0261 <= mem < 0x02C4:
            # Unsure if this is where the document numbers end.
            return "Document Number", mem - 0x260
        if mem == 0x02C4:
            return "Read Scan Backlash Flag", 0
        if mem == 0x02C5:
            return "Read Scan Backlash 1", 0
        if mem == 0x02D5:
            return "Read Scan Backlash 2", 0
        if mem == 0x02FE:
            return "Card ID", 0x65006500  # RDC6442G
        if mem == 0x02FF:
            return "Mainboard Version", b"MEERK40T\x00"
        if mem == 0x0313:
            return "Material Thickness", 0
        if mem == 0x031C:
            return "File Fault", 0  # Error counter.
        if mem == 0x0320:
            return "File Total Length", 0
        if mem == 0x0321:
            return "File Progress Len", 0
        if mem == 0x033B:
            return "Read Process Feed Length", 0
        if mem == 0x0340:
            return "Stop Time", 0
        if 0x0391 <= mem < 0x0420:
            return f"Time for File {mem - 0x00390} to Run", 100
        if mem == 0x0591:
            return "Card Lock", 0  # 0x55aaaa55
        if mem == 0x05C0:
            return "Laser Life", 0
        if 0x05C0 <= mem < 0x600:
            pass
        return "Unknown", 0

    def unswizzle(self, data):
        return bytes([self.lut_unswizzle[b] for b in data])

    def swizzle(self, data):
        return bytes([self.lut_swizzle[b] for b in data])
