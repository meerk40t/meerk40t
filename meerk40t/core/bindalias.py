from ..kernel import CommandMatchRejected, Modifier

# The following dicts consist of a tuple of values, the first of
# which is the current default, with any prior defaults following.
# Prior defaults are used to keep a users keymap / aliases up to date with
# any changes, unless the user has already changed away from the default.
# If you want to delete a bind / alias, set the first value to a null string.

# CHOICE OF BINDALIAS vs. MENU
# These key bindings are in addition to those specified in the menus
# (like Ctrl+S for File Save). The choice of which of these to use is debatable.
# On one hand bindalias is a more flexible approach because the user can
# change keys mappings to whatever they wish whilst menus are fixed.
# On the other hand, default menu keys can be set per language because the
# menu strings are translated, whereas bindalias keys are not.

# RESERVED KEYS
# Regardless of the platform used by individual developers, bindalias needs
# to conform to BOTH of the following:
#
# 1. Mac - common shortcuts defined in https://support.apple.com/en-us/HT201236
#    should be followed where appropriate and avoided if not. This is important
#    for MK to be accepted into the Apple app store.
#    Where keys defined in other sections on this page make sense for this application,
#    these should also be used by preference.
#
# 2. Windows - alt-single letter should be avoided as these correspond to menu
#    shortcuts (e.g. in english locale, alt-f should activate the file menu).
#    Common Windows shortcuts can be found at
#    https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec
#
# In addition where they do not conflict with the above, any synergy with keys commonly used
# in popular SVG / image editors (e.g. paint.net, inkscape) may be beneficial.

DEFAULT_KEYMAP = {
    "a": ("+left",),
    "d": ("+right",),
    "w": ("+up",),
    "s": ("+down",),
    "l": ("lock",),
    "u": ("unlock",),
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
    "f12": (
        "",
        "window open Console",
        "window open Terminal",
    ),
    "delete": (
        "tree selected delete",
        "element delete",
    ),
    "escape": ("", "pause",),
    "home": ("home",),
    "numpad_down": ("+translate_down",),
    "numpad_up": ("+translate_up",),
    "numpad_left": ("+translate_left",),
    "numpad_right": ("+translate_right",),
    "numpad_multiply": ("+scale_up",),
    "numpad_divide": ("+scale_down",),
    "numpad_add": ("+rotate_cw",),
    "numpad_subtract": ("+rotate_ccw",),
    "pause": ("pause",),
    "alt+c": ("", "cut",),
    "alt+e": ("", "engrave",),
    "alt+f": ("", "dialog_fill",),
    "alt+h": ("", "dialog_path",),
    "alt+p": ("", "dialog_flip",),
    "alt+r": ("", "raster",),
    "alt+s": ("", "dialog_stroke",),
    "alt+t": ("", "dialog_transform",),
    "alt+f3": (
        "",
        "rotaryscale",
    ),
    "ctrl+a": ("element* select",),
    "ctrl+c": ("clipboard copy",),
    "ctrl+e": ("circle 500 500 500",),
    "ctrl+f": (
        "",
        "dialog_fill",
        "control Fill",
    ),
    "ctrl+i": ("element* select^",),
    "ctrl+d": ("element copy",),
    "ctrl+g": ("planz clear copy preprocess validate blob preopt optimize spool0",),
    "ctrl+o": (
        "",
        "outline",
    ),
    "ctrl+r": ("rect 0 0 1000 1000",),
    "ctrl+s": (
        "",
        "dialog_stroke",
        "control Stroke",
    ),
    "ctrl+v": ("clipboard paste",),
    "ctrl+x": ("clipboard cut",),
    "ctrl+z": ("reset",),
    "ctrl+1": ("bind 1 move $x $y",),
    "ctrl+2": ("bind 2 move $x $y",),
    "ctrl+3": ("bind 3 move $x $y",),
    "ctrl+4": ("bind 4 move $x $y",),
    "ctrl+5": ("bind 5 move $x $y",),
    "ctrl+f3": (
        "",
        "rotaryview",
    ),
    "ctrl+f9": (
        "",
        "dialog_flip",
        "control Flip",
    ),
    "ctrl+alt+d": ("image wizard Gold",),
    "ctrl+alt+e": ("image wizard Simple",),
    "ctrl+alt+g": (
        "",
        "image wizard Gold",
    ),
    "ctrl+alt+n": ("image wizard Newsy",),
    "ctrl+alt+o": (
        "image wizard Stipo",
        "outline -1mm",
    ),
    "ctrl+alt+s": (
        "",
        "image wizard Stipo",
    ),
    "ctrl+alt+x": ("image wizard Xin",),
    "ctrl+alt+y": ("image wizard Gravy",),
    "ctrl+shift+h": ("scale -1 1",),
    "ctrl+shift+o": ("outline 1mm",),
    "ctrl+shift+v": ("scale 1 -1",),
    "ctrl+alt+shift+escape": ("reset_bind_alias",),
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
                channel(_("Binds:"))
                def keymap_index(key):
                    mods, key = key.rsplit("+", 1) if "+" in key else ("", key)
                    return (
                        mods,
                        len(key) if len(key) <= 2 else 3,
                        key,
                    )
                channel(_("    Key                    Command"))
                for i, key in enumerate(sorted(context.keymap.keys(), key=keymap_index)):
                    value = context.keymap[key]
                    channel("%2d: %s %s" % (i, key.ljust(22), value))
                channel("----------")
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
                reverse_keymap = {v: k for k, v in context.keymap.items()}
                channel(_("Aliases (keybind)`:"))
                channel(_("    Alias                Command(s)"))
                for i, key in enumerate(sorted(
                    context.alias.keys(),
                    key=lambda x: x if x[0] not in "+-" else x[1:] + x[0]
                )):
                    value = context.alias[key]
                    keystroke = reverse_keymap[key] if key in reverse_keymap else ""
                    if keystroke and len(key) + len(keystroke) < 18:
                        key += " (%s)" % keystroke
                        keystroke = ""
                    channel("%2d: %s %s" % (i, key.ljust(22), value))
                    if keystroke:
                        channel("    (%s)" % keystroke)
                channel("----------")
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
        # Remap "control+" to "ctrl+"
        for key in list(context.keymap.keys()):
            if key.startswith("control+"):
                newkey = "ctrl+" + key[8:]
                context.keymap[newkey] = context.keymap[key]
                del context.keymap[key]
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
