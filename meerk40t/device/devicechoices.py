from meerk40t.kernel import _


def get_effect_choices(context):
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
