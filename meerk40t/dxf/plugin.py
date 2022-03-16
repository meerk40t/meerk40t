
def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import ezdxf
        except ImportError:
            print("DXF plugin could not load because ezdxf is not installed.")
            return True
    elif lifecycle == "register":
        from meerk40t.dxf.dxf_io import DxfLoader
        kernel.register("load/DxfLoader", DxfLoader)
        _ = kernel.translation
        choices = [
            {
                "attr": "dxf_center",
                "object": kernel.elements,
                "default": True,
                "type": bool,
                "label": _("DXF Centering"),
                "tip": _(
                    "Fit (scale down if necessary) and center a DXF file within the bed"
                ),
            },
        ]
        kernel.register_choices("preferences", choices)
