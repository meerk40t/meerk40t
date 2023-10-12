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

        try:
            from importlib.metadata import entry_points
        except ImportError:
            from importlib_metadata import entry_points

        entry_points = entry_points()
        try:
            ep = entry_points.select(group="meerk40t.extension")
        except AttributeError:
            ep = entry_points.get("meerk40t.extension")

        for entry_point in ep:
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
