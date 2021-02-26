from ...core.cutcode import CutCode, LaserSettings
from ...kernel import Module
from ..lasercommandconstants import *
from .laserspeed import LaserSpeed


class LhystudioEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = LaserSettings()
        self.cutcode = CutCode()

        self.small_jump = True
        self.speed_code = None

        self.x = 0.0
        self.y = 0.0
        self.number_value = None
        self.distance_x = 0
        self.distance_y = 0

        self.filename = ""

        self.left = False
        self.top = False
        self.x_on = False
        self.y_on = False
        self.horizontal_major = False
        self.context.setting(bool, "fix_speeds", False)
        self.process = self.state_default

        send = context.channel("pipe/usb_send")
        send.watch(self.write_packet)

        self.channel = self.context.channel("lhy")

    def __repr__(self):
        return "LhystudioEmulator(%s, %d cuts)" % (self.name, len(self.cutcode))

    def generate(self):
        for cutobject in self.cutcode:
            yield COMMAND_PLOT, cutobject
        yield COMMAND_PLOT_START

    def new_file(self):
        self.header_skipped = False
        self.count_flag = 0
        self.count_lines = 0

    def header_write(self, data):
        if self.header_skipped:
            self.write(data)
        for i in range(len(data)):
            c = data[i]
            if c == b"\n":
                self.count_lines += 1
            elif c == b"%":
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
            self.context.signal("interpreter;position", (self.x, self.y, 0, 0))
            self.x = 0
            self.y = 0
            self.process = self.state_default
            return
        elif c == "F":
            return
        else:
            self.channel("Finish State Unknown: %s" % c)

    def state_speed(self, b, c):
        if c in "GCV01234567890":
            self.speed_code += c
            return
        speed = LaserSpeed(self.speed_code, fix_speeds=self.context.fix_speeds)
        self.settings.steps = speed.raster_step
        self.settings.speed = speed.speed
        self.channel("Setting Speed: %f" % self.settings.speed)
        self.speed_code = None

        self.process = self.state_default
        self.process(b, c)

    def state_switch(self, b, c):
        if c in "S012":
            if c == "1":
                self.horizontal_major = self.x_on
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

            self.context.signal(
                "interpreter;position", (self.x, self.y, self.x + dx, self.y + dy)
            )
            self.x += dx
            self.y += dy
            self.channel("Moving (%d %d) now at %d %d" % (dx, dy, self.x, self.y))

    def state_compact(self, b, c):
        if self.state_distance(b, c):
            return
        self.execute_distance()

        if c == "F":
            self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "@":
            self.channel("Reset")
            self.process = self.state_reset
            self.process(b, c)
            return
        elif c == "P":
            self.channel("Pause")
            self.process = self.state_pause
        elif c == "N":
            self.channel("Jog")
            self.process = self.state_jog
            self.process(b, c)
        elif c == "S":
            self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.channel("Compact-Compact")
            self.process = self.state_execute
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True
        elif c == "M":
            self.x_on = True
            self.y_on = True

    def state_default(self, b, c):
        if self.state_distance(b, c):
            return

        # Execute Commands.
        if c == "N":
            self.execute_distance()
        elif c == "F":
            self.channel("Finish")
            self.process = self.state_finish
            self.process(b, c)
            return
        elif c == "P":
            self.channel("Popping")
            self.process = self.state_pop
            return
        elif c in "CVG":
            self.channel("Speedcode")
            self.speed_code = ""
            self.process = self.state_speed
            self.process(b, c)
            return
        elif c == "S":
            self.execute_distance()
            self.channel("Switch")
            self.process = self.state_switch
            self.process(b, c)
        elif c == "E":
            self.channel("Compact")
            self.process = self.state_execute
            self.process(b, c)
        elif c == "B":
            self.left = False
            self.x_on = True
            self.y_on = False
        elif c == "T":
            self.left = True
            self.x_on = True
            self.y_on = False
        elif c == "R":
            self.top = False
            self.x_on = False
            self.y_on = True
        elif c == "L":
            self.top = True
            self.x_on = False
            self.y_on = True


class EgvLoader:
    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            lhymicroemulator = kernel.get_context("/").open_as(
                "module/LhystudiosEmulator", basename
            )
            lhymicroemulator.write_header(f.read())
            return [lhymicroemulator.cutcode], None, None, pathname, basename
