GUI_START = True


def plugin(kernel, lifecycle):
    _ = kernel.translation
    kernel_root = kernel.root

    # pylint: disable=global-statement
    global GUI_START

    if lifecycle == "cli":
        try:
            import wx
        except ImportError:
            return
        kernel.set_feature("wx")
    if lifecycle == "invalidate":
        try:
            import wx
        except ImportError:
            print("wxMeerK40t plugin could not load because wx is not installed.")
            return True
    if lifecycle == "init" and kernel.args.no_gui:
        GUI_START = False

        @kernel.console_command("gui", help=_("starts the gui"))
        def gui_start(**kwargs):
            kernel.console_command_remove("gui")
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            meerk40tgui.MainLoop()

    elif lifecycle == "preregister":
        from meerk40t.gui.laserrender import LaserRender

        from meerk40t.gui.wxmeerk40t import wxMeerK40t
        kernel.register("module/wxMeerK40t", wxMeerK40t)
        kernel_root.open("module/wxMeerK40t")

        # Registers the render-op make_raster. This is used to do cut planning.
        renderer = LaserRender(kernel_root)
        kernel_root.register("render-op/make_raster", renderer.make_raster)
    if lifecycle == "register":

        from meerk40t.gui.scene.scene import Scene
        kernel.register("module/Scene", Scene)

    elif lifecycle == "boot":
        kernel_root = kernel.root
        choices = [
            {
                "attr": "units_name",
                "object": kernel_root,
                "default": "mm",
                "type": str,
            },
        ]
        kernel.register_choices("units", choices)
    elif lifecycle == "postboot":
        choices = [
            {
                "attr": "show_negative_guide",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Show Negative Guide"),
                "tip": _(
                    "Extend the Guide rulers with negative values to assist lining up objects partially outside the left/top of the bed"
                ),
            },
            {
                "attr": "windows_save",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Save Window Positions"),
                "tip": _("Open Windows at the same place they were last closed"),
            },
            {
                "attr": "auto_spooler",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Launch Spooler on Job Start"),
                "tip": _(
                    "Open the Spooler window automatically when you Execute a Job"
                ),
            },
            {
                "attr": "mouse_wheel_pan",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("MouseWheel Pan"),
                "tip": "\n".join(
                    (
                        _("Unset: MouseWheel=Zoom. Shift+MouseWheel=Horizontal pan."),
                        _(
                            "Set: MouseWheel=Vertical pan. Ctrl+MouseWheel=Zoom. Shift+MouseWheel=Horizontal pan."
                        ),
                    )
                ),
            },
            {
                "attr": "mouse_pan_invert",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Invert MouseWheel Pan"),
                "tip": _(
                    "Reverses the direction of the MouseWheel for horizontal & vertical pan"
                ),
            },
            {
                "attr": "mouse_zoom_invert",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Invert MouseWheel Zoom"),
                "tip": _("Reverses the direction of the MouseWheel for zoom"),
            },
            {
                "attr": "disable_tool_tips",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Disable ToolTips"),
                "tip": "\n".join(
                    (
                        _(
                            "If you do not want to see tooltips like this one, check this box."
                        ),
                        _("Particularly useful if you have a touch screen."),
                        _(
                            "Note: You will need to restart MeerK40t for any change to take effect."
                        ),
                    )
                ),
            },
        ]
        kernel.register_choices("preferences", choices)

    elif lifecycle == "mainloop":
        # Replace the default kernel data prompt for a wx Popup.

        def prompt_popup(data_type, prompt):
            with wx.TextEntryDialog(
                None, prompt, _("Information Required:"), ""
            ) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    value = dlg.GetValue()
                else:
                    return
            try:
                return data_type(value)
            except ValueError:
                return None

        kernel.prompt = prompt_popup

        def interrupt_popup():
            dlg = wx.MessageDialog(
                None,
                _("Spooling Interrupted. Press OK to Continue."),
                _("Interrupt"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

        kernel_root.planner.register("function/interrupt", interrupt_popup)

        def interrupt():
            yield "wait_finish"
            yield "function", kernel_root.lookup("function/interrupt")

        kernel_root.planner.register("plan/interrupt", interrupt)

        if GUI_START:
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            for window in kernel.derivable("window"):
                wsplit = window.split(":")
                window_name = wsplit[0]
                window_index = wsplit[-1] if len(wsplit) > 1 else None
                if kernel.read_persistent(
                    bool, "window/%s/open_on_start" % window, False
                ):
                    if window_index is not None:
                        kernel.console(
                            "window open -m {index} {window} {index}\n".format(
                                index=window_index, window=window_name
                            )
                        )
                    else:
                        kernel.console(
                            "window open {window}\n".format(window=window_name)
                        )
            meerk40tgui.MainLoop()
