from meerk40t.core.cutcode import CutCode, RawCut
from meerk40t.core.parameters import Parameters
from meerk40t.svgelements import Color
from meerk40t.core.units import UNITS_PER_MIL


class LihuiyuParser:
    """
    LihuiyuParser parses LHYMicro-GL code with a state diagram. This should accurately reconstruct the values.
    When the position is changed it calls a self.position() function if one exists.
    """

    def __init__(self):
        self.channel = None
        self.position = None
        self.board = "M2"
        self.header_skipped = False
        self.count_lines = 0
        self.count_flag = 0
        self.settings = Parameters({"speed": 20.0, "power": 1000.0})

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
        self.small_jump = False
        self.returning_compact = True
        self.returning_finished = False

        self.mode = None
        self.raster_step = 0
        self.paused_state = False
        self.compact_state = False
        self.finish_state = False
        self.horizontal_major = False
        self.fix_speeds = False
        self.number_consumer = {}

    def parse(self, data, elements):
        from meerk40t.numpath import Numpath
        self.path = Numpath()

        def position(p):
            if p is None:
                return
            from_x, from_y, to_x, to_y = p

            if self.program_mode:
                if self.laser:
                    self.path.line(complex(from_x, from_y), complex(to_x, to_y))

        self.position = position
        self.write(data)
        self.path.uscale(UNITS_PER_MIL)
        elements.elem_branch.add(
            type="elem numpath",
            path=self.path,
            stroke=Color("black"),
            **self.settings.settings,
        )
        elements.signal("refresh_scene", 0)

    @property
    def program_mode(self):
        return self.compact_state

    @property
    def default_mode(self):
        return not self.compact_state

    @property
    def raster_mode(self):
        return self.settings.settings.get("raster_step", 0) != 0

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
            data = LihuiyuParser.remove_header(data)
            self.write(data)

    def write_packet(self, packet):
        self.write(packet[1:31])

    def write(self, data):
        for b in data:
            self.process(b, chr(b))

    def distance_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            self.append_distance(int(self.number_value))
            self.number_value = ""

    def speedcode_b1_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Speedcode B1 = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.speedcode_b2_consumer

    def speedcode_b2_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Speedcode B2 = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.speedcode_accel_consumer

    def speedcode_accel_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 1:
            if self.channel:
                self.channel(f"Speedcode Accel = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.speedcode_mult_consumer

    def speedcode_mult_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Speedcode Accel = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.speedcode_dratio_b1_consumer

    def speedcode_dratio_b1_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Speedcode Dratio b1 = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.speedcode_dratio_b2_consumer

    def speedcode_dratio_b2_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Speedcode Dratio b2 = {self.number_value}")
            self.number_value = ""
            self.number_consumer = self.distance_consumer

    def raster_step_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 3:
            if self.channel:
                self.channel(f"Raster Step = {self.number_value}")
            self.raster_step = int(self.number_value)
            self.number_value = ""

            self.number_consumer = self.distance_consumer

    def mode_consumer(self, c):
        self.number_value += c
        if len(self.number_value) >= 1:
            if self.channel:
                self.channel(f"Set Mode = {self.number_value}")
            self.mode = int(self.number_value)
            self.number_value = ""
            self.number_consumer = self.speedcode_mult_consumer

    def append_distance(self, amount):
        if self.x_on:
            self.distance_x += amount
        if self.y_on:
            self.distance_y += amount

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
                self.channel(f"Moving ({dx} {dy}) now at {self.x} {self.y}")

    def process(self, b, c):
        if c == "I":
            self.finish_state = False
            self.compact_state = False
            self.paused_state = False
            self.distance_x = 0
            self.distance_y = 0
        if self.finish_state:  # In finished all commands are black holed
            return
        if ord("0") <= b <= ord("9"):
            self.number_consumer(c)
            return
        else:
            self.number_consumer = self.distance_consumer
            self.number_value = ""

        if self.compact_state:
            # Every command in compact state executes distances.
            self.execute_distance()

        if c == "|":
            self.append_distance(25)
            self.small_jump = True
        elif ord("a") <= b <= ord("y"):
            self.append_distance(b + 1 - ord("a"))
            self.small_jump = False
        elif c == "z":
            self.append_distance(26 if self.small_jump else 255)
            self.small_jump = False
        elif c == "B":  # Move to Right.
            if self.left and self.horizontal_major:
                # Was T switched to B with horizontal rastering.
                if self.raster_step:
                    self.distance_y += self.raster_step
            self.left = False
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Right")
        elif c == "T":  # Move to Left
            if not self.left and self.horizontal_major:
                # Was T switched to B with horizontal rastering.
                if self.raster_step:
                    self.distance_y += self.raster_step
            self.left = True
            self.x_on = True
            self.y_on = False
            if self.channel:
                self.channel("Left")
        elif c == "R":  # Move to Bottom
            if self.top and not self.horizontal_major:
                # Was L switched to R with vertical rastering.
                if self.raster_step:
                    self.distance_x += self.raster_step
            self.top = False
            self.x_on = False
            self.y_on = True
            if self.channel:
                self.channel("Bottom")
        elif c == "L":  # Move to Top
            if not self.top and not self.horizontal_major:
                # Was R switched to L with vertical rastering.
                if self.raster_step:
                    self.distance_x += self.raster_step
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
            self.returning_finished = False
            self.returning_compact = False
        elif c in "C":
            if self.channel:
                self.channel("Speedcode")
            self.speed_code = ""
        elif c in "V":
            self.raster_step = None
            if self.channel:
                self.channel("Velocity")
            self.number_consumer = self.speedcode_b1_consumer
        elif c in "G":
            if self.channel:
                self.channel("Step Value")
            self.number_consumer = self.raster_step_consumer
        elif c == "S":
            if self.channel:
                self.channel("Mode Set")
            self.laser = 0
            self.execute_distance()

            self.mode = None
            self.number_consumer = self.mode_consumer
        elif c == "E":
            if self.channel:
                self.channel("Execute State")
            if self.mode is None:
                if self.returning_compact:
                    self.compact_state = True
                if self.returning_finished:
                    self.finish_state = True
                if self.horizontal_major:
                    self.left = not self.left
                    self.x_on = True
                    self.y_on = False
                    if self.raster_step:
                        self.distance_y += self.raster_step
                else:
                    # vertical major
                    self.top = not self.top
                    self.x_on = False
                    self.y_on = True
                    if self.raster_step:
                        self.distance_x += self.raster_step
            elif self.mode == 0:
                # Homes then moves position.
                pass
            elif self.mode == 1:
                self.compact_state = True
                self.horizontal_major = self.x_on
                if self.channel:
                    self.channel("Setting Axis: h=" + str(self.x_on))
            elif self.mode == 2:
                # Rail unlocked.
                self.compact_state = True
            self.returning_finished = False
            self.returning_compact = True
            self.laser = 0
        elif c == "P":
            if self.channel:
                self.channel("Pause")
            self.laser = 0
            if self.paused_state:
                # Home sequence triggered by 2 P commands in the same packet.
                # This should resume if not located within the same packet.
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
        elif c == "M":
            self.x_on = True
            self.y_on = True
            if self.channel:
                self.channel(
                    f"Diagonal {'Top' if self.top else 'Bottom'} {'Left' if self.left else 'Right'}"
                )


class EGVBlob:
    def __init__(self, data: bytearray, name=None):
        self.name = name
        self.data = data
        self.operation = "blob"
        self._cutcode = None
        self._cut = None

    def __repr__(self):
        return f"EGV({self.name}, {len(self.data)} bytes)"

    def as_cutobjects(self):
        parser = LihuiyuParser()
        self._cutcode = CutCode()
        self._cut = RawCut()

        def new_cut():
            if self._cut is not None and len(self._cut):
                self._cutcode.append(self._cut)
            self._cut = RawCut()
            self._cut.settings = dict(parser.settings)

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
        yield "blob", "egv", LihuiyuParser.remove_header(self.data)


class EgvLoader:
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

    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            op_branch = elements_modifier.get(type="branch ops")
            op_branch.add(
                data=bytearray(EgvLoader.remove_header(f.read())),
                data_type="egv",
                type="blob",
                name=basename,
            )
        return True
