from ..kernel import CommandMatchRejected, Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/BindAlias", BindAlias)
    elif lifecycle == "boot":
        kernel_root = kernel.root
        kernel_root.activate("modifier/BindAlias")


class BindAlias(Modifier):
    """
    Functionality to add BindAlias commands.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        # Keymap/alias values
        self.keymap = {}
        self.alias = {}

    def attach(self, *a, **kwargs):
        _ = self.context._
        self.context.keymap = self.keymap
        self.context.alias = self.alias
        self.context.default_keymap = self.default_keymap
        self.context.default_alias = self.default_alias

        @self.context.console_command("bind", help=_("bind <key> <console command>"))
        def bind(command, channel, _, args=tuple(), **kwgs):
            """
            Binds a key to a given keyboard keystroke.
            """
            context = self.context
            _ = self.context._
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Binds:"))
                for i, key in enumerate(context.keymap):
                    value = context.keymap[key]
                    channel(_("%d: key %s %s") % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    context.keymap = dict()
                    context.default_keymap()
                    channel(_("Set default keymap."))
                    return
                command_line = " ".join(args[1:])
                f = command_line.find("bind")
                if f == -1:  # If bind value has a bind, do not evaluate.
                    spooler, input_driver, output = context.registered[
                        "device/%s" % context.root.active
                    ]
                    if "$x" in command_line:
                        try:
                            x = input_driver.current_x
                        except AttributeError:
                            x = 0
                        command_line = command_line.replace("$x", str(x))
                    if "$y" in command_line:
                        try:
                            y = input_driver.current_y
                        except AttributeError:
                            y = 0
                        command_line = command_line.replace("$y", str(y))
                if len(command_line) != 0:
                    context.keymap[key] = command_line
                else:
                    try:
                        del context.keymap[key]
                        channel(_("Unbound %s") % key)
                    except KeyError:
                        pass
            return

        @self.context.console_command(
            "alias", help=_("alias <alias> <console commands[;console command]*>")
        )
        def alias(command, channel, _, args=tuple(), **kwgs):
            context = self.context
            _ = self.context._
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Aliases:"))
                for i, key in enumerate(context.alias):
                    value = context.alias[key]
                    channel("%d: %s %s" % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    context.alias = dict()
                    context.default_alias()
                    channel(_("Set default aliases."))
                    return
                context.alias[args[0]] = " ".join(args[1:])
            return

        @self.context.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks values for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            context = self.context
            if command in self.alias:
                aliased_command = self.alias[command]
                for cmd in aliased_command.split(";"):
                    context("%s\n" % cmd)
            else:
                raise CommandMatchRejected(_("This is not an alias."))

    def boot(self, *args, **kwargs):
        self.boot_keymap()
        self.boot_alias()

    def detach(self, *args, **kwargs):
        self.save_keymap_alias()

    def save_keymap_alias(self):
        keys = self.context.derive("keymap")
        alias = self.context.derive("alias")

        keys.clear_persistent()
        alias.clear_persistent()

        for key in self.keymap:
            if key is None or len(key) == 0:
                continue
            keys.write_persistent(key, self.keymap[key])

        for key in self.alias:
            if key is None or len(key) == 0:
                continue
            alias.write_persistent(key, self.alias[key])

    def boot_keymap(self):
        self.keymap.clear()
        prefs = self.context.derive("keymap")
        prefs.kernel.load_persistent_string_dict(prefs.path, self.keymap, suffix=True)
        if not len(self.keymap):
            self.default_keymap()

    def boot_alias(self):
        self.alias.clear()
        prefs = self.context.derive("alias")
        prefs.kernel.load_persistent_string_dict(prefs.path, self.alias, suffix=True)
        if not len(self.alias):
            self.default_alias()

    def default_keymap(self):
        self.keymap["escape"] = "pause"
        self.keymap["pause"] = "pause"
        self.keymap["d"] = "+right"
        self.keymap["a"] = "+left"
        self.keymap["w"] = "+up"
        self.keymap["s"] = "+down"
        self.keymap["l"] = "lock"
        self.keymap["u"] = "unlock"
        self.keymap["numpad_down"] = "+translate_down"
        self.keymap["numpad_up"] = "+translate_up"
        self.keymap["numpad_left"] = "+translate_left"
        self.keymap["numpad_right"] = "+translate_right"
        self.keymap["numpad_multiply"] = "+scale_up"
        self.keymap["numpad_divide"] = "+scale_down"
        self.keymap["numpad_add"] = "+rotate_cw"
        self.keymap["numpad_subtract"] = "+rotate_ccw"
        self.keymap["control+a"] = "element* select"
        self.keymap["control+c"] = "clipboard copy"
        self.keymap["control+v"] = "clipboard paste"
        self.keymap["control+x"] = "clipboard cut"
        self.keymap["control+i"] = "element* select^"
        self.keymap["control+f"] = "control Fill"
        self.keymap["control+s"] = "control Stroke"
        self.keymap["control+r"] = "rect 0 0 1000 1000"
        self.keymap["control+e"] = "circle 500 500 500"
        self.keymap["control+d"] = "element copy"
        self.keymap["control+o"] = "outline"
        self.keymap["control+shift+o"] = "outline 1mm"
        self.keymap["control+alt+o"] = "outline -1mm"
        self.keymap["control+shift+h"] = "scale -1 1"
        self.keymap["control+shift+v"] = "scale 1 -1"
        self.keymap["control+1"] = "bind 1 move $x $y"
        self.keymap["control+2"] = "bind 2 move $x $y"
        self.keymap["control+3"] = "bind 3 move $x $y"
        self.keymap["control+4"] = "bind 4 move $x $y"
        self.keymap["control+5"] = "bind 5 move $x $y"
        self.keymap["alt+r"] = "raster"
        self.keymap["alt+e"] = "engrave"
        self.keymap["alt+c"] = "cut"
        self.keymap["delete"] = "tree selected delete"
        self.keymap["control+f3"] = "rotaryview"
        self.keymap["alt+f3"] = "rotaryscale"
        self.keymap["f4"] = "window open CameraInterface"
        self.keymap["f5"] = "refresh"
        self.keymap["f6"] = "window open JobSpooler"
        self.keymap["f7"] = "window open -o Controller"
        self.keymap["f8"] = "control Path"
        self.keymap["f9"] = "control Transform"
        self.keymap["control+f9"] = "control Flip"
        self.keymap["f12"] = "window open Console"
        self.keymap["control+alt+g"] = "image wizard Gold"
        self.keymap["control+alt+x"] = "image wizard Xin"
        self.keymap["control+alt+s"] = "image wizard Stipo"
        self.keymap["home"] = "home"
        self.keymap["control+z"] = "reset"
        self.keymap["control+alt+shift+escape"] = "reset_bind_alias"

    def default_alias(self):
        self.alias["+scale_up"] = "loop scale 1.02"
        self.alias["+scale_down"] = "loop scale 0.98"
        self.alias["+rotate_cw"] = "loop rotate 2"
        self.alias["+rotate_ccw"] = "loop rotate -2"
        self.alias["+translate_right"] = "loop translate 1mm 0"
        self.alias["+translate_left"] = "loop translate -1mm 0"
        self.alias["+translate_down"] = "loop translate 0 1mm"
        self.alias["+translate_up"] = "loop translate 0 -1mm"
        self.alias["+right"] = "loop right 1mm"
        self.alias["+left"] = "loop left 1mm"
        self.alias["+up"] = "loop up 1mm"
        self.alias["+down"] = "loop down 1mm"
        self.alias["-scale_up"] = "end scale 1.02"
        self.alias["-scale_down"] = "end scale 0.98"
        self.alias["-rotate_cw"] = "end rotate 2"
        self.alias["-rotate_ccw"] = "end rotate -2"
        self.alias["-translate_right"] = "end translate 1mm 0"
        self.alias["-translate_left"] = "end translate -1mm 0"
        self.alias["-translate_down"] = "end translate 0 1mm"
        self.alias["-translate_up"] = "end translate 0 -1mm"
        self.alias["-right"] = "end right 1mm"
        self.alias["-left"] = "end left 1mm"
        self.alias["-up"] = "end up 1mm"
        self.alias["-down"] = "end down 1mm"
        self.alias["reset_bind_alias"] = "bind default;alias default"
