from setuptools import setup
setup(
    install_requires=[
        "pyusb>=1.0.0",
    ],
    extras_require={
        'all': ['wxPython>=4.0.0', "Pillow>=7.0.0", "meerk40t_camera", "opencv-python-headless>=3.4.0.0", "ezdxf>=0.14.0"],
        'gui': ['wxPython>=4.0.0', "Pillow>=7.0.0"],
        'cam': ["meerk40t_camera", "opencv-python-headless>=3.4.0.0"],
        'dxf': ["ezdxf>=0.14.0"],
        'camhead': ["meerk40t_camera", "opencv-python>=3.4.0.0"],
    }
)