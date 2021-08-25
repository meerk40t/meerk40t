import os.path
from subprocess import PIPE, run
from sys import platform


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_command(
            "load",
            help=_("inkscape ... load  - load the previous conversion"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inscape_load(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            channel(_("inkscape load - loading the previous conversion..."))
            e = kernel.root
            e.load(filename)
            e.signal("refresh_scene", 0)
            return "inkscape", data

        @kernel.console_command(
            "simplify",
            help=_("inkscape simplify  - convert to plain svg"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_simplify(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            if not os.path.exists(inkscape_path):
                channel(_("Inkscape not found. Try 'inkscape locate'"))
                return
            channel(_("inkscape simplify - converting to plain svg"))
            c = run(
                [
                    inkscape_path,
                    "--export-plain-svg",
                    "--export-filename=temp.svg",
                    filename,
                ],
                stdout=PIPE,
            )
            channel(c.stdout)
            return "inkscape", (inkscape_path, "temp.svg")

        @kernel.console_command(
            "text2path",
            help=_("inkscape text2path - convert text objects to paths"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_text2path(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            if not os.path.exists(inkscape_path):
                channel(_("Inkscape not found. Try 'inkscape locate'"))
                return
            channel(_("inkscape text2path - converting text objects to paths"))
            c = run(
                [
                    inkscape_path,
                    "--export-area-drawing",
                    "--export-text-to-path",
                    "--export-plain-svg",
                    "--export-filename=temp.svg",
                    filename,
                ],
                stdout=PIPE,
            )
            channel(c.stdout)
            return "inkscape", (inkscape_path, "temp.svg")

        @kernel.console_option("dpi", "d", type=int, help=_("dpi to use"), default=1000)
        @kernel.console_option("step", "s", type=int, help=_("step to use"))
        @kernel.console_command(
            "makepng",
            help=_("inkscape makepng   - make a png of all elements"),
            input_type="inkscape",
            output_type="inkscape"
        )
        def inkscape_png(channel, _, dpi=1000, step=None, data=None, **kwargs):
            if step is not None and step > 0:
                dpi = 1000 / step
            inkscape_path, filename = data
            if not os.path.exists(inkscape_path):
                channel(_("Inkscape not found. Try 'inkscape locate'"))
                return
            channel(_("inkscape makepng - making a png of all elements"))
            c = run(
                [
                    inkscape_path,
                    "--export-background",
                    "white",
                    "--export-background-opacity",
                    "255",
                    "--export-area-drawing",
                    "--export-type=png",
                    "--export-filename=temp.png",
                    "--export-dpi=%d" % dpi,
                    filename,
                ],
                stdout=PIPE,
            )
            channel(c.stdout)
            return "inkscape", (inkscape_path, "temp.png")

        @kernel.console_argument(
            "filename", type=str, help=_("filename of svg to be simplified")
        )
        @kernel.console_command(
            "input",
            help=_("input filename fn ... - provide the filename to process"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_input_filename(channel, _, filename, data, **kwargs):
            inkscape_path, fn = data
            if filename is None:
                channel(_("inkscape filename fn - filename not specified"))
            if not os.path.exists(filename):
                channel(_("inkscape filename %s - file not found") % filename)
                return
            return "inkscape", (inkscape_path, filename)

        @kernel.console_command(
            "version",
            help=_("inkscape version   - get the inkscape version"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_version(channel, _, data, **kwargs):
            inkscape_path, filename = data
            if not os.path.exists(inkscape_path):
                channel(_("Inkscape not found. Try 'inkscape locate'"))
                return
            c = run([inkscape_path, "-V"], stdout=PIPE)
            channel('Inkscape executable at "%s" is: %s' % (inkscape_path, c.stdout.decode("utf-8")))
            return "inkscape", data

        @kernel.console_command(
            "locate",
            help=_("inkscape locate    - set the path to inkscape on your computer"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_locate(channel, _, data, **kwargs):
            if "darwin" in platform:
                inkscape = [
                    "/Applications/Inkscape.app/Contents/MacOS/Inkscape",
                    "/Applications/Inkscape.app/Contents/Resources/bin/inkscape",
                ]
            elif "win" in platform:
                inkscape = [
                    "C:/Program Files (x86)/Inkscape/inkscape.exe",
                    "C:/Program Files (x86)/Inkscape/bin/inkscape.exe",
                    "C:/Program Files/Inkscape/inkscape.exe",
                    "C:/Program Files/Inkscape/bin/inkscape.exe",
                ]
            elif "linux" in platform:
                inkscape = [
                    "/usr/local/bin/inkscape",
                    "/usr/bin/inkscape",
                ]
            else:
                channel(_("Inkscape location: Platform '%s' unknown so no idea where to look") % platform)
                return
            inkscape_path, filename = data
            channel(_("----------"))
            channel(_("Finding Inkscape"))
            match = None
            for ink in inkscape:
                if os.path.exists(ink):
                    match = ink
                    result = _("Success")
                else:
                    result = _("Fail")
                channel(_("Searching: %s -- Result: %s") % (ink, result))
            channel(_("----------"))
            root_context = kernel.root
            root_context.setting(str, "inkscape_path", "inkscape.exe")
            if match is None:
                root_context.inkscape_path = "inkscape.exe"
                channel(_("Inkscape location: Inkscape not found in default installation directories"))
                return
            root_context.inkscape_path = match
            return "inkscape", (match, filename)

        @kernel.console_command(
            "inkscape",
            help=_("invoke inkscape to convert elements"),
            output_type="inkscape",
        )
        def inkscape_base(**kwargs):
            root_context = kernel.root
            root_context.setting(str, "inkscape_path", "inkscape.exe")
            return "inkscape", (root_context.inkscape_path, None)
