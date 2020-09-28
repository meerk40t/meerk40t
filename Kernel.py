import os
import time
from threading import Thread, Lock

from LaserOperation import *
from svgelements import *
from zinglplotter import ZinglPlotter

STATE_UNKNOWN = -1
STATE_INITIALIZE = 0
STATE_IDLE = 1
STATE_ACTIVE = 2
STATE_BUSY = 3
STATE_PAUSE = 4
STATE_END = 5
STATE_TERMINATE = 10

INTERPRETER_STATE_RAPID = 0
INTERPRETER_STATE_FINISH = 1
INTERPRETER_STATE_PROGRAM = 2


class Modifier:
    """
    A modifier alters a given context with some additional functionality set during attachment and detachment.

    These are also booted and shutdown with the kernel. The modifications to the kernel are not expected to be undone.
    Rather the detach should kill any secondary processes the modifier may possess.
    """

    def __init__(self, context, name=None, channel=None):
        self.context = context
        self.name = name
        self.state = STATE_INITIALIZE

    def boot(self, channel=None):
        """
        Called when a kernel is booted, to boot the respective modifiers.
        :return:
        """
        pass

    def attach(self, channel=None):
        """
        Called by open to attach module to device.

        This should be overloaded when making a specific module type for reuse, where using init would require specific
        subclassing, or for modules that are intended to expand the functionality of a device rather than compliment
        that functionality.
        """
        pass

    def shutdown(self, channel=None):
        """
        Called when a kernel is shutdown, to shutdown the respective modifiers.
        :return:
        """
        pass

    def detach(self, channel=None):
        """
        Called by close to detach the module from device.

        :param device:
        :param channel:
        :return:
        """
        pass


class Module:
    """
    Modules are a generic lifecycle object. These are registered in the kernel as modules and when open() is called for
    context, the module is opened. When close() is called on the context, it will close and delete refrences to the
    opened module, and call finalize. When the kernel is shutting down the shutdown() event is called.

    If a module is attempted to be open() a second time in a context, and was never closed. The device restore()
    function is called for the device, with the same args and kwargs that would have been called on __init__().

    A module always has an understanding of its current state within the context, and is notified of any changes in this
    state.

    All life cycles events are provided channels. These can be used calling channel(string) to notify the channel of
    any relevant information.
    """

    def __init__(self, context, name=None, channel=None):
        self.context = context
        self.name = name
        self.state = STATE_INITIALIZE

    def initialize(self, channel=None):
        """Called when device is registered and module is named. On a freshly opened module."""
        pass

    def restore(self, *args, **kwargs):
        """Called if a second open attempt is made for this module."""
        pass

    def finalize(self, channel=None):
        """Called when the module is being closed."""
        pass

    def shutdown(self, channel=None):
        """Called during the shutdown process to notify the module that it should stop working."""
        pass


class Interpreter:
    """
    An Interpreter Module takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.

    Interpreters register themselves as device.interpreter objects.
    Interpreters expect the device.spooler object exists to provide spooled commands as needed.

    These modules function to interpret hardware specific backend information from the reusable spoolers and server
    objects that may also be common within devices.
    """

    def __init__(self, context):
        self.context = context
        self.process_item = None
        self.spooled_item = None
        self.extra_hold = None

        self.state = INTERPRETER_STATE_RAPID
        self.plot_planner = ZinglPlotter()
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self.raster_step = 0
        self.overscan = 20
        self.speed = 30
        self.power = 1000.0
        self.d_ratio = None  # None means to use speedcode default.
        self.acceleration = None  # None means to use speedcode default

    def process_spool(self, *args):
        """
        Get next spooled element if needed.
        Calls execute.

        :param args:
        :return:
        """
        if self.spooled_item is None:
            self.fetch_next_item()
        if self.spooled_item is not None:
            self.execute()
        else:
            if self.context.quit:
                self.context.stop()

    def execute(self):
        """
        Default process to run entire command as a single call.
        """
        if self.hold():
            return
        if self.spooled_item is None:
            return
        if isinstance(self.spooled_item, tuple):
            self.command(self.spooled_item[0], *self.spooled_item[1:])
            self.spooled_item = None
            return
        try:
            e = next(self.spooled_item)
            if isinstance(e, int):
                self.command(e)
            else:
                self.command(e[0], *e[1:])
        except StopIteration:
            self.spooled_item = None

    def fetch_next_item(self):
        element = self.context.spooler.peek()
        if element is None:
            return  # Spooler is empty.

        self.context.spooler.pop()
        if isinstance(element, int):
            self.spooled_item = (element,)
        elif isinstance(element, tuple):
            self.spooled_item = element
        else:
            try:
                self.spooled_item = element.generate()
            except AttributeError:
                try:
                    self.spooled_item = element()
                except TypeError:
                    # This could be a text element, some unrecognized type.
                    return

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        try:
            if command == COMMAND_LASER_OFF:
                self.laser_off()
            elif command == COMMAND_LASER_ON:
                self.laser_on()
            elif command == COMMAND_LASER_DISABLE:
                self.laser_disable()
            elif command == COMMAND_LASER_ENABLE:
                self.laser_enable()
            elif command == COMMAND_CUT:
                x, y = values
                self.cut(x, y)
            elif command == COMMAND_MOVE:
                x, y = values
                self.move(x, y)
            elif command == COMMAND_HOME:
                self.home()
            elif command == COMMAND_LOCK:
                self.lock_rail()
            elif command == COMMAND_UNLOCK:
                self.unlock_rail()
            elif command == COMMAND_PLOT:
                self.plot_path(values[0])
            elif command == COMMAND_RASTER:
                self.plot_raster(values[0])
            elif command == COMMAND_SET_SPEED:
                self.set_speed(values[0])
            elif command == COMMAND_SET_POWER:
                self.set_power(values[0])
            elif command == COMMAND_SET_PPI:
                self.set_ppi(values[0])
            elif command == COMMAND_SET_PWM:
                self.set_pwm(values[0])
            elif command == COMMAND_SET_STEP:
                self.set_step(values[0])
            elif command == COMMAND_SET_OVERSCAN:
                self.set_overscan(values[0])
            elif command == COMMAND_SET_ACCELERATION:
                self.set_acceleration(values[0])
            elif command == COMMAND_SET_D_RATIO:
                self.set_d_ratio(values[0])
            elif command == COMMAND_SET_DIRECTION:
                self.set_directions(values[0], values[1], values[2], values[3])
            elif command == COMMAND_SET_INCREMENTAL:
                self.set_incremental()
            elif command == COMMAND_SET_ABSOLUTE:
                self.set_absolute()
            elif command == COMMAND_SET_POSITION:
                self.set_position(values[0], values[1])
            elif command == COMMAND_MODE_RAPID:
                self.ensure_rapid_mode()
            elif command == COMMAND_MODE_PROGRAM:
                self.ensure_program_mode()
            elif command == COMMAND_MODE_FINISHED:
                self.ensure_finished_mode()
            elif command == COMMAND_WAIT:
                self.wait(values[0])
            elif command == COMMAND_WAIT_FINISH:
                self.wait_finish()
            elif command == COMMAND_BEEP:
                if os.name == 'nt':
                    try:
                        import winsound
                        for x in range(5):
                            winsound.Beep(2000, 100)
                    except:
                        pass
                if os.name == 'posix':
                    # Mac or linux.
                    print('\a')  # Beep.
                    os.system('say "Ding"')
                else:
                    print('\a')  # Beep.
            elif command == COMMAND_FUNCTION:
                if len(values) >= 1:
                    t = values[0]
                    if callable(t):
                        t()
            elif command == COMMAND_SIGNAL:
                if isinstance(values, str):
                    self.context.signal(values, None)
                elif len(values) >= 2:
                    self.context.signal(values[0], *values[1:])
        except AttributeError:
            pass

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        try:
            if command == REALTIME_PAUSE:
                self.pause()
            elif command == REALTIME_RESUME:
                self.resume()
            elif command == REALTIME_RESET:
                self.reset()
            elif command == REALTIME_STATUS:
                self.status()
            elif command == REALTIME_SAFETY_DOOR:
                self.safety_door()
            elif command == REALTIME_JOG_CANCEL:
                self.jog_cancel(*values)
            elif command == REALTIME_SPEED_PERCENT:
                self.realtime_speed_percent(*values)
            elif command == REALTIME_SPEED:
                self.realtime_speed(*values)
            elif command == REALTIME_RAPID_PERCENT:
                self.realtime_rapid_percent(*values)
            elif command == REALTIME_RAPID:
                self.realtime_rapid(*values)
            elif command == REALTIME_POWER_PERCENT:
                self.realtime_power_percent(*values)
            elif command == REALTIME_POWER:
                self.realtime_power(*values)
            elif command == REALTIME_OVERSCAN:
                self.realtime_overscan(*values)
            elif command == REALTIME_LASER_DISABLE:
                self.realtime_laser_disable(*values)
            elif command == REALTIME_LASER_ENABLE:
                self.realtime_laser_enable(*values)
            elif command == REALTIME_FLOOD_COOLANT:
                self.realtime_flood_coolant(*values)
            elif command == REALTIME_MIST_COOLANT:
                self.realtime_mist_coolant(*values)
        except AttributeError:
            pass  # Method doesn't exist.

    def hold(self):
        if self.extra_hold is not None:
            if self.extra_hold():
                return True
            else:
                self.extra_hold = None
        return False

    def laser_off(self, *values):
        self.laser = False

    def laser_on(self, *values):
        self.laser = True

    def laser_disable(self, *values):
        self.plot_planner.laser_enabled = False

    def laser_enable(self, *values):
        self.plot_planner.laser_enabled = True

    def move(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def cut(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def home(self, *values):
        self.context.current_x = 0
        self.context.current_y = 0

    def ensure_rapid_mode(self, *values):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal('interpreter;mode', self.state)

    def ensure_finished_mode(self, *values):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        self.state = INTERPRETER_STATE_FINISH
        self.context.signal('interpreter;mode', self.state)

    def ensure_program_mode(self, *values):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        self.state = INTERPRETER_STATE_PROGRAM
        self.context.signal('interpreter;mode', self.state)

    def set_speed(self, speed=None):
        self.speed = speed

    def set_power(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def set_ppi(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def set_pwm(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def set_d_ratio(self, d_ratio=None):
        self.d_ratio = d_ratio

    def set_acceleration(self, accel=None):
        self.acceleration = accel

    def set_step(self, step=None):
        self.raster_step = step

    def set_overscan(self, overscan=None):
        self.overscan = overscan

    def set_incremental(self, *values):
        self.is_relative = True

    def set_absolute(self, *values):
        self.is_relative = False

    def set_position(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def wait(self, t):
        self.next_run = t

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.extra_hold = lambda: len(self.pipe) != 0

    def reset(self):
        self.spooled_item = None
        self.context.spooler.clear_queue()
        self.spooled_item = None
        self.extra_hold = None

    def status(self):
        parts = list()
        parts.append("x=%f" % self.context.current_x)
        parts.append("y=%f" % self.context.current_y)
        parts.append("speed=%f" % self.speed)
        parts.append("power=%d" % self.power)
        status = ";".join(parts)
        self.context.signal('interpreter;status', status)

    def set_prop(self, mask):
        self.properties |= mask

    def unset_prop(self, mask):
        self.properties &= ~mask

    def is_prop(self, mask):
        return bool(self.properties & mask)

    def toggle_prop(self, mask):
        if self.is_prop(mask):
            self.unset_prop(mask)
        else:
            self.set_prop(mask)


class Spooler(Modifier):
    """
    The spooler module stores spoolable lasercode events as a synchronous queue.

    Spooler registers itself as the device.spooler object and provides a standard location to send data to an unknown
    device.

    * peek()
    * pop()
    * job(job)
    * jobs(iterable<job>)
    * job_if_idle(job) -- Will enqueue the job if the device is currently idle.
    * clear_queue()
    * remove(job)
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.queue_lock = Lock()
        self._queue = []

    def __repr__(self):
        return "Spooler()"

    def attach(self, channel=None):
        """Overloaded attach to demand .spooler attribute."""
        self.context.spooler = self

    def peek(self):
        if len(self._queue) == 0:
            return None
        return self._queue[0]

    def pop(self):
        if len(self._queue) == 0:
            return None
        self.queue_lock.acquire(True)
        queue_head = self._queue[0]
        del self._queue[0]
        self.queue_lock.release()
        self.context.signal('spooler;queue', len(self._queue))
        return queue_head

    def job(self, *job):
        """
        Send a single job event with parameters as needed.

        The job can be a single command with (COMMAND_MOVE 20 20) or without parameters (COMMAND_HOME), or a generator
        which can yield many lasercode commands.

        :param job: job to send to the spooler.
        :return:
        """
        self.queue_lock.acquire(True)

        if len(job) == 1:
            self._queue.extend(job)
        else:
            self._queue.append(job)
        self.queue_lock.release()
        self.context.signal('spooler;queue', len(self._queue))

    def jobs(self, jobs):
        """
        Send several jobs generators to be appended to the end of the queue.

        The jobs parameter must be suitable to be .extended to the end of the queue list.
        :param jobs: jobs to extend
        :return:
        """
        self.queue_lock.acquire(True)
        if isinstance(jobs, (list, tuple)):
            self._queue.extend(jobs)
        else:
            self._queue.append(jobs)
        self.queue_lock.release()
        self.context.signal('spooler;queue', len(self._queue))

    def job_if_idle(self, element):
        if len(self._queue) == 0:
            self.job(element)
            return True
        else:
            return False

    def clear_queue(self):
        self.queue_lock.acquire(True)
        self._queue = []
        self.queue_lock.release()
        self.context.signal('spooler;queue', len(self._queue))

    def remove(self, element):
        self.queue_lock.acquire(True)
        self._queue.remove(element)
        self.queue_lock.release()
        self.context.signal('spooler;queue', len(self._queue))


class Elemental(Modifier):
    """
    The elemental module is governs all the interactions with the various elements,
    operations, and filenodes. Handling structure change and selection, emphasis, and
    highlighting changes. The goal of this module is to make sure that the life cycle
    of the elements is strictly enforced. For example, every element that is removed
    must have had the .cache deleted. And anything selecting an element must propagate
    that information out to inform other interested modules.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._plan = list()
        self._operations = list()
        self._elements = list()
        self._filenodes = {}
        self.note = None
        self._bounds = None

    def attach(self, channel=None):
        context = self.context
        context.elements = self
        context.classify = self.classify
        context.save = self.save
        context.save_types = self.save_types
        context.load = self.load
        context.load_types = self.load_types
        self.add_elem(Rect(0,0,1000,1000, stroke='black'))

        context = self.context
        kernel = self.context._kernel
        elements = self
        _ = kernel.translation

        def grid(command, *args):
            try:
                cols = int(args[0])
                rows = int(args[1])
                x_distance = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
                y_distance = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            except (ValueError, IndexError):
                yield _("Syntax Error: grid <columns> <rows> <x_distance> <y_distance>")
                return
            items = list(elements.elems(emphasized=True))
            y_pos = elements._bounds[1]
            for j in range(rows):
                x_pos = elements._bounds[0]
                for k in range(cols):
                    if j != 0 or k != 0:
                        add_elem = list(map(copy, items))
                        for e in add_elem:
                            e *= 'translate(%f, %f)' % (x_pos, y_pos)
                        elements.add_elems(add_elem)
                    x_pos += x_distance
                y_pos += y_distance

        kernel.register('command/grid', grid)

        def element(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Graphical Elements:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if element.emphasized:
                        yield '%d: * %s' % (i, name)
                    else:
                        yield '%d: %s' % (i, name)
                    i += 1
                yield _('----------')
            else:
                for value in args:
                    try:
                        value = int(value)
                    except ValueError:
                        if value == "*":
                            yield _('Selecting all elements.')
                            elements.set_selected(list(elements.elems()))
                            continue
                        elif value == "~":
                            yield _('Invert selection.')
                            elements.set_selected(list(elements.elems(emphasized=False)))
                            continue
                        elif value == "!":
                            yield _('Select none')
                            elements.set_selected(None)
                            continue
                        elif value == "delete":
                            yield _('deleting.')
                            elements.remove_elements(list(elements.elems(emphasized=True)))
                            self.context.signal('refresh_scene', 0)
                            continue
                        elif value == "copy":
                            add_elem = list(map(copy, elements.elems(emphasized=True)))
                            elements.add_elems(add_elem)
                            for e in add_elem:
                                e.select()
                                e.emphasize()
                            continue
                        elif value == "merge":
                            superelement = Path()
                            for e in elements.elems(emphasized=True):
                                if superelement.stroke is None:
                                    superelement.stroke = e.stroke
                                if superelement.fill is None:
                                    superelement.fill = e.fill
                                superelement += abs(e)
                            elements.remove_elements(list(elements.elems(emphasized=True)))
                            elements.add_elem(superelement)
                            superelement.emphasize()
                            continue
                        elif value == "subpath":
                            for e in elements.elems(emphasized=True):
                                p = abs(e)
                                add = []
                                for subpath in p.as_subpaths():
                                    subelement = Path(subpath)
                                    add.append(subelement)
                                elements.add_elems(add)
                            continue
                        yield _('Value Error: %s is not an integer') % value
                        continue
                    try:
                        element = elements.get_elem(value)
                        name = str(element)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if element.selected:
                            element.unselect()
                            element.unemphasize()
                            yield _('Deselecting item %d called %s') % (value, name)
                        else:
                            element.select()
                            element.emphasize()
                            yield _('Selecting item %d called %s') % (value, name)
                    except IndexError:
                        yield _('index %d out of range') % value
            return

        kernel.register('command/element', element)

        def path(command, *args):
            path_d = ' '.join(args)
            element = Path(path_d)
            self.add_element(element)
            return

        kernel.register('command/path', path)

        def circle(command, *args):
            if len(args) == 3:
                x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
                y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
                r_pos = Length(args[2]).value(ppi=1000.0,
                                              relative_length=min(self.context.bed_height,
                                                                  self.context.bed_width) * 39.3701)
            elif len(args) == 1:
                x_pos = 0
                y_pos = 0
                r_pos = Length(args[0]).value(ppi=1000.0,
                                              relative_length=min(self.context.bed_height,
                                                                  self.context.bed_width) * 39.3701)
            else:
                yield _('Circle <x> <y> <r> or circle <r>')
                return
            element = Circle(cx=x_pos, cy=y_pos, r=r_pos)
            element = Path(element)
            self.add_element(element)

        kernel.register('command/circle', circle)

        def ellipse(command, *args):
            if len(args) < 4:
                yield _('Too few arguments (needs center_x, center_y, radius_x, radius_y)')
                return
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            rx_pos = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            ry_pos = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            element = Ellipse(cx=x_pos, cy=y_pos, rx=rx_pos, ry=ry_pos)
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/ellipse', ellipse)

        def rect(command, *args):
            if len(args) < 4:
                yield _("Too few arguments (needs x, y, width, height)")
                return
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            width = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            height = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            element = Rect(x=x_pos, y=y_pos, width=width, height=height)
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/rect', rect)

        def text(command, *args):
            text = ' '.join(args)
            element = SVGText(text)
            self.add_element(element)

        kernel.register('command/text', text)

        def polygon(command, *args):
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/polygon', polygon)

        def polyline(command, *args):
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/polyline', polyline)

        def stroke(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Stroke Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if element.stroke is None or element.stroke == 'none':
                        yield _('%d: stroke = none - %s') % (i, name)
                    else:
                        yield _('%d: stroke = %s - %s') % (i, element.stroke.hex, name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _("No selected elements.")
                return
            if args[0] == 'none':
                for element in elements.elems(emphasized=True):
                    element.stroke = None
                    element.altered()
            else:
                for element in elements.elems(emphasized=True):
                    element.stroke = Color(args[0])
                    element.altered()
            context.signal('refresh_scene')
            return

        kernel.register('command/stroke', stroke)

        def fill(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Fill Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if element.fill is None or element.fill == 'none':
                        yield _('%d: fill = none - %s') % (i, name)
                    else:
                        yield _('%d: fill = %s - %s') % (i, element.fill.hex, name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            if args[0] == 'none':
                for element in elements.elems(emphasized=True):
                    element.fill = None
                    element.altered()
            else:
                for element in elements.elems(emphasized=True):
                    element.fill = Color(args[0])
                    element.altered()
            context.signal('refresh_scene')
            return

        kernel.register('command/fill', fill)

        def rotate(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Rotate Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield _('%d: rotate(%fturn) - %s') % \
                          (i, element.rotation.as_turns, name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            bounds = elements.bounds()
            if len(args) >= 1:
                rot = Angle.parse(args[0]).as_degrees
            else:
                rot = 0
            if len(args) >= 2:
                center_x = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 3:
                center_y = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix('rotate(%f,%f,%f)' % (rot, center_x, center_y))
            try:
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/rotate', rotate)

        def scale(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Scale Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: scale(%f, %f) - %s' % \
                          (i, element.transform.value_scale_x(), element.transform.value_scale_x(), name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            bounds = elements.bounds()

            if len(args) >= 1:
                sx = Length(args[0]).value(relative_length=1.0)
            else:
                sx = 1
            if len(args) >= 2:
                sy = Length(args[1]).value(relative_length=1.0)
            else:
                sy = sx
            if len(args) >= 3:
                center_x = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 4:
                center_y = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            if sx == 0 or sy == 0:
                yield _('Scaling by Zero Error')
                return
            matrix = Matrix('scale(%f,%f,%f,%f)' % (sx, sy, center_x, center_y))
            try:
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/scale', scale)

        def translate(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Translate Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield _('%d: translate(%f, %f) - %s') % \
                          (i, element.transform.value_trans_x(), element.transform.value_trans_y(), name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            if len(args) >= 1:
                tx = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                tx = 0
            if len(args) >= 2:
                ty = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                ty = 0
            matrix = Matrix('translate(%f,%f)' % (tx, ty))
            try:
                for element in elements.elems(emphasized=True):
                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/translate', translate)

        def rotate_to(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Rotate Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield _('%d: rotate(%fturn) - %s') % \
                          (i, element.rotation.as_turns, name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            bounds = elements.bounds()
            try:
                end_angle = Angle.parse(args[0])
            except ValueError:
                yield _('Invalid Value.')
                return
            if len(args) >= 2:
                center_x = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 3:
                center_y = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0

            try:
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    start_angle = element.rotation
                    amount = end_angle - start_angle
                    matrix = Matrix('rotate(%f,%f,%f)' % (Angle(amount).as_degrees, center_x, center_y))
                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/rotate_to', rotate_to)

        def scale_to(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Scale Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield _('%d: scale(%f, %f) - %s') % \
                          (i, element.transform.value_scale_x(), element.transform.value_scale_y(), name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            bounds = elements.bounds()
            if len(args) >= 1:
                sx = Length(args[0]).value(relative_length=1.0)
            else:
                sx = 1
            if len(args) >= 2:
                sy = Length(args[1]).value(relative_length=1.0)
            else:
                sy = sx
            if len(args) >= 3:
                center_x = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 4:
                center_y = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            try:
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    osx = element.transform.value_scale_x()
                    osy = element.transform.value_scale_y()
                    if sx == 0 or sy == 0:
                        yield _('Scaling by Zero Error')
                        return
                    nsx = sx / osx
                    nsy = sy / osy
                    matrix = Matrix('scale(%f,%f,%f,%f)' % (nsx, nsy, center_x, center_y))
                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/scale_to', scale_to)

        def translate_to(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Translate Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield _('%d: translate(%f, %f) - %s') % \
                          (i, element.transform.value_trans_x(), element.transform.value_trans_y(), name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return

            if len(args) >= 1:
                tx = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
            else:
                tx = 0
            if len(args) >= 2:
                ty = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            else:
                ty = 0
            try:
                for element in elements.elems(emphasized=True):
                    otx = element.transform.value_trans_x()
                    oty = element.transform.value_trans_y()
                    ntx = tx - otx
                    nty = ty - oty
                    matrix = Matrix('translate(%f,%f)' % (ntx, nty))
                    element *= matrix
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/translate_to', translate_to)

        def resize(command, *args):
            if len(args) < 4:
                yield _('Too few arguments (needs x, y, width, height)')
                return
            try:
                x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701)
                y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
                w_dim = Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
                h_dim = Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
                x, y, x1, y1 = elements.bounds()
                w, h = x1 - x, y1 - y
                sx = w_dim / w
                sy = h_dim / h
                matrix = Matrix('translate(%f,%f) scale(%f,%f) translate(%f,%f)' % (x_pos, y_pos, sx, sy, -x, -y))
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass
                    element *= matrix
                    element.modified()
                context.signal('refresh_scene')
            except (ValueError, ZeroDivisionError):
                return

        kernel.register('command/resize', resize)

        def matrix(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Matrix Values:')
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: %s - %s' % \
                          (i, str(element.transform), name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            if len(args) != 6:
                yield _('Requires six matrix parameters')
                return
            try:
                matrix = Matrix(float(args[0]), float(args[1]), float(args[2]), float(args[3]),
                                Length(args[4]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701),
                                Length(args[5]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701))
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    element.transform = Matrix(matrix)
                    element.modified()
            except ValueError:
                yield _('Invalid value')
            context.signal('refresh_scene')
            return

        kernel.register('command/matrix', matrix)

        def reset(command, *args):
            for element in elements.elems(emphasized=True):
                try:
                    if element.lock:
                        continue
                except AttributeError:
                    pass

                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield _('reset - %s') % name
                element.transform.reset()
                element.modified()
            context.signal('refresh_scene')
            return

        kernel.register('command/reset', reset)

        def reify(command, *args):
            for element in elements.elems(emphasized=True):
                try:
                    if element.lock:
                        continue
                except AttributeError:
                    pass

                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield _('reified - %s') % name
                element.reify()
                element.altered()
            context.signal('refresh_scene')
            return

        kernel.register('command/reify', reify)

        # REQUIRES CUTPLANNER
        def optimize(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            elif len(args) == 0:
                yield _('Optimizations: cut_inner, travel, cut_travel')
                return
            elif args[0] == 'cut_inner':
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_cut_inside(element)
                    element.clear()
                    element += e
                    element.altered()
            elif args[0] == 'travel':
                yield _('Travel Optimizing: %f') % CutPlanner.length_travel(elements.elems(emphasized=True))
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_travel(element)
                    element.clear()
                    element += e
                    element.altered()
                yield _('Optimized: %f') % CutPlanner.length_travel(elements.elems(emphasized=True))
            elif args[0] == 'cut_travel':
                yield _('Cut Travel Initial: %f') % CutPlanner.length_travel(elements.elems(emphasized=True))
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_general(element)
                    element.clear()
                    element += e
                    element.altered()
                yield _('Cut Travel Optimized: %f') % CutPlanner.length_travel(elements.elems(emphasized=True))
            else:
                yield _('Optimization not found.')
                return

        kernel.register('command/optimize', optimize)

        # REQUIRES CUTPLANNER
        def embroider(command, *args):
            yield _('Embroidery Filling')
            if len(args) >= 1:
                angle = Angle.parse(args[0])
            else:
                angle = None
            if len(args) >= 2:
                distance = Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701)
            else:
                distance = 16
            for element in elements.elems(emphasized=True):
                if not isinstance(element, Path):
                    continue
                if angle is not None:
                    element *= Matrix.rotate(angle)
                e = CutPlanner.eulerian_fill([abs(element)], distance=distance)
                element.transform.reset()
                element.clear()
                element += e
                if angle is not None:
                    element *= Matrix.rotate(-angle)
                element.altered()

        kernel.register('command/embroider', embroider)

        def operation(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Operations:')
                i = 0

                for operation in elements.ops():
                    selected = operation.selected
                    name = str(operation)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if selected:
                        yield '%d: * %s' % (i, name)
                    else:
                        yield '%d: %s' % (i, name)
                    i += 1
                yield _('----------')
            else:
                for value in args:
                    try:
                        value = int(value)
                    except ValueError:
                        if value == "*":
                            yield _('Selecting all operations.')
                            elements.set_selected(list(elements.ops()))
                            continue
                        elif value == "~":
                            yield _('Invert selection.')
                            elements.set_selected(list(elements.ops(emphasized=False)))
                            continue
                        elif value == "!":
                            yield _('Select none')
                            elements.set_selected(None)
                            continue
                        elif value == "delete":
                            yield _('Deleting.')
                            elements.remove_operations(list(elements.ops(emphasized=True)))
                            continue
                        elif value == "copy":
                            add_elem = list(map(copy, elements.ops(emphasized=True)))
                            elements.add_ops(add_elem)
                            for e in add_elem:
                                e.select()
                                e.emphasize()
                            continue
                        yield _('Value Error: %s is not an integer') % value
                        continue
                    try:
                        operation = elements.get_op(value)
                        name = str(operation)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if operation.emphasized:
                            operation.unemphasize()
                            operation.unselect()
                            yield _('Deselecting operation %d called %s') % (value, name)
                        else:
                            operation.emphasize()
                            operation.select()
                            yield _('Selecting operation %d called %s') % (value, name)
                    except IndexError:
                        yield _('index %d out of range') % value
            return

        kernel.register('command/operation', operation)

        def classify(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            elements.classify(list(elements.elems(emphasized=True)))
            return

        kernel.register('command/classify', classify)

        def declassify(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            elements.remove_elements_from_operations(list(elements.elems(emphasized=True)))
            return

        kernel.register('command/declassify', declassify)

        def note(command, *args):
            if len(args) == 0:
                if elements.note is None:
                    yield _('No Note.')
                else:
                    yield str(elements.note)
            else:
                elements.note = ' '.join(args)
                yield _('Note Set.')

        kernel.register('command/note', note)

        def cut(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            op = LaserOperation()
            op.operation = "Cut"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return

        kernel.register('command/cut', cut)

        def engrave(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            op = LaserOperation()
            op.operation = "Engrave"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return

        kernel.register('command/engrave', engrave)

        def raster(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            op = LaserOperation()
            op.operation = "Raster"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return

        kernel.register('command/raster', raster)

        def step(command, *args):
            if len(args) == 0:
                found = False
                for op in elements.ops(emphasized=True):
                    if op.operation in ("Raster", "Image"):
                        step = op.raster_step
                        yield _('Step for %s is currently: %d') % (str(op), step)
                        found = True
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            step = element.values['raster_step']
                        except KeyError:
                            step = 1
                        yield _('Image step for %s is currently: %s') % (str(element), step)
                        found = True
                if not found:
                    yield _('No raster operations selected.')
                return
            try:
                step = int(args[0])
            except ValueError:
                yield _('Not integer value for raster step.')
                return
            for op in elements.ops(emphasized=True):
                if op.operation in ("Raster", "Image"):
                    op.raster_step = step
                    self.context.signal('element_property_update', op)
            for element in elements.elems(emphasized=True):
                element.values['raster_step'] = str(step)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step), float(step))
                element.transform.post_translate(tx, ty)
                element.modified()
                self.context.signal('element_property_update', element)
                self.context.signal('refresh_scene')
            return

        kernel.register('command/step', step)

        # REQUIRES OPERATION PREPROCESSOR.
        def image(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Images:')
                i = 0
                for element in elements.elems():
                    if not isinstance(element, SVGImage):
                        continue
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: (%d, %d) %s, %s' % (i,
                                                   element.image_width,
                                                   element.image_height,
                                                   element.image.mode,
                                                   name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected images.')
                return
            elif args[0] == 'wizard':
                if len(args) == 1:
                    try:
                        for script_name in context.match('raster_script', True):
                            yield _('Raster Script: %s') % script_name
                    except KeyError:
                        yield _('No Raster Scripts Found.')
                    return
                try:
                    script = context.registered['raster_script/%s' % args[1]]
                except KeyError:
                    yield _('Raster Script %s is not registered.') % args[1]
                    return
                from RasterScripts import RasterScripts
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        element.image, element.transform, step = RasterScripts.wizard_image(element, script)
                        if step is not None:
                            element.values['raster_step'] = step
                        element.image_width, element.image_height = element.image.size
                        element.lock = True
                        element.altered()
                return
            elif args[0] == 'unlock':
                yield _('Unlocking Elements...')
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            yield "Unlocked: %s" % str(element)
                            element.lock = False
                        else:
                            yield _('Element was not locked: %s') % str(element)
                    except AttributeError:
                        yield _('Element was not locked: %s') % str(element)
                return
            elif args[0] == 'threshold':
                try:
                    threshold_min = float(args[1])
                    threshold_max = float(args[2])
                except (ValueError, IndexError):
                    yield _('Threshold values improper.')
                    return
                divide = (threshold_max - threshold_min) / 255.0
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    image_element = copy(element)
                    image_element.image = image_element.image.copy()
                    if OperationPreprocessor.needs_actualization(image_element):
                        OperationPreprocessor.make_actual(image_element)
                    img = image_element.image
                    new_data = img.load()
                    width, height = img.size
                    for y in range(height):
                        for x in range(width):
                            pixel = new_data[x, y]
                            if pixel[3] == 0:
                                new_data[x, y] = (255, 255, 255, 255)
                                continue
                            gray = (pixel[0] + pixel[1] + pixel[2]) / 3.0
                            if threshold_min >= gray:
                                new_data[x, y] = (0, 0, 0, 255)
                            elif threshold_max < gray:
                                new_data[x, y] = (255, 255, 255, 255)
                            else:  # threshold_min <= grey < threshold_max
                                v = gray - threshold_min
                                v *= divide
                                v = int(round(v))
                                new_data[x, y] = (v, v, v, 255)
                    elements.add_elem(image_element)
            elif args[0] == 'resample':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        OperationPreprocessor.make_actual(element)
                        element.altered()
                return
            elif args[0] == 'dither':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        if img.mode == 'RGBA':
                            pixel_data = img.load()
                            width, height = img.size
                            for y in range(height):
                                for x in range(width):
                                    if pixel_data[x, y][3] == 0:
                                        pixel_data[x, y] = (255, 255, 255, 255)
                        element.image = img.convert("1")
                        element.altered()
            elif args[0] == 'remove':
                if len(args) == 1:
                    yield _('Must specify a color, and optionally a distance.')
                    return
                distance = 50.0
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield _('Color Invalid.')
                    return
                if len(args) >= 3:
                    try:
                        distance = float(args[2])
                    except ValueError:
                        yield _('Color distance is invalid.')
                        return
                distance_sq = distance * distance

                def dist(pixel):
                    r = color.red - pixel[0]
                    g = color.green - pixel[1]
                    b = color.blue - pixel[2]
                    return r * r + g * g + b * b <= distance_sq

                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    img = element.image
                    if img.mode != "RGBA":
                        img = img.convert('RGBA')
                    new_data = img.load()
                    width, height = img.size
                    for y in range(height):
                        for x in range(width):
                            pixel = new_data[x, y]
                            if dist(pixel):
                                new_data[x, y] = (255, 255, 255, 0)
                                continue
                    element.image = img
                    element.altered()
            elif args[0] == 'add':
                if len(args) == 1:
                    yield _('Must specify a color, to add.')
                    return
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield _('Color Invalid.')
                    return
                pix = (color.red, color.green, color.blue, color.alpha)
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    img = element.image
                    if img.mode != "RGBA":
                        img = img.convert('RGBA')
                    new_data = img.load()
                    width, height = img.size
                    for y in range(height):
                        for x in range(width):
                            pixel = new_data[x, y]
                            if pixel[3] == 0:
                                new_data[x, y] = pix
                                continue
                    element.image = img
                    element.altered()
            elif args[0] == 'crop':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        try:
                            left = int(args[1])
                            upper = int(args[2])
                            right = int(args[3])
                            lower = int(args[4])
                            element.image = img.crop((left, upper, right, lower))
                            element.image_width = right - left
                            element.image_height = lower - upper
                            element.altered()
                        except (KeyError, ValueError):
                            yield _('image crop <left> <upper> <right> <lower>')
                return
            elif args[0] == 'contrast':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:

                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Contrast(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            yield _('Image Contrast Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image contrast <factor>')
                return
            elif args[0] == 'brightness':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Brightness(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            yield _('Image Brightness Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image brightness <factor>')
                return
            elif args[0] == 'color':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Color(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            yield _('Image Color Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image color <factor>')
                return
            elif args[0] == 'sharpness':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Sharpness(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            yield _('Image Sharpness Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image sharpness <factor>')
                return
            elif args[0] == 'blur':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.BLUR)
                        element.altered()
                        yield _('Image Blurred.')
                return
            elif args[0] == 'sharpen':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SHARPEN)
                        element.altered()
                        yield _('Image Sharpened.')
                return
            elif args[0] == 'edge_enhance':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
                        element.altered()
                        yield _('Image Edges Enhanced.')
                return
            elif args[0] == 'find_edges':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.FIND_EDGES)
                        element.altered()
                        yield _('Image Edges Found.')
                return
            elif args[0] == 'emboss':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EMBOSS)
                        element.altered()
                        yield _('Image Embossed.')
                return
            elif args[0] == 'smooth':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SMOOTH)
                        element.altered()
                        yield _('Image Smoothed.')
                return
            elif args[0] == 'contour':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.CONTOUR)
                        element.altered()
                        yield _('Image Contoured.')
                return
            elif args[0] == 'detail':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.DETAIL)
                        element.altered()
                        yield _('Image Detailed.')
                return
            elif args[0] == 'quantize':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            colors = int(args[1])
                            img = element.image
                            element.image = img.quantize(colors=colors)
                            element.altered()
                            yield _('Image Quantized to %d colors.') % colors
                        except (IndexError, ValueError):
                            yield _('image quantize <colors>')
                return
            elif args[0] == 'solarize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            threshold = int(args[1])
                            img = element.image
                            element.image = ImageOps.solarize(img, threshold=threshold)
                            element.altered()
                            yield _('Image Solarized at %d gray.') % threshold
                        except (IndexError, ValueError):
                            yield _('image solarize <threshold>')
                return
            elif args[0] == 'invert':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        original_mode = img.mode
                        if img.mode == 'P' or img.mode == 'RGBA' or img.mode == '1':
                            img = img.convert('RGB')
                        try:
                            element.image = ImageOps.invert(img)
                            if original_mode == '1':
                                element.image = element.image.convert('1')
                            element.altered()
                            yield _('Image Inverted.')
                        except OSError:
                            yield _('Image type cannot be converted. %s') % img.mode
                return
            elif args[0] == 'flip':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.flip(img)
                        element.altered()
                        yield _('Image Flipped.')
                return
            elif args[0] == 'mirror':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.mirror(img)
                        element.altered()
                        yield _('Image Mirrored.')
                return
            elif args[0] == 'ccw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_90)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield _('Rotated image counterclockwise.')
                return
            elif args[0] == 'cw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_270)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield _('Rotated image clockwise.')
                return
            elif args[0] == 'autocontrast':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            cutoff = int(args[1])
                            img = element.image
                            if img.mode == 'RGBA':
                                img = img.convert('RGB')
                            element.image = ImageOps.autocontrast(img, cutoff=cutoff)
                            element.altered()
                            yield _('Image Auto-Contrasted.')
                        except (IndexError, ValueError):
                            yield _('image autocontrast <cutoff-percent>')
                return
            elif args[0] == 'grayscale' or args[0] == 'greyscale':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.grayscale(img)
                        element.altered()
                        yield _('Image Grayscale.')
                return
            elif args[0] == 'equalize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.equalize(img)
                        element.altered()
                        yield _('Image Equalized.')
                return
            elif args[0] == 'save':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            img = element.image
                            img.save(args[1])
                            yield _('Saved: %s') % (args[1])
                        except IndexError:
                            yield _('No file given.')
                        except OSError:
                            yield _('File could not be written / created.')
                        except ValueError:
                            yield _('Could not determine expected format.')

                return
            elif args[0] == 'flatrotary':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        points = len(args) - 1
                        im = element.image
                        w, h = im.size
                        from PIL import Image

                        def t(i):
                            return int(i * w / (points - 1))

                        def x(i):
                            return int(w * float(args[i + 1]))

                        boxes = list((t(i), 0, t(i + 1), h) for i in range(points - 1))
                        quads = list((x(i), 0, x(i), h, x(i + 1), h, x(i + 1), 0) for i in range(points - 1))
                        mesh = list(zip(boxes, quads))
                        element.image = im.transform(im.size, Image.MESH,
                                                     mesh,
                                                     Image.BILINEAR)
                        element.altered()
            elif args[0] == 'halftone':
                #  https://stackoverflow.com/questions/10572274/halftone-images-in-python/10575940#10575940
                pass
            else:
                yield _('Image command unrecognized.')
                return

        kernel.register('command/image', image)

        def halftone(command, *args):
            '''Returns list of half-tone images for cmyk image. sample (pixels),
               determines the sample box size from the original image. The maximum
               output dot diameter is given by sample * scale (which is also the number
               of possible dot sizes). So sample=1 will presevere the original image
               resolution, but scale must be >1 to allow variation in dot size.'''
            from PIL import Image, ImageDraw, ImageStat
            oversample = 2
            sample = 10
            scale = 1
            angle = 22
            for element in elements.elems(emphasized=True):
                if not isinstance(element, SVGImage):
                    continue
                image = element.image
                im = image
                image = image.convert('L')
                image = image.rotate(angle, expand=1)
                size = image.size[0] * scale, image.size[1] * scale
                half_tone = Image.new('L', size)
                draw = ImageDraw.Draw(half_tone)
                for x in range(0, image.size[0], sample):
                    for y in range(0, image.size[1], sample):
                        box = image.crop(
                            (x - oversample, y - oversample, x + sample + oversample, y + sample + oversample))
                        stat = ImageStat.Stat(box)
                        diameter = (stat.mean[0] / 255) ** 0.5
                        edge = 0.5 * (1 - diameter)
                        x_pos, y_pos = (x + edge) * scale, (y + edge) * scale
                        box_edge = sample * diameter * scale
                        draw.ellipse((x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=255)
                half_tone = half_tone.rotate(-angle, expand=1)
                width_half, height_half = half_tone.size
                xx = (width_half - im.size[0] * scale) / 2
                yy = (height_half - im.size[1] * scale) / 2
                half_tone = half_tone.crop((xx, yy, xx + im.size[0] * scale, yy + im.size[1] * scale))
            element.image = half_tone
            element.altered()

        kernel.register('command/halftone', halftone)
        kernel.register('command-help/halftone', 'image halftone <diameter> <scale> <angle> ')

        def trace_hull(command, *args):
            spooler = context.active.spooler
            pts = []
            for obj in elements.elems(emphasized=True):
                if isinstance(obj, Path):
                    epath = abs(obj)
                    pts += [q for q in epath.as_points()]
                elif isinstance(obj, SVGImage):
                    bounds = obj.bbox()
                    pts += [(bounds[0], bounds[1]),
                            (bounds[0], bounds[3]),
                            (bounds[2], bounds[1]),
                            (bounds[2], bounds[3])]
            hull = [p for p in Point.convex_hull(pts)]
            if len(hull) == 0:
                yield _('No elements bounds to trace.')
                return
            hull.append(hull[0])  # loop

            def trace_hull():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MODE_RAPID
                for p in hull:
                    yield COMMAND_MOVE, p[0], p[1]

            spooler.job(trace_hull)
            return

        kernel.register('command/trace_hull', trace_hull)

        def trace_quick(command, *args):
            spooler = context.active.spooler
            bbox = elements.bounds()
            if bbox is None:
                yield _('No elements bounds to trace.')
                return

            def trace_quick():
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, bbox[0], bbox[1]
                yield COMMAND_MOVE, bbox[2], bbox[1]
                yield COMMAND_MOVE, bbox[2], bbox[3]
                yield COMMAND_MOVE, bbox[0], bbox[3]
                yield COMMAND_MOVE, bbox[0], bbox[1]

            spooler.job(trace_quick)
            return

        kernel.register('command/trace_quick', trace_quick)

    def add_element(self, element):
        context_root = self.context.get_context('/')
        element.stroke = Color('black')
        context_root.elements.add_elem(element)
        context_root.elements.set_selected([element])

    def register(self, obj):
        obj.cache = None
        obj.icon = None
        obj.bounds = None
        obj.last_transform = None
        obj.selected = False
        obj.emphasized = False
        obj.highlighted = False

        def select():
            obj.selected = True
            self.context.signal('selected', obj)

        def unselect():
            obj.selected = False
            self.context.signal('selected', obj)

        def highlight():
            obj.highlighted = True
            self.context.signal('highlighted', obj)

        def unhighlight():
            obj.highlighted = False
            self.context.signal('highlighted', obj)

        def emphasize():
            obj.emphasized = True
            self.context.signal('emphasized', obj)
            self.validate_bounds()

        def unemphasize():
            obj.emphasized = False
            self.context.signal('emphasized', obj)
            self.validate_bounds()

        def modified():
            """
            The matrix transformation was changed.
            """
            obj.bounds = None
            self._bounds = None
            self.validate_bounds()
            self.context.signal('modified', obj)

        def altered():
            """
            The data structure was changed.
            """
            try:
                obj.cache.UnGetNativePath(obj.cache.NativePath)
            except AttributeError:
                pass
            del obj.cache
            obj.cache = None
            del obj.icon
            obj.icon = None
            obj.bounds = None
            self._bounds = None
            self.validate_bounds()
            self.context.signal('altered', obj)

        obj.select = select
        obj.unselect = unselect
        obj.highlight = highlight
        obj.unhighlight = unhighlight
        obj.emphasize = emphasize
        obj.unemphasize = unemphasize
        obj.modified = modified
        obj.altered = altered

    def unregister(self, e):
        try:
            e.cache.UngetNativePath(e.cache.NativePath)
        except AttributeError:
            pass
        try:
            del e.cache
        except AttributeError:
            pass
        try:
            del e.icon
        except AttributeError:
            pass
        try:
            e.unselect()
            e.unemphasize()
            e.unhighlight()
            e.modified()
        except AttributeError:
            pass

    def load_default(self):
        self.clear_operations()
        self.add_op(LaserOperation(operation="Image", color="black",
                                   speed=140.0,
                                   power=1000.0,
                                   raster_step=3))
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
        self.classify(self.elems())

    def load_default2(self):
        self.clear_operations()
        self.add_op(LaserOperation(operation="Image", color="black",
                                   speed=140.0,
                                   power=1000.0,
                                   raster_step=3))
        self.add_op(LaserOperation(operation="Raster", color="black", speed=140.0))
        self.add_op(LaserOperation(operation="Engrave", color="green", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="blue", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="magenta", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="cyan", speed=35.0))
        self.add_op(LaserOperation(operation="Engrave", color="yellow", speed=35.0))
        self.add_op(LaserOperation(operation="Cut", color="red", speed=10.0))
        self.classify(self.elems())

    def finalize(self, channel=None):
        context = self.context
        settings = context.derive('operations')
        settings.clear_persistent()
        for i, op in enumerate(self.ops()):
            op_set = settings.derive(str(i))
            for key in dir(op):
                if key.startswith('_'):
                    continue
                value = getattr(op, key)
                if value is None:
                    continue
                if isinstance(value, Color):
                    value = value.value
                op_set.write_persistent(key, value)

    def boot(self, channel=None):
        settings = self.context.derive('operations')
        subitems = list(settings.derivable())
        ops = [None] * len(subitems)
        for i, v in enumerate(subitems):
            op_set = settings.derive(v)
            op = LaserOperation()
            op_set.load_persistent_object(op)
            try:
                ops[i] = op
            except (ValueError, IndexError):
                ops.append(op)
        if not len(ops):
            self.load_default()
            return
        self.add_ops([o for o in ops if o is not None])
        self.context.signal('rebuild_tree')

    def items(self, **kwargs):
        def combined(*args):
            for listv in args:
                for itemv in listv:
                    yield itemv

        for j in combined(self.ops(**kwargs), self.elems(**kwargs)):
            yield j

    def _filtered_list(self, item_list, **kwargs):
        """
        Filters a list of items with selected, emphasized, and highlighted.
        False values means find where that parameter is false.
        True values means find where that parameter is true.
        If the filter does not exist then it isn't used to filter that data.

        Items which are set to None are skipped.

        :param item_list:
        :param kwargs:
        :return:
        """
        s = 'selected' in kwargs
        if s:
            s = kwargs['selected']
        else:
            s = None
        e = 'emphasized' in kwargs
        if e:
            e = kwargs['emphasized']
        else:
            e = None
        h = 'highlighted' in kwargs
        if h:
            h = kwargs['highlighted']
        else:
            h = None
        for obj in item_list:
            if obj is None:
                continue
            if s is not None and s != obj.selected:
                continue
            if e is not None and e != obj.emphasized:
                continue
            if h is not None and s != obj.highlighted:
                continue
            yield obj

    def ops(self, **kwargs):
        for item in self._filtered_list(self._operations, **kwargs):
            yield item

    def elems(self, **kwargs):
        for item in self._filtered_list(self._elements, **kwargs):
            yield item

    def first_element(self, **kwargs):
        for e in self.elems(**kwargs):
            return e
        return None

    def has_emphasis(self):
        return self.first_element(emphasized=True) is not None

    def count_elems(self, **kwargs):
        return len(list(self.elems(**kwargs)))

    def count_op(self, **kwargs):
        return len(list(self.ops(**kwargs)))

    def get_op(self, index, **kwargs):
        for i, op in enumerate(self.ops(**kwargs)):
            if i == index:
                return op
        raise IndexError

    def get_elem(self, index, **kwargs):
        for i, elem in enumerate(self.elems(**kwargs)):
            if i == index:
                return elem
        raise IndexError

    def add_op(self, op):
        self._operations.append(op)
        self.register(op)
        self.context.signal('operation_added', op)

    def add_ops(self, adding_ops):
        self._operations.extend(adding_ops)
        for op in adding_ops:
            self.register(op)
        self.context.signal('operation_added', adding_ops)

    def add_elem(self, element):
        self._elements.append(element)
        self.register(element)
        self.context.signal('element_added', element)

    def add_elems(self, adding_elements):
        self._elements.extend(adding_elements)
        for element in adding_elements:
            self.register(element)
        self.context.signal('element_added', adding_elements)

    def files(self):
        return self._filenodes

    def clear_operations(self):
        for op in self._operations:
            self.unregister(op)
            self.context.signal('operation_removed', op)
        self._operations.clear()

    def clear_elements(self):
        for e in self._elements:
            self.unregister(e)
            self.context.signal('element_removed', e)
        self._elements.clear()

    def clear_files(self):
        self._filenodes.clear()

    def clear_elements_and_operations(self):
        self.clear_elements()
        self.clear_operations()

    def clear_all(self):
        self.clear_elements()
        self.clear_operations()
        self.clear_files()
        self.clear_note()
        self.validate_bounds()

    def clear_note(self):
        self.note = None

    def remove_files(self, file_list):
        for f in file_list:
            del self._filenodes[f]

    def remove_elements(self, elements_list):
        for elem in elements_list:
            for i, e in enumerate(self._elements):
                if elem is e:
                    self.unregister(elem)
                    self.context.signal('element_removed', elem)
                    self._elements[i] = None
        self.remove_elements_from_operations(elements_list)
        self.validate_bounds()

    def remove_operations(self, operations_list):
        for op in operations_list:
            for i, o in enumerate(self._operations):
                if o is op:
                    self.unregister(op)
                    self.context.signal('operation_removed', op)
                    self._operations[i] = None
        self.purge_unset()

    def remove_elements_from_operations(self, elements_list):
        for i, op in enumerate(self._operations):
            if op is None:
                continue
            elems = [e for e in op if e not in elements_list]
            op.clear()
            op.extend(elems)
        self.purge_unset()

    def purge_unset(self):
        if None in self._operations:
            ops = [op for op in self._operations if op is not None]
            self._operations.clear()
            self._operations.extend(ops)
        if None in self._elements:
            elems = [elem for elem in self._elements if elem is not None]
            self._elements.clear()
            self._elements.extend(elems)

    def bounds(self):
        return self._bounds

    def validate_bounds(self):
        boundary_points = []
        for e in self._elements:
            if e.last_transform is None or e.last_transform != e.transform or e.bounds is None:
                try:
                    e.bounds = e.bbox(False)
                except AttributeError:
                    # Type does not have bbox.
                    continue
                e.last_transform = copy(e.transform)
            if e.bounds is None:
                continue
            if not e.emphasized:
                continue
            box = e.bounds
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)

        if len(boundary_points) == 0:
            new_bounds = None
        else:
            xmin = min([e[0] for e in boundary_points])
            ymin = min([e[1] for e in boundary_points])
            xmax = max([e[0] for e in boundary_points])
            ymax = max([e[1] for e in boundary_points])
            new_bounds = [xmin, ymin, xmax, ymax]
        if self._bounds != new_bounds:
            self._bounds = new_bounds
            self.context.signal('selected_bounds', self._bounds)

    def is_in_set(self, v, selected, flat=True):
        for q in selected:
            if flat and isinstance(q, (list, tuple)) and self.is_in_set(v, q, flat):
                return True
            if q is v:
                return True
        return False

    def set_selected(self, selected):
        """
        Sets selected and other properties of a given element.

        All selected elements are also semi-selected.

        If elements itself is selected, all subelements are semiselected.

        If any operation is selected, all sub-operations are highlighted.

        """
        if selected is None:
            selected = []
        for s in self._elements:
            should_select = self.is_in_set(s, selected, False)
            should_emphasize = self.is_in_set(s, selected)
            if s.emphasized:
                if not should_emphasize:
                    s.unemphasize()
            else:
                if should_emphasize:
                    s.emphasize()
            if s.selected:
                if not should_select:
                    s.unselect()
            else:
                if should_select:
                    s.select()
        for s in self._operations:
            should_select = self.is_in_set(s, selected, False)
            should_emphasize = self.is_in_set(s, selected)
            if s.emphasized:
                if not should_emphasize:
                    s.unemphasize()
            else:
                if should_emphasize:
                    s.emphasize()
            if s.selected:
                if not should_select:
                    s.unselect()
            else:
                if should_select:
                    s.select()

    def center(self):
        bounds = self._bounds
        return (bounds[2] + bounds[0]) / 2.0, (bounds[3] + bounds[1]) / 2.0

    def ensure_positive_bounds(self):
        b = self._bounds
        self._bounds = [min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])]
        self.context.signal('selected_bounds', self._bounds)

    def update_bounds(self, b):
        self._bounds = [b[0], b[1], b[0], b[1]]
        self.context.signal('selected_bounds', self._bounds)

    @staticmethod
    def bounding_box(elements):
        if isinstance(elements, SVGElement):
            elements = [elements]
        elif isinstance(elements, list):
            try:
                elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
            except AttributeError:
                pass
        boundary_points = []
        for e in elements:
            box = e.bbox(False)
            if box is None:
                continue
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)
        if len(boundary_points) == 0:
            return None
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        return xmin, ymin, xmax, ymax

    def move_selected(self, dx, dy):
        for obj in self.elems(emphasized=True):
            obj.transform.post_translate(dx, dy)
            obj.modified()

    def set_selected_by_position(self, position):
        def contains(box, x, y=None):
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        if self.has_emphasis():
            if self._bounds is not None and contains(self._bounds, position):
                return  # Select by position aborted since selection position within current select bounds.
        for e in reversed(list(self.elems())):
            try:
                bounds = e.bbox()
            except AttributeError:
                continue  # No bounds.
            if bounds is None:
                continue
            if contains(bounds, position):
                self.set_selected([e])
                return
        self.set_selected(None)

    def classify(self, elements):
        """
        Classify does the initial placement of elements as operations.
        "Image" is the default for images.
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        """
        if elements is None:
            return
        for element in elements:
            found_color = False
            try:
                stroke = element.stroke
            except AttributeError:
                stroke = None  # Element has no stroke.
            try:
                fill = element.fill
            except AttributeError:
                fill = None  # Element has no stroke.
            for op in self.ops():
                if op.operation in ("Engrave", "Cut", "Raster") and op.color == stroke:
                    op.append(element)
                    found_color = True
                elif op.operation == 'Image' and isinstance(element, SVGImage):
                    op.append(element)
                    found_color = True
                elif op.operation == 'Raster' and \
                        not isinstance(element, SVGImage) and \
                        fill is not None and \
                        fill.value is not None:
                    op.append(element)
                    found_color = True
            if not found_color:
                if stroke is not None and stroke.value is not None:
                    op = LaserOperation(operation="Engrave", color=stroke, speed=35.0)
                    op.append(element)
                    self.add_op(op)

    def load(self, pathname, **kwargs):
        kernel = self.context._kernel
        for loader_name in kernel.match('load'):
            loader = kernel.registered[loader_name]
            for description, extensions, mimetype in loader.load_types():
                if pathname.lower().endswith(extensions):
                    results = loader.load(self.context, pathname, **kwargs)
                    if results is None:
                        continue
                    elements, ops, note, pathname, basename = results
                    self._filenodes[pathname] = elements
                    self.add_elems(elements)
                    if ops is not None:
                        self.clear_operations()
                        self.add_ops(ops)
                    if note is not None:
                        self.clear_note()
                        self.note = note
                    return elements, pathname, basename
        return None

    def load_types(self, all=True):
        kernel = self.context._kernel
        filetypes = []
        if all:
            filetypes.append('All valid types')
            exts = []
            for loader_name in kernel.match('load'):
                loader = kernel.registered[loader_name]
                for description, extensions, mimetype in loader.load_types():
                    for ext in extensions:
                        exts.append('*.%s' % ext)
            filetypes.append(';'.join(exts))
        for loader_name in kernel.match('load'):
            loader = kernel.registered[loader_name]
            for description, extensions, mimetype in loader.load_types():
                exts = []
                for ext in extensions:
                    exts.append('*.%s' % ext)
                filetypes.append("%s (%s)" % (description, extensions[0]))
                filetypes.append(';'.join(exts))
        return "|".join(filetypes)

    def save(self, pathname):
        kernel = self.context._kernel
        for save_name in kernel.match('save'):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                if pathname.lower().endswith(extension):
                    saver.save(self.context, pathname, 'default')
                    return True
        return False

    def save_types(self):
        kernel = self.context._kernel
        filetypes = []
        for save_name in kernel.match('save'):
            saver = kernel.registered[save_name]
            for description, extension, mimetype in saver.save_types():
                filetypes.append("%s (%s)" % (description, extension))
                filetypes.append("*.%s" % (extension))
        return "|".join(filetypes)


class BindAlias(Modifier):
    """
    Functionality to add BindAlias commands.

    Stub.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        # Keymap/alias values
        self.keymap = {}
        self.alias = {}

    def attach(self, channel=None):
        self.context.keymap = self.keymap
        self.context.alias = self.alias
        self.context.default_keymap = self.default_keymap
        self.context.default_alias = self.default_alias

        def bind(command, *args):
            context = self.context
            _ = self.context._kernel.translation
            if len(args) == 0:
                yield _('----------')
                yield _('Binds:')
                for i, key in enumerate(context.keymap):
                    value = context.keymap[key]
                    yield _('%d: key %s -> %s') % (i, key, value)
                yield _('----------')
            else:
                key = args[0].lower()
                if key == 'default':
                    context.keymap = dict()
                    context.default_keymap()
                    yield _('Set default keymap.')
                    return
                command_line = ' '.join(args[1:])
                f = command_line.find('bind')
                if f == -1:  # If bind value has a bind, do not evaluate.
                    if '$x' in command_line:
                        try:
                            x = context.active.current_x
                        except AttributeError:
                            x = 0
                        command_line = command_line.replace('$x', str(x))
                    if '$y' in command_line:
                        try:
                            y = context.active.current_y
                        except AttributeError:
                            y = 0
                        command_line = command_line.replace('$y', str(y))
                if len(command_line) != 0:
                    context.keymap[key] = command_line
                else:
                    try:
                        del context.keymap[key]
                        yield _('Unbound %s') % key
                    except KeyError:
                        pass
            return

        self.context.register('command/bind', bind)

        def alias(command, *args):
            context = self.context
            _ = self.context._kernel.translation
            if len(args) == 0:
                yield _('----------')
                yield _('Aliases:')
                for i, key in enumerate(context.alias):
                    value = context.alias[key]
                    yield ('%d: %s -> %s') % (i, key, value)
                yield _('----------')
            else:
                key = args[0].lower()
                if key == 'default':
                    context.alias = dict()
                    context.default_alias()
                    yield _('Set default aliases.')
                    return
                context.alias[args[0]] = ' '.join(args[1:])
            return

        self.context.register('command/alias', alias)

        def server_console(command, *args):
            _ = self.context._kernel.translation
            port = 23
            try:
                self.context.open_as('module/TCPServer', 'console-server', port=port)
                send = self.context.channel('console-server/send')
                send.greet = "MeerK40t 0.7.0 Telnet Console.\r\n"
                send.line_end = '\r\n'
                recv = self.context.channel('console-server/recv')
                recv.watch(self.context.console)
                self.context.channel('console').watch(send)
            except OSError:
                yield _('Server failed on port: %d') % port
            return
        self.context.register('command/consoleserver', server_console)

    def boot(self, channel=None):
        self.boot_keymap()
        self.boot_alias()

    def shutdown(self, channel=None):
        self.save_keymap_alias()

    def save_keymap_alias(self):
        keys = self.context.derive('keymap')
        alias = self.context.derive('alias')

        keys._kernel.clear_persistent(keys._path)
        alias._kernel.clear_persistent(alias._path)

        for key in self.keymap:
            if key is None or len(key) == 0:
                continue
            keys._kernel.write_persistent(keys.abs_path(key), self.keymap[key])

        for key in self.alias:
            if key is None or len(key) == 0:
                continue
            alias._kernel.write_persistent(alias.abs_path(key), self.alias[key])

    def boot_keymap(self):
        self.keymap.clear()
        prefs = self.context.derive('keymap')
        prefs._kernel.load_persistent_string_dict(prefs._path, self.keymap)
        if not len(self.keymap):
            self.default_keymap()

    def boot_alias(self):
        self.alias.clear()
        prefs = self.context.derive('alias')
        prefs._kernel.load_persistent_string_dict(prefs._path, self.alias)
        if not len(self.alias):
            self.default_alias()

    def default_keymap(self):
        self.keymap["escape"] = "window open Adjustments"
        self.keymap["d"] = "+right"
        self.keymap["a"] = "+left"
        self.keymap["w"] = "+up"
        self.keymap["s"] = "+down"
        self.keymap['numpad_down'] = '+translate_down'
        self.keymap['numpad_up'] = '+translate_up'
        self.keymap['numpad_left'] = '+translate_left'
        self.keymap['numpad_right'] = '+translate_right'
        self.keymap['numpad_multiply'] = '+scale_up'
        self.keymap['numpad_divide'] = '+scale_down'
        self.keymap['numpad_add'] = '+rotate_cw'
        self.keymap['numpad_subtract'] = '+rotate_ccw'
        self.keymap['control+a'] = 'element *'
        self.keymap['control+i'] = 'element ~'
        self.keymap['control+f'] = 'control Fill'
        self.keymap['control+s'] = 'control Stroke'
        self.keymap['control+r'] = 'rect 0 0 1000 1000'
        self.keymap['control+e'] = 'circle 500 500 500'
        self.keymap['control+d'] = 'element copy'
        self.keymap['control+shift+h'] = 'scale -1 1'
        self.keymap['control+shift+v'] = 'scale 1 -1'
        self.keymap['control+1'] = "bind 1 move $x $y"
        self.keymap['control+2'] = "bind 2 move $x $y"
        self.keymap['control+3'] = "bind 3 move $x $y"
        self.keymap['control+4'] = "bind 4 move $x $y"
        self.keymap['control+5'] = "bind 5 move $x $y"
        self.keymap['alt+r'] = 'raster'
        self.keymap['alt+e'] = 'engrave'
        self.keymap['alt+c'] = 'cut'
        self.keymap['delete'] = 'element delete'
        self.keymap['f4'] = "window open CameraInterface"
        self.keymap['f5'] = "refresh"
        self.keymap['f6'] = "window open JobSpooler"
        self.keymap['f7'] = "window open Controller"
        self.keymap['f8'] = "control Path"
        self.keymap['f9'] = "control Transform"
        self.keymap['control+f9'] = "control Flip"
        self.keymap['f12'] = "window open Terminal"
        self.keymap['control+alt+g'] = "image wizard Gold"
        self.keymap['control+alt+x'] = "image wizard Xin"
        self.keymap['control+alt+s'] = "image wizard Stipo"
        self.keymap['alt+f12'] = "terminal_ruida"
        self.keymap['alt+f11'] = 'terminal_watch'
        self.keymap['pause'] = "control Realtime Pause_Resume"
        self.keymap['home'] = "home"
        self.keymap['control+z'] = "reset"
        self.keymap['control+alt+shift+escape'] = 'reset_bind_alias'

    def default_alias(self):
        self.alias['+scale_up'] = "loop scale 1.02"
        self.alias['+scale_down'] = "loop scale 0.98"
        self.alias['+rotate_cw'] = "loop rotate 2"
        self.alias['+rotate_ccw'] = "loop rotate -2"
        self.alias['+translate_right'] = "loop translate 1mm 0"
        self.alias['+translate_left'] = "loop translate -1mm 0"
        self.alias['+translate_down'] = "loop translate 0 1mm"
        self.alias['+translate_up'] = "loop translate 0 -1mm"
        self.alias['+right'] = "loop right 1mm"
        self.alias['+left'] = "loop left 1mm"
        self.alias['+up'] = "loop up 1mm"
        self.alias['+down'] = "loop down 1mm"
        self.alias['-scale_up'] = "end scale 1.02"
        self.alias['-scale_down'] = "end scale 0.98"
        self.alias['-rotate_cw'] = "end rotate 2"
        self.alias['-rotate_ccw'] = "end rotate -2"
        self.alias['-translate_right'] = "end translate 1mm 0"
        self.alias['-translate_left'] = "end translate -1mm 0"
        self.alias['-translate_down'] = "end translate 0 1mm"
        self.alias['-translate_up'] = "end translate 0 -1mm"
        self.alias['-right'] = "end right 1mm"
        self.alias['-left'] = "end left 1mm"
        self.alias['-up'] = "end up 1mm"
        self.alias['-down'] = "end down 1mm"
        self.alias['terminal_ruida'] = "window open Terminal;ruidaserver"
        self.alias['terminal_watch'] = "window open Terminal;channel save usb;channel save send;channel save recv"
        self.alias['reset_bind_alias'] = "bind default;alias default"


class Context:
    """
    Contexts serve as path relevant snapshots of the kernel. These are are the primary interaction between the modules
    and the kernel. They permit getting other contexts of the kernel as well. This should serve as the primary interface
    code between the kernel and the modules.
    """

    def __init__(self, kernel, path):
        self._kernel = kernel
        self._path = path
        self._state = STATE_UNKNOWN
        self.opened = {}
        self.attached = {}

    def __str__(self):
        return "Context('%s')" % self._path

    def boot(self, channel=None):
        """
        Boot calls all attached modifiers with the boot command.

        :param channel:
        :return:
        """
        for opened_name in self.opened:
            opened = self.opened[opened_name]
        for attached_name in self.attached:
            attached = self.attached[attached_name]
            attached.boot(channel=channel)

    def abs_path(self, subpath):
        """
        The absolute path function determines the absolute path of the given subpath within the current path of the
        context.

        :param subpath: relative path to the path at this context
        :return:
        """
        subpath = str(subpath)
        if subpath.startswith('/'):
            return subpath[1:]
        if self._path is None or self._path == '/':
            return subpath
        return "%s/%s" % (self._path, subpath)

    def derive(self, path):
        """
        Derive a subpath context.

        :param path:
        :return:
        """
        return self._kernel.get_context(self.abs_path(path))

    def get_context(self, path):
        """
        Get a context at a given path location.

        :param path: path location to get a context.
        :return:
        """
        return self._kernel.get_context(path)

    def derivable(self):
        """
        Generate all sub derived paths.

        :return:
        """
        for e in self._kernel.derivable(self._path):
            yield e

    def setting(self, setting_type, key, default=None):
        """
        Registers a setting to be used between modules.

        If the setting exists, its value remains unchanged.
        If the setting exists in the persistent storage that value is used.
        If there is no settings value, the default will be used.

        :param setting_type: int, float, str, or bool value
        :param key: name of the setting
        :param default: default value for the setting to have.
        :return: load_value
        """
        if hasattr(self, key) and getattr(self, key) is not None:
            return getattr(self, key)

        # Key is not located in the attr. Load the value.
        if not key.startswith('_'):
            load_value = self._kernel.read_persistent(setting_type, self.abs_path(key), default)
        else:
            load_value = default
        setattr(self, key, load_value)
        return load_value

    def flush(self):
        """
        Commit any and all values currently stored as attr for this object to persistent storage.
        """
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, (int, bool, str, float, Color)):
                self._kernel.write_persistent(self.abs_path(attr), value)

    def execute(self, control):
        """
        Execute the given control code relative to the path of this context.

        :param control: Function to execute relative to the current position.
        :return:
        """
        try:
            funct = self._kernel.registered[self.abs_path("control/%s" % control)]
        except KeyError:
            return
        funct()

    def register(self, path, obj):
        """
        Register a object at a relative path to the current location.

        :param path: Path postion within this context to register an object.
        :param obj: Object to register.
        :return:
        """
        self._kernel.register(self.abs_path(path), obj)

    @property
    def registered(self):
        return self._kernel.registered

    @property
    def active(self):
        return self._kernel.active

    @property
    def contexts(self):
        return self._kernel.contexts

    def match(self, matchtext, suffix=False):
        """
        Delegate of Kernel match.
        :param matchtext:  regex matchtext to locate.
        :yield: matched entries.
        """
        for m in self._kernel.match(matchtext):
            if suffix:
                yield list(m.split('/'))[-1]
            else:
                yield m

    def find(self, path):
        """
        Finds a loaded instance. Or returns None if not such instance.

        Note: 'name' is not necessarily the type of instance. It could be the named value of the instance.

        :param path: The opened path to find the given instance.
        :return: The instance, if found, otherwise None.
        """
        try:
            return self.opened[path]
        except KeyError:
            return None

    def open(self, registered_path, *args, **kwargs):
        """
        Opens a registered module with the same instance path as the registered path. This is fairly standard but should
        not be used if the goal would be to open the same module several times.

        :param registered_path: registered path of the given module.
        :param args: args to open the module with.
        :param kwargs: kwargs to open the module with.
        :return:
        """
        return self.open_as(registered_path, registered_path, *args, **kwargs)

    def open_as(self, registered_path, instance_path, *args, **kwargs):
        """
        Opens a registered module. If that module already exists it returns the already open module.

        Instance_name is the name under which this given module is opened.

        If the module already exists, the restore function is called on that object, if restore() exists, with the same
        args and kwargs that were intended for the init() routine.

        :param registered_path: path of object being opened.
        :param instance_path: path of object should be attached.
        :param args: Args to pass to newly opened module.
        :param kwargs: Kwargs to pass to newly opened module.
        :return: Opened module.
        """
        try:
            find = self.opened[instance_path]
            try:
                find.restore(*args, **kwargs)
            except AttributeError:
                pass
            return find
        except KeyError:
            pass

        try:
            open_object = self._kernel.registered[registered_path]
        except KeyError:
            raise ValueError

        instance = open_object(self, instance_path, *args, **kwargs)
        channel = self._kernel.channel('open')
        instance.initialize(channel=channel)

        self.opened[instance_path] = instance
        return instance

    def close(self, instance_path):
        """
        Closes an opened instance. Located at the instance_path location.

        This calls the close() function on the object (which may not exist). And calls finalize() on the module,
        which should exist.

        :param instance_path: Instance path to close.
        :return:
        """
        try:
            instance = self.opened[instance_path]
        except KeyError:
            return  # Nothing to close. Return.
        try:
            instance.close()
        except AttributeError:
            pass
        instance.finalize(self._kernel.channel('close'))
        try:
            del self.opened[instance_path]
        except KeyError:
            pass

    def activate(self, registered_path, *args, **kwargs):
        """
        Activates a modifier at this context. The activate calls and attaches a modifier located at the given path
        to be attached to this context.

        The modifier is opened and attached at the current context.

        :param registered_path: registered_path location of the modifier.
        :param args: arguments to call the modifier
        :param kwargs: kwargs to call the modifier
        :return: Modifier object.
        """
        try:
            open_object = self._kernel.registered[registered_path]
        except KeyError:
            raise ValueError

        try:
            instance = open_object(self, registered_path, *args, **kwargs)
            self.attached[registered_path] = instance
            instance.attach(self)
            return instance
        except AttributeError:
            return None

    def deactivate(self, instance_path):
        """
        Deactivate a modifier attached to this context.
        The modifier is deleted from the list of attached and detach() is called on the modifier.

        :param instance_path: Attached path location.
        :return:
        """
        try:
            instance = self.attached[instance_path]
            del self.attached[instance_path]
            instance.detach(self)
        except (KeyError, AttributeError):
            pass

    def load_persistent_object(self, obj):
        """
        Loads values of the persistent attributes, at this context and assigns them to the provided object.

        The attribute type of the value depends on the provided object value default values.

        :param obj:
        :return:
        """
        for attr in dir(obj):
            if attr.startswith('_'):
                continue
            obj_value = getattr(obj, attr)

            if not isinstance(obj_value, (int, float, str, bool, Color)):
                continue
            load_value = self._kernel.read_persistent(type(obj_value), self.abs_path(attr))
            setattr(obj, attr, load_value)
            setattr(self, attr, load_value)

    def set_attrib_keys(self):
        """
        Iterate all the entries keys for the registered persistent settings, adds a None attribute for any key that
        exists.

        :return:
        """
        for k in self._kernel.keylist(self._path):
            if not hasattr(self, k):
                setattr(self, k, None)

    def signal(self, code, *message):
        """
        Signal delegate to the kernel.
        :param code: Code to delegate at this given context location.
        :param message: Message to send.
        :return:
        """
        self._kernel.signal(self.abs_path(code), *message)

    def last_signal(self, code):
        """
        Last Signal delegate to the kernel.

        :param code: Code to delegate at this given context location.
        :return: message value of the last signal sent for that code.
        """
        return self._kernel.last_signal(self.abs_path(code))

    def listen(self, signal, process):
        """
        Listen delegate to the kernel.

        :param signal: Signal code to listen for
        :param process: listener to be attached
        :return:
        """
        self._kernel.listen(self.abs_path(signal), process)

    def unlisten(self, signal, process):
        """
        Unlisten delegate to the kernel.

        :param signal: Signal to unlisten for.
        :param process: listener that is to be detached.
        :return:
        """
        self._kernel.unlisten(self.abs_path(signal), process)

    def channel(self, channel, *args, **kwargs):
        """
        Channel channel_open delegate to the kernel.

        :param channel: Channel to be opened.
        :param buffer: Buffer to be applied to the given channel and sent to any watcher upon connection.
        :return: Channel object that is opened.
        """
        return self._kernel.channel(self.abs_path(channel), *args, **kwargs)

    def console_function(self, data):
        return ConsoleFunction(self, data)

    def console(self, data):
        self._kernel.console(data)

    def schedule(self, job):
        self._kernel.schedule(job)

    def unschedule(self, job):
        self._kernel.unschedule(job)

    def threaded(self, func, thread_name=None):
        self._kernel.threaded(func, thread_name=thread_name)


class ConsoleFunction:
    def __init__(self, context, data):
        self.context = context
        self.data = data

    def __call__(self, *args, **kwargs):
        self.context.console(self.data)

    def __repr__(self):
        return self.data.replace('\n', '')


class Channel:
    def __init__(self, name, buffer_size=0, line_end=None):
        self.watchers = []
        self.greet = None
        self.name = name
        self.buffer_size = buffer_size
        self.line_end = line_end
        if buffer_size == 0:
            self.buffer = None
        else:
            self.buffer = list()

    def __call__(self, message, *args, **kwargs):
        if self.line_end is not None:
            message = message + self.line_end
        for w in self.watchers:
            w(message)
        if self.buffer is not None:
            self.buffer.append(message)
            if len(self.buffer) + 10 > self.buffer_size:
                self.buffer = self.buffer[-self.buffer_size:]

    def __len__(self):
        return self.buffer_size

    def __iadd__(self, other):
        self.watch(monitor_function=other)

    def __isub__(self, other):
        self.unwatch(monitor_function=other)

    def watch(self, monitor_function):
        for q in self.watchers:
            if q is monitor_function:
                return  # This is already being watched by that.
        self.watchers.append(monitor_function)
        if self.greet is not None:
            monitor_function(self.greet)
        if self.buffer is not None:
            for line in self.buffer:
                monitor_function(line)

    def unwatch(self, monitor_function):
        self.watchers.remove(monitor_function)


class Kernel:
    """
    The Kernel serves as the central hub of communication between different objects within the system. These are mapped
    to particular contexts that have locations within the kernel. The contexts can have modules opened and modifiers
    applied to them. The kernel serves to store the location of registered objects, as well as providing a scheduler,
    signals, channels, and a command console to be used by the modules, modifiers, devices, and other objects.

    The Kernel stores a persistence object, thread interactions, contexts, a translation routine, a run_later operation,
    jobs for the scheduler, listeners for signals, channel information, a list of devices, registered commands.

    Devices are contexts with a device. These are expected to have a Spooler attached, and the path should consist
    of numbers.
    """

    def __init__(self, config=None):
        self.devices = {}
        self.active = None

        self.contexts = {}
        self.threads = {}
        self.registered = {}
        self.translation = lambda e: e
        self.run_later = lambda listener, message: listener(message)
        self.state = STATE_INITIALIZE
        self.jobs = {}

        self.thread = None

        self.signal_job = None
        self.listeners = {}
        self.adding_listeners = []
        self.removing_listeners = []
        self.last_message = {}
        self.queue_lock = Lock()
        self.message_queue = {}
        self._is_queue_processing = False

        self.channels = {}

        self.commands = []
        self.console_job = Job(name="kernel.console.ticks", process=self._console_tick, interval=0.05)
        self._console_buffer = ''
        self.queue = []
        self._console_channel = self.channel('console')
        self.console_channel_file = None

        if config is not None:
            self.set_config(config)
        else:
            self._config = None

    @staticmethod
    def sub_register(device):
        device.register('modifier/Elemental', Elemental)
        device.register('modifier/Spooler', Spooler)
        device.register('modifier/BindAlias', BindAlias)

    def __str__(self):
        return "Kernel()"

    def __setitem__(self, key, value):
        """
        Kernel value settings. If Config is registered this will be persistent.

        :param key: Key to set.
        :param value: Value to set
        :return: None
        """
        if isinstance(key, str):
            self.write_persistent(key, value)

    def __getitem__(self, item):
        """
        Kernel value get. If Config is set registered this will be persistent.

        As a shorthand any float, int, string, or bool set with this will also be found at kernel.item

        :param item:
        :return:
        """
        if isinstance(item, tuple):
            if len(item) == 2:
                t, key = item
                return self.read_persistent(t, key)
            else:
                t, key, default = item
                return self.read_persistent(t, key, default)
        return self.read_item_persistent(item)

    def _start_debugging(self):
        """
        Debug function hooks all functions within the device with a debug call that saves the data to the disk and
        prints that information.

        :return:
        """
        import functools
        import datetime
        import types
        filename = "MeerK40t-debug-{date:%Y-%m-%d_%H_%M_%S}.txt".format(date=datetime.datetime.now())
        debug_file = open(filename, "a")
        debug_file.write("\n\n\n")

        def debug(func, obj):
            @functools.wraps(func)
            def wrapper_debug(*args, **kwargs):
                args_repr = [repr(a) for a in args]

                kwargs_repr = ["%s=%s" % (k, v) for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                start = "Calling %s.%s(%s)" % (str(obj), func.__name__, signature)
                debug_file.write(start + '\n')
                print(start)
                t = time.time()
                value = func(*args, **kwargs)
                t = time.time() - t
                finish = "    %s returned %s after %fms" % (func.__name__, value, t * 1000)
                print(finish)
                debug_file.write(finish + '\n')
                debug_file.flush()
                return value

            return wrapper_debug

        attach_list = [modules for modules, module_name in self.opened.items()]
        attach_list.append(self)
        for obj in attach_list:
            for attr in dir(obj):
                if attr.startswith('_'):
                    continue
                fn = getattr(obj, attr)
                if not isinstance(fn, types.FunctionType) and \
                        not isinstance(fn, types.MethodType):
                    continue
                setattr(obj, attr, debug(fn, obj))

    def get_context(self, path):
        """
        Create a context derived from this kernel, at the given path.

        If this has been created previously, then return the previous object.

        :param path: path of context being gotten
        :return: Context object.
        """
        try:
            return self.contexts[path]
        except KeyError:
            pass
        derive = Context(self, path=path)
        self.contexts[path] = derive
        return derive

    def match(self, matchtext):
        """
        Lists all registered paths that regex match the given matchtext

        :param matchtext: match text to match.
        :return:
        """
        match = re.compile(matchtext)
        for r in self.registered:
            if match.match(r):
                yield r

    def read_item_persistent(self, key):
        """Directly read from persistent storage the value of an item."""
        if self._config is None:
            return None
        return self._config.Read(key)

    def read_persistent(self, t, key, default=None):
        """
        Directly read from persistent storage the value of an item.

        :param t: datatype.
        :param key: key used to reference item.
        :param default: default value if item does not exist.
        :return: value
        """
        if self._config is None:
            return default
        if default is not None:
            if t == str:
                return self._config.Read(key, default)
            elif t == int:
                return self._config.ReadInt(key, default)
            elif t == float:
                return self._config.ReadFloat(key, default)
            elif t == bool:
                return self._config.ReadBool(key, default)
            elif t == Color:
                return self._config.ReadInt(key, default)
        else:
            if t == str:
                return self._config.Read(key)
            elif t == int:
                return self._config.ReadInt(key)
            elif t == float:
                return self._config.ReadFloat(key)
            elif t == bool:
                return self._config.ReadBool(key)
            elif t == Color:
                return self._config.ReadInt(key)
        return default

    def write_persistent(self, key, value):
        """
        Directly write the value to persistent storage.

        :param key: The item key being read.
        :param value: the value of the item.
        """
        if self._config is None:
            return
        if isinstance(value, str):
            self._config.Write(key, value)
        elif isinstance(value, int):
            self._config.WriteInt(key, value)
        elif isinstance(value, float):
            self._config.WriteFloat(key, value)
        elif isinstance(value, bool):
            self._config.WriteBool(key, value)
        elif isinstance(value, Color):
            self._config.WriteInt(key, value)

    def clear_persistent(self, path):
        if self._config is None:
            return
        self._config.DeleteGroup(path)

    def delete_persistent(self, key):
        if self._config is None:
            return
        self._config.DeleteEntry(key)

    def load_persistent_string_dict(self, path, dictionary=None):
        if dictionary is None:
            dictionary = dict()
        for k in list(self.keylist(path)):
            dictionary[k] = self.read_item_persistent(k)
        return dictionary

    def keylist(self, path):
        if self._config is None:
            return
        self._config.SetPath(path)
        more, value, index = self._config.GetFirstEntry()
        while more:
            yield "%s/%s" % (path, value)
            more, value, index = self._config.GetNextEntry(index)
        self._config.SetPath('/')

    def derivable(self, path):
        if self._config is None:
            return
        self._config.SetPath(path)
        more, value, index = self._config.GetFirstGroup()
        while more:
            yield value
            more, value, index = self._config.GetNextGroup(index)
        self._config.SetPath('/')

    def set_config(self, config):
        """
        Set the config object.

        :param config: Persistent storage object.
        :return:
        """
        if config is None:
            return
        self._config = config

    def register(self, path, obj):
        """
        Register an element at a given subpath. If this Kernel is not root. Then
        it is registered relative to this location.

        :param path:
        :param obj:
        :return:
        """
        self.registered[path] = obj
        try:
            obj.sub_register(self)
        except AttributeError:
            pass

    def threaded(self, func, thread_name=None):
        """
        Register a thread, and run the provided function with the name if needed. When the function finishes this thread
        will exit, and deregister itself. During shutdown any active threads created will be told to stop and the kernel
        will wait until such time as it stops.

        :param func: The function to be executed.
        :param thread_name: The name under which the thread should be registered.
        :return: The thread object created.
        """
        if thread_name is None:
            thread_name = func.__name__
        thread = Thread(name=thread_name)

        def run():
            self.threads[thread_name] = thread
            # try:
            func()
            # except:
            #     import sys
            #     sys.excepthook(*sys.exc_info())
            del self.threads[thread_name]

        thread.run = run
        thread.start()
        return thread

    def boot(self):
        """
        Kernel boot sequence. This should be called after all the registered devices are established.

        :return:
        """
        self.thread = self.threaded(self.run, 'Scheduler')
        self.signal_job = self.add_job(run=self.delegate_messages, name='kernel.signals', interval=0.005)
        for context_name in list(self.contexts):
            context = self.contexts[context_name]
            try:
                context.boot()
            except AttributeError:
                pass
        self.set_active(None)
        for device in self.derivable('/'):
            try:
                d = int(device)
            except ValueError:
                # Devices are marked as integers.
                continue
            self.device_boot(d)

    def device_boot(self, d, device_name=None, autoboot=True):
        device_str = str(d)
        if device_str in self.devices:
            return self.devices[device_str]
        boot_device = self.get_context(device_str)
        boot_device.setting(str, 'device_name', device_name)
        boot_device.setting(bool, 'autoboot', autoboot)
        if boot_device.autoboot and boot_device.device_name is not None:
            boot_device.activate("device/%s" % boot_device.device_name)
            try:
                boot_device.boot()
            except AttributeError:
                pass
            self.devices[device_str] = boot_device
            self.set_active(boot_device)

    def set_active(self, active):
        old_active = self.active
        self.active = active
        self.signal('active', old_active, self.active)

    def shutdown(self, channel=None):
        """
        Starts full shutdown procedure. Each registered context is shutdown.

        :param channel:
        :return:
        """
        _ = self.translation

        def signal(code, *message):
            channel(_("Suspended Signal: %s for %s" % (code, message)))

        self.signal = signal

        for context_name in list(self.contexts):
            context = self.contexts[context_name]
            channel(_("Context Shutdown Started: '%s'") % str(context))
            context.flush()
            channel(_("Saving Context State: '%s'") % str(context))
            # Stop all instances
            for opened_name in list(context.opened):
                obj = context.opened[opened_name]
                try:
                    obj.stop()
                    channel(_("Stopping %s: %s") % (opened_name, str(obj)))
                except AttributeError:
                    pass
                channel(_("Closing %s: %s") % (opened_name, str(obj)))
                context.close(opened_name)

            for attached_name in list(context.attached):
                obj = context.attached[attached_name]
                try:
                    obj.shutdown(channel=channel)
                    channel(_("Shutdown-modifier %s: %s") % (attached_name, str(obj)))
                except AttributeError:
                    pass
                channel(_("Detaching %s: %s") % (attached_name, str(obj)))
                context.deactivate(attached_name)

            del self.contexts[context_name]
            channel(_("Context Shutdown Finished: '%s'") % str(context))
        channel(_("Shutting down."))

        # Stop/Wait for all threads
        thread_count = 0
        for thread_name in list(self.threads):
            thread_count += 1
            try:
                thread = self.threads[thread_name]
            except KeyError:
                channel(_("Thread %s exited safely") % (thread_name))
                continue

            if not thread.is_alive:
                channel(_("WARNING: Dead thread %s still registered to %s.") % (thread_name, str(thread)))
                continue

            channel(_("Finishing Thread %s for %s") % (thread_name, str(thread)))
            try:
                if thread is self.thread:
                    channel(_("%s is the current shutdown thread") % (thread_name))
                    continue
                channel(_("Asking thread to stop."))
                thread.stop()
            except AttributeError:
                pass
            channel(_("Waiting for thread %s: %s") % (thread_name, str(thread)))
            thread.join()
            channel(_("Thread %s has finished. %s") % (thread_name, str(thread)))
        if thread_count == 0:
            channel(_("No threads required halting."))

        for key, listener in self.listeners.items():
            if len(listener):
                if channel is not None:
                    channel(_("WARNING: Listener '%s' still registered to %s.") % (key, str(listener)))
        self.last_message = {}
        self.listeners = {}
        self.state = STATE_TERMINATE
        self.thread.join()
        channel(_("Shutdown."))

    def get_text_thread_state(self, state):
        _ = self.translation
        if state == STATE_INITIALIZE:
            return _("Unstarted")
        elif state == STATE_TERMINATE:
            return _("Abort")
        elif state == STATE_END:
            return _("Finished")
        elif state == STATE_PAUSE:
            return _("Pause")
        elif state == STATE_BUSY:
            return _("Busy")
        elif state == STATE_ACTIVE:
            return _("Active")
        elif state == STATE_IDLE:
            return _("Idle")
        elif state == STATE_UNKNOWN:
            return _("Unknown")

    def run(self):
        """
        Scheduler main loop.

        Check the Scheduler thread state, and whether it should abort or pause.
        Check each job, and if that job is scheduled to run. Executes that job.
        :return:
        """
        self.state = STATE_ACTIVE
        while self.state != STATE_END:
            time.sleep(0.005)  # 200 ticks a second.
            if self.state == STATE_TERMINATE:
                break
            while self.state == STATE_PAUSE:
                # The scheduler is paused.
                time.sleep(0.1)
            if self.state == STATE_TERMINATE:
                break
            jobs = self.jobs
            for job_name in list(jobs):
                job = jobs[job_name]

                # Checking if jobs should run.
                if job.scheduled:
                    job._next_run = 0  # Set to zero while running.
                    if job.times is not None:
                        job.times = job.times - 1
                        if job.times <= 0:
                            del jobs[job_name]
                        if job.times < 0:
                            continue
                    try:
                        if isinstance(jobs, int):
                            job.process(job.args[0])
                        elif isinstance(job.args, tuple):
                            job.process(*job.args)
                        else:
                            job.process(job.args)
                    except:
                        import sys
                        sys.excepthook(*sys.exc_info())
                    job._last_run = time.time()
                    job._next_run += job._last_run + job.interval
        self.state = STATE_END

    def schedule(self, job):
        self.jobs[job.name] = job
        return job

    def unschedule(self, job):
        del self.jobs[job.name]
        return job

    def add_job(self, run, name=None, args=(), interval=1.0, times=None):
        """
        Adds a job to the scheduler.

        :param run: function to run
        :param args: arguments to give to that function.
        :param interval: in seconds, how often should the job be run.
        :param times: limit on number of executions.
        :return: Reference to the job added.
        """

        job = Job(name=name, process=run, args=args, interval=interval, times=times)
        return self.schedule(job)

    def remove_job(self, job):
        return self.unschedule(job)

    def set_timer(self, command, name=None, times=1, interval=1.0):
        def timer():
            self.console("%s\n" % command)

        if name is None or len(name) == 0:
            i = 1
            while 'timer%d' % i in self.jobs:
                i += 1
            name = 'timer%d' % i
        if not name.startswith('timer'):
            name = 'timer' + name
        self.add_job(timer, name=name, interval=interval, times=times)

    # Signal processing.

    def signal(self, code, *message):
        """
        Signals add the latest message to the message queue.

        :param code: Signal code
        :param message: Message to send.
        """
        self.queue_lock.acquire(True)
        self.message_queue[code] = message
        self.queue_lock.release()

    def delegate_messages(self):
        """
        Delegate the process queue to the run_later thread.
        run_later should be a threading instance wherein all signals are delivered.
        """
        if self._is_queue_processing:
            return
        if self.run_later is not None:
            self.run_later(self.process_queue, None)
        else:
            self.process_queue(None)

    def process_queue(self, *args):
        """
        Performed in the run_later thread. Signal groups. Threadsafe.

        Process the signals queued up. Inserting any attaching listeners, removing any removing listeners. And
        providing the newly attached listeners the last message known from that signal.
        :param args: None
        :return:
        """
        if len(self.message_queue) == 0 and len(self.adding_listeners) == 0 and len(self.removing_listeners) == 0:
            return
        self._is_queue_processing = True
        add = None
        remove = None
        self.queue_lock.acquire(True)
        queue = self.message_queue
        if len(self.adding_listeners) != 0:
            add = self.adding_listeners
            self.adding_listeners = []
        if len(self.removing_listeners):
            remove = self.removing_listeners
            self.removing_listeners = []
        self.message_queue = {}
        self.queue_lock.release()
        if add is not None:
            for signal, funct in add:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    listeners.append(funct)
                else:
                    self.listeners[signal] = [funct]
                if signal in self.last_message:
                    last_message = self.last_message[signal]
                    funct(*last_message)
        if remove is not None:
            for signal, funct in remove:
                if signal in self.listeners:
                    listeners = self.listeners[signal]
                    try:
                        listeners.remove(funct)
                    except ValueError:
                        print("Value error removing: %s  %s" % (str(listeners), signal))

        for code, message in queue.items():
            if code in self.listeners:
                listeners = self.listeners[code]
                for listener in listeners:
                    listener(*message)
            self.last_message[code] = message
        self._is_queue_processing = False

    def last_signal(self, code):
        """
        Queries the last signal for a particular code.
        :param code: code to query.
        :return: Last signal sent through the kernel for that code.
        """
        try:
            return self.last_message[code]
        except KeyError:
            return None

    def listen(self, signal, funct):
        self.queue_lock.acquire(True)
        self.adding_listeners.append((signal, funct))
        self.queue_lock.release()

    def unlisten(self, signal, funct):
        self.queue_lock.acquire(True)
        self.removing_listeners.append((signal, funct))
        self.queue_lock.release()

    # Channel processing.

    def channel(self, channel, *args, **kwargs):
        if channel not in self.channels:
            self.channels[channel] = Channel(channel, *args, **kwargs)
        return self.channels[channel]

    # Console Processing.

    def console(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        self._console_buffer += data
        while '\n' in self._console_buffer:
            pos = self._console_buffer.find('\n')
            command = self._console_buffer[0:pos].strip('\r')
            self._console_buffer = self._console_buffer[pos + 1:]
            for response in self._console_interface(command):
                self._console_channel(response)

    def _console_tick(self):
        for command in self.commands:
            for e in self._console_interface(command):
                if self._console_channel is not None:
                    self._console_channel(e)
        if len(self.queue):
            for command in self.queue:
                for e in self._console_interface(command):
                    if self._console_channel is not None:
                        self._console_channel(e)
            self.queue.clear()
        if len(self.commands) == 0 and len(self.queue) == 0:
            self.remove_job(self.console_job)

    def _console_queue(self, command):
        self.queue = [c for c in self.queue if c != command]  # Only allow 1 copy of any command.
        self.queue.append(command)
        if self.console_job not in self.jobs:
            self.jobs.append(self.console_job)

    def _tick_command(self, command):
        self.commands = [c for c in self.commands if c != command]  # Only allow 1 copy of any command.
        self.commands.append(command)
        if self.console_job not in self.jobs:
            self.jobs.append(self.console_job)

    def _untick_command(self, command):
        self.commands = [c for c in self.commands if c != command]
        if len(self.commands) == 0:
            self.remove_job(self.console_job)

    def _console_file_write(self, v):
        if self.console_channel_file is not None:
            self.console_channel_file.write('%s\r\n' % v)
            self.console_channel_file.flush()

    def _console_interface(self, command):
        yield command
        args = str(command).split(' ')
        for e in self._console_parse(*args):
            yield e

    def _console_parse(self, command, *args):
        _ = self.translation
        active_context = self.active
        command = command.lower()
        if command == 'help' or command == '?':
            yield 'loop <command>'
            yield 'end <commmand>'
            yield '-------------------'
            yield 'device [<value>]'
            yield 'set [<key> <value>]'
            yield 'control [<executive>]'
            yield 'module [(open|close) <module_name>]'
            yield 'modifier [(open|close) <module_name>]'
            yield 'schedule'
            yield 'channel [(open|close|save) <channel_name>]'
            yield 'shutdown'
            return
        # +- controls.
        elif command == "loop":
            self._tick_command(' '.join(args))
            return
        elif command == "end":
            if len(args) == 0:
                self.commands.clear()
                self.remove_job(self.console_job)
            else:
                self._untick_command(' '.join(args))
        elif command.startswith("timer"):
            name = command[5:]
            if len(args) == 0:
                yield _('----------')
                yield _('Timers:')
                for i, job_name in enumerate(self.jobs):
                    if not job_name.startswith('timer'):
                        continue
                    obj = self.jobs[job_name]
                    yield _('%d: %s %s') % (i + 1, job_name, str(obj))
                yield _('----------')
                return
            if len(args) == 1:
                if args[0] == 'off':
                    obj = self.jobs[command]
                    obj.cancel()
                    self.unschedule(obj)
                    yield _("timer %s canceled." % command)
                return
            if len(args) == 2:
                yield _("Syntax Error: timer<name> <times> <interval> <command>")
                return
            try:
                self.set_timer(' '.join(args[2:]), name=name, times=int(args[0]), interval=float(args[1]))
            except ValueError:
                yield _("Syntax Error: timer<name> <times> <interval> <command>")
            return

        # Kernel Element commands.
        elif command == 'register':
            if len(args) == 0:
                yield _('----------')
                yield _('Objects Registered:')
                for i, name in enumerate(self.match('.*')):
                    obj = self.registered[name]
                    yield _('%d: %s type of %s') % (i + 1, name, str(obj))
                yield _('----------')
            if len(args) == 1:
                yield _('----------')
                yield 'Objects Registered:'
                for i, name in enumerate(self.match('%s.*' % args[0])):
                    obj = self.registered[name]
                    yield '%d: %s type of %s' % (i + 1, name, str(obj))
                yield _('----------')
        elif command == 'context':
            if len(args) == 0:
                for control_name in active_context.match('\d+/control'):
                    yield control_name
            else:
                control_name = ' '.join(args)
                if control_name in active_context.match('\d+/control'):
                    active_context.execute(control_name)
                    yield _("Executed '%s'") % control_name
                else:
                    yield _("Control '%s' not found.") % control_name
            return
        elif command == 'set':
            if len(args) == 0:
                for attr in dir(active_context):
                    v = getattr(active_context, attr)
                    if attr.startswith('_') or not isinstance(v, (int, float, str, bool)):
                        continue
                    yield '"%s" := %s' % (attr, str(v))
                return
            if len(args) >= 2:
                attr = args[0]
                value = args[1]
                try:
                    if hasattr(active_context, attr):
                        v = getattr(active_context, attr)
                        if isinstance(v, bool):
                            if value == 'False' or value == 'false' or value == 0:
                                setattr(active_context, attr, False)
                            else:
                                setattr(active_context, attr, True)
                        elif isinstance(v, int):
                            setattr(active_context, attr, int(value))
                        elif isinstance(v, float):
                            setattr(active_context, attr, float(value))
                        elif isinstance(v, str):
                            setattr(active_context, attr, str(value))
                except RuntimeError:
                    yield _('Attempt failed. Produced a runtime error.')
                except ValueError:
                    yield _('Attempt failed. Produced a value error.')
            return
        elif command == 'control':
            if len(args) == 0:
                for control_name in active_context.match('\d+/control'):
                    yield control_name
            else:
                control_name = ' '.join(args)
                if control_name in active_context.match('\d+/control'):
                    active_context.execute(control_name)
                    yield _("Executed '%s'") % control_name
                else:
                    yield _("Control '%s' not found.") % control_name
            return
        elif command == 'module':
            if len(args) == 0:
                yield _('----------')
                yield _('Modules Registered:')
                for i, name in enumerate(self.match('module')):
                    yield '%d: %s' % (i + 1, name)
                yield _('----------')
                for i, name in enumerate(self.contexts):
                    context = self.contexts[name]
                    if len(context.opened) == 0:
                        continue
                    yield _('Loaded Modules in Context %s:') % str(context._path)
                    for i, name in enumerate(context.opened):
                        module = context.opened[name]
                        yield _('%d: %s as type of %s') % (i + 1, name, type(module))
                    yield _('----------')
            else:
                value = args[0]
                if value == 'open':
                    index = args[1]
                    name = None
                    if len(args) >= 3:
                        name = args[2]
                    if index in self.registered:
                        if name is not None:
                            active_context.open_as(index, name)
                        else:
                            active_context.open(index)
                    else:
                        yield _("Module '%s' not found.") % index
                elif value == 'close':
                    index = args[1]
                    if index in active_context.opened:
                        active_context.close(index)
                    else:
                        yield _("Module '%s' not found.") % index
            return
        elif command == 'modifier':
            if len(args) == 0:
                yield _('----------')
                yield _('Modifiers Registered:')
                for i, name in enumerate(self.match('modifier')):
                    yield '%d: %s' % (i + 1, name)
                yield _('----------')
                yield _('Loaded Modifiers in Context %s:') % str(active_context._path)
                for i, name in enumerate(active_context.attached):
                    modifier = active_context.attached[name]
                    yield _('%d: %s as type of %s') % (i + 1, name, type(modifier))
                yield _('----------')
                yield _('Loaded Modifiers in Device %s:') % str(active_context._path)
                for i, name in enumerate(active_context.attached):
                    modifier = active_context.attached[name]
                    yield _('%d: %s as type of %s') % (i + 1, name, type(modifier))
                yield _('----------')
            else:
                value = args[0]
                if value == 'open':
                    index = args[1]
                    if index in self.registered:
                        active_context.activate(index)
                    else:
                        yield _("Modifier '%s' not found.") % index
                elif value == 'close':
                    index = args[1]
                    if index in active_context.attached:
                        active_context.deactivate(index)
                    else:
                        yield _("Modifier '%s' not found.") % index
            return
        elif command == 'schedule':
            yield _('----------')
            yield _('Scheduled Processes:')
            for i, job_name in enumerate(self.jobs):
                job = self.jobs[job_name]
                parts = list()
                parts.append('%d:' % (i + 1))
                parts.append(str(job))
                if job.times is None:
                    parts.append(_('forever'))
                else:
                    parts.append(_('%d times') % job.times)
                if job.interval is None:
                    parts.append(_('never'))
                else:
                    parts.append(_(', each %f seconds') % job.interval)
                yield ' '.join(parts)
            yield _('----------')
            return
        elif command == 'channel':
            if len(args) == 0:
                yield _('----------')
                yield _('Channels Active:')
                for i, name in enumerate(self.channels):
                    channel = self.channels[name]
                    if self._console_channel in channel.watchers:
                        is_watched = '* '
                    else:
                        is_watched = ''
                    yield '%s%d: %s' % (is_watched, i + 1, name)
            else:
                value = args[0]
                chan = args[1]
                if value == 'open':
                    if chan == 'console':
                        yield _('Infinite Loop Error.')
                    else:
                        active_context.channel(chan).watch(self._console_channel)
                        yield _('Watching Channel: %s') % chan
                elif value == 'close':
                    try:
                        active_context.channel(chan).unwatch(self._console_channel)
                        yield _('No Longer Watching Channel: %s') % chan
                    except KeyError:
                        yield _('Channel %s is not opened.') % chan
                elif value == 'save':
                    from datetime import datetime
                    if self.console_channel_file is None:
                        filename = "MeerK40t-channel-{date:%Y-%m-%d_%H_%M_%S}.txt".format(date=datetime.now())
                        yield _('Opening file: %s') % filename
                        self.console_channel_file = open(filename, "a")
                    yield _('Recording Channel: %s') % chan
                    active_context.channel(chan).watch(self._console_file_write)
            return
        elif command == 'device':
            if len(args) == 0:
                yield _('----------')
                yield _('Backends permitted:')
                for i, name in enumerate(self.match('device/')):
                    yield '%d: %s' % (i + 1, name)
                yield _('----------')
                yield _('Existing Device:')

                for device in list(active_context.derivable()):
                    try:
                        d = int(device)
                    except ValueError:
                        continue
                    try:
                        settings = active_context.derive(device)
                        device_name = settings.setting(str, 'device_name', 'Lhystudios')
                        autoboot = settings.setting(bool, 'autoboot', True)
                        yield _('Device %d. "%s" -- Boots: %s') % (d, device_name, autoboot)
                    except ValueError:
                        break
                    except AttributeError:
                        break
                yield _('----------')
                yield _('Devices Instances:')
                try:
                    device_name = active_context.device_name
                except AttributeError:
                    device_name = "Unknown"

                try:
                    device_location = active_context.device_location
                except AttributeError:
                    device_location = "Unknown"
                for i, name in enumerate(self.devices):
                    device = self.devices[name]
                    try:
                        device_name = device.device_name
                    except AttributeError:
                        device_name = "Unknown"

                    try:
                        device_location = device.device_location
                    except AttributeError:
                        device_location = "Unknown"
                    yield _('%d: %s on %s') % (i + 1, device_name, device_location)
                yield _('----------')
            else:
                value = args[0]
                try:
                    value = int(value)
                except ValueError:
                    value = None
                for i, name in enumerate(self.devices):
                    if i + 1 == value:
                        self.active = self.devices[name]
                        active_context.setting(str, 'device_location', 'Unknown')
                        yield _('Device set: %s on %s') % \
                              (active_context.device_name, active_context.device_location)
                        break
            return
        elif command == 'flush':
            active_context.flush()
            yield _('Persistent settings force saved.')
        elif command == 'shutdown':
            active_context.stop()
            return
        else:
            for command_name in self.match('\d+/command/%s' % command):
                command = self.registered[command_name]
                try:
                    for line in command(command_name, *args):
                        yield line
                except TypeError:
                    pass
                return
            try:
                for line in self.registered['command/%s' % command](command, *args):
                    yield line
            except KeyError:
                yield _('Error. Command Unrecognized: %s') % command
            except TypeError:
                pass  # Did not yield anything. Still success. But, not a generator.


class Job:
    """
    Generic job for the scheduler.

    Jobs that can be scheduled in the scheduler-kernel to run at a particular time and a given number of times.
    This is done calling schedule() and unschedule() and setting the parameters for process, args, interval,
    and times. This is usually extended directly by a module requiring that functionality.
    """

    def __init__(self, process=None, args=(), interval=1.0, times=None, name=None):
        self.name = name
        self.state = STATE_INITIALIZE

        self.process = process
        self.args = args
        self.interval = interval
        self.times = times
        self._last_run = None
        self._next_run = time.time() + self.interval

    def __str__(self):
        if self.name is not None:
            return self.name
        else:
            return self.process.__name__

    @property
    def scheduled(self):
        return self._next_run is not None and time.time() >= self._next_run

    def cancel(self):
        self.times = -1
