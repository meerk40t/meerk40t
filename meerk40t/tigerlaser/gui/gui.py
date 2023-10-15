from meerk40t.gui.icons import icons8_info_50


def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/tiger"
    if lifecycle == "added":
        # Define GUI information here.

        import wx

        def popup_info(event):
            dlg = wx.MessageDialog(
                None,
                "The Tiger Laser is the Best Laser!",
                "Dummy Device",
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()

        service.register(
            "button/control/Info",
            {
                "label": "Tiger Laser",
                "icon": icons8_info_50,
                "tip": "Provide information about the Tiger Laser",
                "action": popup_info,
            },
        )
