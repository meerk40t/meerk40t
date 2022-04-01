from ...core.cutcode import CutCode, LaserSettings, RawCut
from ...kernel import Module
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed


class LhystudiosEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.context.setting(bool, "fix_speeds", False)

        self.parser = LhystudiosParser()
        self.parser.fix_speeds = self.context.fix_speeds
        self.parser.channel = self.context.channel("lhy")

        def pos(p):
            if p is None:
                return
            x0, y0, x1, y1 = p
            self.context.signal("emulator;position", (x0, y0, x1, y1))

        self.parser.position = pos

    def __repr__(self):
        return "LhystudiosEmulator(%s)" % self.name

    def initialize(self, *args, **kwargs):
        context = self.context
        active = self.context.root.active
        send = context.channel("%s/usb_send" % active)
        send.watch(self.parser.write_packet)

    def finalize(self, *args, **kwargs):
        context = self.context
        active = self.context.root.active
        send = context.channel("%s/usb_send" % active)
        send.unwatch(self.parser.write_packet)


class LhystudiosParser:
    """
    LhystudiosParser parses LHYMicro-GL code with a state diagram. This should accurately reconstruct the values.
    When the position is changed it calls a self.position() function if one exists.
    """

    def __init__(self):
        self.channel = None
        self.position = None
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = LaserSettings(speed=20.0, power=1000.0)

        self.small_jump = True
        self.speed_code = None

        self.x = 0.0
        self.y = 0.0
        self.number_value = ""
        self.distance_x = 0
        self.distance_y = 0

        self.filename = ""

        self.laser = 0
        self.left = False
        self.top = False
        self.x_on = False
        self.y_on = False
        self.returning_compact = True
        self.returning_finished = False

        self.paused_state = False
        self.compact_state = False
        self.finish_state = False
        self.horizontal_major = False
        self.fix_speeds = False

    @property
    def program_mode(self):
        return self.compact_state

    @property
    def default_mode(self):
        return not self.compact_state

    @property
    def raster_mode(self):
        return self.settings.raster_step != 0

    def new_file(self):
        self.header_skipped = False
        self.count_flag = 0
        self.count_lines = 0

    @staticmethod
    def remove_header(data):
        count_lines = 0
        count_flag = 0
        for i in range(len(data)):
            b = data[i]
            c = chr(b)
            if c == "\n":
                count_lines += 1
            elif c == "%":
                count_flag += 1
            if count_lines >= 3 and count_flag >= 5:
                return data[i:]

    def header_write(self, data):
        """
        Write data to the emulator including the header. This is intended for saved .egv files which include a default
        header.
        """
        if self.header_skipped:
            self.write(data)
        else:
            data = LhystudiosParser.remove_header(data)
            self.write(data)

    def append_distance(self, amount):
        if self.x_on:
            self.distance_x += amount
        if self.y_on:
            self.distance_y += amount

    def write_packet(self, packet):
        self.write(packet[1:31])

    def write(self, data):
        for b in data:
            c = chr(b)
            if c == "I":
                self.process = self.process
                continue
            self.process(b, c)

    def process(self, b, c):
        if self.finish_state:
            # In finished all commands are black holed
            return

        # Not processing number distance or finish.
        if self.compact_state:
            # Every command in compact state executes distances.
            self.execute_distance()

        if ord("0") <= b <= ord("9"):
            self.number_value += c
        elif c == "|":
            self.append_distance(25)
            self.small_jump = True
        elif ord("a") <= b <= ord("y"):
            self.append_distance(b + 1 - ord("a"))
            self.small_jump = False
        elif c == "z":
            self.append_distance(26 if self.small_jump else 255)
            self.small_jump = False
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Right")
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Left")
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Bottom")
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Top")
        elif c == "U":
            self.laser = 0
            if self.channel:
                self.channel("Laser Off")
        elif c == "D":
            self.laser = 1
            if self.channel:
                self.channel("Laser On")
        elif c == "F":
            if self.channel:
                self.channel("Finish")
            self.returning_compact = False
            self.returning_finished = True
        elif c == "@":
            if self.channel:
                self.channel("Reset")
            self.returning_compact = False
        elif c in "C":
            if self.channel:
                self.channel("Speedcode")
            self.speed_code = ""
            self.process = self.process_speed_characters
            self.process(b, c)
            return
        elif c in "V":
            if c in "GCV01234567890":
                self.speed_code += c
                return
            speed = LaserSpeed(
                self.speed_code, board=self.board, fix_speeds=self.fix_speeds
            )
            self.settings.raster_step = speed.raster_step
            self.settings.speed = speed.speed
            if self.channel:
                self.channel("Setting Speed: %f" % self.settings.speed)
            self.speed_code = None
        elif c in "G":
            pass
        elif c == "S":
            self.laser = 0
            self.execute_distance()
            if self.channel:
                self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            if c in "S012":
                if c == "1":
                    self.horizontal_major = self.x_on
                    if self.channel:
                        self.channel("Setting Axis.")
                return
            self.laser = 0
            if self.channel:
                self.channel("Execute State")
            self.process = self.state_execute
            self.process(b, c)

        elif c == "P":
            if self.channel:
                self.channel("Pause")
            self.laser = 0
            if self.paused_state:
                # Home sequence triggered by 2 F commands in the same packet.
                if self.position:
                    self.position((self.x, self.y, 0, 0))
                self.x = 0
                self.y = 0
                self.distance_y = 0
                self.distance_x = 0
                self.finish_state = True
                self.paused_state = False
            else:
                self.execute_distance()  # distance is executed by a P command
                self.paused_state = True
        elif c == "N":
            if self.channel:
                self.channel("N")
            self.execute_distance()  # distance is executed by an N command.
            self.laser = 0
            self.compact_state = False

            if self.position:
                self.position(None)
            self.process(b, c)
        elif c == "M":
            self.x_on = True
            self.y_on = True
            if self.channel:
                a = "Top" if self.top else "Bottom"
                b = "Left" if self.left else "Right"
                self.channel("Diagonal %s %s" % (a, b))

    def state_reset(self, b, c):
        if c in "@NSE":
            return
        else:
            self.process = self.process
            self.process(b, c)


    def state_pause(self, b, c):
        if c in "NF":
            return
        if c == "P":
            self.process = self.state_resume
        else:
            self.process = self.state_compact
            self.process(b, c)

    def state_resume(self, b, c):
        if c in "NF":
            return
        self.process = self.state_compact
        self.process(b, c)

    def state_pad(self, b, c):
        if c == "F":
            return

    def state_execute(self, b, c):
        if self.returning_compact:
            self.process = self.state_compact
        else:
            self.process = self.process
        self.returning_compact = False


    def execute_distance(self):
        if self.distance_x != 0 or self.distance_y != 0:
            dx = self.distance_x
            dy = self.distance_y
            if self.left:
                dx = -dx
            if self.top:
                dy = -dy
            self.distance_x = 0
            self.distance_y = 0

            ox = self.x
            oy = self.y

            self.x += dx
            self.y += dy

            if self.position:
                self.position((ox, oy, self.x, self.y))

            if self.channel:
                self.channel("Moving (%d %d) now at %d %d" % (dx, dy, self.x, self.y))


class EGVBlob:
    def __init__(self, data: bytearray, name=None):
        self.name = name
        self.data = data
        self.operation = "blob"
        self._cutcode = None
        self._cut = None

    def __repr__(self):
        return "EGV(%s, %d bytes)" % (self.name, len(self.data))

    def as_cutobjects(self):
        parser = LhystudiosParser()
        self._cutcode = CutCode()
        self._cut = RawCut()

        def new_cut():
            if self._cut is not None and len(self._cut):
                self._cutcode.append(self._cut)
            self._cut = RawCut()
            self._cut.settings = LaserSettings(parser.settings)

        def position(p):
            if p is None or self._cut is None:
                new_cut()
                return

            from_x, from_y, to_x, to_y = p

            if parser.program_mode:
                if len(self._cut.plot) == 0:
                    self._cut.plot_append(int(from_x), int(from_y), parser.laser)
                self._cut.plot_append(int(to_x), int(to_y), parser.laser)
            else:
                new_cut()

        parser.position = position
        parser.header_write(self.data)

        cutcode = self._cutcode
        self._cut = None
        self._cutcode = None
        return cutcode

    def generate(self):
        yield COMMAND_BLOB, "egv", LhystudiosParser.remove_header(self.data)


class EgvLoader:
    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            blob = EGVBlob(bytearray(f.read()), basename)
            op_branch = elements_modifier.get(type="branch ops")
            op_branch.add(blob, type="blob")
            kernel.root.close(basename)
        return True
