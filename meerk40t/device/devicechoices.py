

def get_effect_choices(context):
    _ = context.kernel.translation
    def get_wobble_options():
        return list(context.match("wobble", suffix=True))

    return [
        {
            "attr": "effect_hatch_default_distance",
            "object": context,
            "default": "1.0mm",
            "type": str,
            "label": _("Hatch Distance"),
            "tip": _("Default Hatch Distance"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_hatch_default_angle",
            "object": context,
            "default": "0deg",
            "type": str,
            "label": _("Hatch Angle"),
            "tip": _("Default Hatch Angle"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_hatch_default_angle_delta",
            "object": context,
            "default": "0deg",
            "type": str,
            "label": _("Hatch Angle Delta"),
            "tip": _("Default Hatch Angle Delta"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_type",
            "object": context,
            "default": "circle",
            "type": str,
            "style": "combo",
            "choices": get_wobble_options(),
            "label": _("Wobble Type"),
            "tip": _("Default Wobble Type"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_speed",
            "object": context,
            "default": 50,
            "type": int,
            "label": _("Wobble Speed"),
            "tip": _("Default Wobble Speed"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_radius",
            "object": context,
            "default": "0.5mm",
            "type": str,
            "label": _("Wobble Radius"),
            "tip": _("Default Wobble Radius"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_interval",
            "object": context,
            "default": "0.1mm",
            "type": str,
            "label": _("Wobble Interval"),
            "tip": _("Default Wobble Interval"),
            # Hint for translation _("Effect Defaults")
            "section": "Effect Defaults",
        },
    ]


def get_operation_choices(
    context, default_cut_speed=5, default_engrave_speed=10, default_raster_speed=200
):
    _ = context.kernel.translation
    choices = []
    operations = {
        "op_cut": (_("Cut"), default_cut_speed),
        "op_engrave": (_("Engrave"), default_engrave_speed),
        "op_raster": (_("Raster"), default_raster_speed),
        "op_image": (_("Image"), default_raster_speed),
    }
    idx = 0

    def use_percent_for_power_display():
        return getattr(context, "use_percent_for_power_display", False)

    def use_mm_min_for_speed_display():
        return getattr(context, "use_mm_min_for_speed_display", False)

    for optype, (opname, sensible_speed) in operations.items():
        idx += 10
        choices.extend(
            (
                {
                    "attr": f"default_power_{optype}",
                    "object": context,
                    "default": "1000",
                    "type": float,
                    "style": "power",
                    "percent": use_percent_for_power_display,
                    "label": _("Power"),
                    "tip": _("Default power for {op}").format(op=opname),
                    "section": "Operation Defaults",
                    "subsection": f"_{idx}_{opname}",
                },
                {
                    "attr": f"default_speed_{optype}",
                    "object": context,
                    "default": sensible_speed,
                    "type": float,
                    "style": "speed",
                    "perminute": use_mm_min_for_speed_display,
                    "label": _("Speed"),
                    "tip": _("Default speed for {op}").format(op=opname),
                    "section": "Operation Defaults",
                    "subsection": f"_{idx}_{opname}",
                },
            )
        )

    return choices
