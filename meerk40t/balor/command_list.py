import math

import numpy as np

import sys


class Simulation:
    def __init__(self, job, machine, draw, resolution, show_travels=False):
        self.job = job
        self.machine = machine
        self.draw = draw
        self.resolution = resolution
        self.scale = float(self.resolution) / 0x10000
        self.segcount = 0
        self.laser_power = 0
        self.laser_on = False
        self.q_switch_period = 0
        self.cut_speed = 0
        self.x = 0x8000
        self.y = 0x8000
        self.show_travels = show_travels


    def simulate(self, op):
        op.simulate(self)

    def cut(self, x, y):
        cm = 128 if self.segcount % 2 else 255
        self.segcount += 1
        if not self.laser_on:
            color = (cm, 0, 0)
        else:
            color = (
                int(cm * ((self.q_switch_period - 5000) / 50000.0)),
                int(round(cm * (2000 - self.cut_speed) / 2000.0)),
                # cm,)
                int(round((cm / 100.0) * self.laser_power)))
        self.draw.line((self.x * self.scale, self.y * self.scale,
                        self.scale * x, self.scale * y),
                       fill=color,
                       width=1)
        self.x, self.y = x, y

    def travel(self, x, y):
        if not self.show_travels:
            return
        cm = 128 if self.segcount % 2 else 255
        self.segcount += 1
        self.draw.line((self.x*self.scale, self.y*self.scale,
           self.scale*x, self.scale*y),
           fill=(cm//2,cm//2,cm//2, 64), width=1)
        self.x, self.y = x, y


class Operation:
    opcode = 0x8000
    name = 'UNDEFINED OPERATION'
    x = None  # know which is x and which is y,
    y = None  # for adjustment purposes by correction filters
    d = None
    a = None
    job = None

    def bind(self, job):
        self.job = job

    def simulate(self, sim):
        pass

    def __init__(self, *params, from_binary=None, tracking=None, position=0):
        self.tracking = tracking
        self.position = position
        self.params = [0] * 5
        if from_binary is None:
            for n, p in enumerate(params):
                self.params[n] = int(p)
                if p > 0xFFFF:
                    print("Parameter overflow", self.name, self.opcode, p, file=sys.stderr)
                    raise ValueError
        else:
            self.opcode = from_binary[0] | (from_binary[1] << 8)
            i = 2
            while i < len(from_binary):
                self.params[i // 2 - 1] = from_binary[i] | (from_binary[i + 1] << 8)
                i += 2

        self.validate()

    def serialize(self):
        blank = bytearray([0] * 12)
        blank[0] = self.opcode & 0xFF
        blank[1] = self.opcode >> 8
        i = 2
        for param in self.params:
            blank[i] = param & 0xFF
            try:
                blank[i + 1] = param >> 8
            except ValueError:
                print("Parameter overflow %x" % param, self.name, self.opcode, self.params, file=sys.stderr)
            i += 2
        return blank

    def validate(self):
        for n, param in enumerate(self.params):
            if param > 0xFFFF: raise ValueError(
                "A parameter can't be greater than 0xFFFF (Op %s, Param %d = 0x%04X" % (self.name,
                                                                                        n, param))

    def text_decode(self):
        return self.name

    def text_debug(self, show_tracking=False):
        return (('%s:%03X' % (self.tracking, self.position) if show_tracking else '')
                + ' | %04X | ' % self.opcode
                + ' '.join(['%04X' % x for x in self.params])
                + ' | ' + self.text_decode())

    def has_xy(self):
        return self.x is not None and self.y is not None

    def has_d(self):
        return self.d is not None

    def set_xy(self, nxy):
        self.params[self.x] = nxy[0]
        self.params[self.y] = nxy[1]
        self.validate()

    def set_d(self, d):
        self.params[self.d] = d & 0xFFFF
        self.params[self.d + 1] = (d >> 16) & 0x0001
        self.validate()

    def set_a(self, a):
        self.params[self.a] = a
        self.validate()

    def get_xy(self):
        return self.params[self.x], self.params[self.y]


class OpEndOfList(Operation):
    name = "NO OPERATION ()"
    opcode = 0x8002

    def text_decode(self):
        return "No operation"


class OpTravel(Operation):
    name = "TRAVEL (y, x, angle, distance)"
    opcode = 0x8001
    x = 1
    y = 0
    d = 3

    def text_decode(self):
        xs, ys, unit = self.job.get_scale()
        x = '%.3f %s' % (self.params[1] * xs, unit) if unit else '%d' % self.params[1]
        y = '%.3f %s' % (self.params[0] * ys, unit) if unit else '%d' % self.params[0]
        distance = self.params[3] | ((self.params[3] & 0x0001) << 16)
        d = '%.3f %s' % (distance * xs, unit) if unit else '%d' % distance
        return "Travel to x=%s y=%s angle=%04X dist=%s" % (
            x, y, self.params[2],
            d)

    def simulate(self, sim):
        sim.travel(self.params[self.x], self.params[self.y])


class OpLaserOnPoint(Operation):

    opcode = 0x8003
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4]
        )


class OpSetMarkEndDelay(Operation):
    name = "WAIT (time)"
    opcode = 0x8004

    def text_decode(self):
        return "Wait %d microseconds" % (self.params[0] * 10)


class OpCut(Operation):
    name = "CUT (y, x, angle, distance)"
    opcode = 0x8005
    x = 1
    y = 0
    d = 3
    a = 2

    def text_decode(self):
        xs, ys, unit = self.job.get_scale()
        x = '%.3f %s' % (self.params[1] * xs, unit) if unit else '%d' % self.params[1]
        y = '%.3f %s' % (self.params[0] * ys, unit) if unit else '%d' % self.params[0]
        d = '%.3f %s' % (self.params[3] * xs, unit) if unit else '%d' % self.params[3]
        return "Cut to x=%s y=%s angle=%04X dist=%s" % (
            x, y, self.params[2],
            d)

    def simulate(self, sim):
        sim.cut(self.params[self.x], self.params[self.y])


class OpSetTravelSpeed(Operation):
    name = "SET TRAVEL SPEED (speed)"
    opcode = 0x8006

    def text_decode(self):
        return "Set travel speed = %.2f mm/s" % (self.params[0] * 1.9656)


class OpSetLaserOnDelay(Operation):
    name = "SET ON TIME COMPENSATION (time)"
    opcode = 0x8007

    def text_decode(self):
        return "Set on time compensation = %d us" % (self.params[0])


class OpSetLaserOffDelay(Operation):
    name = "SET OFF TIME COMPENSATION (time)"
    opcode = 0x8008

    def text_decode(self):
        return "Set off time compensation = %d us" % (self.params[0])


class OpMarkFrequency(Operation):
    opcode = 0x800A
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpMarkPulseWidth(Operation):
    opcode = 0x800B
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpSetCutSpeed(Operation):
    name = "SET CUTTING SPEED (speed)"
    opcode = 0x800C

    def text_decode(self):
        return "Set cut speed = %.2f mm/s" % (self.params[0] * 1.9656)

    def simulate(self, sim):
        sim.cut_speed = self.params[0] * 1.9656


class OpSetJumpDelay(Operation):
    name = "JUMP DELAY (0x800D)"
    opcode = 0x800D

    def text_decode(self):
        return "Set jump delay, param=(%d,%d)" % (self.params[0],self.params[1])


class OpSetPolygonDelay(Operation):
    name = "POLYGON DELAY"
    opcode = 0x800F

    def text_decode(self):
        return "Set polygon delay, param=%d" % self.params[0]


class OpWritePort(Operation):
    opcode = 0x8011
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpMarkPowerRatio(Operation):
    name = "SET LASER POWER (power)"
    opcode = 0x8012

    def text_decode(self):
        return "Set laser power = %.1f%%" % (self.params[0] / 40.960)

    def simulate(self, sim):
        sim.laser_power = self.params[0] / 40.960


class OpFlyEnable(Operation):

    opcode = 0x801A
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpSetQSwitchPeriod(Operation):
    name = "SET Q SWITCH PERIOD (period)"
    opcode = 0x801B

    def text_decode(self):
        return "Set Q-switch period = %d ns (%.0f kHz)" % (
            self.params[0] * 50,
            1.0 / (1000 * self.params[0] * 50e-9))

    def simulate(self, sim):
        sim.q_switch_period = self.params[0] * 50.0


class OpDirectLaserSwitch(Operation):
    opcode = 0x801C
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpFlyDelay(Operation):
    opcode = 0x801D
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpSetCo2FPK(Operation):
    opcode = 0x801E
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpFlyWaitInput(Operation):

    opcode = 0x801F
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpLaserControl(Operation):
    name = "LASER CONTROL (on)"
    opcode = 0x8021

    def text_decode(self):
        return "Laser control - turn " + ('ON' if self.params[0] else 'OFF')

    def simulate(self, sim):
        sim.laser_on = bool(self.params[0])


class OpChangeMarkCount(Operation):
    opcode = 0x8023
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpSetWeldPowerWave(Operation):

    opcode = 0x8024
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpEnableWeldPowerWave(Operation):

    opcode = 0x8025
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpFiberYLPMPulseWidth(Operation):
    opcode = 0x8026
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpFlyEncoderCount(Operation):

    opcode = 0x8028
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )


class OpSetDaZWord(Operation):

    opcode = 0x8029
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )

class OpJptSetParam(Operation):

    opcode = 0x8050
    # name = "Name"
    name = str(opcode)

    def text_decode(self):
        return "sets command {opcode}={p1}, {p2}, {p3}, {p4}".format(
            opcode=self.opcode,
            p1=self.params[1],
            p2=self.params[2],
            p3=self.params[3],
            p4=self.params[4],
        )




class OpReadyMark(Operation):
    name = "BEGIN JOB"
    opcode = 0x8051

    def text_decode(self):
        return "Begin job"




all_operations = [OpReadyMark, OpLaserControl, OpSetQSwitchPeriod, OpCut, OpLaserOnPoint,
                  OpMarkPowerRatio, OpSetPolygonDelay, OpSetJumpDelay, OpSetCutSpeed,
                  OpSetLaserOffDelay, OpSetLaserOnDelay, OpSetTravelSpeed,
                  OpSetMarkEndDelay, OpEndOfList, OpTravel, OpMarkFrequency, OpMarkPulseWidth,
                  OpWritePort, OpDirectLaserSwitch, OpFlyDelay, OpSetCo2FPK, OpFlyWaitInput,
                  OpChangeMarkCount, OpSetWeldPowerWave, OpEnableWeldPowerWave, OpFiberYLPMPulseWidth,
                  OpFlyEncoderCount, OpJptSetParam, OpSetDaZWord
                  ]

operations_by_opcode = {OpClass.opcode: OpClass for OpClass in all_operations}


def OperationFactory(code, tracking=None, position=0):
    opcode = code[0] | (code[1] << 8)
    OpClass = operations_by_opcode.get(opcode, Operation)
    return OpClass(from_binary=code, tracking=tracking, position=position)

class CommandSource:
    tick = None
    def packet_generator(self):
        assert False, "Override this abstract method!"

class CommandBinary(CommandSource):
    def __init__(self, data, repeat=1):
        self._original_data = data
        self._repeat = repeat
    def packet_generator(self):
        while self._repeat > 0:
            self._data = self._original_data
            while len(self._data):
                data = self._data[:0xC00]
                assert len(data) == 3072
                yield data
                self._data = self._data[0xC00:]
            self._repeat -= 1


class CommandList(CommandSource):
    def __init__(self,
                 machine=None,
                 x=0x8000,
                 y=0x8000,
                 cal=None,
                 sender=None,
                 tick=None,
                 ):
        self.machine = machine
        self.tick = tick

        self._last_x = x
        self._last_y = y
        self._start_x = x
        self._start_y = y
        self.cal = cal
        self._sender = sender
        self.operations = []

        self._ready = False
        self._cut_speed = None
        self._travel_speed = None
        self._q_switch_frequency = None
        self._power = None
        self._jump_delay = None
        self._laser_control = None
        self._laser_on_delay = None
        self._laser_off_delay = None
        self._poly_delay = None
        self._mark_end_delay = None
        if self._sender:
            self._write_port = self._sender._write_port
        else:
            self._write_port = 0x0001

        self._scale_x = 1.0
        self._scale_y = 1.0
        self._units = "galvo"

    @property
    def position(self):
        return len(self.operations) - 1

    def get_last_xy(self):
        return self._last_x, self._last_y

    def get_scale(self):
        return self._scale_x, self._scale_y, self._units

    def clear(self):
        self.operations.clear()
        self._ready = False
        self._cut_speed = None
        self._travel_speed = None
        self._q_switch_frequency = None
        self._power = None
        self._jump_delay = None
        self._laser_control = None
        self._laser_on_delay = None
        self._laser_off_delay = None
        self._poly_delay = None
        self._mark_end_delay = None
        if self._sender:
            self._write_port = self._sender._write_port
        else:
            self._write_port = 0x0001

    def duplicate(self, begin, end, repeats=1):
        for _ in range(repeats):
            self.operations.extend(self.operations[begin:end])

    def append(self, x):
        x.bind(self)
        self.operations.append(x)

    def extend(self, x):
        for op in x:
            op.bind(self)
        self.operations.extend(x)

    def execute(self, loop_count=1, *args, **kwargs):
        if not self._sender:
            raise ValueError("No sender attached to the job.")
        self._sender.execute(self, loop_count, *args, **kwargs)

    def __iter__(self):
        return iter(self.operations)

    def __bytes__(self):
        return bytes(self.serialize())

    def serialize(self):
        """
        Performs final operations before creating bytearray.
        :return:
        """
        # Calculate distances.
        last_xy = self._start_x, self._start_y
        for op in self.operations:
            if op.has_d():
                nx, ny = op.get_xy()
                x, y = last_xy
                op.set_d(int(((nx - x) ** 2 + (ny - y) ** 2) ** 0.5))

            if op.has_xy():
                last_xy = op.get_xy()

        # Write buffer.
        size = 256 * int(round(math.ceil(len(self.operations) / 256.0)))
        buf = bytearray(([0x02, 0x80] + [0] * 10) * size)  # Create buffer full of NOP
        i = 0
        for op in self.operations:
            buf[i : i + 12] = op.serialize()
            i += 12
        return buf

    def packet_generator(self):
        """
        Performs final operations and generates packets on the fly.
        :return:
        """
        last_xy = self._start_x, self._start_y

        # Write buffer.
        buf = bytearray([0] * 0xC00)  # Create a packet.
        eol = bytes([0x02, 0x80] + [0] * 10)  # End of Line Command
        i = 0
        for op in self.operations:
            if op.has_d():
                nx, ny = op.get_xy()
                x, y = last_xy
                op.set_d(int(((nx - x) ** 2 + (ny - y) ** 2) ** 0.5))

            if op.has_xy():
                last_xy = op.get_xy()
            buf[i : i + 12] = op.serialize()
            i += 12
            if i >= 0xC00:
                i = 0
                yield buf
        while i < 0xC00:
            buf[i: i + 12] = eol
            i += 12
        yield buf

    ######################
    # GEOMETRY HELPERS
    ######################

    def draw_line(self, x0, y0, x1, y1, seg_size=5, Op=OpCut):
        length = ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5
        segs = max(2, int(round(length / seg_size)))
        # print ("**", x0, y0, x1, y1, length, segs, file=sys.stderr)

        xs = np.linspace(x0, x1, segs)
        ys = np.linspace(y0, y1, segs)

        for n in range(segs):
            # print ("*", xs[n], ys[n], self.cal.interpolate(xs[n], ys[n]), file=sys.stderr)
            self._last_x, self._last_y = xs[n], ys[n]
            self.append(Op(*self.pos(xs[n], ys[n])))

    ######################
    # UNIT CONVERSION
    ######################

    def pos(self, x, y):
        if self.cal is None:
            return x, y
        return self.cal.interpolate(x, y)

    def convert_time(self, time):
        # TODO: WEAK IMPLEMENTATION
        raise NotImplementedError("No time units")

    def convert_speed(self, speed):
        return int(round(speed / 2.0))  # units are 2mm/sec

    def convert_power(self, power):
        "Power in percent of full power."
        return int(round(power * 40.95))

    def convert_frequency_to_period(self, frequency):
        "Frequency in kHz"
        # q_switch_period
        return int(round(1.0 / (frequency * 1e3) / 50e-9))

    #def convert_period(self, period):
    #    return int(round(period / 50e-9))

    ######################
    # COMMAND DELEGATES
    ######################

    def ready(self):
        """
        Flag this job with ReadyMark.
        :return:
        """
        if not self._ready:
            self._ready = True
            self.append(OpReadyMark())

    def laser_control(self, control):
        """
        Enable the laser control.
        :param control:
        :return:
        """
        if self._laser_control == control:
            return
        self._laser_control = control

        # TODO: Does this order matter?
        # Yes it does, very much so. You're waiting for the laser source
        # to turn on, it doesn't come on instantly. It takes time for the pump
        # diodes to come on and create a population inversion in the gain
        # medium. It also takes time for the laser to stop lasing from the
        # time the command is sent, and you wouldn't want it to still be
        # firing when you started the next non-marking travel op, say.
        # TODO: These should probably be configurable, the idea values might
        # be different for different (e.g. non raycus q-switched fiber) lasers.
        # EzCAD lets you configure them.
        if control:
            self.append(OpLaserControl(0x0001))
            self.set_mark_end_delay(0x0320)
        else:
            self.set_mark_end_delay(0x001E)
            self.append(OpLaserControl(0x0000))

    def set_travel_speed(self, speed):
        if self._travel_speed == speed:
            return
        self.ready()
        self._travel_speed = speed
        self.append(OpSetTravelSpeed(self.convert_speed(speed)))

    def set_cut_speed(self, speed):
        if self._cut_speed == speed:
            return
        self.ready()
        self._cut_speed = speed
        self.append(OpSetCutSpeed(self.convert_speed(speed)))

    def set_power(self, power):
        # TODO: use or conversion differs by machine
        if self._power == power:
            return
        self.ready()
        self._power = power
        self.append(OpMarkPowerRatio(self.convert_power(power)))

    # def set_q_switch_period(self, period):
    #     if self._q_switch_period == period:
    #        return
    #    self._q_switch_period = period
    #    self.append(OpSetQSwitchPeriod(self.convert_period(period)))

    def set_frequency(self, frequency):
        # TODO: use differs by machine: 0x800A Mark Frequency, 0x800B Mark Pulse Width
        if self._q_switch_frequency == frequency:
            return
        self.ready()
        self._q_switch_frequency = frequency
        self.append(OpSetQSwitchPeriod(self.convert_frequency_to_period(frequency)))

    def set_write_port(self, port):
        if self._write_port == port:
            return
        self.ready()
        self.append(OpWritePort(port))
        self._write_port = port

    def set_laser_on_delay(self, *args):
        # TODO: WEAK IMPLEMENTATION
        if self._laser_on_delay == args:
            return
        self.ready()
        self._laser_on_delay = args
        self.append(OpSetLaserOnDelay(*args))

    def set_laser_off_delay(self, delay):
        # TODO: WEAK IMPLEMENTATION
        if self._laser_off_delay == delay:
            return
        self.ready()
        self._laser_off_delay = delay
        self.append(OpSetLaserOffDelay(delay))

    def set_polygon_delay(self, delay):
        # TODO: WEAK IMPLEMENTATION
        if self._poly_delay == delay:
            return
        self.ready()
        self._poly_delay = delay
        self.append(OpSetPolygonDelay(delay))

    def set_mark_end_delay(self, delay):
        # TODO: WEAK IMPLEMENTATION
        if self._mark_end_delay == delay:
            return
        self.ready()
        self._mark_end_delay = delay
        self.append(OpSetMarkEndDelay(delay))

    def mark(self, x, y):
        """
        Mark to a new location with the laser firing.
        :param x:
        :param y:
        :return:
        """
        self.ready()
        if self._q_switch_frequency is None:
            raise ValueError("Qswitch frequency must be set before a mark(x,y)")
        if self._power is None:
            raise ValueError("Laser Power must be set before a mark(x,y)")
        if self._cut_speed is None:
            raise ValueError("Mark Speed must be set before a mark(x,y)")
        if self._laser_on_delay is None:
            raise ValueError("LaserOn Delay must be set before a mark(x,y)")
        if self._laser_off_delay is None:
            raise ValueError("LaserOff Delay must be set before a mark(x,y)")
        if self._poly_delay is None:
            raise ValueError("Polygon Delay must be set before a mark(x,y)")
        self._last_x = x
        self._last_y = y
        self.append(OpCut(*self.pos(x, y)))

    def jump_delay(self, delay=0x0008):
        if self._jump_delay == delay:
            return
        self.ready()
        self._jump_delay = delay
        self.append(OpSetJumpDelay(delay))

    def light(self, x, y, light=True, jump_delay=None):
        """
        Move to a new location with light enabled.
        :param x:
        :param y:
        :param light: explicitly set light state
        :param jump_delay:
        :return:
        """
        if light:
            self.light_on()
        else:
            self.light_off()
        self.goto(x, y, jump_delay=jump_delay)

    def goto(self, x, y, jump_delay=None):
        """
        Move to a new location without laser or light.
        :param x:
        :param y:
        :param light:
        :param jump_delay:
        :return:
        """
        self.ready()
        if not self._travel_speed:
            raise ValueError("Travel speed must be set before a jumping")
        self._last_x = x
        self._last_y = y
        if jump_delay is not None:
            self.jump_delay(jump_delay)
        self.append(OpTravel(*self.pos(x, y)))

    def init(self, x, y):
        """
        Sets the initial position. This is the position we came from to get to this set of operations. It matters for
        the time calculation to the initial goto or mark commands.
        :param x:
        :param y:
        :return:
        """
        self._last_x = x
        self._last_y = y
        self._start_x = x
        self._start_y = y

    def set_mark_settings(
        self,
        travel_speed,
        frequency,
        power,
        cut_speed,
        laser_on_delay,
        laser_off_delay,
        polygon_delay,
    ):
        self.set_frequency(frequency)
        self.set_power(power)
        self.set_travel_speed(travel_speed)
        self.set_cut_speed(cut_speed)
        self.set_laser_on_delay(laser_on_delay)
        self.set_laser_off_delay(laser_off_delay)
        self.set_polygon_delay(polygon_delay)
        # This was set on during execute but singleton commands could turn it off.
        self.port_on(bit=0)

    def port_toggle(self, bit):
        port = self._write_port ^ (1 << bit)
        self.set_write_port(port)

    def port_on(self, bit):
        port = self._write_port | (1 << bit)
        self.set_write_port(port)

    def port_off(self, bit):
        port = ~((~self._write_port) | (1 << bit))
        self.set_write_port(port)

    def get_port(self, bit=None):
        if bit is None:
            return self._write_port
        return (self._write_port >> bit) & 1

    def light_on(self):
        self.port_on(bit=8) # 0x100

    def light_off(self):
        self.port_off(bit=8)

    ######################
    # DEBUG FUNCTIONS
    ######################

    def add_packet(self, data, tracking=None):
        """
        Parse MSBF data and add it as operations
        :param data:
        :param tracking:
        :return:
        """
        i = 0
        while i < len(data):
            command = data[i : i + 12]
            op = OperationFactory(command, tracking=tracking, position=i)
            op.bind(self)
            self.operations.append(op)
            i += 12

    def plot(self, draw, resolution=2048, show_travels=False):
        sim = Simulation(self, self.machine, draw, resolution, show_travels=show_travels)
        for op in self.operations:
            sim.simulate(op)

    def serialize_to_file(self, file):
        with open(file, "wb") as out_file:
            out_file.write(self.serialize())

    ######################
    # RAW APPENDS
    ######################

    def raw_end_of_list(self, *args):
        self.append(OpEndOfList(*args))

    def raw_travel(self, *args):
        self.append(OpTravel(*args))

    def raw_laser_on_point(self, *args):
        self.append(OpLaserOnPoint(*args))

    def raw_mark_end_delay(self, *args):
        self.append(OpSetMarkEndDelay(*args))

    def raw_cut(self, *args):
        self.append(OpCut(*args))

    def raw_travel_speed(self, *args):
        self.append(OpSetTravelSpeed(*args))

    def raw_laser_on_delay(self, *args):
        self.append(OpSetLaserOnDelay(*args))

    def raw_laser_off_delay(self, *args):
        self.append(OpSetLaserOffDelay(*args))

    def raw_mark_frequency(self, *args):
        self.append(OpMarkFrequency(*args))

    def raw_mark_pulse_width(self, *args):
        self.append(OpMarkPulseWidth(*args))

    def raw_cut_speed(self, *args):
        self.append(OpSetCutSpeed(*args))

    def raw_jump_delay(self, *args):
        self.append(OpSetJumpDelay(*args))

    def raw_set_polygon_delay(self, *args):
        self.append(OpSetPolygonDelay(*args))

    def raw_write_port(self, *args):
        self.append(OpWritePort(*args))

    def raw_mark_power_ratio(self, *args):
        self.append(OpMarkPowerRatio(*args))

    def raw_fly_enabled(self, *args):
        self.append(OpFlyEnable(*args))

    def raw_q_switch_period(self, *args):
        self.append(OpSetQSwitchPeriod(*args))

    def raw_direct_laser_switch(self, *args):
        self.append(OpDirectLaserSwitch(*args))

    def raw_fly_delay(self, *args):
        self.append(OpFlyDelay(*args))

    def raw_set_co2_fpk(self, *args):
        self.append(OpSetCo2FPK(*args))

    def raw_fly_wait_input(self, *args):
        self.append(OpFlyWaitInput(*args))

    def raw_laser_control(self, *args):
        self.append(OpLaserControl(*args))

    def raw_change_mark_count(self, *args):
        self.append(OpChangeMarkCount(*args))

    def raw_set_weld_power_wave(self, *args):
        self.append(OpSetWeldPowerWave(*args))

    def raw_enable_weld_power_wave(self, *args):
        self.append(OpEnableWeldPowerWave(*args))

    def raw_fiber_ylpmp_pulse_width(self, *args):
        self.append(OpFiberYLPMPulseWidth(*args))

    def raw_fly_encoder_count(self, *args):
        self.append(OpFlyEncoderCount(*args))

    def raw_set_da_z_word(self, *args):
        self.append(OpSetDaZWord(*args))

    def raw_jpt_set_param(self, *args):
        self.append(OpJptSetParam(*args))

    def raw_ready_mark(self, *args):
        self.append(OpReadyMark(*args))
