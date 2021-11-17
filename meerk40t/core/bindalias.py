from ..kernel import CommandMatchRejected, Service


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("bind", Bind(kernel))
        kernel.add_service("alias", Alias(kernel))


class Bind(Service):
    """
    Bind service, establishes keymap
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "keymap")
        self.keymap = {}
        self.triggered = dict()

        _ = self._

        @self.console_command("bind", help=_("bind <key> <console command>"))
        def bind(command, channel, _, args=tuple(), **kwgs):
            """
            Binds a key to a given keyboard keystroke.
            """
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Binds:"))
                for i, key in enumerate(self.keymap):
                    value = self.keymap[key]
                    channel(_("%d: key %s %s") % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    self.keymap = dict()
                    self.default_keymap()
                    channel(_("Set default keymap."))
                    return
                command_line = " ".join(args[1:])
                f = command_line.find("bind")
                if f == -1:  # If bind value has a bind, do not evaluate.
                    if "$x" in command_line:
                        try:
                            x = self.device.current_x
                        except AttributeError:
                            x = 0
                        command_line = command_line.replace("$x", str(x))
                    if "$y" in command_line:
                        try:
                            y = self.device.current_y
                        except AttributeError:
                            y = 0
                        command_line = command_line.replace("$y", str(y))
                if len(command_line) != 0:
                    self.keymap[key] = command_line
                else:
                    try:
                        del self.keymap[key]
                        channel(_("Unbound %s") % key)
                    except KeyError:
                        pass
            return

        self.kernel.load_persistent_string_dict(self.path, self.keymap, suffix=True)
        if not len(self.keymap):
            self.default_keymap()

    def trigger(self, keyvalue):
        if keyvalue in self.keymap:
            if keyvalue not in self.triggered:
                self.triggered[keyvalue] = 1
                action = self.keymap[keyvalue]
                self(action + "\n")
                return True
        else:
            return False

    def untrigger(self, keyvalue):
        keymap = self.keymap
        if keyvalue in keymap:
            if keyvalue in self.triggered:
                del self.triggered[keyvalue]
            action = keymap[keyvalue]
            if action.startswith("+"):
                # Keyup commands only trigger if the down command started with +
                action = "-" + action[1:]
                self(action + "\n")
                return True
        else:
            return False

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()

        for key in self.keymap:
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, self.keymap[key])

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
        self.keymap["alt+f"] = "dialog_fill"
        self.keymap["alt+p"] = "dialog_flip"
        self.keymap["alt+s"] = "dialog_stroke"
        self.keymap["alt+h"] = "dialog_path"
        self.keymap["alt+t"] = "dialog_transform"
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
        self.keymap["f5"] = "refresh"
        self.keymap["control+alt+g"] = "image wizard Gold"
        self.keymap["control+alt+x"] = "image wizard Xin"
        self.keymap["control+alt+s"] = "image wizard Stipo"
        self.keymap["home"] = "home"
        self.keymap["control+z"] = "reset"
        self.keymap["control+alt+shift+escape"] = "reset_bind_alias"


class Alias(Service):
    """
    Alias service, establishes command aliases
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "alias")
        self.aliases = {}
        _ = self._

        @self.console_argument("alias", type=str, help=_("alias command"))
        @self.console_command(
            "alias", help=_("alias <alias> <console commands[;console command]*>")
        )
        def alias(command, channel, _, alias=None, remainder=None, **kwgs):
            if alias is None:
                channel(_("----------"))
                channel(_("Aliases:"))
                for i, key in enumerate(self.aliases):
                    value = self.aliases[key]
                    channel("%d: %s %s" % (i, key.ljust(15), value))
                channel(_("----------"))
                return
            alias = alias.lower()
            if alias == "default":
                self.aliases = dict()
                self.default_alias()
                channel(_("Set default aliases."))
                return
            if remainder is None:
                if alias in self.aliases:
                    channel(_("Alias %s unset.") % alias)
                    del self.aliases[alias]
                else:
                    channel(_("No alias for %s was set.") % alias)
            else:
                self.aliases[alias] = remainder

        @self.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks values for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            if command in self.aliases:
                aliased_command = self.aliases[command]
                for cmd in aliased_command.split(";"):
                    self("%s\n" % cmd)
            else:
                raise CommandMatchRejected(_("This is not an alias."))

        self.aliases.clear()
        self.kernel.load_persistent_string_dict(self.path, self.aliases, suffix=True)
        if not len(self.aliases):
            self.default_alias()

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()
        for key in self.aliases:
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, self.aliases[key])

    def default_alias(self):
        self.aliases["+scale_up"] = "loop scale 1.02"
        self.aliases["+scale_down"] = "loop scale 0.98"
        self.aliases["+rotate_cw"] = "loop rotate 2"
        self.aliases["+rotate_ccw"] = "loop rotate -2"
        self.aliases["+translate_right"] = "loop translate 1mm 0"
        self.aliases["+translate_left"] = "loop translate -1mm 0"
        self.aliases["+translate_down"] = "loop translate 0 1mm"
        self.aliases["+translate_up"] = "loop translate 0 -1mm"
        self.aliases["+right"] = "loop right 1mm"
        self.aliases["+left"] = "loop left 1mm"
        self.aliases["+up"] = "loop up 1mm"
        self.aliases["+down"] = "loop down 1mm"
        self.aliases["-scale_up"] = "end scale 1.02"
        self.aliases["-scale_down"] = "end scale 0.98"
        self.aliases["-rotate_cw"] = "end rotate 2"
        self.aliases["-rotate_ccw"] = "end rotate -2"
        self.aliases["-translate_right"] = "end translate 1mm 0"
        self.aliases["-translate_left"] = "end translate -1mm 0"
        self.aliases["-translate_down"] = "end translate 0 1mm"
        self.aliases["-translate_up"] = "end translate 0 -1mm"
        self.aliases["-right"] = "end right 1mm"
        self.aliases["-left"] = "end left 1mm"
        self.aliases["-up"] = "end up 1mm"
        self.aliases["-down"] = "end down 1mm"
        self.aliases["reset_bind_alias"] = "bind default;alias default"
