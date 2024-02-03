"""
These are external plugins. They are dynamically found by entry points. This file is replaced with the build file during
builds, since compiled versions do not have access to entry points. External plugins therefore must be hard-coded for
builds. See the external_plugin_build.py file for regular built plugins.
"""

MEERK40T_ENTRYPOINT = "meerk40t.extension"


def plugins_pre_38():
    """
    Import plugins using pkg_resources. pkg_resources was deprecated in 3.10 and removed in 3.12
    @return:
    """
    import pkg_resources

    for entry_point in pkg_resources.iter_entry_points(MEERK40T_ENTRYPOINT):
        try:
            ep_plugin = entry_point.load()
        except pkg_resources.DistributionNotFound:
            pass
        except pkg_resources.VersionConflict as e:
            print(
                "Cannot install plugin - '{entrypoint}' due to version conflict.".format(
                    entrypoint=str(entry_point)
                )
            )
            print(e)
        else:
            yield ep_plugin


def plugins_importlib():
    """
    Import entry points with importlib.

    @return:
    """
    from importlib.metadata import entry_points

    entry_points = entry_points()

    try:
        ep = entry_points.select(group=MEERK40T_ENTRYPOINT)
    except AttributeError:
        ep = entry_points.get(MEERK40T_ENTRYPOINT)

    if ep is None:
        return []

    for entry_point in ep:
        try:
            yield entry_point.load()
        except ImportError as e:
            print(
                "Cannot install plugin - '{entrypoint}'.".format(
                    entrypoint=str(entry_point.value)
                )
            )
            print(e)


def plugin(kernel, lifecycle):
    import sys

    if lifecycle == "plugins":
        if getattr(sys, "frozen", False):
            return
        if kernel.args.no_plugins:
            return

        try:
            return list(plugins_importlib())
        except ImportError:
            return list(plugins_pre_38())

    if lifecycle == "invalidate":
        # Do not maintain plugin.
        return True
