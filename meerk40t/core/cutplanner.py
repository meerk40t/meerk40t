from copy import copy
from math import ceil, isinf, isnan

from ..core.cutcode import CutCode
from ..device.lasercommandconstants import (
    COMMAND_BEEP,
    COMMAND_FUNCTION,
    COMMAND_HOME,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_SET_ABSOLUTE,
    COMMAND_SET_POSITION,
    COMMAND_UNLOCK,
    COMMAND_WAIT,
    COMMAND_WAIT_FINISH,
)
from ..kernel import Modifier
from ..svgelements import (
    Angle,
    Group,
    Length,
    Matrix,
    Move,
    Path,
    Point,
    Polygon,
    Polyline,
    SVGElement,
    SVGImage,
    SVGText,
)
from .elements import LaserOperation


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Planner", Planner)
    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Planner")


class Planner(Modifier):
    """
    Planner is a modifier that adds 'plan' commands to the kernel. These are text based versions of the job preview and
    should be permitted to control the job creation process.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._plan = dict()
        self._default_plan = "0"

    def get_or_make_plan(self, plan_name):
        """
        Plans are a tuple of 3 lists. Plan, Original, Commands.
        """
        try:
            return self._plan[plan_name]
        except KeyError:
            self._plan[plan_name] = list(), list(), list()
            return self._plan[plan_name]

    def default_plan(self):
        return self.get_or_make_plan(self._default_plan)

    def attach(self, *a, **kwargs):
        context = self.context
        context.planner = self
        context.default_plan = self.default_plan

        kernel = self.context._kernel
        _ = kernel.translation
        elements = context.elements
        rotary_context = self.context.get_context("rotary/1")
        bed_dim = self.context.get_context("/")
        rotary_context.setting(bool, "rotary", False)
        rotary_context.setting(float, "scale_x", 1.0)
        rotary_context.setting(float, "scale_y", 1.0)
        self.context.setting(bool, "prehome", False)
        self.context.setting(bool, "prephysicalhome", False)
        self.context.setting(bool, "postunlock", False)
        self.context.setting(bool, "autohome", False)
        self.context.setting(bool, "autophysicalhome", False)
        self.context.setting(bool, "autoorigin", False)
        self.context.setting(bool, "autobeep", True)
        self.context.setting(bool, "opt_reduce_travel", True)
        self.context.setting(bool, "opt_inner_first", True)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_remove_overlap", False)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_start_from_position", False)
        self.context.setting(bool, "opt_rapid_between", False)
        self.context.setting(int, "opt_jog_minimum", 127)
        self.context.setting(int, "opt_jog_mode", 0)

        kernel.register("plan/physicalhome", self.physicalhome)
        kernel.register("plan/home", self.home)
        kernel.register("plan/origin", self.origin)
        kernel.register("plan/unlock", self.unlock)
        kernel.register("plan/wait", self.wait)
        kernel.register("plan/beep", self.beep)
        kernel.register("plan/interrupt", self.interrupt)

        @self.context.console_argument("alias", type=str, help="plan command name to alias")
        @self.context.console_command(
            "plan-alias",
            help="Define a spoolable console command",
            input_type=None,
            output_type=None,
        )
        def plan_alias(command, channel, _, alias=None, remainder=None, **kwargs):
            """
            Plan alias allows the user to define a spoolable console command.
            eg. plan-alias export egv_export myfile.egv

            This creates a plan command called "export" that executes "egv_export myfile.egv".
            This can then be placed into the spooler during the planning stages.
            When the spooler reaches the command it will execute the console command.
            This would then run: "egv_export myfile.egv" which would save the current buffer.
            """
            if alias is None:
                raise SyntaxError
            plan_command = "plan/%s" % alias
            if plan_command in self.context.registered:
                raise SyntaxError("You may not overwrite an already used alias.")

            def user_defined_alias():
                for s in remainder.split(';'):
                    self.context(s + '\n')
            user_defined_alias.__name__ = remainder
            self.context.registered[plan_command] = user_defined_alias

        @self.context.console_command(
            "plan",
            help="plan<?> <command>",
            regex=True,
            input_type=(None, "ops"),
            output_type="plan",
        )
        def plan(command, channel, _, op=None, args=tuple(), **kwargs):
            if len(command) > 4:
                self._default_plan = command[4:]
                self.context.signal("plan", self._default_plan, None)
            return "plan", self.get_or_make_plan(self._default_plan)

        @self.context.console_command(
            "list",
            help="plan<?> list",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            channel(_("----------"))
            channel(_("Plan:"))
            for i, plan_name in enumerate(self._plan):
                channel("%d: %s" % (i, plan_name))
            channel(_("----------"))
            channel(_("Plan %s:" % self._default_plan))
            for i, op_name in enumerate(plan):
                channel("%d: %s" % (i, op_name))
            channel(_("Commands %s:" % self._default_plan))
            for i, cmd_name in enumerate(commands):
                channel("%d: %s" % (i, cmd_name))
            channel(_("----------"))
            return data_type, data

        @self.context.console_command(
            "classify",
            help="plan<?> classify",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            elements.classify(list(elements.elems(emphasized=True)), plan, plan.append)
            return data_type, data

        @self.context.console_command(
            "copy-selected",
            help="plan<?> copy-selected",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            for c in elements.ops(emphasized=True):
                if not c.output:
                    continue
                try:
                    if len(c) == 0:
                        continue
                except TypeError:
                    pass
                plan.append(copy(c))
            channel(_("Copied Operations."))
            self.context.signal("plan", self._default_plan, 1)
            return data_type, data

        @self.context.console_command(
            "copy",
            help="plan<?> copy",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            for c in elements.ops():
                if not c.output:
                    continue
                try:
                    if len(c) == 0:
                        continue
                except TypeError:
                    pass
                plan.append(copy(c))
            channel(_("Copied Operations."))
            self.context.signal("plan", self._default_plan, 1)
            return data_type, data

        @self.context.console_option("index", "i", type=int, help="insert index")
        @self.context.console_option("op", "o", type=str, help="unlock, origin, home, etc.")
        @self.context.console_command(
            "command",
            help="plan<?> command",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, op=None, index=None, data=None, **kwargs):
            plan, original, commands = data
            if op is None:
                channel(_("Plan Commands:"))
                for command_name in self.context.match("plan/.*", suffix=True):
                    channel(command_name)
                return
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    if index is None:
                        plan.append(plan_command)
                    else:
                        try:
                            plan.insert(index, plan_command)
                        except ValueError:
                            channel(_("Invalid index for command insert."))
                    break
                self.context.signal("plan", self._default_plan, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.context.console_argument("op", type=str, help="unlock, origin, home, etc")
        @self.context.console_command(
            "append",
            help="plan<?> append <op>",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, op=None, data=None, **kwargs):
            plan, original, commands = data
            if op is None:
                raise SyntaxError
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    plan.append(plan_command)
                    break
                self.context.signal("plan", self._default_plan, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.context.console_argument("op", type=str, help="unlock, origin, home, etc")
        @self.context.console_command(
            "prepend",
            help="plan<?> prepend <op>",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, op=None, data=None, **kwargs):
            plan, original, commands = data
            if op is None:
                raise SyntaxError
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    plan.insert(0, plan_command)
                    break
                self.context.signal("plan", self._default_plan, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.context.console_command(
            "preprocess",
            help="plan<?> preprocess",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            rotary_context = self.context.get_context("rotary/1")
            if self.context.prephysicalhome:
                if not rotary_context.rotary:
                    plan.insert(0, self.context.registered["plan/physicalhome"])
                else:
                    plan.insert(0, _("Physical Home Before: Disabled (Rotary On)"))
            if self.context.prehome:
                if not rotary_context.rotary:
                    plan.insert(0, self.context.registered["plan/home"])
                else:
                    plan.insert(0, _("Home Before: Disabled (Rotary On)"))
            if self.context.autobeep:
                plan.append(self.context.registered["plan/beep"])
            if self.context.autohome:
                if not rotary_context.rotary:
                    plan.append(self.context.registered["plan/home"])
                else:
                    plan.append(_("Home After: Disabled (Rotary On)"))
            if self.context.autophysicalhome:
                if not rotary_context.rotary:
                    plan.append(self.context.registered["plan/physicalhome"])
                else:
                    plan.append(_("Physical Home After: Disabled (Rotary On)"))
            if self.context.autoorigin:
                plan.append(self.context.registered["plan/origin"])
            if self.context.postunlock:
                plan.append(self.context.registered["plan/unlock"])
            # divide
            self.conditional_jobadd_strip_text()
            if rotary_context.rotary:
                self.conditional_jobadd_scale_rotary()
            self.conditional_jobadd_actualize_image()
            self.conditional_jobadd_make_raster()
            self.context.signal("plan", plan, 2)
            return data_type, data

        @self.context.console_command(
            "validate",
            help="plan<?> validate",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            self.execute()
            self.context.signal("plan", self._default_plan, 3)
            return data_type, data

        @self.context.console_command(
            "blob",
            help="plan<?> blob",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data

            blob = CutCode()
            first_index = None
            for i, c in enumerate(plan):
                # try:
                try:
                    c.settings.jog_distance = self.context.opt_jog_minimum
                    c.settings.jog_enable = self.context.opt_rapid_between
                    b = c.as_blob()
                    if b is not None:
                        blob.extend(b)
                        if first_index is None:
                            first_index = i
                    plan[i] = None
                except AttributeError:
                    pass
            if first_index is not None:
                plan.insert(first_index, blob)
            for i in range(len(plan) - 1, -1, -1):
                c = plan[i]
                if c is None:
                    del plan[i]
            self.context.signal("plan", self._default_plan, 4)
            return data_type, data

        @self.context.console_command(
            "preopt",
            help="plan<?> preopt",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            if self.context.opt_reduce_travel:
                self.conditional_jobadd_optimize_travel()
            if self.context.opt_inner_first:
                self.conditional_jobadd_optimize_cuts()
            if self.context.opt_reduce_directions:
                pass
            if self.context.opt_remove_overlap:
                pass
            self.context.signal("plan", self._default_plan, 5)
            return data_type, data

        @self.context.console_command(
            "optimize",
            help="plan<?> optimize",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            self.execute()
            self.context.signal("plan", self._default_plan, 6)
            return data_type, data

        @self.context.console_command(
            "clear",
            help="plan<?> clear",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            plan.clear()
            commands.clear()
            self.context.signal("plan", self._default_plan, 0)
            return data_type, data

        @self.context.console_command(
            "spool",
            help="plan<?> spool",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands = data
            active = context.active
            if active is None:
                return
            context.active.spooler.jobs(plan)
            channel(_("Spooled Plan."))
            self.context.signal("plan", self._default_plan, 6)
            return data_type, data

        @self.context.console_option("op", "o", type=str, help="unlock, origin, home")
        @self.context.console_argument("cols", type=int, help="columns for the grid")
        @self.context.console_argument("rows", type=int, help="rows for the grid")
        @self.context.console_argument(
            "x_distance", type=Length, help="x_distance each column step"
        )
        @self.context.console_argument(
            "y_distance", type=Length, help="y_distance each row step"
        )
        @self.context.console_command(
            "step_repeat",
            help="plan<?> step_repeat",
            input_type="plan",
            output_type="plan",
        )
        def plan(
            command,
            channel,
            _,
            cols=0,
            rows=0,
            x_distance=None,
            y_distance=None,
            data_type=None,
            data=None,
            **kwargs
        ):
            plan, original, commands = data
            if y_distance is None:
                raise SyntaxError
            # TODO: IMPLEMENT!
            # TODO: Implement the 0.6.19 switch changes.
            self.operations.clear()
            self.preprocessor.commands = list()
            x_distance = int(x_distance)
            y_distance = int(y_distance)
            x_last = 0
            y_last = 0
            y_pos = 0
            x_pos = 0
            for j in range(rows):
                x_pos = 0
                for k in range(cols):
                    x_offset = x_pos - x_last
                    y_offset = y_pos - y_last
                    self.operations.append(OperationPreprocessor.origin)
                    if x_offset != 0 or y_offset != 0:
                        self.operations.append(
                            OperationPreprocessor.offset(x_offset, y_offset)
                        )
                    self.operations.extend(list(self._original_ops))
                    x_last = x_pos
                    y_last = y_pos
                    x_pos += x_distance
                y_pos += y_distance
            if x_pos != 0 or y_pos != 0:
                self.operations.append(OperationPreprocessor.offset(-x_pos, -y_pos))
            self.refresh_lists()
            self.update_gui()
            return data_type, data

        # @self.context.console_command(
        #     "scale_speed",
        #     help="plan<?> scale_speed",
        #     input_type="plan",
        #     output_type="plan",
        # )
        # def plan(command, channel, _, data_type=None, data=None, **kwargs):
        #     plan, original, commands = data
        #     return data_type, data

    def plan(self, **kwargs):
        for item in self._plan:
            yield item

    def execute(self):
        # Using copy of commands, so commands can add ops.
        plan, original, commands = self.default_plan()
        cmds = commands[:]
        commands.clear()
        for cmd in cmds:
            cmd()

    def conditional_jobadd_strip_text(self):
        plan, original, commands = self.default_plan()
        for op in plan:
            try:
                if op.operation in ("Cut", "Engrave"):
                    for e in op.children:
                        if not isinstance(e, SVGText):
                            continue  # make raster not needed since its a single real raster.
                        self.jobadd_strip_text()
                        return True
            except AttributeError:
                pass
        return False

    def jobadd_strip_text(self):
        plan, original, commands = self.default_plan()

        def strip_text():
            stripped = False
            for k, op in enumerate(plan):
                try:
                    if op.operation in ("Cut", "Engrave"):
                        changed = False
                        for i, e in enumerate(op.children):
                            if isinstance(e, SVGText):
                                op[i] = None
                                changed = True
                        if changed:
                            p = [q for q in op if q is not None]
                            op.clear()
                            op.extend(p)
                            if len(op) == 0:
                                plan[k] = None
                                stripped = True
                except AttributeError:
                    pass
            if stripped:
                p = [q for q in plan if q is not None]
                plan.clear()
                plan.extend(p)

        commands.append(strip_text)

    def conditional_jobadd_make_raster(self):
        plan, original, commands = self.default_plan()
        for op in plan:
            try:
                if op.operation == "Raster":
                    if len(op.children) == 0:
                        continue
                    if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                        continue  # make raster not needed since its a single real raster.
                    self.jobadd_make_raster()
                    return True
            except AttributeError:
                pass
        return False

    def jobadd_make_raster(self):
        make_raster = self.context.registered.get("render-op/make_raster")
        plan, original, commands = self.default_plan()

        def strip_rasters():
            stripped = False
            for k, op in enumerate(plan):
                try:
                    if op.operation in ("Raster"):
                        if len(op) == 1 and isinstance(op[0], SVGImage):
                            continue
                        plan[k] = None
                        stripped = True
                except AttributeError:
                    pass
            if stripped:
                p = [q for q in plan if q is not None]
                plan.clear()
                plan.extend(p)

        def make_image():
            for op in plan:
                try:
                    if op.operation == "Raster":
                        if len(op.children) == 1 and isinstance(
                            op.children[0], SVGImage
                        ):
                            continue

                        subitems = list(op.flat(types=("elem", "opnode")))
                        make_raster = self.context.registered.get(
                            "render-op/make_raster"
                        )
                        bounds = Group.union_bbox([s.object for s in subitems])

                        if bounds is None:
                            continue
                        xmin, ymin, xmax, ymax = bounds

                        image = make_raster(
                            subitems, bounds, step=op.settings.raster_step
                        )
                        image_element = SVGImage(image=image)
                        image_element.transform.post_translate(xmin, ymin)
                        op.children.clear()
                        op.add(image_element, type="opnode")
                except AttributeError:
                    continue

        if make_raster is None:
            commands.append(strip_rasters)
        else:
            commands.append(make_image)

    def conditional_jobadd_optimize_travel(self):
        self.jobadd_optimize_travel()

    def jobadd_optimize_travel(self):
        def optimize_travel():
            pass

        plan, original, commands = self.default_plan()
        commands.append(optimize_travel)

    def conditional_jobadd_optimize_cuts(self):
        plan, original, commands = self.default_plan()
        for op in plan:
            try:
                if op.operation in ("Cut"):
                    self.jobadd_optimize_cuts()
                    return
            except AttributeError:
                pass

    def jobadd_optimize_cuts(self):
        def optimize_cuts():
            plan, original, commands = self.default_plan()
            for op in plan:
                try:
                    if op.operation in ("Cut"):
                        op_cuts = self.optimize_cut_inside(op)
                        op.clear()
                        op.append(op_cuts)
                except AttributeError:
                    pass

        plan, original, commands = self.default_plan()
        commands.append(optimize_cuts)

    def conditional_jobadd_actualize_image(self):
        plan, original, commands = self.default_plan()
        for op in plan:
            try:
                if op.operation == "Raster":
                    for elem in op.children:
                        elem = elem.object
                        if self.needs_actualization(elem, op.settings.raster_step):
                            self.jobadd_actualize_image()
                            return
                if op.operation == "Image":
                    for elem in op.children:
                        elem = elem.object
                        if self.needs_actualization(elem, None):
                            self.jobadd_actualize_image()
                            return
            except AttributeError:
                pass

    def jobadd_actualize_image(self):
        def actualize():
            plan, original, commands = self.default_plan()
            for op in plan:
                try:
                    if op.operation == "Raster":
                        for elem in op.children:
                            elem = elem.object
                            if self.needs_actualization(elem, op.settings.raster_step):
                                self.make_actual(elem, op.settings.raster_step)
                    if op.operation == "Image":
                        for elem in op.children:
                            elem = elem.object
                            if self.needs_actualization(elem, None):
                                self.make_actual(elem, None)
                except AttributeError:
                    pass

        plan, original, commands = self.default_plan()
        commands.append(actualize)

    def conditional_jobadd_scale_rotary(self):
        rotary_context = self.context.get_context("rotary/1")
        if rotary_context.scale_x != 1.0 or rotary_context.scale_y != 1.0:
            self.jobadd_scale_rotary()

    def jobadd_scale_rotary(self):
        def scale_for_rotary():
            r = self.context.get_context("rotary/1")
            a = self.context.active
            scale_str = "scale(%f,%f,%f,%f)" % (
                r.scale_x,
                r.scale_y,
                a.current_x,
                a.current_y,
            )
            plan, original, commands = self.default_plan()
            for o in plan:
                if isinstance(o, LaserOperation):
                    for e in o.children:
                        e = e.object
                        try:
                            e *= scale_str
                        except AttributeError:
                            pass
            self.conditional_jobadd_actualize_image()

        plan, original, commands = self.default_plan()
        commands.append(scale_for_rotary)

    @staticmethod
    def needs_actualization(image_element, step_level=None):
        if not isinstance(image_element, SVGImage):
            return False
        if step_level is None:
            if "raster_step" in image_element.values:
                step_level = float(image_element.values["raster_step"])
            else:
                step_level = 1.0
        m = image_element.transform
        # Transformation must be uniform to permit native rastering.
        return m.a != step_level or m.b != 0.0 or m.c != 0.0 or m.d != step_level

    @staticmethod
    def make_actual(image_element, step_level=None):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        if not isinstance(image_element, SVGImage):
            return
        from PIL import Image

        pil_image = image_element.image
        image_element.cache = None
        matrix = image_element.transform
        bbox = Group.union_bbox([image_element])
        element_width = int(ceil(bbox[2] - bbox[0]))
        element_height = int(ceil(bbox[3] - bbox[1]))
        if step_level is None:
            # If we are not told the step amount either draw it from the object or set it to default.
            if "raster_step" in image_element.values:
                step_level = float(image_element.values["raster_step"])
            else:
                step_level = 1.0
        step_scale = 1 / float(step_level)
        tx = bbox[0]
        ty = bbox[1]
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(
            step_scale, step_scale
        )  # step level requires the actual image be scaled down.
        matrix.inverse()

        if (
            matrix.value_skew_y() != 0.0 or matrix.value_skew_y() != 0.0
        ) and pil_image.mode != "RGBA":
            # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
            pil_image = pil_image.convert("RGBA")

        pil_image = pil_image.transform(
            (element_width, element_height),
            Image.AFFINE,
            (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
            resample=Image.BICUBIC,
        )
        image_element.image_width, image_element.image_height = (
            element_width,
            element_height,
        )
        matrix.reset()

        box = pil_image.getbbox()
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width != element_width and height != element_height:
            image_element.image_width, image_element.image_height = (width, height)
            pil_image = pil_image.crop(box)
            matrix.post_translate(box[0], box[1])
        # step level requires the new actualized matrix be scaled up.
        matrix.post_scale(step_level, step_level)
        matrix.post_translate(tx, ty)
        image_element.image = pil_image

    @staticmethod
    def origin():
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MOVE, 0, 0

    @staticmethod
    def unlock():
        yield COMMAND_MODE_RAPID
        yield COMMAND_UNLOCK

    @staticmethod
    def home():
        yield COMMAND_HOME

    @staticmethod
    def physicalhome():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_HOME, 0, 0

    @staticmethod
    def offset(x, y):
        def offset_value():
            yield COMMAND_WAIT_FINISH
            yield COMMAND_SET_POSITION, -int(x), -int(y)

        return offset_value

    @staticmethod
    def wait():
        wait_amount = 5.0
        yield COMMAND_WAIT_FINISH
        yield COMMAND_WAIT, wait_amount

    @staticmethod
    def beep():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_BEEP

    @staticmethod
    def interrupt():
        yield COMMAND_WAIT_FINISH

        def intr():
            input("waiting for user...")

        yield COMMAND_FUNCTION, intr

    @staticmethod
    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)
        self.scene_bounds = None

    @staticmethod
    def bounding_box(elements):
        if isinstance(elements, SVGElement):
            elements = [elements]
        elif isinstance(elements, list):
            try:
                elements = [
                    e.object for e in elements if isinstance(e.object, SVGElement)
                ]
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

    @staticmethod
    def is_inside(inner_path, outer_path):
        """
        Test that path1 is inside path2.
        :param inner_path: inner path
        :param outer_path: outer path
        :return: whether path1 is wholely inside path2.
        """
        if not hasattr(inner_path, "bounding_box"):
            inner_path.bounding_box = Group.union_bbox([inner_path])
        if not hasattr(outer_path, "bounding_box"):
            outer_path.bounding_box = Group.union_bbox([outer_path])
        if outer_path.bounding_box[0] > inner_path.bounding_box[0]:
            # outer minx > inner minx (is not contained)
            return False
        if outer_path.bounding_box[1] > inner_path.bounding_box[1]:
            # outer miny > inner miny (is not contained)
            return False
        if outer_path.bounding_box[2] < inner_path.bounding_box[2]:
            # outer maxx < inner maxx (is not contained)
            return False
        if outer_path.bounding_box[3] < inner_path.bounding_box[3]:
            # outer maxy < inner maxy (is not contained)
            return False
        if outer_path.bounding_box == inner_path.bounding_box:
            if outer_path == inner_path:  # This is the same object.
                return False
        if not hasattr(outer_path, "vm"):
            outer_path = Polygon(
                [outer_path.point(i / 100.0, error=1e4) for i in range(101)]
            )
            vm = VectorMontonizer()
            vm.add_cluster(outer_path)
            outer_path.vm = vm
        for i in range(101):
            p = inner_path.point(i / 100.0, error=1e4)
            if not outer_path.vm.is_point_inside(p.x, p.y):
                return False
        return True

    @staticmethod
    def optimize_cut_inside(paths):
        optimized = Path()
        if isinstance(paths, Path):
            paths = [paths]
        subpaths = []
        for path in paths:
            subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if Planner.is_inside(subpaths[k], subpaths[j]):
                    t = subpaths[j]
                    subpaths[j] = subpaths[k]
                    subpaths[k] = t
        for p in subpaths:
            optimized += p
            try:
                del p.vm
            except AttributeError:
                pass
            try:
                del p.bounding_box
            except AttributeError:
                pass
        return optimized


class Segment:
    def __init__(self, a, b, index=0):
        self.visited = 0
        self.a = a
        self.b = b
        self.active = False
        self.value = "RUNG"
        self.index = index
        self.bisectors = []
        self.object = None

    def __len__(self):
        # [False, i, p0, p1, high, low, m, b, path]
        return 9

    def __getitem__(self, item):
        if item == 0:
            return self.active
        if item == 1:
            return self.index
        if item == 2:
            return self.a
        if item == 3:
            return self.b
        if item == 4:
            if self.a.y > self.b.y:
                return self.a
            else:
                return self.b
        if item == 5:
            if self.a.y < self.b.y:
                return self.a
            else:
                return self.b
        if item == 6:
            if self.b[0] - self.a[0] == 0:
                return float("inf")
            return (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
        if item == 7:
            if self.b[0] - self.a[0] == 0:
                return float("inf")
            im = (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
            return self.a[1] - (im * self.a[0])
        if item == 8:
            return self.object

    def intersect(self, segment):
        return Segment.line_intersect(
            self.a[0],
            self.a[1],
            self.b[0],
            self.b[1],
            segment.a[0],
            segment.a[1],
            segment.b[0],
            segment.b[1],
        )

    def sort_bisectors(self):
        def distance(a):
            return self.a.distance_to(a)

        self.bisectors.sort(key=distance)

    def get_intercept(self, y):
        im = (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
        ib = self.a[1] - (im * self.a[0])
        if isnan(im) or isinf(im):
            return self.a[0]
        return (y - ib) / im

    @staticmethod
    def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return None  # Parallel.
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
            return (x1 + ua * (x2 - x1)), (y1 + ua * (y2 - y1))
        return None


class VectorMontonizer:
    def __init__(
        self, low_value=-float("inf"), high_value=float("inf"), start=-float("inf")
    ):
        self.clusters = []
        self.dirty_cluster_sort = True

        self.actives = []
        self.dirty_actives_sort = True

        self.current = start
        self.dirty_cluster_position = True

        self.valid_low_value = low_value
        self.valid_high_value = high_value
        self.cluster_range_index = 0
        self.cluster_low_value = float("inf")
        self.cluster_high_value = -float("inf")

    def add_segments(self, links):
        self.dirty_cluster_position = True
        self.dirty_cluster_sort = True
        self.dirty_actives_sort = True
        for s in links:
            self.clusters.append((s[4].y, s))  # High
            self.clusters.append((s[5].y, s))  # Low

    def add_cluster(self, path):
        self.dirty_cluster_position = True
        self.dirty_cluster_sort = True
        self.dirty_actives_sort = True
        for i in range(len(path) - 1):
            p0 = path[i]
            p1 = path[i + 1]
            if p0.y > p1.y:
                high = p0
                low = p1
            else:
                high = p1
                low = p0
            try:
                m = (high.y - low.y) / (high.x - low.x)
            except ZeroDivisionError:
                m = float("inf")

            b = low.y - (m * low.x)
            if self.valid_low_value > high.y:
                continue  # Cluster before range.
            if self.valid_high_value < low.y:
                continue  # Cluster after range.
            cluster = Segment(p0, p1)
            # cluster = [False, i, p0, p1, high, low, m, b, path]
            if self.valid_low_value < low.y:
                self.clusters.append((low.y, cluster))
            if self.valid_high_value > high.y:
                self.clusters.append((high.y, cluster))
            if high.y >= self.current >= low.y:
                cluster.active = True
                self.actives.append(cluster)

    def valid_range(self):
        return self.valid_high_value >= self.current >= self.valid_low_value

    def next_intercept(self, delta):
        self.scanline(self.current + delta)
        self.sort_actives()
        return self.valid_range()

    def sort_clusters(self):
        if not self.dirty_cluster_sort:
            return
        self.clusters.sort(key=lambda e: e[0])
        self.dirty_cluster_sort = False

    def sort_actives(self):
        if not self.dirty_actives_sort:
            return
        self.actives.sort(key=self.intercept)
        self.dirty_actives_sort = False

    def intercept(self, e, y=None):
        if y is None:
            y = self.current
        m = e[6]
        b = e[7]
        if m == float("nan") or m == float("inf"):
            low = e[5]
            return low.x
        return (y - b) / m

    def find_cluster_position(self):
        if not self.dirty_cluster_position:
            return
        self.dirty_cluster_position = False
        self.sort_clusters()

        self.cluster_range_index = -1
        self.cluster_high_value = -float("inf")
        self.increment_cluster()

        while self.is_higher_than_cluster_range(self.current):
            self.increment_cluster()

    def in_cluster_range(self, v):
        return not self.is_lower_than_cluster_range(
            v
        ) and not self.is_higher_than_cluster_range(v)

    def is_lower_than_cluster_range(self, v):
        return v < self.cluster_low_value

    def is_higher_than_cluster_range(self, v):
        return v > self.cluster_high_value

    def increment_cluster(self):
        self.cluster_range_index += 1
        self.cluster_low_value = self.cluster_high_value
        if self.cluster_range_index < len(self.clusters):
            self.cluster_high_value = self.clusters[self.cluster_range_index][0]
        else:
            self.cluster_high_value = float("inf")
        if self.cluster_range_index > 0:
            return self.clusters[self.cluster_range_index - 1][1]
        else:
            return None

    def decrement_cluster(self):
        self.cluster_range_index -= 1
        self.cluster_high_value = self.cluster_low_value
        if self.cluster_range_index > 0:
            self.cluster_low_value = self.clusters[self.cluster_range_index - 1][0]
        else:
            self.cluster_low_value = -float("inf")
        return self.clusters[self.cluster_range_index][1]

    def is_point_inside(self, x, y):
        self.scanline(y)
        self.sort_actives()
        for i in range(1, len(self.actives), 2):
            prior = self.actives[i - 1]
            after = self.actives[i]
            if self.intercept(prior, y) <= x <= self.intercept(after, y):
                return True
        return False

    def scanline(self, scan):
        self.dirty_actives_sort = True
        self.sort_clusters()
        self.find_cluster_position()

        while self.is_lower_than_cluster_range(scan):
            c = self.decrement_cluster()
            if c.active:
                c.active = False
                self.actives.remove(c)
            else:
                c.active = True
                self.actives.append(c)

        while self.is_higher_than_cluster_range(scan):
            c = self.increment_cluster()
            if c.active:
                c.active = False
                self.actives.remove(c)
            else:
                c.active = True
                self.actives.append(c)

        self.current = scan


