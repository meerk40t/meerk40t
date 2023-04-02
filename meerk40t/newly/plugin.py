"""
Newly Device Plugin

"""


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        from meerk40t.newly.gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import usb.core  # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Newly plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        from meerk40t.newly.device import NewlyDevice

        speed_chart = [
            {
                "speed": 100,
                "acceleration_length": 8,
                "backlash": 0,
                "corner_speed": 20,
            },
            {
                "speed": 200,
                "acceleration_length": 10,
                "backlash": 0,
                "corner_speed": 20,
            },
            {
                "speed": 300,
                "acceleration_length": 14,
                "backlash": 0,
                "corner_speed": 20,
            },
            {
                "speed": 400,
                "acceleration_length": 16,
                "backlash": 0,
                "corner_speed": 20,
            },
            {
                "speed": 500,
                "acceleration_length": 18,
                "backlash": 0,
                "corner_speed": 20,
            },
        ]

        _ = kernel.translation
        kernel.register("provider/device/newly", NewlyDevice)
        kernel.register(
            "dev_info/g3v8-raylaser",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("RayLaser/U-SET"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "RayLaser/U-SET",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {"attr": "axis", "default": 1},
                    {"attr": "pos_mode", "default": 1},
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-beijing",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Beijing SZTaiming"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Beijing SZTaiming",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {"attr": "axis", "default": 1},
                    {"attr": "pos_mode", "default": 1},
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-gama",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Gama"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Gama",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {"attr": "axis", "default": 1},
                    {"attr": "pos_mode", "default": 1},
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-gama",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Cybertech ltd - u-set"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Cybertech",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {"attr": "axis", "default": 1},
                    {"attr": "pos_mode", "default": 1},
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-artsign-u",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Artsign JSM-40U/3040U/3060U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Artsign",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-artsign-n",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Artsign JSM-40N/3040N/3060N"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Artsign",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-light-tech",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Light Technology LH40U/3040U/3060U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Light Technology",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-greatsign",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Greatsign LE40U/3040U/3060U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Greatsign",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-helo",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Helo Lasergraviermaschine-HLG 40N"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Helo",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-workline",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Workline laser"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Workline",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-hpc",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("HPC LASER-LS 3020"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "HPC",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-sicono",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Sicano - SIC-L40B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Sicono",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-rabbit",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Rabbit - Rabbit40B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Rabbit",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-zl",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("ZL Tech - ZL40B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "ZL",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-jinan-suke",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan Suke"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Jinan-Suke",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "308mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "220mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 0,
                    },
                    {
                        "attr": "speedchart",
                        "default": speed_chart,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-jinan-jinweik",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan Jinweik - Laser B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Jinan-Jinweik",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "600mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "400mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {
                        "attr": "board",
                        "default": 1,
                    },
                    {
                        "attr": "z_type",
                        "default": 2,
                    },
                    {
                        "attr": "z_dir",
                        "default": 0,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-lion",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Lion laser"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Lion",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-villa",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Villa L. & Figlio S.R.L. - Laser B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserB",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "600mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "400mm",
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {
                        "attr": "z_type",
                        "default": 2,
                    },
                    {
                        "attr": "z_dir",
                        "default": 0,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-amc",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("AMC CO damascus - Laser B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserB",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "600mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "400mm",
                    },
                    {
                        "attr": "board",
                        "default": 1,
                    },
                    {
                        "attr": "axis",
                        "default": 3,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {
                        "attr": "z_type",
                        "default": 2,
                    },
                    {
                        "attr": "z_dir",
                        "default": 0,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-ruijie",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan Ruijie - Laser U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserU",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-mini",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Mini Laser - USB"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Mini Laser",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-xinyi",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan Xinyi - USB"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Mini Laser",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-weifang",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Weifang Tiangong - Laser B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserB",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-duowei",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Duowei Laser - Laser U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserU",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-duowei",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Weifang Tiangong - Laser B"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LaserB",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-dagong",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan DaGong - TLU series"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "DaGong",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "1000mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "800mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-senfeng",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Jinan Senfeng - Laser U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Senfeng",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-lecai-laser",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("ZhengZhou LeCai - LC Laser"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LCLaser",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-lecai-plasma",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("ZhengZhou LeCai - LC Plasma"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "LCPlasma",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "2500mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "1300mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {
                        "attr": "z_type",
                        "default": 1,
                    },
                    {
                        "attr": "z_dir",
                        "default": 0,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-jinli",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Wuhan Jinli - JL Cylinder"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "JLCylinder",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-evertech",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("DongGuan EverTech - ETL3525 Laser"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "EverTech",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-anwei",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Wuhan Anwei - AW-U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "AW-U",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "600mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "400mm",
                    },
                    {
                        "attr": "w_dpi",
                        "default": 803,
                    },
                    {
                        "attr": "h_dpi",
                        "default": 803,
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 3,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )
        kernel.register(
            "dev_info/g3v8-xinxing",
            {
                "provider": "provider/device/newly",
                "friendly_name": _("Liaocheng Xinxing - U"),
                "extended_info": _("Older CO2 Laser running the NewlyDraw software"),
                "priority": 5,
                "family": _("Older CO2-Laser"),
                "family_priority": 15,
                "choices": [
                    {
                        "attr": "label",
                        "default": "xinxing",
                    },
                    {
                        "attr": "bedwidth",
                        "default": "900mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "600mm",
                    },
                    {
                        "attr": "axis",
                        "default": 1,
                    },
                    {
                        "attr": "pos_mode",
                        "default": 1,
                    },
                    {"attr": "source", "default": "Older CO2"},
                ],
            },
        )

    elif lifecycle == "preboot":
        suffix = "newly"
        for d in kernel.settings.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
