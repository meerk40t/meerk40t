import sys


def plugins(kernel, lifecycle):
    """
    These are dynamic plugins. They are dynamically found by entry points.
    """
    if lifecycle == "plugins":
        if getattr(sys, "frozen", False):
            return
        if kernel.args.no_plugins:
            return

        plugins = list()
        import pkg_resources

        for entry_point in pkg_resources.iter_entry_points("meerk40t.extension"):
            try:
                plugin = entry_point.load()
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
                plugins.append(plugin)
        return plugins
    if lifecycle == "invalidate":
        return True
