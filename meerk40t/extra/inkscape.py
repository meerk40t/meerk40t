import gzip
import os.path
import platform
from subprocess import PIPE, TimeoutExpired, run

from meerk40t.core.exceptions import BadFileError
from meerk40t.kernel.kernel import get_safe_path


def get_inkscape(context, manual_candidate=None):
    root_context = context
    root_context.setting(str, "inkscape_path", "inkscape.exe")
    inkscape = ""
    try:
        inkscape = root_context.inkscape_path
    except AttributeError:
        inkscape = ""
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/Inkscape.app/Contents/MacOS/Inkscape",
            "/Applications/Inkscape.app/Contents/Resources/bin/inkscape",
        ]
    elif system == "Windows":
        candidates = [
            "C:/Program Files (x86)/Inkscape/inkscape.exe",
            "C:/Program Files (x86)/Inkscape/bin/inkscape.exe",
            "C:/Program Files/Inkscape/inkscape.exe",
            "C:/Program Files/Inkscape/bin/inkscape.exe",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/local/bin/inkscape",
            "/usr/bin/inkscape",
        ]
    else:
        candidates = []
    if inkscape and inkscape not in candidates:
        candidates.insert(0, inkscape)
    if manual_candidate and manual_candidate not in candidates:
        candidates.insert(0, manual_candidate)
    match = None
    for ink in candidates:
        if os.path.exists(ink):
            match = ink
            root_context.inkscape_path = match
            break
    if match is None:
        inkscape = ""
    return inkscape


class MultiLoader:
    """
    This module makes use of inkscape to convert a multitude of format into svg :
    """

    @staticmethod
    def load_types():
        yield "Inkscape supported files", (
            "pdf",
            "pdxf",
            "eps",
            "cdr",
            "cmx",
            "ccx",
            "cdt",
            "wmf",
            "vsd",
            "ai",
        ), "image/svg+xml"
        # yield "Portable Document Format files", ("pdf",  "pdxf", "eps"), "image/svg+xml"
        # yield "Corel Draw files", ("cdr", "cmx", "ccx", "cdt"), "image/svg+xml"
        # yield "Windows Metafile files", ("wmf",), "image/svg+xml"
        # yield "Visio files", ("vsd",), "image/svg+xml"
        # yield "Adobe Illustrator files", ("ai",), "image/svg+xml"

    @staticmethod
    def load(kernel_service, elements_service, pathname, **kwargs):
        """
        Load content by means of inkscapes ability to convert
        multiple vector formats into svg.
        Requires the installation of inkscape on your system.
        """
        # Elemental calls this routine claiming it would be the kernel...
        if hasattr(kernel_service, "kernel"):
            kernel = kernel_service.kernel
        else:
            kernel = kernel_service

        safe_dir = os.path.realpath(get_safe_path(kernel.name))

        # Establish the standard svg-handler first
        handler = None
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                if "svg" in extensions:
                    handler = loader
                    break

        context_root = kernel.root
        safe_dir = os.path.realpath(get_safe_path(kernel.name))
        timeout_value = None

        inkscape = get_inkscape(context_root)
        if not inkscape:
            raise BadFileError("Inkscape not found")

        try:
            c = run([inkscape, "-V"], timeout=timeout_value, stdout=PIPE)
        except (FileNotFoundError, TimeoutExpired):
            # Return std response
            # print ("Error while getting version")
            return pathname

        version = c.stdout.decode("utf-8")

        svg_temp_file = os.path.join(safe_dir, "inkscape.svg")

        # Check Version of Inkscape
        if "inkscape 1." in version.lower():
            cmd = [
                inkscape,
                "--export-plain-svg",
                f"--export-filename={svg_temp_file}",
                pathname,
            ]
        else:
            cmd = [
                inkscape,
                "--export-plain-svg",
                svg_temp_file,
                pathname,
            ]
        try:
            c = run(cmd, timeout=timeout_value, stdout=PIPE)
            if c.returncode == 1:
                return False
            filename_to_process = svg_temp_file
            preproc = elements_service.lookup("preprocessor/.svg")
            if preproc is not None:
                filename_to_process = preproc(filename_to_process)
            results = handler.load(
                elements_service, elements_service, filename_to_process
            )
            return results
        except (FileNotFoundError, TimeoutExpired) as e:
            # Return std response
            raise BadFileError(str(e)) from e


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
            try:
                kernel.elements.load(filename)
            except BadFileError as e:
                channel(_("File is Malformed."))
                channel(str(e))
            else:
                kernel.elements.classify(list(kernel.elements.elems()))
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
            output_type="inkscape",
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
                    f"--export-dpi={dpi}",
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
                channel(
                    _("inkscape filename {filename} - file not found").format(
                        filename=filename
                    )
                )
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
            channel(
                _('Inkscape executable at "{path}" is: {version}').format(
                    path=inkscape_path, version=c.stdout.decode("utf-8")
                )
            )
            return "inkscape", data

        @kernel.console_argument(
            "inkpath", type=str, help=_("Optional: location of inkscape executable")
        )
        @kernel.console_command(
            "locate",
            help=_("inkscape locate    - set the path to inkscape on your computer"),
            input_type="inkscape",
            output_type="inkscape",
        )
        def inkscape_locate(channel, _, data, inkpath=None, **kwargs):
            inkscape_path, filename = data
            match = get_inkscape(kernel.root, inkpath)
            root_context = kernel.root
            root_context.setting(str, "inkscape_path", "inkscape.exe")
            if match:
                channel(_("Inkscape location: {match}").format(match=match))
            else:
                root_context.inkscape_path = "inkscape.exe"
                channel(
                    _(
                        "Inkscape location: Inkscape not found in default installation directories"
                    )
                )

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

        def check_for_features(pathname, **kwargs):

            # We try to establish if a file contains certain features...

            source = pathname
            if pathname.lower().endswith("svgz"):
                source = gzip.open(pathname, "rb")
            METHOD_CONVERT_TO_OBJECT = 1
            METHOD_CONVERT_TO_PNG = 2
            features = {
                "text": [False, ("<text",), METHOD_CONVERT_TO_OBJECT],
                "clipping": [False, ("<clippath",), METHOD_CONVERT_TO_PNG],
                "mask": [False, ("<mask",), METHOD_CONVERT_TO_PNG],
                "gradient": [
                    False,
                    ("<lineargradient", "<radialgradient"),
                    METHOD_CONVERT_TO_PNG,
                ],
                "pattern": [False, ("<pattern",), METHOD_CONVERT_TO_PNG],
            }
            needs_conversion = 0
            with open(source, mode="r") as f:
                while True:
                    line = f.readline().lower()
                    if not line:
                        break
                    for feat, entry in features.items():
                        for candidate in entry[1]:
                            if candidate in line:
                                entry[0] = True
                                if entry[2] > needs_conversion:
                                    needs_conversion = entry[2]
            context = kernel.root
            inkscape = get_inkscape(context)
            timeout_value = None
            if needs_conversion == 0:
                return pathname
            if len(inkscape) == 0:
                # Inkscape not found.
                return pathname
            # What is our preference? Load, convert, ask?
            conversion_preference = int(kernel.root.svg_not_supported)

            if conversion_preference == 1:
                # Ask
                msg = _(
                    "This file contains certain features that might not be fully supported by MeerK40t"
                )
                for feat, entry in features.items():
                    if entry[0]:
                        msg += "\n" + f" - {feat}"
                if needs_conversion == METHOD_CONVERT_TO_PNG:
                    msg += "\n" + (
                        "The complete design would be rendered into a single graphic."
                    )
                elif needs_conversion == METHOD_CONVERT_TO_OBJECT:
                    msg += "\n" + (
                        "Text elements would be converted into path objects."
                    )

                msg += "\n" + _(
                    "Do you want to convert the file via inkscape or do you want load the unmodified file?"
                )

                response = kernel.yesno(
                    msg,
                    option_yes=_("Convert"),
                    option_no=_("Load original"),
                    caption=_("SVG-Conversion"),
                )
                if response:
                    # convert
                    conversion_preference = 2
                else:
                    # Load
                    conversion_preference = 0

            if conversion_preference == 0:
                # Load
                return pathname

            try:
                c = run([inkscape, "-V"], timeout=timeout_value, stdout=PIPE)
            except (FileNotFoundError, TimeoutExpired):
                # Return std response
                # print ("Error while getting version")
                return pathname

            version = c.stdout.decode("utf-8")
            safe_dir = os.path.realpath(get_safe_path(kernel.name))
            svg_temp_file = os.path.join(safe_dir, "temp.svg")
            png_temp_file = os.path.join(safe_dir, "temp.png")

            if needs_conversion == METHOD_CONVERT_TO_OBJECT:
                # Ask inkscape to convert all text elements to paths
                # slightly different invocation for different values
                # Check Version of Inkscape
                if "inkscape 1." in version.lower():
                    cmd = [
                        inkscape,
                        "--export-text-to-path",
                        "--export-plain-svg",
                        f"--export-filename={svg_temp_file}",
                        pathname,
                    ]
                else:
                    cmd = [
                        inkscape,
                        "--export-text-to-path",
                        "--export-plain-svg",
                        svg_temp_file,
                        pathname,
                    ]
                try:
                    c = run(cmd, timeout=timeout_value, stdout=PIPE)
                    return svg_temp_file
                except (FileNotFoundError, TimeoutExpired):
                    # Return std response
                    # print (f"Error while converting text: {cmd}")
                    return pathname

            if needs_conversion == METHOD_CONVERT_TO_PNG:
                dpi = 500
                if "inkscape 1." in version.lower():
                    cmd = [
                        inkscape,
                        "--export-background",
                        "white",
                        "--export-background-opacity",
                        "255",
                        "--export-area-drawing",
                        "--export-type=png",
                        f"--export-filename={png_temp_file}",
                        f"--export-dpi={dpi}",
                        pathname,
                    ]
                else:
                    cmd = [
                        inkscape,
                        "--export-area-drawing",
                        "--export-dpi",
                        dpi,
                        "--export-background",
                        "rgb(255, 255, 255)",
                        "--export-background-opacity",
                        "255",
                        "--export-png",
                        png_temp_file,
                        pathname,
                    ]
                try:
                    c = run(cmd, timeout=timeout_value, stdout=PIPE)
                    return png_temp_file
                except (FileNotFoundError, TimeoutExpired):
                    # Return std response
                    # print (f"Error while converting to bitmap: {cmd}")
                    return pathname

        kernel.register("preprocessor/.svg", check_for_features)
        # Lets establish some settings too
        stip = (
            _("Meerk40t does not support all svg-features, so you might want")
            + "\n"
            + _("to preprocess the file to get a proper representation of the design.")
            + "\n"
            + _(
                " - Certain subvariants of Fonts - single element will be converted to a path"
            )
            + "\n"
            + _(
                " - Gradient fills / patterns - the whole design will be rendered into a graphic"
            )
            + "\n"
            + _(" - Clipping/Mask - the whole design will be rendered into a graphic")
        )
        system = platform.system()
        if system == "Darwin":
            wildcard = "Inkscape|(Inkscape;inkscape)|All files|*.*"
        elif system == "Windows":
            wildcard = "Inkscape|inkscape.exe|All files|*.*"
        elif system == "Linux":
            wildcard = "Inkscape|inkscape|All files|*.*"
        else:
            wildcard = "Inkscape|(Inkscape;inkscape)|All files|*.*"

        kernel.root.setting(str, "inkscape_path", "")
        choices = [
            {
                "attr": "inkscape_path",
                "object": kernel.root,
                "default": "",
                "type": str,
                "style": "file",
                "wildcard": wildcard,
                "label": _("Inkscape"),
                "tip": _(
                    "Path to inkscape-executable. Leave empty to let Meerk40t establish standard locations"
                ),
                "page": "Input/Output",
                "section": "SVG-Features",
            },
            {
                "attr": "svg_not_supported",
                "object": kernel.root,
                "default": 0,
                "type": int,
                "style": "option",
                "label": _("Unsupported elements"),
                "choices": (0, 2, 1),
                "display": (
                    _("Always load into meerk40t"),
                    _("Convert with inkscape"),
                    _("Ask at load time"),
                ),
                "tip": stip,
                "page": "Input/Output",
                "section": "SVG-Features",
            },
        ]
        kernel.register_choices("preferences", choices)
        kernel.register("load/MultiLoader", MultiLoader)
