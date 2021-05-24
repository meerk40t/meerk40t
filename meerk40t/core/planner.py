from copy import copy
from math import ceil

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
from ..svgelements import Group, Length, Path, Polygon, SVGElement, SVGImage, SVGText
from ..tools.pathtools import VectorMontonizer
from .elements import LaserOperation


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel_root = kernel.root
        kernel.register("modifier/Planner", Planner)

        kernel.register("plan/physicalhome", Planner.physicalhome)
        kernel.register("plan/home", Planner.home)
        kernel.register("plan/origin", Planner.origin)
        kernel.register("plan/unlock", Planner.unlock)
        kernel.register("plan/wait", Planner.wait)
        kernel.register("plan/beep", Planner.beep)
        kernel.register("plan/interrupt", Planner.interrupt)

        def shutdown():
            yield COMMAND_WAIT_FINISH

            def shutdown_program():
                kernel_root("quit\n")

            yield COMMAND_FUNCTION, shutdown_program

        kernel.register("plan/shutdown", shutdown)

    elif lifecycle == "boot":
        kernel_root = kernel.root
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
        Plans are a tuple of 3 lists and the name. Plan, Original, Commands, and Plan-Name
        """
        try:
            return self._plan[plan_name]
        except KeyError:
            self._plan[plan_name] = list(), list(), list(), plan_name
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
        bed_dim = self.context.root
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

        @self.context.console_argument(
            "alias", type=str, help="plan command name to alias"
        )
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
                for s in remainder.split(";"):
                    self.context(s + "\n")

            user_defined_alias.__name__ = remainder
            self.context.registered[plan_command] = user_defined_alias

        @self.context.console_command(
            "plan",
            help="plan<?> <command>",
            regex=True,
            input_type=(None, "ops"),
            output_type="plan",
        )
        def plan(command, channel, _, data=None, remainder=None, **kwargs):
            if len(command) > 4:
                self._default_plan = command[4:]
                self.context.signal("plan", self._default_plan, None)

            if data is not None:
                # If ops data is in data, then we copy that and move on to next step.
                plan, original, commands, name = self.get_or_make_plan(
                    self._default_plan
                )
                for c in data:
                    if not c.output:
                        continue
                    try:
                        if len(c.children) == 0:
                            continue
                    except TypeError:
                        pass
                    copy_c = copy(c)
                    try:
                        copy_c.deep_copy_children(c)
                    except AttributeError:
                        pass
                    plan.append(copy_c)
                self.context.signal("plan", self._default_plan, 1)
                return "plan", (plan, original, commands, self._default_plan)

            data = self.get_or_make_plan(self._default_plan)
            if remainder is None:
                plan, original, commands, name = data
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

            return "plan", data

        @self.context.console_command(
            "list",
            help="plan<?> list",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands, name = data
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
            plan, original, commands, name = data
            elements.classify(list(elements.elems(emphasized=True)), plan, plan.append)
            return data_type, data

        @self.context.console_command(
            "copy-selected",
            help="plan<?> copy-selected",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands, name = data
            for c in elements.ops(emphasized=True):
                try:
                    if not c.output:
                        continue
                except AttributeError:
                    pass
                copy_c = copy(c)
                try:
                    copy_c.deep_copy_children(c)
                except AttributeError:
                    pass
                plan.append(copy_c)

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
            plan, original, commands, name = data
            operations = elements.get(type="branch ops")
            for c in operations.flat(types=("op", "cutcode", "cmdop"), depth=1):
                try:
                    if not c.output:
                        continue
                except AttributeError:
                    pass
                try:
                    if len(c) == 0:
                        continue
                except TypeError:
                    pass
                copy_c = copy(c)
                try:
                    copy_c.deep_copy_children(c)
                except AttributeError:
                    pass
                plan.append(copy_c)
            channel(_("Copied Operations."))
            self.context.signal("plan", self._default_plan, 1)
            return data_type, data

        @self.context.console_option("index", "i", type=int, help="insert index")
        @self.context.console_option(
            "op", "o", type=str, help="unlock, origin, home, etc."
        )
        @self.context.console_command(
            "command",
            help="plan<?> command",
            input_type="plan",
            output_type="plan",
        )
        def plan(
            command,
            channel,
            _,
            data_type=None,
            op=None,
            index=None,
            data=None,
            **kwargs
        ):
            plan, original, commands, name = data
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
            plan, original, commands, name = data
            if op is None:
                raise SyntaxError
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    plan.append(plan_command)
                    self.context.signal("plan", self._default_plan, None)
                    return data_type, data
            except (KeyError, IndexError):
                pass
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
            plan, original, commands, name = data
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
            plan, original, commands, name = data
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
            self.context.signal("plan", self._default_plan, 2)
            return data_type, data

        @self.context.console_command(
            "validate",
            help="plan<?> validate",
            input_type="plan",
            output_type="plan",
        )
        def plan(command, channel, _, data_type=None, data=None, **kwargs):
            plan, original, commands, name = data
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
            plan, original, commands, name = data

            for i, c in enumerate(plan):
                first_index = None
                blob = CutCode()
                try:
                    if c.operation == "Dots":
                        continue
                    b = c.as_blob()
                    if b is not None:
                        blob.extend(b)
                        if first_index is None:
                            first_index = i
                    plan[i] = None
                    c.settings.jog_distance = self.context.opt_jog_minimum
                    c.settings.jog_enable = self.context.opt_rapid_between
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
            plan, original, commands, name = data
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
            plan, original, commands, name = data
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
            plan, original, commands, name = data
            plan.clear()
            commands.clear()
            self.context.signal("plan", self._default_plan, 0)
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
            plan, original, commands, name = data
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

    def plan(self, **kwargs):
        for item in self._plan:
            yield item

    def execute(self):
        # Using copy of commands, so commands can add ops.
        plan, original, commands, name = self.default_plan()
        cmds = commands[:]
        commands.clear()
        for cmd in cmds:
            cmd()

    def conditional_jobadd_strip_text(self):
        plan, original, commands, name = self.default_plan()
        for op in plan:
            try:
                if op.operation in ("Cut", "Engrave"):
                    for e in op.children:
                        if not isinstance(e.object, SVGText):
                            continue  # make raster not needed since its a single real raster.
                        self.jobadd_strip_text()
                        return True
            except AttributeError:
                pass
        return False

    def jobadd_strip_text(self):
        plan, original, commands, name = self.default_plan()

        def strip_text():
            for k in range(len(plan) - 1, -1, -1):
                op = plan[k]
                try:
                    if op.operation in ("Cut", "Engrave"):
                        for i, e in enumerate(list(op.children)):
                            if isinstance(e.object, SVGText):
                                e.remove_node()
                        if len(op.children) == 0:
                            del plan[k]
                except AttributeError:
                    pass

        commands.append(strip_text)

    def conditional_jobadd_make_raster(self):
        plan, original, commands, name = self.default_plan()
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
        plan, original, commands, name = self.default_plan()

        def strip_rasters():
            stripped = False
            for k, op in enumerate(plan):
                try:
                    if op.operation == "Raster":
                        if len(op.children) == 1 and isinstance(op[0], SVGImage):
                            continue
                        plan[k] = None
                        stripped = True
                except AttributeError:
                    pass
            if stripped:
                p = [q for q in plan if q is not None]
                plan.clear()
                plan.extend(p)

        def make_image_for_op(op):
            subitems = list(op.flat(types=("elem", "opnode")))
            make_raster = self.context.registered.get("render-op/make_raster")
            objs = [s.object for s in subitems]
            bounds = Group.union_bbox(objs)
            if bounds is None:
                return None
            xmin, ymin, xmax, ymax = bounds
            image = make_raster(subitems, bounds, step=op.settings.raster_step)
            image_element = SVGImage(image=image)
            image_element.transform.post_translate(xmin, ymin)
            return image_element

        def make_image():
            for op in plan:
                try:
                    if op.operation == "Raster":
                        if len(op.children) == 1 and isinstance(
                            op.children[0], SVGImage
                        ):
                            continue
                        image_element = make_image_for_op(op)
                        if image_element is None:
                            continue
                        if (
                            image_element.image_width == 1
                            and image_element.image_height == 1
                        ):
                            # TODO: Solve this is a less kludgy manner. The call to make the image can fail the first
                            #  time around because the renderer is what sets the size of the text. If the size hasn't
                            #  already been set, the initial bounds are wrong.
                            image_element = make_image_for_op(op)
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
            for c in plan:
                if isinstance(c, CutCode):
                    c.short_travel_cutcode()

        plan, original, commands, name = self.default_plan()
        commands.append(optimize_travel)

    def conditional_jobadd_optimize_cuts(self):
        plan, original, commands, name = self.default_plan()
        for op in plan:
            try:
                if op.operation in ("Cut"):
                    self.jobadd_optimize_cuts()
                    return
            except AttributeError:
                pass

    def jobadd_optimize_cuts(self):
        def optimize_cuts():
            plan, original, commands, name = self.default_plan()
            for op in plan:
                try:
                    if op.operation in ("Cut"):
                        op_cuts = self.optimize_cut_inside(op)
                        op.clear()
                        op.append(op_cuts)
                except AttributeError:
                    pass

        plan, original, commands, name = self.default_plan()
        commands.append(optimize_cuts)

    def conditional_jobadd_actualize_image(self):
        plan, original, commands, name = self.default_plan()
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
            plan, original, commands, name = self.default_plan()
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

        plan, original, commands, name = self.default_plan()
        commands.append(actualize)

    def conditional_jobadd_scale_rotary(self):
        rotary_context = self.context.get_context("rotary/1")
        if rotary_context.scale_x != 1.0 or rotary_context.scale_y != 1.0:
            self.jobadd_scale_rotary()

    def jobadd_scale_rotary(self):
        def scale_for_rotary():
            r = self.context.get_context("rotary/1")
            spooler, input_driver, output = self.context.registered["device/%s" % self.context.root.active]
            scale_str = "scale(%f,%f,%f,%f)" % (
                r.scale_x,
                r.scale_y,
                input_driver.current_x,
                input_driver.current_y,
            )
            plan, original, commands, name = self.default_plan()
            for o in plan:
                if isinstance(o, LaserOperation):
                    for e in o.children:
                        e = e.object
                        try:
                            e *= scale_str
                        except AttributeError:
                            pass
            self.conditional_jobadd_actualize_image()

        plan, original, commands, name = self.default_plan()
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
        try:
            matrix.inverse()
        except ZeroDivisionError:
            # Rare crash if matrix is malformed and cannot invert.
            matrix.reset()
            matrix.post_translate(-tx, -ty)
            matrix.post_scale(step_scale, step_scale)
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
