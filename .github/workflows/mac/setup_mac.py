from setuptools import setup

FileTypePlist = dict(
    CFBundleDocumentTypes=[
        dict(
            CFBundleTypeExtensions=["html", "htm"],
            CFBundleTypeName="HTML Document",
            CFBundleTypeRole="Viewer",
        ),
    ]
)

APP = ["meerk40t.py"]
DATA_FILES = ["locale"]
OPTIONS = {
    "iconfile": "meerk40t.icns",
    "arch": "x86_64",
    "plist": {
        "CFBundleSupportedPlatforms": "MacOSX",
        "LSApplicationCategoryType": "public.app-category.utilities",
        "CFBundleIdentifier": "org.tatarize.MeerK40t",
        "CFBundleShortVersionString": "0.0.0",
        "NSHumanReadableCopyright": "Copyright © 2019-2021 MeerK40t Developers, MIT License",
        "NSHighResolutionCapable": "YES",
        "NSRequiresAquaSystemAppearance": "NO",
        "CFBundleDevelopmentRegion": "en",
        "CFBundleAllowMixedLocalizations": "NO",
        "CFAppleHelpAnchor": "YES",
        "CFBundleDisplayName": "MeerK40t",
        "CFBundleSpokenName": "Meerkat",
        "CFBundleExecutable": "MeerK40t",
        "CFBundleVersion": "0.0.0",
        "CFBundleName": "MeerK40t",
        "LSFileQuarantineEnabled": "YES",
        "CFBundleTypeExtensions": "*",
        "CFBundleTypeRole": "Editor",
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    install_requires=[
        "pyusb>=1.0.0",
    ],
    extras_require={
        "all": [
            "wxPython>=4.0.0",
            "Pillow>=7.0.0",
            "meerk40t_camera",
            "opencv-python-headless>=3.4.0.0",
            "ezdxf>=0.14.0",
        ],
        "gui": ["wxPython>=4.0.0", "Pillow>=7.0.0"],
        "cam": ["meerk40t_camera", "opencv-python-headless>=3.4.0.0"],
        "dxf": ["ezdxf>=0.14.0"],
        "camhead": ["meerk40t_camera", "opencv-python>=3.4.0.0"],
    },
)
