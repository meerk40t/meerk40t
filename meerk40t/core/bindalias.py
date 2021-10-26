from ..kernel import CommandMatchRejected, Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_modifier(Bind)
        kernel.add_modifier(Alias)


class Bind(Modifier):
    """
    Functionality to add Bind commands.
    """

    def __init__(self, kernel, *args, **kwargs):
        Modifier.__init__(self, kernel, "bind")
        # Keymap/alias values
        self.map = {}
        _ = self._

        @kernel.console_command("bind", help=_("bind <key> <console command>"))
        def bind(command, channel, _, args=tuple(), **kwgs):
            """
            Binds a key to a given keyboard keystroke.
            """
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Binds:"))
                for i, key in enumerate(self.map):
                    value = self.map[key]
                    channel(_("%d: key %s %s") % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    self.map = dict()
                    self.default_keymap()
                    channel(_("Set default keymap."))
                    return
                command_line = " ".join(args[1:])
                f = command_line.find("bind")
                if f == -1:  # If bind value has a bind, do not evaluate.
                    spooler, input_driver, output = self.registered[
                        "device/%s" % self.active
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
                    self.map[key] = command_line
                else:
                    try:
                        del self.map[key]
                        channel(_("Unbound %s") % key)
                    except KeyError:
                        pass
            return

        self.map.clear()
        kernel.load_persistent_string_dict(self.path, self.map, suffix=True)
        if not len(self.map):
            self.default_keymap()

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()

        for key in self.map:
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, self.map[key])

    def default_keymap(self):
        self.map["escape"] = "pause"
        self.map["pause"] = "pause"
        self.map["d"] = "+right"
        self.map["a"] = "+left"
        self.map["w"] = "+up"
        self.map["s"] = "+down"
        self.map["l"] = "lock"
        self.map["u"] = "unlock"
        self.map["numpad_down"] = "+translate_down"
        self.map["numpad_up"] = "+translate_up"
        self.map["numpad_left"] = "+translate_left"
        self.map["numpad_right"] = "+translate_right"
        self.map["numpad_multiply"] = "+scale_up"
        self.map["numpad_divide"] = "+scale_down"
        self.map["numpad_add"] = "+rotate_cw"
        self.map["numpad_subtract"] = "+rotate_ccw"
        self.map["control+a"] = "element* select"
        self.map["control+c"] = "clipboard copy"
        self.map["control+v"] = "clipboard paste"
        self.map["control+x"] = "clipboard cut"
        self.map["control+i"] = "element* select^"
        self.map["control+f"] = "control Fill"
        self.map["control+s"] = "control Stroke"
        self.map["control+r"] = "rect 0 0 1000 1000"
        self.map["control+e"] = "circle 500 500 500"
        self.map["control+d"] = "element copy"
        self.map["control+o"] = "outline"
        self.map["control+shift+o"] = "outline 1mm"
        self.map["control+alt+o"] = "outline -1mm"
        self.map["control+shift+h"] = "scale -1 1"
        self.map["control+shift+v"] = "scale 1 -1"
        self.map["control+1"] = "bind 1 move $x $y"
        self.map["control+2"] = "bind 2 move $x $y"
        self.map["control+3"] = "bind 3 move $x $y"
        self.map["control+4"] = "bind 4 move $x $y"
        self.map["control+5"] = "bind 5 move $x $y"
        self.map["alt+r"] = "raster"
        self.map["alt+e"] = "engrave"
        self.map["alt+c"] = "cut"
        self.map["delete"] = "tree selected delete"
        self.map["control+f3"] = "rotaryview"
        self.map["alt+f3"] = "rotaryscale"
        self.map["f4"] = "window open CameraInterface"
        self.map["f5"] = "refresh"
        self.map["f6"] = "window open JobSpooler"
        self.map["f7"] = "window open -o Controller"
        self.map["f8"] = "control Path"
        self.map["f9"] = "control Transform"
        self.map["control+f9"] = "control Flip"
        self.map["f12"] = "window open Console"
        self.map["control+alt+g"] = "image wizard Gold"
        self.map["control+alt+x"] = "image wizard Xin"
        self.map["control+alt+s"] = "image wizard Stipo"
        self.map["home"] = "home"
        self.map["control+z"] = "reset"
        self.map["control+alt+shift+escape"] = "reset_bind_alias"


class Alias(Modifier):
    """
    Functionality to add Alias commands.
    """

    def __init__(self, kernel, *args, **kwargs):
        Modifier.__init__(self, kernel, "alias")
        # Keymap/alias values
        self.map = {}
        _ = self._

        @kernel.console_command(
            "alias", help=_("alias <alias> <console commands[;console command]*>")
        )
        def alias(command, channel, _, args=tuple(), **kwgs):
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Aliases:"))
                for i, key in enumerate(self.map):
                    value = self.map[key]
                    channel("%d: %s %s" % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    self.map = dict()
                    self.default_alias()
                    channel(_("Set default aliases."))
                    return
                value = " ".join(args[1:])
                if value == "":
                    del self.map[args[0]]
                else:
                    self.map[args[0]] = value

        @kernel.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks values for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            if command in self.map:
                aliased_command = self.map[command]
                for cmd in aliased_command.split(";"):
                    self("%s\n" % cmd)
            else:
                raise CommandMatchRejected(_("This is not an alias."))

        self.map.clear()
        kernel.load_persistent_string_dict(self.path, self.map, suffix=True)
        if not len(self.map):
            self.default_alias()

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()

        for key in self.map:
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, self.map[key])

    def default_alias(self):
        self.map["+scale_up"] = "loop scale 1.02"
        self.map["+scale_down"] = "loop scale 0.98"
        self.map["+rotate_cw"] = "loop rotate 2"
        self.map["+rotate_ccw"] = "loop rotate -2"
        self.map["+translate_right"] = "loop translate 1mm 0"
        self.map["+translate_left"] = "loop translate -1mm 0"
        self.map["+translate_down"] = "loop translate 0 1mm"
        self.map["+translate_up"] = "loop translate 0 -1mm"
        self.map["+right"] = "loop right 1mm"
        self.map["+left"] = "loop left 1mm"
        self.map["+up"] = "loop up 1mm"
        self.map["+down"] = "loop down 1mm"
        self.map["-scale_up"] = "end scale 1.02"
        self.map["-scale_down"] = "end scale 0.98"
        self.map["-rotate_cw"] = "end rotate 2"
        self.map["-rotate_ccw"] = "end rotate -2"
        self.map["-translate_right"] = "end translate 1mm 0"
        self.map["-translate_left"] = "end translate -1mm 0"
        self.map["-translate_down"] = "end translate 0 1mm"
        self.map["-translate_up"] = "end translate 0 -1mm"
        self.map["-right"] = "end right 1mm"
        self.map["-left"] = "end left 1mm"
        self.map["-up"] = "end up 1mm"
        self.map["-down"] = "end down 1mm"
        self.map["reset_bind_alias"] = "bind default;alias default"
