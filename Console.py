from Kernel import *
from svgelements import *
from OperationPreprocessor import OperationPreprocessor


class Console(Module, Pipe):
    def __init__(self):
        Module.__init__(self)
        Pipe.__init__(self)
        self.channel = None
        self.pipe = None
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
        if data == 'exit\n':  # process first to quit a delegate.
            self.pipe = None
            self.channel("Exited Mode.\n")
            return
        if self.pipe is not None:
            self.pipe.write(data)
            return
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
        self.commands = [c for c in self.commands if c != command] # Only allow 1 copy of any command.
        self.commands.append(command)
        self.schedule()

    def untick_command(self, command):
        self.commands = [c for c in self.commands if c != command]
        if len(self.commands) == 0:
            self.unschedule()

    def execute_set_position(self, position_x, position_y):
        x_pos = Length(position_x).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
        y_pos = Length(position_y).value(ppi=1000.0, relative_length=self.device.bed_height * 39.3701)

        def move():
            yield COMMAND_MODE_RAPID
            yield COMMAND_LASER_OFF
            yield COMMAND_MOVE, int(x_pos), int(y_pos)
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
                yield COMMAND_LASER_ON
                yield COMMAND_MOVE, x, y
                yield COMMAND_LASER_OFF
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

    def interface(self, command):
        yield command
        args = str(command).split(' ')
        for e in self.interface_parse_command(*args):
            yield e

    def interface_parse_command(self, command, *args):
        kernel = self.device.device_root
        active_device = self.active_device
        try:
            spooler = active_device.spooler
        except AttributeError:
            spooler = None
        try:
            interpreter = active_device.interpreter
        except AttributeError:
            interpreter = None
        if command == 'help':
            yield '(right|left|up|down) <length>'
            yield 'laser [(on|off)]'
            yield 'move <x> <y>'
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
            yield 'channel [(open|close) <channel_name>]'
            yield '-------------------'
            yield 'element [<element>]*'
            yield 'path <svg_path>'
            yield 'circle <cx> <cy> <r>'
            yield 'ellipse <cx> <cy> <rx> <ry>'
            yield 'rect <x> <y> <width> <height>'
            yield 'text <text>'
            yield 'polygon [<x> <y>]*'
            yield 'polyline [<x> <y>]*'
            yield 'group'
            yield 'ungroup'
            yield 'stroke <color>'
            yield 'fill <color>'
            yield 'rotate <angle>'
            yield 'scale <scale> [<scale_y>]'
            yield 'translate <translate_x> <translate_y>'
            yield '-------------------'
            yield 'operation [<element>]*'
            yield 'classify'
            yield 'cut'
            yield 'engrave'
            yield 'raster'
            yield '-------------------'
            yield 'bind [<key> <command>]'
            yield 'alias [<alias> <command>]'
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
            spooler.add_command(COMMAND_LASER_ON)
        elif command == '-laser':
            spooler.add_command(COMMAND_LASER_OFF)
        # Laser Control Commands
        elif command == 'right' or command == 'left' or command == 'up' or command == 'down':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 1:
                spooler.send_job(self.execute_jog(command, *args))
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
        elif command == 'move':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            if len(args) == 2:
                spooler.send_job(self.execute_set_position(*args))
            else:
                yield 'Syntax Error'
            return
        elif command == 'home':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            spooler.add_command(COMMAND_HOME)
            return
        elif command == 'unlock':
            if spooler is None:
                yield 'Device has no spooler.'
                return
            spooler.add_command(COMMAND_UNLOCK)
            return
        elif command == 'speed':
            if interpreter is None:
                yield 'Device has no interpreter.'
                return
            if len(args) == 0:
                yield 'Speed set at: %f mm/s' % interpreter.speed
            else:
                try:
                    interpreter.set_speed(float(args[0]))
                except ValueError:
                    pass
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
                        active_device.open('window', name, None, -1, "")
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
            #'channel [(open|close) <channel_name>]'
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
                        yield "Not Watching Channel: %s" % chan
                    except KeyError:
                        yield "Channel %s is not opened." % chan
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
                yield '%d: %s on %s' % (0, kernel.device_name, kernel.location_name)
                for i, name in enumerate(kernel.instances['device']):
                    device = kernel.instances['device'][name]
                    yield '%d: %s on %s' % (i+1, device.device_name, device.location_name)
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
                          (self.active_device.device_name, self.active_device.location_name)
                else:
                    for i, name in enumerate(kernel.instances['device']):
                        if i + 1 == value:
                            self.active_device = kernel.instances['device'][name]
                            yield 'Device set: %s on %s' % \
                                  (self.active_device.device_name, self.active_device.location_name)
                            break
            return
        # Element commands.
        elif command == 'element':
            if len(args) == 0:
                yield '----------'
                yield 'Graphical Elements:'
                i = 0
                for element in kernel.elements:
                    selected = element in kernel.selected_elements
                    name = str(element)
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
                        yield "Value Error: %s is not an integer" % value
                        continue
                    if 0 <= value <= len(kernel.elements):
                        element = kernel.elements[value]
                        name = str(element)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if element in kernel.selected_elements:
                            kernel.selected_elements.remove(element)
                            yield "Deselecting item %d called %s" % (value, name)
                        else:
                            kernel.selected_elements.append(element)
                            yield "Selecting item %d called %s" % (value, name)
                    else:
                        yield 'index %d out of range' % value
                kernel.signal("selected_elements", kernel.selected_elements)
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
        elif command == 'group':
            # if len(kernel.selected_elements) == 0:
            #     yield "No selected elements."
            #     return
            element = Group()
            kernel = self.device.device_root
            kernel.elements.append(element)
            kernel.selected_elements.clear()
            kernel.selected_elements.append(element)
            kernel.signal("selected_elements", kernel.selected_elements)
            kernel.signal("elements", kernel.elements)
            kernel.signal("rebuild_tree", kernel.elements)
            self.active_device.signal("rebuild_tree", kernel.elements)
            return
        elif command == 'ungroup':
            # TODO: Correct this after figuring out groups.
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            for element in kernel.selected_elements:
                if isinstance(element, Group):
                    pos = element.parent.find(element)
                    if pos == -1:
                        continue
                    for e in element:
                        element.parent.insert(pos, e)
                    element.parent.remove(element)
            kernel.selected_elements.clear()
            kernel.signal("selected_elements", kernel.selected_elements)
            kernel.signal("elements", kernel.elements)
            kernel.signal("rebuild_tree", kernel.elements)
            active_device.signal('refresh_scene')
            return
        elif command == 'stroke':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            for element in kernel.selected_elements:
                element.stroke = Color(args[0])
            active_device.signal('refresh_scene')
            return
        elif command == 'fill':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            for element in kernel.selected_elements:
                element.fill = Color(args[0])
            active_device.signal('refresh_scene')
            return
        elif command == 'rotate':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            bounds = OperationPreprocessor.bounding_box(kernel.selected_elements)
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            matrix = Matrix('rotate(%s,%f,%f)' % (args[0], center_x, center_y))
            min_dim = min(self.device.window_width, self.device.window_height)
            matrix.render(ppi=1000.0, relative_length=min_dim)
            for element in kernel.selected_elements:
                element *= matrix
            active_device.signal('refresh_scene')
            return
        elif command == 'scale':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            bounds = OperationPreprocessor.bounding_box(kernel.selected_elements)
            center_x = (bounds[2] + bounds[0]) / 2.0
            center_y = (bounds[3] + bounds[1]) / 2.0
            sx = '1'
            sy = '1'
            if len(args) >= 1:
                sx = args[0]
                sy = args[0]
            if len(args) >= 2:
                sy = args[1]
            matrix = Matrix('scale(%s,%s,%f,%f)' % (sx, sy, center_x, center_y))
            min_dim = min(self.device.window_width, self.device.window_height)
            matrix.render(ppi=1000.0, relative_length=min_dim)
            for element in kernel.selected_elements:
                element *= matrix
            active_device.signal('refresh_scene')
            return
        elif command == 'translate':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            tx = '0'
            ty = '0'
            if len(args) >= 1:
                tx = args[0]
            if len(args) >= 2:
                ty = args[1]
            matrix = Matrix('translate(%s,%s)' % (tx, ty))
            min_dim = min(self.device.window_width, self.device.window_height)
            matrix.render(ppi=1000.0, relative_length=min_dim)
            for element in kernel.selected_elements:
                element *= matrix
            active_device.signal('refresh_scene')
            return
        elif command == 'reset':
            for e in kernel.selected_elements:
                e.transform.reset()
            self.device.signal('rebuild_tree', 0)
            active_device.signal('refresh_scene')
        # Operation Command Elements
        elif command == 'operation':
            if len(args) == 0:
                yield '----------'
                yield 'Operations:'
                i = 0
                for operation in kernel.operations:
                    selected = operation in kernel.selected_operations
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
                        yield "Value Error: %s is not an integer" % value
                        continue
                    if 0 <= value <= len(kernel.operations):
                        operation = kernel.operations[value]
                        name = str(operation)
                        if len(name) > 50:
                            name = name[:50] + '...'
                        if operation in kernel.selected_operations:
                            kernel.selected_operations.remove(operation)
                            yield "Deselecting item %d called %s" % (value, name)
                        else:
                            kernel.selected_operations.append(operation)
                            yield "Selecting item %d called %s" % (value, name)
                    else:
                        yield 'index %d out of range' % value
                kernel.signal("selected_operations", kernel.selected_operations)
            return
        elif command == 'classify':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            kernel.classify(kernel.selected_elements)
            self.active_device.signal("rebuild_tree", kernel.elements)
            return
        elif command == 'cut':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            op = CutOperation()
            op.extend(kernel.selected_elements)
            kernel.operations.append(op)
            self.active_device.signal("rebuild_tree", kernel.elements)
            return
        elif command == 'engrave':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            op = EngraveOperation()
            op.extend(kernel.selected_elements)
            kernel.operations.append(op)
            self.active_device.signal("rebuild_tree", kernel.elements)
            return
        elif command == 'raster':
            if len(kernel.selected_elements) == 0:
                yield "No selected elements."
                return
            op = RasterOperation()
            op.extend(kernel.selected_elements)
            kernel.operations.append(op)
            self.active_device.signal("rebuild_tree", kernel.elements)
            return
        elif command == 'step':
            if len(args) == 0:
                found = False
                for op in kernel.selected_operations:
                    if isinstance(op, RasterOperation):
                        step = op.raster_step
                        yield 'Step for %s is currently: %d' % (str(op), step)
                        found = True
                for element in kernel.selected_elements:
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
            for op in kernel.selected_operations:
                if isinstance(op, RasterOperation):
                    op.raster_step = step
                    self.device.signal("element_property_update", op)
            for element in kernel.selected_elements:
                element.values[VARIABLE_NAME_RASTER_STEP] = str(step)
                m = element.transform
                tx = m.e
                ty = m.f
                element.transform = Matrix.scale(float(step), float(step))
                element.transform.post_translate(tx, ty)
                self.device.signal("element_property_update", element)
                active_device.signal('refresh_scene')
            return
        elif command == 'resample':
            for element in kernel.selected_elements:
                if isinstance(element, SVGImage):
                    OperationPreprocessor.make_actual(element)
            active_device.signal('refresh_scene')
            return
        elif command == 'reify':
            for element in kernel.selected_elements:
                element.reify()
            active_device.signal('refresh_scene')
            return
        elif command == 'duplicate':
            copies = 1
            if len(args) >= 1:
                try:
                    copies = int(args[0])
                except ValueError:
                    pass
            adding_elements = [copy(e) for e in list(kernel.selected_elements) * copies]
            kernel.elements.extend(adding_elements)
            kernel.selected_elements.clear()
            self.device.signal('rebuild_tree', 0)
            active_device.signal('refresh_scene')
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
                server = kernel.open('module', 'LaserServer', port=port, tcp=tcp)
                yield "GRBL Mode."
                chan = 'grbl'
                active_device.add_watcher(chan, self.channel)
                yield "Watching Channel: %s" % chan
                server.set_pipe(active_device.using('module', 'GrblEmulator'))
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
        elif command == 'camera_snapshot':
            active_device.open('window', 'CameraInterface', None, -1, "")
            active_device.execute("camera_snapshot")
            return
        elif command == 'camera_update':
            active_device.open('window', 'CameraInterface', None, -1, "")
            active_device.execute("camera_update")
            return
        elif command == 'refresh':
            active_device.signal('refresh_scene')
            yield "Refreshed."
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
        kernel.elements.append(element)
        kernel.selected_elements.clear()
        kernel.selected_elements.append(element)
        kernel.signal("selected_elements", kernel.selected_elements)
        kernel.signal("elements", kernel.elements)
        kernel.signal("rebuild_tree", kernel.elements)
        self.active_device.signal("rebuild_tree", kernel.elements)
