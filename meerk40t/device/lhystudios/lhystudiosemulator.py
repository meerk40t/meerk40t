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

        def pos(x0, y0, x1, y1):
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
    def __init__(self):
        self.channel = None
        self.position = None
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = LaserSettings(speed=20.0, power=1000.0)
        self.cutcode = CutCode()
        self.cut = None

        self.small_jump = True
        self.speed_code = None

        self.x = 0.0
        self.y = 0.0
        self.number_value = None
        self.distance_x = 0
        self.distance_y = 0

        self.filename = ""

        self.laser = 0
        self.left = False
        self.top = False
        self.x_on = False
        self.y_on = False
        self.horizontal_major = False
        self.fix_speeds = False
        self.process = self.state_default

    @property
    def program_mode(self):
        return self.process == self.state_compact

    @property
    def default_mode(self):
        return self.process is self.state_default

    @property
    def raster_mode(self):
        return self.settings.raster_step != 0

    def new_cut(self):
        if self.cut is not None and len(self.cut):
            self.cutcode.append(self.cut)
        self.cut = RawCut()
        self.cut.settings = LaserSettings(self.settings)

    def new_file(self):
        self.header_skipped = False
        self.count_flag = 0
        self.count_lines = 0

    def header_write(self, data):
        """
        Write data to the emulator including the header. This is intended for saved .egv files which include a default
        header.
        """
        if self.header_skipped:
            self.write(data)
        for i in range(len(data)):
            b = data[i]
            c = chr(b)
            if c == "\n":
                self.count_lines += 1
            elif c == "%":
                self.count_flag += 1

            if self.count_lines >= 3 and self.count_flag >= 5:
                self.header_skipped = True
                self.write(data[i:])
                break

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
                self.process = self.state_default
                continue
            self.process(b, c)

    def state_finish(self, b, c):
        if c in "NSEF":
            return
        if self.channel:
            self.channel("Finish State Unknown: %s" % c)

    def state_reset(self, b, c):
        if c in "@NSE":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_jog(self, b, c):
        if c in "N":
            return
        else:
            self.process = self.state_default
            self.process(b, c)

    def state_pop(self, b, c):
        if c == "P":
            # Home sequence triggered.
            if self.position:
                self.position((self.x, self.y, 0, 0))
            self.x = 0
            self.y = 0
            self.laser = 0
            self.process = self.state_default
            return
        elif c == "F":
            return
        else:
            if self.channel:
                self.channel("Finish State Unknown: %s" % c)

    def state_speed(self, b, c):
        if c in "GCV01234567890":
            self.speed_code += c
            return
        speed = LaserSpeed(self.speed_code, board=self.board, fix_speeds=self.fix_speeds)
        self.settings.steps = speed.raster_step
        self.settings.speed = speed.speed
        if self.channel:
            self.channel("Setting Speed: %f" % self.settings.speed)
        self.speed_code = None

        self.process = self.state_default
        self.process(b, c)

    def state_switch(self, b, c):
        if c in "S012":
            if c == "1":
                self.horizontal_major = self.x_on
                if self.channel:
                    self.channel("Setting Axis.")
            return
        self.process = self.state_default
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
        self.process = self.state_compact

    def state_distance(self, b, c):
        if c == "|":
            self.append_distance(25)
            self.small_jump = True
            return True
        elif ord("0") <= b <= ord("9"):
            if self.number_value is None:
                self.number_value = c
            else:
                self.number_value += c
            if len(self.number_value) >= 3:
                self.append_distance(int(self.number_value))
                self.number_value = None
            return True
        elif ord("a") <= b <= ord("y"):
            self.append_distance(b + 1 - ord("a"))
        elif c == "z":
            self.append_distance(26 if self.small_jump else 255)
        else:
            self.small_jump = False
            return False
        self.small_jump = False
        return True

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

    def state_compact(self, b, c):
        if self.state_distance(b, c):
            return
        self.execute_distance()

        if c == "F":
            self.laser = 0
            if self.channel:
                self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "@":
            self.laser = 0
            if self.channel:
                self.channel("Reset")
            self.process = self.state_reset
            self.process(b, c)
            return
        elif c == "P":
            self.laser = 0
            if self.channel:
                self.channel("Pause")
            self.process = self.state_pause
        elif c == "N":
            if self.channel:
                self.channel("Jog")
            self.process = self.state_jog
            if self.position:
                self.position(None)
            self.process(b, c)
        elif c == "S":
            self.laser = 0
            if self.channel:
                self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.laser = 0
            if self.channel:
                self.channel("Compact-Compact")
            self.process = self.state_execute
            if self.position:
                self.position(None)
            self.process(b, c)
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
        elif c == "M":
            self.x_on = True
            self.y_on = True
            if self.channel:
                a = "Top" if self.top else "Bottom"
                b = "Left" if self.left else "Right"
                self.channel("Diagonal %s %s" % (a, b))
        elif c == "U":
            self.laser = 0
        elif c == "D":
            self.laser = 1

    def state_default(self, b, c):
        if self.state_distance(b, c):
            return

        # Execute Commands.
        if c == "N":
            self.execute_distance()
        elif c == "F":
            if self.channel:
                self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "P":
            if self.channel:
                self.channel("Popping")
            self.process = self.state_pop
            return
        elif c in "CVG":
            if self.channel:
                self.channel("Speedcode")
            self.speed_code = ""
            self.process = self.state_speed
            self.process(b, c)
            return
        elif c == "S":
            self.execute_distance()
            if self.channel:
                self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            if self.channel:
                self.channel("Compact")
            self.process = self.state_execute
            self.process(b, c)
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


class EGVBlob:
    def __init__(self, data: bytearray, name=None):
        self.name = name
        self.data = data
        self.operation = "blob"

    def __repr__(self):
        return "EGV(%s, %d bytes)" % (self.name, len(self.data))

    def as_cutobjects(self):
        parser = LhystudiosParser()

        def position(p):
            if p is None or parser.cut is None:
                parser.new_cut()
                return

            from_x, from_y, to_x, to_y = p

            if parser.program_mode:
                if len(parser.cut.plot) == 0:
                    parser.cut.plot_append(int(from_x), int(from_y), parser.laser)
                parser.cut.plot_append(int(to_x), int(to_y), parser.laser)
            else:
                parser.new_cut()
        parser.position = position
        parser.header_write(self.data)
        return parser.cutcode


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
