from copy import copy

from Kernel import Modifier
from LaserOperation import *
from svgelements import *
from LaserCommandConstants import *


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
        self._plan = dict()
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
            if items is None or len(items) == 0 or elements._bounds is None:
                yield _('No item selected.')
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

        kernel.register('command/grid', grid)
        kernel.register('command-help/grid', 'grid <columns> <rows> <x_distance> <y_distance>')

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
        kernel.register('command-help/element', 'element <command>*: <#>, merge, subpath, copy, delete, *, ~, !')

        def path(command, *args):
            path_d = ' '.join(args)
            element = Path(path_d)
            self.add_element(element)
            return

        kernel.register('command/path', path)
        kernel.register('command-help/path', 'path <svg path>')

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
        kernel.register('command-help/circle', 'circle <x> <y> <r> or circle <r>')

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
        kernel.register('command-help/ellipse', 'ellipse <cx> <cy> <rx> <ry>')

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
        kernel.register('command-help/rect', 'rect <x> <y> <width> <height>')

        def text(command, *args):
            text = ' '.join(args)
            element = SVGText(text)
            self.add_element(element)

        kernel.register('command/text', text)
        kernel.register('command-help/text', 'text <text>')

        def polygon(command, *args):
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/polygon', polygon)
        kernel.register('command-help/polygon', 'polygon (<point>, <point>)*')

        def polyline(command, *args):
            element = Polygon(list(map(float, args)))
            element = Path(element)
            self.add_element(element)
            return

        kernel.register('command/polyline', polyline)
        kernel.register('command-help/polyline', 'polyline (<point>, <point>)*')

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
        kernel.register('command-help/stroke', 'stroke <svg color>')

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
        kernel.register('command-help/fill', 'fill <svg color>')

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
        kernel.register('command-help/rotate', 'rotate <angle>')

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
        kernel.register('command-help/scale', 'scale <scale> [<scale-y>]?')

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
        kernel.register('command-help/translate', 'translate <tx> <ty>')

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
        kernel.register('command-help/rotate_to', 'rotate_to <angle>')

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
        kernel.register('command-help/scale_to', 'scale_to <scale> [<scale-y>]?')

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
        kernel.register('command-help/translate_to', 'translate_to <tx> <ty>')

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
        kernel.register('command-help/resize', 'resize <x-pos> <y-pos> <width> <height>')

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
        kernel.register('command-help/matrix', 'matrix <sx> <kx> <sy> <ky> <tx> <ty>')

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
        kernel.register('command-help/reset', 'reset')

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
        kernel.register('command-help/reify', 'reify')

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
        kernel.register('command-help/operation', 'operation <commands>: <#>, *, ~, !, delete, copy')

        def classify(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            elements.classify(list(elements.elems(emphasized=True)))
            return

        kernel.register('command/classify', classify)
        kernel.register('command-help/classify', 'classify')

        def declassify(command, *args):
            if not elements.has_emphasis():
                yield _('No selected elements.')
                return
            elements.remove_elements_from_operations(list(elements.elems(emphasized=True)))
            return

        kernel.register('command/declassify', declassify)
        kernel.register('command-help/declassify', 'declassify')

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
        kernel.register('command-help/note', 'note <note>')

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
        kernel.register('command-help/cut', 'cut')

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
        kernel.register('command-help/engrave', 'engrave')

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
        kernel.register('command-help/raster', 'raster')

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
        kernel.register('command-help/step', 'step <step-size>')

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
        kernel.register('command-help/trace_hull', 'trace_hull')

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
        kernel.register('command-help/trace_quick', 'trace_quick')

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
            try:
                del obj.cache
                del obj.icon
            except AttributeError:
                pass
            obj.cache = None
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

    def clear_plan(self):
        self._plan.clear()

    def clear_files(self):
        self._filenodes.clear()

    def clear_elements_and_operations(self):
        self.clear_elements()
        self.clear_operations()

    def clear_all(self):
        self.clear_plan()
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

    def classify(self, elements, items=None, add_funct=None):
        """
        Classify does the initial placement of elements as operations.
        "Image" is the default for images.
        If element strokes are red they get classed as cut operations
        If they are otherwise they get classed as engrave.
        """
        if elements is None:
            return
        if items is None:
            items = self.ops()
        if add_funct is None:
            add_funct = self.add_op
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
            for op in items:
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
                    add_funct(op)

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

