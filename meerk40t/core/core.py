"""
This plugin registers the other major plugins found in core.
"""


def plugin(kernel, lifecycle=None):
    _ = kernel.translation

    # Install color caching as early as possible
    if lifecycle == "preregister":
        from .color_cache import install_color_cache
        if install_color_cache():
            print("Color caching enabled (14x faster color parsing)")

    if lifecycle == "plugins":
        plugins = []

        from . import spoolers

        plugins.append(spoolers.plugin)

        from . import space

        plugins.append(space.plugin)

        from .elements import elements

        plugins.append(elements.plugin)

        from .elements import penbox

        plugins.append(penbox.plugin)

        from . import logging

        plugins.append(logging.plugin)

        from . import bindalias

        plugins.append(bindalias.plugin)

        from . import webhelp

        plugins.append(webhelp.plugin)

        from . import planner

        plugins.append(planner.plugin)

        from . import svg_io

        plugins.append(svg_io.plugin)

        return plugins
