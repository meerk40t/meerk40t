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

SLEEP_CONTEXT = None
SLEEP_ORIGIN_RUNNING = dict()
SLEEP_VALUE = False


def on_usb_running(origin, value):
    """
    Registered during the boot and unregistered during shutdown lifecycle.

    On_usb_running listens for pipe;running signals and if any origin value is true
    This calls sleepmode_disable.
    """
    global SLEEP_ORIGIN_RUNNING
    global SLEEP_VALUE
    global SLEEP_CONTEXT
    running = SLEEP_ORIGIN_RUNNING
    running[origin] = value
    any = False
    for v in running:
        q = running[v]
        if q:
            any = True
            break

    if any != SLEEP_VALUE:
        SLEEP_VALUE = any
        if any:
            SLEEP_CONTEXT(".sleepmode_disable\n")
        else:
            SLEEP_CONTEXT(".sleepmode_enable\n")


def plugin(kernel, lifecycle):
    global SLEEP_CONTEXT

    if platform.system() != "Windows":
        # Plugin only matters for MSW platform
        return
    if lifecycle == "boot":
        context = kernel.root

        context.listen("pipe;running", on_usb_running)
    elif lifecycle == "register":
        context = kernel.root
        SLEEP_CONTEXT = context
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
