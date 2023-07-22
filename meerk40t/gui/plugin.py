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
            def gui_fail(channel=None, **kwargs):
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
        # Let's check whether we have an incompatible version of wxpython and python.
        # Python 3.10 onwards no longer supports automatic casts of decimals to ints:
        # Builtin and extension functions that take integer arguments no longer accept
        # Decimals, Fractions and other objects that can be converted to integers only
        # with a loss (e.g. that have the __int__() method but do not have the __index__() method).
        # wxpython up to 4.1.1 exposes this issue
        try:
            if wx.VERSION[:2] <= (4, 1):
                testcase = wx.Size(0.5, 1)
        except TypeError:
            print(
                """The version of wxPython you are running is incompatible with your current Python version.
At the time of writing this is especially true for any Python version >= 3.10
and a wxpython version <= 4.1.1."""
            )
            return True
        return False
    if not kernel.has_feature("wx"):
        return
    if lifecycle == "preregister":
        from meerk40t.gui.fonts import wxfont_to_svg
        from meerk40t.gui.laserrender import LaserRender
        from meerk40t.gui.wxmeerk40t import wxMeerK40t

        kernel.register("module/wxMeerK40t", wxMeerK40t)
        kernel_root.open("module/wxMeerK40t")

        # Registers the render-op make_raster. This is used to do cut planning.
        renderer = LaserRender(kernel_root)
        kernel_root.register("render-op/make_raster", renderer.make_raster)
        kernel_root.register("font/wx_to_svg", wxfont_to_svg)
    if lifecycle == "register":
        from meerk40t.gui.guicolors import GuiColors

        kernel.add_service("colors", GuiColors(kernel))

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
                "attr": "windows_save",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Save Window Positions"),
                "tip": _("Open Windows at the same place they were last closed"),
                "page": "Gui",
                "section": "General",
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
                "page": "Laser",
                "section": "General",
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
                "page": "Gui",
                "section": "General",
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
                "page": "Gui",
                "section": "General",
            },
            {
                "attr": "mouse_zoom_invert",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Invert MouseWheel Zoom"),
                "tip": _("Reverses the direction of the MouseWheel for zoom"),
                "page": "Gui",
                "section": "General",
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
                "page": "Gui",
                "section": "General",
            },
            {
                "attr": "disable_tree_tool_tips",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Disable tooltips over tree"),
                "tip": _(
                    "You can suppress the tooltips over operations and elements in the tree"
                ),
                "page": "Gui",
                "section": "General",
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
                    return None
            try:
                return data_type(value)
            except ValueError:
                return None

        kernel.prompt = prompt_popup

        def yesno_popup(prompt, option_yes=None, option_no=None, caption=None):
            """
            @param prompt: question asked of the user.
            @param option_yes: input to be interpreted as yes (first letter is okay too).
            @param option_no: input to be interpreted as no (first letter is okay too).
            @param caption: caption for popup
            """
            import wx

            if option_yes is None:
                option_yes = _("Yes")
            if option_no is None:
                option_no = _("No")
            if caption is None:
                caption = _("Question")
            dlg = wx.MessageDialog(
                None,
                message=prompt,
                caption=caption,
                style=wx.YES_NO | wx.ICON_QUESTION,
            )
            if dlg.SetYesNoLabels(option_yes, option_no):
                dlg.SetMessage(prompt)
            else:
                dlg.SetMessage(
                    prompt
                    + "\n"
                    + _("(Yes={yes}, No={no})").format(yes=option_yes, no=option_no)
                )

            response = dlg.ShowModal()
            dlg.Destroy()
            return bool(response == wx.ID_YES)

        kernel.yesno = yesno_popup

        from meerk40t.gui.busy import BusyInfo

        kernel.busyinfo = BusyInfo()

        @kernel.console_argument("message")
        @kernel.console_command("notify", hidden=True)
        def notification_message(message=None, **kwargs):
            if message is None:
                message = _("Something requires your attention")
            from wx.adv import NotificationMessage

            msg = NotificationMessage(title="MeerK40t", message=message)
            msg.Show()

        @kernel.console_argument(
            "message", help=_("Message to display, optional"), default=""
        )
        @kernel.console_command("interrupt", hidden=True)
        def interrupt(message="", **kwargs):
            """
            Interrupt interrupts but does so in the gui thread. This is so that some
            OSes like linux can be properly stopped in the gui. The gui-thread will
            often be required. But, this will typically be called in the spooler thread.

            If called in the main thread, we call the dialog ourselves to avoid livelock.

            @param message:
            @param kwargs:
            @return:
            """
            if not message:
                message = _("Spooling Interrupted.")

            import threading

            import wx

            lock = threading.Lock()
            lock.acquire(True)

            def message_dialog(*args):
                dlg = wx.MessageDialog(
                    None,
                    message + "\n\n" + _("Press OK to Continue."),
                    _("Interrupt"),
                    wx.OK,
                )
                dlg.ShowModal()
                dlg.Destroy()
                lock.release()

            if wx.IsMainThread():
                # If we're in main thread we much call here or livelock.
                message_dialog()
            else:
                wx.CallAfter(message_dialog, None)
            lock.acquire(True)

        if kernel._gui:
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            if kernel.args.simpleui:
                kernel.console("window open SimpleUI\n")
                meerk40tgui.MainLoop()
                return

            kernel.console("window open MeerK40t\n")
            for window in kernel.derivable("window"):
                wsplit = window.split(":")
                window_name = wsplit[0]
                window_index = wsplit[-1] if len(wsplit) > 1 else None
                if kernel.read_persistent(bool, window, "open_on_start", False):
                    if window_index is not None:
                        kernel.console(
                            f"window open -m {window_index} {window_name[7:]} {window_index}\n"
                        )
                    else:
                        kernel.console(f"window open {window_name[7:]}\n")

            meerk40tgui.MainLoop()
