from CutPlanner import CutPlanner
from Kernel import *
from svgelements import *


class Console(Module, Pipe):
    def __init__(self):
        Module.__init__(self)
        Pipe.__init__(self)
        self.channel_file = None
        self.channel = None
        self.buffer = ''
        self.active_device = None
        self.interval = 0.05
        self.process = self.tick
        self.commands = []
        self.queue = []
        self.laser_on = False
        self.dx = 0
        self.dy = 0

    def initialize(self, channel=None):
        self.device.listen('interpreter;mode', self.on_mode_change)
        self.device.setting(int, "bed_width", 280)
        self.device.setting(int, "bed_height", 200)
        self.channel = self.device.channel_open('console')
        self.active_device = self.device

    def finalize(self, channel=None):
        self.device.unlisten('interpreter;mode', self.on_mode_change)

    def on_mode_change(self, *args):
        self.dx = 0
        self.dy = 0

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        self.buffer += data
        while '\n' in self.buffer:
            pos = self.buffer.find('\n')
            command = self.buffer[0:pos].strip('\r')
            self.buffer = self.buffer[pos + 1:]
            for response in self.interface(command):
                self.channel(response)

    def tick(self):
        for command in self.commands:
            for e in self.interface(command):
                if self.channel is not None:
                    self.channel(e)
        if len(self.queue):
            for command in self.queue:
                for e in self.interface(command):
                    if self.channel is not None:
                        self.channel(e)
            self.queue.clear()
        if len(self.commands) == 0 and len(self.queue) == 0:
            self.unschedule()

    def queue_command(self, command):
        self.queue = [c for c in self.queue if c != command]  # Only allow 1 copy of any command.
        self.queue.append(command)
        self.schedule()

    def tick_command(self, command):
        self.commands = [c for c in self.commands if c != command]  # Only allow 1 copy of any command.
        self.commands.append(command)
        self.schedule()

    def untick_command(self, command):
        self.commands = [c for c in self.commands if c != command]
        if len(self.commands) == 0:
            self.unschedule()

    def execute_absolute_position(self, position_x, position_y):
        x_pos = Length(position_x).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
        y_pos = Length(position_y).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)

        def move():
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)

        return move

    def execute_relative_position(self, position_x, position_y):
        x_pos = Length(position_x).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
        y_pos = Length(position_y).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)

        def move():
            yield COMMAND_SET_INCREMENTAL
            yield COMMAND_MODE_RAPID
            yield COMMAND_MOVE, int(x_pos), int(y_pos)
            yield COMMAND_SET_ABSOLUTE

        return move

    def channel_file_write(self, v):
        if self.channel_file is not None:
            self.channel_file.write('%s\n' % v)
            self.channel_file.flush()

    def interface(self, command):
        yield command
        args = str(command).split(' ')
        for e in self.interface_parse_command(*args):
            yield e

    def interface_parse_command(self, command, *args):
        kernel = self.device.device_root
        elements = kernel.elements
        active_device = self.active_device
        try:
            spooler = active_device.spooler
        except AttributeError:
            spooler = None
        try:
            interpreter = active_device.interpreter
        except AttributeError:
            interpreter = None
        command = command.lower()
        if command == 'help' or command == '?':
            yield '(right|left|up|down) <length>'
            yield 'laser [(on|off)]'
            yield 'move <x> <y>'
            yield 'move_relative <dx> <dy>'
            yield 'home'
            yield 'unlock'
            yield 'speed [<value>]'
            yield 'power [<value>]'
            yield '-------------------'
            yield 'loop <command>'
            yield 'end <commmand>'
            yield '-------------------'
            yield 'device [<value>]'
            yield 'set [<key> <value>]'
            yield 'window [(open|close|toggle) <window_name>]'
            yield 'control [<executive>]'
            yield 'module [(open|close) <module_name>]'
            yield 'schedule'
            yield 'channel [(open|close|save) <channel_name>]'
            yield '-------------------'
            yield 'element [<element>]*'
            yield 'grid <columns> <rows> <x-distance> <y-distance>'
            yield 'path <svg_path>'
            yield 'circle <cx> <cy> <r>'
            yield 'ellipse <cx> <cy> <rx> <ry>'
            yield 'rect <x> <y> <width> <height>'
            yield 'text <text>'
            yield 'polygon [<x> <y>]*'
            yield 'polyline [<x> <y>]*'
            # yield 'group'
            # yield 'ungroup'
            yield 'stroke <color>'
            yield 'fill <color>'
            yield 'rotate <angle>'
            yield 'scale <scale> [<scale_y>]'
            yield 'translate <translate_x> <translate_y>'
            yield 'rotate_to <angle>'
            yield 'scale_to <scale> [<scale_y>]'
            yield 'translate_to <translate_x> <translate_y>'
            yield 'reset'
            yield 'reify'
            yield '-------------------'
            yield 'operation [<op>]*'
            yield 'classify'
            yield 'cut'
            yield 'engrave'
            yield 'raster'
            yield '-------------------'
            yield 'bind [<key> <command>]'
            yield 'alias [<alias> <command>]'
            yield '-------------------'
            yield 'trace_hull'
            yield 'trace_quick'
            yield 'pulse <time_ms>'
            yield '-------------------'
            yield 'ruidaserver'
            yield 'grblserver'
            yield '-------------------'
            yield 'refresh'
            return
        # +- controls.
        elif command == "loop":
            self.tick_command(' '.join(args))
        elif command == "end":
            if len(args) == 0:
                self.commands.clear()
                self.unschedule()
            else:
                self.untick_command(' '.join(args))
        elif command == '+laser':
            spooler.job(COMMAND_LASER_ON)
        elif command == '-laser':
            spooler.job(COMMAND_LASER_OFF)
        # Laser Control Commands
        elif command == 'right' or command == 'left' or command == 'up' or command == 'down':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 1:
                max_bed_height = self.device.bed_height * 39.3701
                max_bed_width = self.device.bed_width * 39.3701
                direction = command
                amount = args[0]
                if direction == 'right':
                    self.dx += Length(amount).value(ppi=1000.0, relative_length=max_bed_width)
                elif direction == 'left':
                    self.dx -= Length(amount).value(ppi=1000.0, relative_length=max_bed_width)
                elif direction == 'up':
                    self.dy -= Length(amount).value(ppi=1000.0, relative_length=max_bed_height)
                elif direction == 'down':
                    self.dy += Length(amount).value(ppi=1000.0, relative_length=max_bed_height)
                self.queue_command('jog')
            else:
                yield 'Syntax Error'
            return
        elif command == 'jog':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            idx = int(self.dx)
            idy = int(self.dy)
            if idx == 0 and idy == 0:
                return
            if spooler.job_if_idle(self.execute_relative_position(idx, idy)):
                yield 'Position moved: %d %d' % (idx, idy)
                self.dx -= idx
                self.dy -= idy
            else:
                yield 'Busy Error'
            return
        elif command == 'laser':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 1:
                if args[0] == 'on':
                    self.laser_on = True
                elif args[0] == 'off':
                    self.laser_on = False
            if self.laser_on:
                yield 'Laser is on.'
            else:
                yield 'Laser is off.'
            return
        elif command == 'move' or command == 'move_absolute':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_absolute_position(*args)):
                    yield 'Busy Error'
            else:
                yield 'Syntax Error'
            return
        elif command == 'move_relative':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 2:
                if not spooler.job_if_idle(self.execute_relative_position(*args)):
                    yield 'Busy Error'
            else:
                yield 'Syntax Error'
            return
        elif command == 'home':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            spooler.job(COMMAND_HOME)
            return
        elif command == 'unlock':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            spooler.job(COMMAND_UNLOCK)
            return
        elif command == 'lock':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            spooler.job(COMMAND_LOCK)
            return
        elif command == 'speed':
            if interpreter is None:
                yield 'Device has no interpreter.'
                return

            if len(args) == 0:
                yield 'Speed set at: %f mm/s' % interpreter.speed
                return
            inc = False
            percent = False
            speed = args[0]
            if speed == "inc":
                speed = args[1]
                inc = True
            if speed.endswith('%'):
                speed = speed[:-1]
                percent = True
            try:
                s = float(speed)
            except ValueError:
                yield 'Not a valid speed or percent.'
                return
            if percent and inc:
                s = interpreter.speed + interpreter.speed * (s / 100.0)
            elif inc:
                s += interpreter.speed
            elif percent:
                s = interpreter.speed * (s / 100.0)
            interpreter.set_speed(s)
            yield 'Speed set at: %f mm/s' % interpreter.speed
        elif command == 'power':
            if interpreter is None:
                yield 'Device has no interpreter.'
                return
            if len(args) == 0:
                yield 'Power set at: %d pulses per inch' % interpreter.power
            else:
                try:
                    interpreter.set_power(int(args[0]))
                except ValueError:
                    pass
        elif command == 'acceleration':
            if interpreter is None:
                yield 'Device has no interpreter.'
                return
            if len(args) == 0:
                if interpreter.acceleration is None:
                    yield 'Acceleration is set to default.'
                else:
                    yield 'Acceleration: %d' % interpreter.acceleration

            else:
                try:
                    v = int(args[0])
                    if v not in (1, 2, 3, 4):
                        interpreter.set_acceleration(None)
                        yield 'Acceleration is set to default.'
                        return
                    interpreter.set_acceleration(v)
                    yield 'Acceleration: %d' % interpreter.acceleration
                except ValueError:
                    yield 'Invalid Acceleration [1-4].'
                    return
        # Kernel Element commands.
        elif command == 'window':
            if len(args) == 0:
                yield '----------'
                yield 'Windows Registered:'
                for i, name in enumerate(kernel.registered['window']):
                    yield '%d: %s' % (i + 1, name)
                yield '----------'
                yield 'Loaded Windows in Device %s:' % str(active_device._uid)
                for i, name in enumerate(active_device.instances['window']):
                    module = active_device.instances['window'][name]
                    yield '%d: %s as type of %s' % (i + 1, name, type(module))
                yield '----------'
            else:
                value = args[0]
                if value == 'toggle':
                    index = args[1]
                    if index in active_device.instances['window']:
                        value = 'close'
                    else:
                        value = 'open'
                if value == 'open':
                    window_name = args[1]
                    if window_name in kernel.registered['window']:
                        parent_window = None
                        try:
                            parent_window = active_device.gui
                        except AttributeError:
                            pass
                        active_device.open('window', window_name, parent_window, *args[2:])
                        yield 'Window %s opened.' % window_name
                    else:
                        yield "Window '%s' not found." % window_name
                elif value == 'close':
                    window_name = args[1]
                    if index in active_device.instances['window']:
                        active_device.close('window', window_name)
                    else:
                        yield "Window '%s' not found." % window_name
        elif command == 'set':
            if len(args) == 0:
                for attr in dir(active_device):
                    v = getattr(active_device, attr)
                    if attr.startswith('_') or not isinstance(v, (int, float, str, bool)):
                        continue
                    yield '"%s" := %s' % (attr, str(v))
                return
            if len(args) >= 2:
                attr = args[0]
                value = args[1]
                try:
                    if hasattr(active_device, attr):
                        v = getattr(active_device, attr)
                        if isinstance(v, bool):
                            if value == 'False' or value == 'false' or value == 0:
                                setattr(active_device, attr, False)
                            else:
                                setattr(active_device, attr, True)
                        elif isinstance(v, int):
                            setattr(active_device, attr, int(value))
                        elif isinstance(v, float):
                            setattr(active_device, attr, float(value))
                        elif isinstance(v, str):
                            setattr(active_device, attr, str(value))
                except RuntimeError:
                    yield 'Attempt failed. Produced a runtime error.'
                except ValueError:
                    yield 'Attempt failed. Produced a value error.'
            return
        elif command == 'control':
            if len(args) == 0:
                for control_name in active_device.instances['control']:
                    yield control_name
            else:
                control_name = ' '.join(args)
                if control_name in active_device.instances['control']:
                    active_device.execute(control_name)
                    yield "Executed '%s'" % control_name
                else:
                    yield "Control '%s' not found." % control_name
            return
        elif command == 'module':
            if len(args) == 0:
                yield '----------'
                yield 'Modules Registered:'
                for i, name in enumerate(kernel.registered['module']):
                    yield '%d: %s' % (i + 1, name)
                yield '----------'
                yield 'Loaded Modules in Device %s:' % str(active_device._uid)
                for i, name in enumerate(active_device.instances['module']):
                    module = active_device.instances['module'][name]
                    yield '%d: %s as type of %s' % (i + 1, name, type(module))
                yield '----------'
            else:
                value = args[0]
                if value == 'open':
                    index = args[1]
                    name = None
                    if len(args) >= 3:
                        name = args[2]
                    if index in kernel.registered['module']:
                        if name is not None:
                            active_device.open('module', index, instance_name=None)
                        else:
                            active_device.open('module', index)
                    else:
                        yield "Module '%s' not found." % index
                elif value == 'close':
                    index = args[1]
                    if index in active_device.instances['module']:
                        active_device.close('module', index)
                    else:
                        yield "Module '%s' not found." % index
            return
        elif command == 'schedule':
            yield '----------'
            yield 'Scheduled Processes:'
            for i, job in enumerate(active_device.jobs):
                parts = list()
                parts.append('%d:' % (i + 1))
                parts.append(str(job))
                if job.times is None:
                    parts.append('forever')
                else:
                    parts.append('%d times' % job.times)
                if job.interval is None:
                    parts.append('never')
                else:
                    parts.append(', each %f seconds' % job.interval)
                yield ' '.join(parts)
            yield '----------'
            return
        elif command == 'channel':
            if len(args) == 0:
                yield '----------'
                yield 'Channels Active:'
                for i, name in enumerate(active_device.channels):
                    yield '%d: %s' % (i + 1, name)
                yield '----------'
                yield 'Channels Watching:'
                for name in active_device.watchers:
                    watchers = active_device.watchers[name]
                    if self.channel in watchers:
                        yield name
                yield '----------'
            else:
                try:
                    value = args[0]
                    chan = args[1]
                except IndexError:
                    yield "Syntax Error"
                    return
                if value == 'open':
                    if chan == 'console':
                        yield "Infinite Loop Error."
                    else:
                        active_device.add_watcher(chan, self.channel)
                        yield "Watching Channel: %s" % chan
                elif value == 'close':
                    try:
                        active_device.remove_watcher(chan, self.channel)
                        yield "No Longer Watching Channel: %s" % chan
                    except KeyError:
                        yield "Channel %s is not opened." % chan
                elif value == 'save':
                    from datetime import datetime
                    if self.channel_file is None:
                        filename = "MeerK40t-channel-{date:%Y-%m-%d_%H_%M_%S}.txt".format(date=datetime.now())
                        yield "Opening file: %s" % filename
                        self.channel_file = open(filename, "a")
                    yield "Recording Channel: %s" % chan
                    active_device.add_watcher(chan, self.channel_file_write)
            return
        elif command == 'device':
            if len(args) == 0:
                yield '----------'
                yield 'Backends permitted:'
                for i, name in enumerate(kernel.registered['device']):
                    yield '%d: %s' % (i + 1, name)
                yield '----------'
                yield 'Existing Device:'

                for device in list(kernel.derivable()):
                    try:
                        d = int(device)
                    except ValueError:
                        continue
                    try:
                        settings = kernel.derive(device)
                        device_name = settings.setting(str, 'device_name', 'Lhystudios')
                        autoboot = settings.setting(bool, 'autoboot', True)
                        yield 'Device %d. "%s" -- Boots: %s' % (d, device_name, autoboot)
                    except ValueError:
                        break
                    except AttributeError:
                        break
                yield '----------'
                yield 'Devices Instances:'
                yield '%d: %s on %s' % (0, kernel.device_name, kernel.device_location)
                for i, name in enumerate(kernel.instances['device']):
                    device = kernel.instances['device'][name]
                    yield '%d: %s on %s' % (i + 1, device.device_name, device.device_location)
                yield '----------'
            else:
                value = args[0]
                try:
                    value = int(value)
                except ValueError:
                    value = None
                if value == 0:
                    self.active_device = kernel
                    yield 'Device set: %s on %s' % \
                          (self.active_device.device_name, self.active_device.device_location)
                else:
                    for i, name in enumerate(kernel.instances['device']):
                        if i + 1 == value:
                            self.active_device = kernel.instances['device'][name]
                            yield 'Device set: %s on %s' % \
                                  (self.active_device.device_name, self.active_device.device_location)
                            break
            return
        # Element commands.
        elif command == 'element':
            if len(args) == 0:
                yield '----------'
                yield 'Graphical Elements:'
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
                yield '----------'
            else:
                for value in args:
                    try:
                        value = int(value)
                    except ValueError:
                        if value == "*":
                            yield "Selecting all elements."
                            elements.set_selected(list(elements.elems()))
                            continue
                        elif value == "~":
                            yield "Invert selection."
                            elements.set_selected(list(elements.elems(emphasized=False)))
                            continue
                        elif value == "!":
                            yield "Select none"
                            elements.set_selected(None)
                            continue
                        elif value == "delete":
                            yield "deleting."
                            elements.remove_elements(list(elements.elems(emphasized=True)))
                            self.device.signal('refresh_scene', 0)
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
                                if isinstance(e, Path):
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
                        yield "Value Error: %s is not an integer" % value
                        continue
                    try:
                        element = elements.get_elem(value)
                        name = str(element)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if element.selected:
                            element.unselect()
                            element.unemphasize()
                            yield "Deselecting item %d called %s" % (value, name)
                        else:
                            element.select()
                            element.emphasize()
                            yield "Selecting item %d called %s" % (value, name)
                    except IndexError:
                        yield 'index %d out of range' % value
            return
        elif command == 'grid':
            try:
                cols = int(args[0])
                rows = int(args[1])
                x_distance = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
                y_distance = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            except (ValueError, IndexError):
                yield "Syntax Error: grid <columns> <rows> <x_distance> <y_distance>"
                return
            items = list(elements.elems(emphasized=True))
            if items is None or len(items) == 0 or elements._bounds is None:
                yield 'No item selected.'
                return
            y_pos = 0
            for j in range(rows):
                x_pos = 0
                for k in range(cols):
                    if j != 0 or k != 0:
                        add_elem = list(map(copy, items))
                        for e in add_elem:
                            e *= 'translate(%f, %f)' % (x_pos, y_pos)
                        elements.add_elems(add_elem)
                    x_pos += x_distance
                y_pos += y_distance
        elif command == 'path':
            path_d = ' '.join(args)
            element = Path(path_d)
            self.add_element(element)
            return
        elif command == 'circle':
            if len(args) == 3:
                x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
                y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
                r_pos = Length(args[2]).value(ppi=1000.0,
                                              relative_length=min(self.device.bed_height, self.device.bed_width) * 39.3701)
            elif len(args) == 1:
                x_pos = 0
                y_pos = 0
                r_pos = Length(args[0]).value(ppi=1000.0,
                                      relative_length=min(self.device.bed_height, self.device.bed_width) * 39.3701)
            else:
                yield 'Circle <x> <y> <r> or circle <r>'
                return
            element = Circle(cx=x_pos, cy=y_pos, r=r_pos)
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'ellipse':
            if len(args) < 4:
                yield "Too few arguments (needs center_x, center_y, radius_x, radius_y)"
                return
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            rx_pos = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            ry_pos = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            element = Ellipse(cx=x_pos, cy=y_pos, rx=rx_pos, ry=ry_pos)
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'rect':
            if len(args) < 4:
                yield "Too few arguments (needs x, y, width, height)"
                return
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            width = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            height = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            element = Rect(x=x_pos, y=y_pos, width=width, height=height)
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'text':
            text = ' '.join(args)
            element = SVGText(text)
            self.add_element(element)
            return
        elif command == 'polygon':
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'polyline':
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return
        # elif command == 'group':
        #     return
        # elif command == 'ungroup':
        #     return
        elif command == 'stroke':
            if len(args) == 0:
                yield '----------'
                yield 'Stroke Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if element.stroke is None or element.stroke == 'none':
                        yield '%d: stroke = none - %s' % \
                              (i, name)
                    else:
                        yield '%d: stroke = %s - %s' % \
                              (i, element.stroke.hex, name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            if args[0] == 'none':
                for element in elements.elems(emphasized=True):
                    element.stroke = None
                    element.altered()
            else:
                for element in elements.elems(emphasized=True):
                    element.stroke = Color(args[0])
                    element.altered()
            active_device.signal('refresh_scene')
            return
        elif command == 'fill':
            if len(args) == 0:
                yield '----------'
                yield 'Fill Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    if element.fill is None or element.fill == 'none':
                        yield '%d: fill = none - %s' % \
                              (i, name)
                    else:
                        yield '%d: fill = %s - %s' % \
                              (i, element.fill.hex, name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            if args[0] == 'none':
                for element in elements.elems(emphasized=True):
                    element.fill = None
                    element.altered()
            else:
                for element in elements.elems(emphasized=True):
                    element.fill = Color(args[0])
                    element.altered()
            active_device.signal('refresh_scene')
            return
        elif command == 'rotate':
            if len(args) == 0:
                yield '----------'
                yield 'Rotate Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: rotate(%fturn) - %s' % \
                          (i, element.rotation.as_turns, name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            bounds = elements.bounds()
            if len(args) >= 1:
                rot = Angle.parse(args[0]).as_degrees
            else:
                rot = 0
            if len(args) >= 2:
                center_x = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 3:
                center_y = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
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
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'scale':
            if len(args) == 0:
                yield '----------'
                yield 'Scale Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: scale(%f, %f) - %s' % \
                          (i, element.transform.value_scale_x(), element.transform.value_scale_x(), name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
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
                center_x = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 4:
                center_y = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                center_y = (bounds[3] + bounds[1]) / 2.0
            if sx == 0 or sy == 0:
                yield 'Scaling by Zero Error'
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
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'translate':
            if len(args) == 0:
                yield '----------'
                yield 'Translate Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: translate(%f, %f) - %s' % \
                          (i, element.transform.value_trans_x(), element.transform.value_trans_y(), name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            if len(args) >= 1:
                tx = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                tx = 0
            if len(args) >= 2:
                ty = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                ty = 0
            matrix = Matrix('translate(%f,%f)' % (tx, ty))
            try:
                for element in elements.elems(emphasized=True):
                    element *= matrix
                    element.modified()
            except ValueError:
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'rotate_to':
            if len(args) == 0:
                yield '----------'
                yield 'Rotate Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: rotate(%fturn) - %s' % \
                          (i, element.rotation.as_turns, name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            bounds = elements.bounds()
            try:
                end_angle = Angle.parse(args[0])
            except ValueError:
                yield "Invalid Value."
                return
            if len(args) >= 2:
                center_x = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 3:
                center_y = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
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
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'scale_to':
            if len(args) == 0:
                yield '----------'
                yield 'Scale Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: scale(%f, %f) - %s' % \
                          (i, element.transform.value_scale_x(), element.transform.value_scale_y(), name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
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
                center_x = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                center_x = (bounds[2] + bounds[0]) / 2.0
            if len(args) >= 4:
                center_y = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
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
                        yield 'Scaling by Zero Error'
                        return
                    nsx = sx / osx
                    nsy = sy / osy
                    matrix = Matrix('scale(%f,%f,%f,%f)' % (nsx, nsy, center_x, center_y))
                    element *= matrix
                    element.modified()
            except ValueError:
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'translate_to':
            if len(args) == 0:
                yield '----------'
                yield 'Translate Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: translate(%f, %f) - %s' % \
                          (i, element.transform.value_trans_x(), element.transform.value_trans_y(), name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return

            if len(args) >= 1:
                tx = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            else:
                tx = 0
            if len(args) >= 2:
                ty = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
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
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'resize':
            if len(args) < 4:
                yield "Too few arguments (needs x, y, width, height)"
                return
            try:
                x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
                y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
                w_dim = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
                h_dim = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
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
                active_device.signal('refresh_scene')
            except (ValueError, ZeroDivisionError):
                return

        elif command == 'matrix':
            if len(args) == 0:
                yield '----------'
                yield 'Matrix Values:'
                i = 0
                for element in elements.elems():
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: %s - %s' % \
                          (i, str(element.transform), name)
                    i += 1
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            if len(args) != 6:
                yield "Requires six matrix parameters"
                return
            try:
                matrix = Matrix(float(args[0]), float(args[1]), float(args[2]), float(args[3]),
                                Length(args[4]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701),
                                Length(args[5]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701))
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            continue
                    except AttributeError:
                        pass

                    element.transform = Matrix(matrix)
                    element.modified()
            except ValueError:
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'reset':
            for element in elements.elems(emphasized=True):
                try:
                    if element.lock:
                        continue
                except AttributeError:
                    pass

                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield 'reset - %s' % name
                element.transform.reset()
                element.modified()
            active_device.signal('refresh_scene')
            return
        elif command == 'reify':
            for element in elements.elems(emphasized=True):
                try:
                    if element.lock:
                        continue
                except AttributeError:
                    pass

                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield 'reified - %s' % name
                element.reify()
                element.altered()
            active_device.signal('refresh_scene')
            return
        elif command == 'optimize':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            elif len(args) == 0:
                yield 'Optimizations: cut_inner, travel, cut_travel'
                return
            elif args[0] == 'cut_inner':
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_cut_inside(element)
                    element.clear()
                    element += e
                    element.altered()
            elif args[0] == 'travel':
                yield "Travel Optimizing: %f" % CutPlanner.length_travel(elements.elems(emphasized=True))
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_travel(element)
                    element.clear()
                    element += e
                    element.altered()
                yield "Optimized: %f" % CutPlanner.length_travel(elements.elems(emphasized=True))
            elif args[0] == 'cut_travel':
                yield "Cut Travel Initial: %f" % CutPlanner.length_travel(elements.elems(emphasized=True))
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_general(element)
                    element.clear()
                    element += e
                    element.altered()
                yield "Cut Travel Optimized: %f" % CutPlanner.length_travel(elements.elems(emphasized=True))
            else:
                yield 'Optimization not found.'
                return
        elif command == 'embroider':
            yield "Embroidery Filling"
            if len(args) >= 1:
                angle = Angle.parse(args[0])
            else:
                angle = None
            if len(args) >= 2:
                distance = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
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
        # Operation Command Elements
        elif command == 'operation':
            if len(args) == 0:
                yield '----------'
                yield 'Operations:'
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
                yield '----------'
            else:
                for value in args:
                    try:
                        value = int(value)
                    except ValueError:
                        if value == "*":
                            yield "Selecting all operations."
                            elements.set_selected(list(elements.ops()))
                            continue
                        elif value == "~":
                            yield "Invert selection."
                            elements.set_selected(list(elements.ops(emphasized=False)))
                            continue
                        elif value == "!":
                            yield "Select none"
                            elements.set_selected(None)
                            continue
                        elif value == "delete":
                            yield "Deleting."
                            elements.remove_operations(list(elements.ops(emphasized=True)))
                            continue
                        elif value == "copy":
                            add_elem = list(map(copy, elements.ops(emphasized=True)))
                            elements.add_ops(add_elem)
                            for e in add_elem:
                                e.select()
                                e.emphasize()
                            continue
                        yield "Value Error: %s is not an integer" % value
                        continue
                    try:
                        operation = elements.get_op(value)
                        name = str(operation)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if operation.emphasized:
                            operation.unemphasize()
                            operation.unselect()
                            yield "Deselecting operation %d called %s" % (value, name)
                        else:
                            operation.emphasize()
                            operation.select()
                            yield "Selecting operation %d called %s" % (value, name)
                    except IndexError:
                        yield 'index %d out of range' % value
            return
        elif command == 'classify':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            elements.classify(list(elements.elems(emphasized=True)))
            return
        elif command == 'declassify':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            elements.remove_elements_from_operations(list(elements.elems(emphasized=True)))
            return
        elif command == 'note':
            if len(args) == 0:
                if elements.note is None:
                    yield "No Note."
                else:
                    yield str(elements.note)
            else:
                elements.note = ' '.join(args)
                yield "Note Set."
        elif command == 'cut':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = LaserOperation()
            op.operation = "Cut"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'engrave':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = LaserOperation()
            op.operation = "Engrave"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'raster':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = LaserOperation()
            op.operation = "Raster"
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'step':
            if len(args) == 0:
                found = False
                for op in elements.ops(emphasized=True):
                    if op.operation in ("Raster", "Image"):
                        step = op.raster_step
                        yield 'Step for %s is currently: %d' % (str(op), step)
                        found = True
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            step = element.values['raster_step']
                        except KeyError:
                            step = 1
                        yield 'Image step for %s is currently: %s' % (str(element), step)
                        found = True
                if not found:
                    yield 'No raster operations selected.'
                return
            try:
                step = int(args[0])
            except ValueError:
                yield 'Not integer value for raster step.'
                return
            for op in elements.ops(emphasized=True):
                if op.operation in ("Raster", "Image"):
                    op.raster_step = step
                    self.device.signal('element_property_update', op)
            for element in elements.elems(emphasized=True):
                element.values['raster_step'] = str(step)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step), float(step))
                element.transform.post_translate(tx, ty)
                element.modified()
                self.device.signal('element_property_update', element)
                active_device.signal('refresh_scene')
            return
        elif command == 'image':
            if len(args) == 0:
                yield '----------'
                yield 'Images:'
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
                yield '----------'
                return
            if not elements.has_emphasis():
                yield "No selected images."
                return
            elif args[0] == 'path':
                for element in list(elements.elems(emphasized=True)):
                    bounds = element.bbox()
                    p = Path()
                    p.move((bounds[0], bounds[1]),
                            (bounds[0], bounds[3]),
                            (bounds[2], bounds[3]),
                           (bounds[2], bounds[1]))
                    p.closed()
                    self.add_element(p)
                return
            elif args[0] == 'wizard':
                if len(args) == 1:
                    try:
                        for script_name in kernel.registered['raster_script']:
                            yield "Raster Script: %s" % script_name
                    except KeyError:
                        yield "No Raster Scripts Found."
                    return
                try:
                    script = kernel.registered['raster_script'][args[1]]
                except KeyError:
                    yield "Raster Script %s is not registered." % args[1]
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
                yield 'Unlocking Elements...'
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            yield "Unlocked: %s" % str(element)
                            element.lock = False
                        else:
                            yield "Element was not locked: %s" % str(element)
                    except AttributeError:
                        yield "Element was not locked: %s" % str(element)
                return
            elif args[0] == 'threshold':
                try:
                    threshold_min = float(args[1])
                    threshold_max = float(args[2])
                except (ValueError, IndexError):
                    yield "Threshold values improper."
                    return
                divide = (threshold_max - threshold_min) / 255.0
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    image_element = copy(element)
                    image_element.image = image_element.image.copy()
                    try:
                        from OperationPreprocessor import OperationPreprocessor
                    except ImportError:
                        yield "No Render Engine Installed."
                        return
                    if OperationPreprocessor.needs_actualization(image_element):
                        OperationPreprocessor.make_actual(image_element)
                    img = image_element.image
                    img = img.convert('L')

                    def thresh(g):
                        if threshold_min >= g:
                            return 0
                        elif threshold_max < g:
                            return 255
                        else:  # threshold_min <= grey < threshold_max
                            value = g - threshold_min
                            value *= divide
                            return int(round(value))
                    lut = [thresh(g) for g in range(256)]
                    img = img.point(lut)
                    image_element.image = img
                    elements.add_elem(image_element)
            elif args[0] == 'resample':
                try:
                    from OperationPreprocessor import OperationPreprocessor
                except ImportError:
                    yield "No Render Engine Installed."
                    return
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
                    yield "Must specify a color, and optionally a distance."
                    return
                distance = 50.0
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield "Color Invalid."
                    return
                if len(args) >= 3:
                    try:
                        distance = float(args[2])
                    except ValueError:
                        yield "Color distance is invalid."
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
                    yield "Must specify a color, to add."
                    return
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield "Color Invalid."
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
                            left = int(Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701))
                            upper = int(Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701))
                            right = int(Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701))
                            lower = int(Length(args[4]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701))
                            element.image = img.crop((left, upper, right, lower))
                            element.image_width = right - left
                            element.image_height = lower - upper
                            element.altered()
                        except (KeyError, ValueError):
                            yield "image crop <left> <upper> <right> <lower>"
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
                            yield "Image Contrast Factor: %f" % factor
                        except (IndexError, ValueError):
                            yield "image contrast <factor>"
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
                            yield "Image Brightness Factor: %f" % factor
                        except (IndexError, ValueError):
                            yield "image brightness <factor>"
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
                            yield "Image Color Factor: %f" % factor
                        except (IndexError, ValueError):
                            yield "image color <factor>"
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
                            yield "Image Sharpness Factor: %f" % factor
                        except (IndexError, ValueError):
                            yield "image sharpness <factor>"
                return
            elif args[0] == 'blur':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.BLUR)
                        element.altered()
                        yield "Image Blurred."
                return
            elif args[0] == 'sharpen':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SHARPEN)
                        element.altered()
                        yield "Image Sharpened."
                return
            elif args[0] == 'edge_enhance':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
                        element.altered()
                        yield "Image Edges Enhanced."
                return
            elif args[0] == 'find_edges':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.FIND_EDGES)
                        element.altered()
                        yield "Image Edges Found."
                return
            elif args[0] == 'emboss':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EMBOSS)
                        element.altered()
                        yield "Image Embossed."
                return
            elif args[0] == 'smooth':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SMOOTH)
                        element.altered()
                        yield "Image Smoothed."
                return
            elif args[0] == 'contour':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.CONTOUR)
                        element.altered()
                        yield "Image Contoured."
                return
            elif args[0] == 'detail':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.DETAIL)
                        element.altered()
                        yield "Image Detailed."
                return
            elif args[0] == 'quantize':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            colors = int(args[1])
                            img = element.image
                            element.image = img.quantize(colors=colors)
                            element.altered()
                            yield "Image Quantized to %d colors." % colors
                        except (IndexError, ValueError):
                            yield "image quantize <colors>"
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
                            yield "Image Solarized at %d gray." % threshold
                        except (IndexError, ValueError):
                            yield "image solarize <threshold>"
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
                            yield "Image Inverted."
                        except OSError:
                            yield "Image type cannot be converted. %s" % img.mode
                return
            elif args[0] == 'flip':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.flip(img)
                        element.altered()
                        yield "Image Flipped."
                return
            elif args[0] == 'mirror':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.mirror(img)
                        element.altered()
                        yield "Image Mirrored."
                return
            elif args[0] == 'ccw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_90)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield "Rotated image counterclockwise."
                return
            elif args[0] == 'cw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_270)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield "Rotated image clockwise."
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
                            yield "Image Auto-Contrasted."
                        except (IndexError, ValueError):
                            yield "image autocontrast <cutoff-percent>"
                return
            elif args[0] == 'grayscale' or args[0] == 'greyscale':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.grayscale(img)
                        element.altered()
                        yield "Image Grayscale."
                return
            elif args[0] == 'equalize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.equalize(img)
                        element.altered()
                        yield "Image Equalized."
                return
            elif args[0] == 'save':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            img = element.image
                            img.save(args[1])
                            yield "Saved: %s" % (args[1])
                        except IndexError:
                            yield "No file given."
                        except OSError:
                            yield "File could not be written / created."
                        except ValueError:
                            yield "Could not determine expected format."

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
            else:
                yield "Image command unrecognized."
                return
        elif command == 'plan':
            if len(args) <= 0:
                yield "plan <start|fulfill|default>"
                return
            if args[0] == "fulfill":
                ops = list(elements.ops())
                spooler.jobs(ops)
                active_device.setting(bool, 'quit', True)
                active_device.quit = True
                return
            elif args[0] == "start":
                ops = list(elements.ops())
                spooler.jobs(ops)
                return
            elif args[0] == "default":
                elements.load_default()
                return
            else:
                yield "Command Unrecognized."
                return
        # Alias / Bind Command Elements.
        elif command == 'bind':
            if len(args) == 0:
                yield '----------'
                yield 'Binds:'
                for i, key in enumerate(kernel.keymap):
                    value = kernel.keymap[key]
                    yield '%d: key %s -> %s' % (i, key, value)
                yield '----------'
            else:
                key = args[0].lower()
                if key == 'default':
                    kernel.keymap = dict()
                    kernel.default_keymap()
                    yield 'Set default keymap.'
                    return
                command_line = ' '.join(args[1:])
                f = command_line.find('bind')
                if f == -1:  # If bind value has a bind, do not evaluate.
                    if '$x' in command_line:
                        try:
                            x = active_device.current_x
                        except AttributeError:
                            x = 0
                        command_line = command_line.replace('$x', str(x))
                    if '$y' in command_line:
                        try:
                            y = active_device.current_y
                        except AttributeError:
                            y = 0
                        command_line = command_line.replace('$y', str(y))
                if len(command_line) != 0:
                    kernel.keymap[key] = command_line
                else:
                    try:
                        del kernel.keymap[key]
                        yield "Unbound %s" % key
                    except KeyError:
                        pass
            return
        elif command == 'alias':
            if len(args) == 0:
                yield '----------'
                yield 'Aliases:'
                for i, key in enumerate(kernel.alias):
                    value = kernel.alias[key]
                    yield '%d: %s -> %s' % (i, key, value)
                yield '----------'
            else:
                key = args[0].lower()
                if key == 'default':
                    kernel.alias = dict()
                    kernel.default_alias()
                    yield 'Set default keymap.'
                    return
                kernel.alias[args[0]] = ' '.join(args[1:])
            return
        # Server Misc Command Elements
        elif command == 'rotaryview':
            if 'RotaryView' in active_device.instances['control']:
                active_device.execute('RotaryView')
            yield "RotaryView Toggled."
            return
        elif command == 'rotaryscale':
            if 'RotaryScale' in active_device.instances['control']:
                active_device.execute('RotaryScale')
            yield "Rotary Scale Applied."
            return
        elif command == 'egv':
            if len(args) >= 1:
                if active_device.device_name != 'Lhystudios':
                    yield 'Device cannot send egv data.'
                active_device.interpreter.pipe.write(bytes(args[0].replace('$', '\n'), "utf8"))
        elif command == "grblserver":
            port = 23
            tcp = True
            try:
                server = active_device.open('module', 'LaserServer',
                                            port=port,
                                            tcp=tcp,
                                            greet="Grbl 1.1e ['$' for help]\r\n")
                yield "GRBL Mode."
                chan = 'grbl'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                chan = 'server'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                server.set_pipe(active_device.using('module', 'GRBLEmulator'))
            except OSError:
                yield 'Server failed on port: %d' % port
            return

        elif command == "ruidaserver":
            try:
                server = active_device.open('module', 'LaserServer', instance_name='ruidaserver', port=50200, tcp=False)
                jog = active_device.open('module', 'LaserServer', instance_name='ruidajog', port=50207, tcp=False)
                yield 'Ruida Data Server opened on port %d.' % 50200
                yield 'Ruida Jog Server opened on port %d.' % 50207
                chan = 'ruida'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                chan = 'server'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                server.set_pipe(active_device.using('module', 'RuidaEmulator'))
                jog.set_pipe(active_device.using('module', 'RuidaEmulator'))
            except OSError:
                yield 'Server failed.'
            return
        elif command == 'flush':
            kernel.flush()
            if kernel != active_device:
                active_device.flush()
                yield 'Persistent settings force saved.'
        elif command == 'trace_hull':
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
                yield 'No elements bounds to trace.'
                return
            hull.append(hull[0])  # loop

            def trace_hull():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_MODE_RAPID
                for p in hull:
                    yield COMMAND_MOVE, p[0], p[1]

            spooler.job(trace_hull)
            return
        elif command == 'trace_quick':
            bbox = elements.bounds()
            if bbox is None:
                yield 'No elements bounds to trace.'
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
        elif command == 'pulse':
            if len(args) == 0:
                yield 'Must specify a pulse time in milliseconds.'
                return
            try:
                value = float(args[0]) / 1000.0
            except ValueError:
                yield '"%s" not a valid pulse time in milliseconds' % (args[0])
                return
            if value > 1.0:
                yield 'Exceeds 1 second limit to fire a standing laser.' % (args[0])
                try:
                    if args[1] != "idonotlovemyhouse":
                        return
                except IndexError:
                    return

            def timed_fire():
                yield COMMAND_WAIT_FINISH
                yield COMMAND_LASER_ON
                yield COMMAND_WAIT, value
                yield COMMAND_LASER_OFF

            if self.device.spooler.job_if_idle(timed_fire):
                yield 'Pulse laser for %f milliseconds' % (value * 1000.0)
            else:
                yield 'Pulse laser failed: Busy'
            return
        elif command == 'refresh':
            active_device.signal('refresh_scene')
            active_device.signal('rebuild_tree')
            yield "Refreshed."
            return
        elif command == 'shutdown':
            active_device.stop()
            return
        else:
            if command in kernel.alias:
                aliased_command = kernel.alias[command]
                for cmd in aliased_command.split(';'):
                    for e in self.interface(cmd):
                        yield e
            else:
                yield "Error. Command Unrecognized: %s" % command

    def add_element(self, element):
        kernel = self.device.device_root
        element.stroke = Color('black')
        kernel.elements.add_elem(element)
        kernel.elements.set_selected([element])
