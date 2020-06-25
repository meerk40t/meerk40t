from Kernel import *
from svgelements import *
from OperationPreprocessor import OperationPreprocessor


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
        self.laser_on = False

    def initialize(self):
        self.device.setting(int, "bed_width", 280)
        self.device.setting(int, "bed_height", 200)
        self.channel = self.device.channel_open('console')
        self.active_device = self.device

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

    def execute_jog(self, direction, amount):
        x = 0
        y = 0
        if direction == 'right':
            amount = Length(amount).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            x = amount
        elif direction == 'left':
            amount = Length(amount).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            x = -amount
        elif direction == 'up':
            amount = Length(amount).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            y = -amount
        elif direction == 'down':
            amount = Length(amount).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            y = amount
        if self.laser_on:
            def cut():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_PROGRAM
                yield COMMAND_CUT, x, y
                yield COMMAND_MODE_RAPID
                yield COMMAND_SET_ABSOLUTE
            return cut
        else:
            def move():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, x, y
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
        if command == 'help':
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
            yield 'window [(open|close) <window_name>]'
            yield 'control [<executive>]'
            yield 'module [(open|close) <module_name>]'
            yield 'schedule'
            yield 'channel [(open|close|save) <channel_name>]'
            yield '-------------------'
            yield 'element [<element>]*'
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
                if not spooler.job_if_idle(self.execute_jog(command, *args)):
                    yield 'Busy Error'
            else:
                yield 'Syntax Error'
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
                    if v not in (1,2,3,4):
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
                yield 'Loaded Windows in Device %s:' % str(active_device.uid)
                for i, name in enumerate(active_device.instances['window']):
                    module = active_device.instances['window'][name]
                    yield '%d: %s as type of %s' % (i + 1, name, type(module))
                yield '----------'
            else:
                value = args[0]
                if value == 'open':
                    index = args[1]
                    name = index
                    if len(args) >= 3:
                        name = args[2]
                    if index in kernel.registered['window']:
                        parent_window = None
                        try:
                            parent_window = active_device.gui
                        except AttributeError:
                            pass
                        active_device.open('window', name, parent_window, -1, "")
                        yield 'Window %s opened.' % name
                    else:
                        yield "Window '%s' not found." % index
                elif value == 'close':
                    index = args[1]
                    if index in active_device.instances['window']:
                        active_device.close('window', index)
                    else:
                        yield "Window '%s' not found." % index
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
                yield 'Loaded Modules in Device %s:' % str(active_device.uid)
                for i, name in enumerate(active_device.instances['module']):
                    module = active_device.instances['module'][name]
                    yield '%d: %s as type of %s' % (i + 1, name, type(module))
                yield '----------'
            else:
                value = args[0]
                if value == 'open':
                    index = args[1]
                    name = index
                    if len(args) >= 3:
                        name = args[2]
                    if index in kernel.registered['module']:
                        active_device.open('module', index, instance_name=name)
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
                parts.append('%d:' % (i+1))
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
                value = args[0]
                chan = args[1]
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
                    yield '%d: %s' % (i+1, name)
                yield '----------'
                yield 'Existing Device:'
                devices = kernel.setting(str, 'list_devices', '')
                for device in devices.split(';'):
                    try:
                        d = int(device)
                        device_name = kernel.read_persistent(str, 'device_name', 'Lhystudios', uid=d)
                        autoboot = kernel.read_persistent(bool, 'autoboot', True, uid=d)
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
                    yield '%d: %s on %s' % (i+1, device.device_name, device.device_location)
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
                            continue
                        elif value == "copy":
                            add_elem = list(map(copy, elements.elems(emphasized=True)))
                            elements.add_elems(add_elem)
                            for e in add_elem:
                                e.select()
                                e.emphasize()
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
        elif command == 'path':
            path_d = ' '.join(args)
            element = Path(path_d)
            self.add_element(element)
            return
        elif command == 'circle':
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            r_pos = Length(args[1]).value(ppi=1000.0,
                                          relative_length=min(self.device.bed_height,self.device.bed_width) * 39.3701)
            element = Circle(cx=x_pos, cy=y_pos, r=r_pos)
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'ellipse':
            x_pos = Length(args[0]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            y_pos = Length(args[1]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            rx_pos = Length(args[2]).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            ry_pos = Length(args[3]).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)
            element = Ellipse(cx=x_pos, cy=y_pos, rx=rx_pos, ry=ry_pos)
            element = Path(element)
            self.add_element(element)
            return
        elif command == 'rect':
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
                    element.transform = Matrix(matrix)
                    element.modified()
            except ValueError:
                yield "Invalid value"
            active_device.signal('refresh_scene')
            return
        elif command == 'reset':
            for element in elements.elems(emphasized=True):
                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield 'reset - %s' % (name)
                element.transform.reset()
                element.modified()
            active_device.signal('refresh_scene')
            return
        elif command == 'reify':
            for element in elements.elems(emphasized=True):
                name = str(element)
                if len(name) > 50:
                    name = name[:50] + '...'
                yield 'reified - %s' % (name)
                element.reify()
                element.altered()
            active_device.signal('refresh_scene')
            return
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
        elif command == 'cut':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = CutOperation()
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'engrave':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = EngraveOperation()
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'raster':
            if not elements.has_emphasis():
                yield "No selected elements."
                return
            op = RasterOperation()
            op.extend(elements.elems(emphasized=True))
            elements.add_op(op)
            return
        elif command == 'step':
            if len(args) == 0:
                found = False
                for op in elements.ops(emphasized=True):
                    if isinstance(op, RasterOperation):
                        step = op.raster_step
                        yield 'Step for %s is currently: %d' % (str(op), step)
                        found = True
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            step = element.values[VARIABLE_NAME_RASTER_STEP]
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
                if isinstance(op, RasterOperation):
                    op.raster_step = step
                    self.device.signal('element_property_update', op)
            for element in elements.elems(emphasized=True):
                element.values[VARIABLE_NAME_RASTER_STEP] = str(step)
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
                    yield '%d: %s' % (i, name)
                    i += 1
                yield '----------'
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
        elif command == 'reify':
            for element in elements.elems(emphasized=True):
                element.reify()
                element.altered()
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
                kernel.alias[args[0]] = ' '.join(args[1:])
            return
        # Server Misc Command Elements
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
            port = 50200
            tcp = False
            try:
                server = active_device.open('module', 'LaserServer', instance_name='ruidaserver', port=port, tcp=tcp)
                yield 'Ruida Server opened on port %d.' % port
                chan = 'ruida'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                chan = 'server'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                server.set_pipe(active_device.using('module', 'RuidaEmulator'))
            except OSError:
                yield 'Server failed on port: %d' % port
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
        elif command == 'pulse_frequency':
            if len(args) == 0:
                yield 'pulse_frequency <duration ms> <frequency hz>'
                return
            try:
                duration = float(args[0]) / 1000.0
            except ValueError:
                yield '"%s" not a valid pulse time in milliseconds' % (args[0])
                return
            try:
                frequency = float(args[1])
            except ValueError:
                yield '"%s" not a valid pulse frequency in hz' % (args[0])
                return
            try:
                pulses = int(round(duration * 500.0 / frequency))
                pulse_time = duration / pulses
            except ZeroDivisionError:
                yield 'Could not pulse within the allotted time.'
                return

            def timed_fire():
                for i in range(pulses):
                    yield COMMAND_WAIT_FINISH
                    yield COMMAND_LASER_ON
                    yield COMMAND_WAIT, pulse_time
                    yield COMMAND_LASER_OFF
                    yield COMMAND_WAIT, pulse_time

            self.device.spooler.job(timed_fire)
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
