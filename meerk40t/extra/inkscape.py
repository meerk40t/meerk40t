import os.path
from sys import platform
from subprocess import run, PIPE


def plugin(kernel, lifecycle):
    if lifecycle == "register":

        @kernel.console_command(
            "load",
            help="load processed file",
            input_type="inkscape",
            output_type="inkscape",
        )
        def load(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            channel(_("Loading..."))
            e = kernel.get_context('/')
            e.load(filename)
            e.signal("refresh_scene", 0)
            return "inkscape", data

        @kernel.console_command(
            "simplify",
            help="simplify path",
            input_type="inkscape",
            output_type="inkscape",
        )
        def simplify(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            channel(_("Making plain_svg with Inkscape."))
            c = run(
                [inkscape_path,
                 "--export-plain-svg",
                 "--export-filename=temp.svg",
                 filename], stdout=PIPE
            )
            channel(c.stdout)
            return "inkscape", (inkscape_path, "temp.svg")

        @kernel.console_command(
            "text2path",
            help="text to path",
            input_type="inkscape",
            output_type="inkscape",
        )
        def text2path(channel, _, data=None, **kwargs):
            inkscape_path, filename = data
            channel(_("Making plain_svg with Inkscape."))
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

        @kernel.console_option("dpi", "d", type=int, help="dpi to use", default=1000)
        @kernel.console_option("step", "s", type=int, help="step to use")
        @kernel.console_command(
            "makepng", help="make png", input_type="inkscape", output_type="inkscape"
        )
        def png(channel, _, dpi=1000, step=None, data=None, **kwargs):
            if step is not None and step > 0:
                dpi = 1000 / step
            inkscape_path, filename = data
            channel(_("Making PNG with Inkscape."))
            c = run(
                [
                    inkscape_path,
                    "--export-background", "white",
                    "--export-background-opacity", "255",
                    "--export-area-drawing",
                    "--export-type=png",
                    "--export-filename=temp.png",
                    "--export-dpi=%d" % dpi,
                    filename,
                ],
                stdout=PIPE,
            )
            channel(c.stdout)
            return "inkscape",  (inkscape_path, "temp.png")

        @kernel.console_argument(
            "filename", type=str, help="filename of svg to be simplified"
        )
        @kernel.console_command(
            "input",
            help="input filename",
            input_type="inkscape",
            output_type="inkscape",
        )
        def input(channel, _, filename, data, **kwargs):
            inkscape_path, fn = data
            if filename is None:
                channel(_("filename not specified"))
            if not os.path.exists(filename):
                channel(_("file is not found."))
                return
            return "inkscape", (inkscape_path, filename)

        @kernel.console_command(
            "version",
            help="determine inkscape version",
            input_type="inkscape",
            output_type="inkscape",
        )
        def version(channel, _, data, **kwargs):
            inkscape_path, filename = data
            if not os.path.exists(inkscape_path):
                channel(_("Inkscape not found."))
                return
            c = run([inkscape_path, "-V"], stdout=PIPE)
            channel(c.stdout)
            return "inkscape", data

        @kernel.console_command(
            "locate",
            help="find inkscape",
            input_type="inkscape",
            output_type="inkscape",
        )
        def locate(channel, _, data, **kwargs):
            if "darwin" in platform:
                inkscape = [
                    "/Applications/Inkscape.app/Contents/MacOS/Inkscape",
                    "/Applications/Inkscape.app/Contents/Resources/bin/inkscape"
                ]
            elif "win" in platform:
                inkscape = [
                    "C:/Program Files/Inkscape/inkscape.exe",
                    "C:/Program Files (x86)/Inkscape/inkscape.exe",
                    "C:/Program Files/Inkscape/bin/inkscape.exe",
                    "C:/Program Files (x86)/Inkscape/bin/inkscape.exe",
                ]
            elif "linux" in platform:
                inkscape = [
                    "/usr/local/bin/inkscape",
                    "/usr/bin/inkscape",
                ]
            else:
                channel(_("Platform inkscape locations unknown."))
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
                channel("Searching: %s -- Result: %s" % (ink, result))
            channel(_("----------"))
            if match is None:
                raise ModuleNotFoundError
            root_context = kernel.get_context("/")
            root_context.setting(str, "inkscape_path", "inkscape.exe")
            root_context.inkscape_path = match
            return "inkscape", (match, filename)

        @kernel.console_command(
            "inkscape",
            help="perform a special inkscape function",
            output_type="inkscape",
        )
        def inkscape(channel, _, **kwargs):
            root_context = kernel.get_context("/")
            root_context.setting(str, "inkscape_path", "inkscape.exe")
            return "inkscape", (root_context.inkscape_path, None)
