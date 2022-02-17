from ..kernel import CommandMatchRejected, Modifier

# The following dicts consist of a tuple of values, the first of
# which is the current default, with any prior defaults following.
# Prior defaults are used to keep a users keymap / aliases up to date with
# any changes, unless the user has already changed away from the default.
# If you want to delete a bind / alias, set the first value to a null string.

DEFAULT_KEYMAP = {
    "escape": ("pause",),
    "pause": ("pause",),
    "d": ("+right",),
    "a": ("+left",),
    "w": ("+up",),
    "s": ("+down",),
    "l": ("lock",),
    "u": ("unlock",),
    "numpad_down": ("+translate_down",),
    "numpad_up": ("+translate_up",),
    "numpad_left": ("+translate_left",),
    "numpad_right": ("+translate_right",),
    "numpad_multiply": ("+scale_up",),
    "numpad_divide": ("+scale_down",),
    "numpad_add": ("+rotate_cw",),
    "numpad_subtract": ("+rotate_ccw",),
    "control+a": ("element* select",),
    "control+c": ("clipboard copy",),
    "control+v": ("clipboard paste",),
    "control+x": ("clipboard cut",),
    "control+i": ("element* select^",),
    "control+f": (
        "",
        "dialog_fill",
        "control Fill",
    ),
    "control+s": (
        "",
        "dialog_stroke",
        "control Stroke",
    ),
    "alt+f": ("dialog_fill",),
    "alt+p": ("dialog_flip",),
    "alt+s": ("dialog_stroke",),
    "alt+h": ("dialog_path",),
    "alt+t": ("dialog_transform",),
    "control+r": ("rect 0 0 1000 1000",),
    "control+e": ("circle 500 500 500",),
    "control+d": ("element copy",),
    "control+o": ("outline",),
    "control+shift+o": ("outline 1mm",),
    "control+alt+o": ("outline -1mm",),
    "control+shift+h": ("scale -1 1",),
    "control+shift+v": ("scale 1 -1",),
    "control+1": ("bind 1 move $x $y",),
    "control+2": ("bind 2 move $x $y",),
    "control+3": ("bind 3 move $x $y",),
    "control+4": ("bind 4 move $x $y",),
    "control+5": ("bind 5 move $x $y",),
    "alt+r": ("raster",),
    "alt+e": ("engrave",),
    "alt+c": ("cut",),
    "delete": (
        "tree selected delete",
        "element delete",
    ),
    "control+f3": (
        "",
        "rotaryview",
    ),
    "alt+f3": (
        "",
        "rotaryscale",
    ),
    "f4": (
        "",
        "window open CameraInterface",
    ),
    "f5": ("refresh",),
    "f6": (
        "",
        "window open JobSpooler",
    ),
    "f7": (
        "",
        "window open -o Controller",
        "window controller",
        "window open Controller",
    ),
    "f8": ("", "dialog_path", "control Path"),
    "f9": (
        "",
        "dialog_transform",
        "control Transform",
    ),
    "control+f9": (
        "",
        "dialog_flip",
        "control Flip",
    ),
    "f12": (
        "",
        "window open Console",
        "window open Terminal",
    ),
    "control+alt+g": ("image wizard Gold",),
    "control+alt+x": ("image wizard Xin",),
    "control+alt+s": ("image wizard Stipo",),
    "home": ("home",),
    "control+z": ("reset",),
    "control+alt+shift+escape": ("reset_bind_alias",),
}
DEFAULT_ALIAS = {
    "+scale_up": ("loop scale 1.02",),
    "+scale_down": ("loop scale 0.98",),
    "+rotate_cw": ("loop rotate 2",),
    "+rotate_ccw": ("loop rotate -2",),
    "+translate_right": ("loop translate 1mm 0",),
    "+translate_left": ("loop translate -1mm 0",),
    "+translate_down": ("loop translate 0 1mm",),
    "+translate_up": ("loop translate 0 -1mm",),
    "+right": ("loop right 1mm",),
    "+left": ("loop left 1mm",),
    "+up": ("loop up 1mm",),
    "+down": ("loop down 1mm",),
    "-scale_up": ("end scale 1.02",),
    "-scale_down": ("end scale 0.98",),
    "-rotate_cw": ("end rotate 2",),
    "-rotate_ccw": ("end rotate -2",),
    "-translate_right": ("end translate 1mm 0",),
    "-translate_left": ("end translate -1mm 0",),
    "-translate_down": ("end translate 0 1mm",),
    "-translate_up": ("end translate 0 -1mm",),
    "-right": ("end right 1mm",),
    "-left": ("end left 1mm",),
    "-up": ("end up 1mm",),
    "-down": ("end down 1mm",),
    "terminal_ruida": (
        "",
        "window open Terminal;ruidaserver",
    ),
    "terminal_watch": (
        "",
        "window open Terminal;channel save usb;channel save send;channel save recv",
    ),
    "reset_bind_alias": ("bind default;alias default",),
}


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
        self.context.keymap = {}
        self.context.alias = {}
        self.context.default_keymap = self.default_keymap
        self.context.default_alias = self.default_alias

    def attach(self, *a, **kwargs):
        _ = self.context._

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
                    self.default_keymap()
                    channel(_("Keymap set to default."))
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

        @self.context.console_argument("alias", type=str, help=_("alias command"))
        @self.context.console_command(
            "alias", help=_("alias <alias> <console commands[;console command]*>")
        )
        def alias(command, channel, _, alias=None, remainder=None, **kwgs):
            context = self.context
            _ = self.context._
            if alias is None:
                channel(_("----------"))
                channel(_("Aliases:"))
                for i, key in enumerate(context.alias):
                    value = context.alias[key]
                    channel("%d: %s %s" % (i, key.ljust(15), value))
                channel(_("----------"))
                return
            alias = alias.lower()
            if alias == "default":
                self.default_alias()
                channel(_("Aliases set to default."))
                return
            if remainder is None:
                if alias in context.alias:
                    channel(_("Alias %s unset.") % alias)
                    del context.alias[alias]
                else:
                    channel(_("No alias for %s was set.") % alias)
            else:
                context.alias[alias] = remainder

        @self.context.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks values for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            context = self.context
            if command in context.alias:
                aliased_command = context.alias[command]
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

        for key, value in self.context.keymap.items():
            if key is None or len(key) == 0:
                continue
            keys.write_persistent(key, value)

        for key, value in self.context.alias.items():
            if key is None or len(key) == 0:
                continue
            alias.write_persistent(key, value)

    def boot_keymap(self):
        context = self.context
        context.keymap.clear()
        prefs = context.derive("keymap")
        prefs.kernel.load_persistent_string_dict(
            prefs.path, context.keymap, suffix=True
        )
        if not len(context.keymap):
            self.default_keymap()
            return
        for key, values in DEFAULT_KEYMAP.items():
            if not key in context.keymap or context.keymap[key] in values[1:]:
                value = values[0]
                if value:
                    context.keymap[key] = value
                elif key in context.keymap:
                    del context.keymap[key]

    def boot_alias(self):
        context = self.context
        context.alias.clear()
        prefs = context.derive("alias")
        prefs.kernel.load_persistent_string_dict(prefs.path, context.alias, suffix=True)
        if not len(context.alias):
            self.default_alias()
            return
        for key, values in DEFAULT_ALIAS.items():
            if not key in context.alias or context.alias[key] in values[1:]:
                value = values[0]
                if value:
                    context.alias[key] = value
                elif key in context.alias:
                    del context.alias[key]

    def default_keymap(self):
        self.context.keymap.clear()
        for key, values in DEFAULT_KEYMAP.items():
            value = values[0]
            if value:
                self.context.keymap[key] = value

    def default_alias(self):
        self.context.alias.clear()
        for key, values in DEFAULT_ALIAS.items():
            value = values[0]
            if value:
                self.context.alias[key] = value
