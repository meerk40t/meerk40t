from meerk40t.lihuiyu.device import LihuiyuDevice


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui as lhygui

        return [lhygui.plugin]

    if lifecycle == "register":
        kernel.register("provider/device/lhystudios", LihuiyuDevice)
        try:
            from meerk40t.lihuiyu.egvloader import EgvLoader

            kernel.register("load/EgvLoader", EgvLoader)
        except ImportError:
            pass
        try:
            from .lihuiyuinterpreter import LihuiyuInterpreter

            kernel.register("interpreter/lihuiyu", LihuiyuInterpreter)
        except ImportError:
            pass
        try:
            from meerk40t.lihuiyu.lihuiyuparser import LihuiyuParser

            kernel.register("parser/egv", LihuiyuParser)
        except ImportError:
            pass
    if lifecycle == "preboot":
        suffix = "lhystudios"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
