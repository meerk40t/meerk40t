def plugin(kernel, lifecycle):
    _ = kernel.translation
    kernel_root = kernel.root

    if lifecycle == "precli":
        kernel._hard_gui = True
        kernel._gui = True

    elif lifecycle == "cli":
        kernel._gui = not kernel.args.no_gui
        kernel._hard_gui = not kernel.args.gui_suppress
        try:
            import wx
        except ImportError:
            kernel._gui = False

            @kernel.console_command("gui", help=_("starts the gui"))
            def gui_start(channel=None, **kwargs):
                channel(
                    "wxPython is not installed. No graphical user interface possible."
                )

            return
        if kernel._hard_gui:
            kernel.set_feature("wx")

            @kernel.console_command("gui", help=_("starts the gui"))
            def gui_start(**kwargs):
                kernel._gui = True  # Set gui to initialize.

        else:
            kernel._gui = False
    if lifecycle == "invalidate":
        if not kernel._hard_gui:
            return True
        try:
            import wx
        except ImportError:
            print("wxMeerK40t plugin could not load because wxPython is not installed.")
            return True
        return False
    if not kernel.has_feature("wx"):
        return
    if lifecycle == "preregister":
        from meerk40t.gui.fonts import svgfont_to_wx, wxfont_to_svg
        from meerk40t.gui.laserrender import LaserRender
        from meerk40t.gui.wxmeerk40t import wxMeerK40t

        kernel.register("module/wxMeerK40t", wxMeerK40t)
        kernel_root.open("module/wxMeerK40t")

        # Registers the render-op make_raster. This is used to do cut planning.
        renderer = LaserRender(kernel_root)
        kernel_root.register("render-op/make_raster", renderer.make_raster)
        kernel_root.register("font/svg_to_wx", svgfont_to_wx)
        kernel_root.register("font/wx_to_svg", wxfont_to_svg)
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
            import wx

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
            import wx

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

        if kernel._gui:

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
            # RC-REMOVE
            kernel_root.setting(bool, "developer_mode", False)
            if not kernel_root.developer_mode:
                message = """This version of MeerK40t is unstable. It is intended primarily for testing purposes. Please report all problems, even small ones to the github issue opened for this version. Do not continue using this version if it is not the latest RC or if your work requires a more stable version.
                
                Open Issue Page?"""
                caption = _("Report Candidate.")
                import wx

                style = wx.YES_NO | wx.CANCEL | wx.ICON_WARNING
                dlg = wx.MessageDialog(
                    None,
                    message,
                    caption=caption,
                    style=style,
                )
                answer = dlg.ShowModal()
                if answer in (wx.YES, wx.ID_YES):
                    issue_page = "https://github.com/meerk40t/meerk40t/issues/1065"
                    import webbrowser

                    webbrowser.open(issue_page, new=0, autoraise=True)
            # END RC-REMOVE

            meerk40tgui.MainLoop()
