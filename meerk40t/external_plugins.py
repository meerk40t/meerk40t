"""
These are external plugins. They are dynamically found by entry points. This file is replaced with the build file during
builds, since compiled versions do not have access to entry points. External plugins therefore must be hard-coded for
builds. See the external_plugin_build.py file for regular built plugins.
"""


def plugin(kernel, lifecycle):
    import sys

    if lifecycle == "plugins":
        if getattr(sys, "frozen", False):
            return
        if kernel.args.no_plugins:
            return

        plugins = list()

        import sys
        if sys.version_info < (3, 8):
            from importlib_metadata import entry_points
        else:
            from importlib.metadata import entry_points

        entry_points = entry_points()
        for entry_point in entry_points.select(group="meerk40t.extension"):
            try:
                plugin = entry_point.load()
                plugins.append(plugin)
            except ImportError as e:
                print(
                    "Cannot install plugin - '{entrypoint}'.".format(
                        entrypoint=str(entry_point.value)
                    )
                )
                print(e)
        return plugins
    if lifecycle == "invalidate":
        return True
