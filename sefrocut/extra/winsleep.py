import platform

"""
Winsleep is a internal standalone Windows-only plugin that works for sys.platform 'win32'.
The plugin does not register if the platform is not MSW.

If any signal origin gives a pipe;running signal of True, it will execute sleepmode_disable.
When all signals then give pipe;running signals of False, it will execute sleepmode_enable.

We also register sleepmode_disable and sleepmode_enable as hidden commands which flag
the ctypes windll kernel32 threadstate to be ES_SYSTEM_REQUIRED which disables sleeping
in windows.
"""


SLEEP_DISABLED = [None, dict(), False]


def on_usb_running(origin, value):
    """
    Registered during the boot and unregistered during shutdown lifecycle.

    On_usb_running listens for pipe;running signals and if any origin value is true
    This calls sleepmode_disable.
    """
    running = SLEEP_DISABLED[1]
    running[origin] = value
    any_origin_running = False
    for v in running:
        q = running[v]
        if q:
            any_origin_running = True
            break
    if any_origin_running != SLEEP_DISABLED[2]:
        SLEEP_DISABLED[2] = any_origin_running
        if any_origin_running:
            # pylint: disable=E1102
            SLEEP_DISABLED[0](".sleepmode_disable\n")
        else:
            # pylint: disable=E1102
            SLEEP_DISABLED[0](".sleepmode_enable\n")


def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        # Plugin only matters for MSW platform
        return platform.system() != "Windows"
    if lifecycle == "boot":
        context = kernel.root

        context.listen("pipe;running", on_usb_running)
    elif lifecycle == "register":
        context = kernel.root
        SLEEP_DISABLED[0] = context
        _ = kernel.translation

        @context.console_command(
            "sleepmode_disable", help=_("disables sleepmode"), hidden=True
        )
        def sleepmode_disable(**kwargs):
            try:
                import ctypes

                # ES_CONTINUOUS, 0x80000000, # ES_SYSTEM_REQUIRED = 0x00000001
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            except AttributeError:
                pass

        @context.console_command(
            "sleepmode_enable", help=_("enables sleepmode"), hidden=True
        )
        def sleepmode_enable(**kwargs):
            try:
                import ctypes

                # ES_CONTINUOUS, 0x80000000
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except AttributeError:
                pass

    elif lifecycle == "shutdown":
        context = kernel.root
        context.unlisten("pipe;running", on_usb_running)
