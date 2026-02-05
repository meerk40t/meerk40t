# -*- mode: python ; coding: utf-8 -*-
import os
import importlib.util

block_cipher = None

# Get the directory of the installed wxPython package without importing it
# This avoids ImportError due to missing system libraries on the build agent
spec = importlib.util.find_spec('wx')
if spec is None:
    raise ImportError("wxPython module not found")
wx_package_path = spec.submodule_search_locations[0]

a = Analysis(
    ["../../../mk40t.py"],
    pathex=["../../../build/meerk40t-import"],
    binaries=[],
    # Copy the entire wx package as data to preserve structure and avoid PyInstaller interference
    datas=[(wx_package_path, "wx")],
    hiddenimports=[
        "usb",
        "barcodes",
        "potrace",
        # Add common wx dependencies that might be missed since we exclude wx from analysis
        "PIL",
        "numpy",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["wx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,
)

a.datas += [('locale/es/LC_MESSAGES/meerk40t.mo', 'locale/es/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/it/LC_MESSAGES/meerk40t.mo', 'locale/it/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/de/LC_MESSAGES/meerk40t.mo', 'locale/de/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/zh/LC_MESSAGES/meerk40t.mo', 'locale/zh/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/fr/LC_MESSAGES/meerk40t.mo', 'locale/fr/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/hu/LC_MESSAGES/meerk40t.mo', 'locale/hu/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/pt_BR/LC_MESSAGES/meerk40t.mo', 'locale/pt_BR/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/pt_PT/LC_MESSAGES/meerk40t.mo', 'locale/pt_PT/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/ja/LC_MESSAGES/meerk40t.mo', 'locale/ja/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/nl/LC_MESSAGES/meerk40t.mo', 'locale/nl/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/ru/LC_MESSAGES/meerk40t.mo', 'locale/ru/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/pl/LC_MESSAGES/meerk40t.mo', 'locale/pl/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/tr/LC_MESSAGES/meerk40t.mo', 'locale/tr/LC_MESSAGES/meerk40t.mo', 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Onedir EXE: only pyz + scripts.  binaries / zipfiles / datas are handed
# exclusively to COLLECT below.  Passing them here as positional args
# (the onefile pattern) causes PyInstaller to append a PKG archive to the
# bootloader; combined with exclude_binaries=True that archive is missing
# libpython, which crashes the bootloader at runtime.
exe = EXE(pyz,
          a.scripts,
          name='MeerK40t',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          exclude_binaries=True,
          console=False, icon='../../../meerk40t.ico')

# onedir: preserves wx/.libs/ directory layout so $ORIGIN RPATHs resolve
# correctly inside the AppImage.  linuxdeploy then patches any remaining
# missing shared-library dependencies.
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='MeerK40t')
