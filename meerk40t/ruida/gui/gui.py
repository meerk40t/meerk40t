def plugin(service, lifecycle):
    if lifecycle == "invalidate":
        return not service.has_feature("wx")
    if lifecycle == "service":
        return "provider/device/ruida"
    if lifecycle == "added":
        import wx

        from meerk40t.gui.icons import (
            icons8_info_50,
            icons8_computer_support_50,
            icons8_connected_50,
        )

        _ = service._

        def popup_info(event):
            dlg = wx.MessageDialog(
                None,
                _("Ruida Driver is not yet completed."),
                _("Non Implemented Device"),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()

        service.register(
            "button/control/Info",
            {
                "label": _("Ruida Info"),
                "icon": icons8_info_50,
                "tip": _("Provide information about the Ruida Driver"),
                "action": popup_info,
            },
        )
        service.register(
            "button/control/Controller",
            {
                "label": _("Controller"),
                "icon": icons8_connected_50,
                "tip": _("Opens Controller Window"),
                "action": lambda e: service("window toggle Controller\n"),
            },
        )
        service.register(
            "button/device/Configuration",
            {
                "label": _("Config"),
                "icon": icons8_computer_support_50,
                "tip": _("Opens device-specific configuration window"),
                "action": lambda v: service("window toggle Configuration\n"),
            },
        )
        from meerk40t.ruida.gui.ruidaconfig import RuidaConfiguration
        from meerk40t.ruida.gui.ruidacontroller import RuidaController
        from meerk40t.ruida.gui.ruidaoperationproperties import RuidaOperationPanel

        service.register("window/Controller", RuidaController)
        service.register("window/Configuration", RuidaConfiguration)

        service.register("winpath/Controller", service)
        service.register("winpath/Configuration", service)

        service.register("property/RasterOpNode/Ruida", RuidaOperationPanel)
        service.register("property/CutOpNode/Ruida", RuidaOperationPanel)
        service.register("property/EngraveOpNode/Ruida", RuidaOperationPanel)
        service.register("property/ImageOpNode/Ruida", RuidaOperationPanel)
        service.register("property/DotsOpNode/Ruida", RuidaOperationPanel)
        service.register("property/HatchOpNode/Ruida", RuidaOperationPanel)

        service.add_service_delegate(RuidaGui(service))


class RuidaGui:
    def __init__(self, context):
        self.context = context
        # This is a stub.
