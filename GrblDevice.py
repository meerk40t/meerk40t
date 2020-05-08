from Kernel import Device, Interpreter, INTERPRETER_STATE_RAPID, INTERPRETER_STATE_PROGRAM
from zinglplotter import ZinglPlotter

"""
GRBL device is a stub device. Serving as a placeholder. 
"""


class GrblDevice(Device):
    """
    """
    def __init__(self, root, uid=''):
        Device.__init__(self, root, uid)
        self.uid = uid
        self.device_name = "GRBL"
        self.location_name = "Print"

        # Device specific stuff. Fold into proper kernel commands or delegate to subclass.
        self._device_log = ''
        self.current_x = 0
        self.current_y = 0

        self.hold_condition = lambda e: False
        self.pipe = None
        self.interpreter = None
        self.spooler = None

    def __repr__(self):
        return "GrblDevice(uid='%s')" % str(self.uid)

    @staticmethod
    def sub_register(device):
        device.register('module', 'GRBLInterpreter', GRBLInterpreter)
        # device.register('module', 'GRBLController')

    def initialize(self, device, name=''):
        """
        Device initialize.

        :param device:
        :param name:
        :return:
        """
        self.uid = name
        self.open('module', 'Spooler')
        self.open('module', 'GRBLInterpreter', pipe=print)


class GRBLInterpreter(Interpreter):
    def __init__(self, pipe):
        Interpreter.__init__(self, pipe=pipe)
        self.plot = None
        self.scale = 1000.0  # g21 default.
        self.feed_convert = lambda s: s / (self.scale * 60.0)  # G94 default
        self.feed_invert = lambda s: s * (self.scale * 60.0)
        self.power_updated = True
        self.speed_updated = True

    def g20(self):
        self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch

    def g21(self):
        self.scale = 39.3701  # g21 is mm mode. 39.3701 mils in a mm

    def g93(self):
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (self.scale * 60.0) / s
        self.feed_invert = lambda s: (self.scale * 60.0) / s

    def g94(self):
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / (self.scale * 60.0)
        self.feed_invert = lambda s: s * (self.scale * 60.0)

    def g90(self):
        self.set_absolute()

    def g91(self):
        self.set_incremental()

    def set_power(self, power=1000.0):
        Interpreter.set_power(self, power)
        self.power_updated = True

    def set_speed(self, speed=None):
        Interpreter.set_speed(self, speed)
        self.speed_updated = True

    def initialize(self):
        self.device.setting(str, 'line_end', '\n')

    def ensure_program_mode(self, *values):
        self.pipe.write('M3' + self.device.line_end)
        Interpreter.ensure_program_mode(*values)

    def ensure_finished_mode(self, *values):
        self.pipe.write('M5' + self.device.line_end)
        Interpreter.ensure_program_mode(*values)

    def plot_path(self, path):
        if len(path) == 0:
            return
        first_point = path.first_point
        self.move(first_point[0], first_point[1])
        sx = self.device.current_x
        sy = self.device.current_y
        self.pulse_modulation = True
        self.plot = self.group_plots(sx, sy, ZinglPlotter.plot_path(path))

    def plot_raster(self, raster):
        sx = self.device.current_x
        sy = self.device.current_y
        self.pulse_modulation = True
        self.plot = self.group_plots(sx, sy, self.ungroup_plots(raster.plot()))

    def move(self, x, y):
        line = []
        if self.state == INTERPRETER_STATE_PROGRAM:
            line.append('G1')
        else:
            line.append('G0')
        line.append('X%d' % (self.scale * x))
        line.append('Y%d' % (self.scale * y))
        if self.power_updated:
            line.append('S%f' % self.power)
            self.power_updated = False
        if self.speed_updated:
            line.append('F%d' % int(self.feed_convert(self.speed)))
            self.speed_updated = False
        self.pipe.write(' '.join(line) + self.device.line_end)

    def execute(self):
        if self.hold():
            return
        while self.plot is not None:
            if self.hold():
                return
            try:
                x, y, on = next(self.plot)
                if on == 0:
                    self.laser_on()
                else:
                    self.laser_off()
                self.move(x, y)
            except StopIteration:
                self.plot = None
                return
            except RuntimeError:
                self.plot = None
                return
        Interpreter.execute(self)

    def ungroup_plots(self, generate):
        """
        Converts a generated x,y,on with long orthogonal steps into a generation of single steps.
        :param generate: generator creating long orthogonal steps.
        :return:
        """
        current_x = None
        current_y = None
        for next_x, next_y, on in generate:
            if current_x is None or current_y is None:
                current_x = next_x
                current_y = next_y
                yield current_x, current_y, on
                continue
            if next_x > current_x:
                dx = 1
            elif next_x < current_x:
                dx = -1
            else:
                dx = 0
            if next_y > current_y:
                dy = 1
            elif next_y < current_y:
                dy = -1
            else:
                dy = 0
            total_dx = next_x - current_x
            total_dy = next_y - current_y
            if total_dy * dx != total_dx * dy:
                raise ValueError("Must be uniformly diagonal or orthogonal: (%d, %d) is not." % (total_dx, total_dy))
            while current_x != next_x or current_y != next_y:
                current_x += dx
                current_y += dy
                yield current_x, current_y, on

    def group_plots(self, start_x, start_y, generate):
        """
        Converts a generated series of single stepped plots into grouped orthogonal/diagonal plots.
        Implements PPI power modulation
        :param start_x: Start x position
        :param start_y: Start y position
        :param generate: generator of single stepped plots
        :return:
        """
        last_x = start_x
        last_y = start_y
        last_on = 0
        dx = 0
        dy = 0
        x = None
        y = None
        for event in generate:
            try:
                x = event[0]
                y = event[1]
                plot_on = event[2]
            except IndexError:
                plot_on = 1
            if self.pulse_modulation:
                self.pulse_total += self.power * plot_on
                if self.group_modulation and last_on == 1:
                    # If we are group modulating and currently on, the threshold for additional on triggers is 500.
                    if self.pulse_total > 0.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
                else:
                    if self.pulse_total >= 1000.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
            else:
                on = int(round(plot_on))
            if x == last_x + dx and y == last_y + dy and on == last_on:
                last_x = x
                last_y = y
                continue
            yield last_x, last_y, last_on
            dx = x - last_x
            dy = y - last_y
            if abs(dx) > 1 or abs(dy) > 1:
                # An error here means the plotting routines are flawed and plotted data more than a pixel apart.
                # The bug is in the code that wrongly plotted the data, not here.
                raise ValueError("dx(%d) or dy(%d) exceeds 1" % (dx, dy))
            last_x = x
            last_y = y
            last_on = on
        yield last_x, last_y, last_on
