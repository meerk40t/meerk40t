def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import ezdxf
        except ImportError:
            print("DXF plugin could not load because ezdxf is not installed.")
            return True
        try:
            # Includes ezdxf and all required imports therein
            from meerk40t.dxf.dxf_io import DxfLoader
        except ImportError:
            print("DXF plugin could not load because, though ezdxf is installed, the version isn't supported.")
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
                "label": _("DXF Center and Fit"),
                "tip": _(
                    "Fit (scale down if necessary) and center a DXF file within the bed"
                ),
                "page": "Input/Output",
                "section": "Input",
            },
        ]
        kernel.register_choices("preferences", choices)
