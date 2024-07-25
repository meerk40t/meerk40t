"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.
"""

import argparse
import os.path
import sys

APPLICATION_NAME = "MeerK40t"
APPLICATION_VERSION = "0.9.4050"

if not getattr(sys, "frozen", False):
    # If .git directory does not exist we are running from a package like pypi
    # Otherwise we are running from source
    if os.path.isdir(sys.path[0] + "/.git"):
        APPLICATION_VERSION += " git"
        try:
            head_file = os.path.join(sys.path[0], ".git", "HEAD")
            if os.path.isfile(head_file):
                ref_prefix = "ref: refs/heads/"
                ref = ""
                with open(head_file) as f:
                    ref = f.readline()
                if ref.startswith(ref_prefix):
                    branch = ref[len(ref_prefix) :].strip("\n")
                    APPLICATION_VERSION += " " + branch
                else:
                    branch = ref.strip("\n")
                    APPLICATION_VERSION += " " + branch
        except Exception:
            # Entirely optional, also this code segment may run in python2
            pass

    elif os.path.isdir(sys.path[0] + "/.github"):
        APPLICATION_VERSION += " src"
    else:
        APPLICATION_VERSION += " pkg"


def pair(value):
    rv = value.split("=")
    if len(rv) != 2:
        # raise argparse.ArgumentError, do not raise error.
        pass
    return rv


parser = argparse.ArgumentParser()
parser.add_argument("-V", "--version", action="store_true", help="MeerK40t version")
parser.add_argument("input", nargs="?", type=argparse.FileType("r"), help="input file")
parser.add_argument(
    "-o", "--output", type=argparse.FileType("w"), help="output file name"
)
parser.add_argument("-z", "--no-gui", action="store_true", help="run without gui")
parser.add_argument(
    "-Z", "--gui-suppress", action="store_true", help="completely suppress gui"
)
parser.add_argument(
    "-w", "--simpleui", action="store_true", help="use simple rather than regular UI"
)
parser.add_argument(
    "-b", "--batch", type=argparse.FileType("r"), help="console batch file"
)
parser.add_argument("-c", "--console", action="store_true", help="start as console")
parser.add_argument(
    "-e",
    "--execute",
    action="append",
    type=str,
    nargs="?",
    help="execute console command",
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="display verbose debugging"
)
parser.add_argument(
    "-q", "--quit", action="store_true", help="quit on spooler complete"
)
parser.add_argument("-a", "--auto", action="store_true", help="start running laser")
parser.add_argument(
    "-s",
    "--set",
    action="append",
    nargs="?",
    type=pair,
    metavar="key=value",
    help="set a device variable",
)
parser.add_argument(
    "-P", "--profile", type=int, default=None, help="Specify a settings profile index"
)
parser.add_argument(
    "-p",
    "--no-plugins",
    action="store_true",
    help="Do not load meerk40t.plugins entrypoints",
)
parser.add_argument(
    "-A",
    "--disable-ansi",
    action="store_true",
    default=False,
    help="Disable ANSI colors",
)
parser.add_argument(
    "-X",
    "--nuke-settings",
    action="store_true",
    default=False,
    help="Don't load config file at startup",
)
parser.add_argument(
    "-L",
    "--language",
    type=str,
    default=None,
    help="force default language (en, de, es, fr, hu, it, ja, nl, pt_BR, pt_PT, zh)",
)
parser.add_argument(
    "-f",
    "--profiler",
    type=str,
    default=None,
    help="run meerk40t with profiler file specified",
)
parser.add_argument(
    "-u",
    "--lock-device-config",
    action="store_true",
    help="lock device config from editing",
)
parser.add_argument(
    "-U",
    "--lock-general-config",
    action="store_true",
    help="lock general config from editing",
)


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    ###################
    # WARNING: DO NOT MODERNIZE!
    # BEGIN Old Python Code.
    ###################

    # This does version checks, it must be compatible. Py2/3 Code.
    if args.version:
        print("%s %s" % (APPLICATION_NAME, APPLICATION_VERSION))
        return
    python_version_required = (3, 6)
    if sys.version_info < python_version_required:
        print(
            "%s %s requires Python %d.%d or greater."
            % (
                APPLICATION_NAME,
                APPLICATION_VERSION,
                python_version_required[0],
                python_version_required[1],
            )
        )
        return
    ###################
    # END Old Python Code.
    ###################
    if args.profiler:
        import cProfile

        profiler = cProfile.Profile()
        profiler.enable()
        _run = _exe(False, args)
        while _run:
            _run = _exe(True, args)
        profiler.disable()
        profiler.dump_stats(args.profiler)
        return
    _run = _exe(False, args)
    while _run:
        _run = _exe(True, args)


def _exe(restarted, args):
    from meerk40t.external_plugins import plugin as external_plugins
    from meerk40t.internal_plugins import plugin as internal_plugins
    from meerk40t.kernel import Kernel

    kernel = Kernel(
        APPLICATION_NAME,
        APPLICATION_VERSION,
        APPLICATION_NAME,
        ansi=not args.disable_ansi,
        ignore_settings=args.nuke_settings,
        restarted=restarted,
    )
    kernel.args = args
    kernel.add_plugin(internal_plugins)
    kernel.add_plugin(external_plugins)
    auto = hasattr(kernel.args, "auto") and kernel.args.auto
    console = hasattr(kernel.args, "console") and kernel.args.console
    for idx, attrib in enumerate(("mktablength", "mktabpositions")):
        kernel.register(f"registered_mk_svg_parameters/tabs{idx}", attrib)

    if auto and not console:
        kernel(partial=True)
    else:
        kernel()
    return hasattr(kernel, "restart") and kernel.restart
