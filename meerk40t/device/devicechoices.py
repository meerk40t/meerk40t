from meerk40t.kernel import _

def get_effect_choices(context):
    return [
        {
            "attr": "effect_hatch_default_distance",
            "object": context,
            "default": "1.0mm",
            "type": str,
            "label": _("Hatch Distance"),
            "tip": _("Default Hatch Distance"),
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_hatch_default_angle",
            "object": context,
            "default": "0deg",
            "type": str,
            "label": _("Hatch Angle"),
            "tip": _("Default Hatch Angle"),
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_hatch_default_angle_delta",
            "object": context,
            "default": "0deg",
            "type": str,
            "label": _("Hatch Angle Delta"),
            "tip": _("Default Hatch Angle Delta"),
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_radius",
            "object": context,
            "default": "0.5mm",
            "type": str,
            "label": _("Wobble Radius"),
            "tip": _("Default Wobble Radius"),
            "section": "Effect Defaults",
        },
        {
            "attr": "effect_wobble_default_interval",
            "object": context,
            "default": "0.05mm",
            "type": str,
            "label": _("Wobble Interval"),
            "tip": _("Default Wobble Interval"),
            "section": "Effect Defaults",
        },
    ]