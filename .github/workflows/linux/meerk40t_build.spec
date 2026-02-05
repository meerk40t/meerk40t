# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# wxPython wheels vendor critical shared libraries in-package (typically in
# wx/.libs). Collect all wx modules, data, and binaries to avoid partial
# imports when running in AppImage.
wx_datas, wx_binaries, wx_hidden = collect_all("wx")

a = Analysis(
    ["../../../mk40t.py"],
    pathex=["../../../build/meerk40t-import"],
    binaries=wx_binaries,
    datas=wx_datas,
    hiddenimports=wx_hidden + [
        "usb",
        "barcodes",
        "potrace",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,
)

# FIX: Remove wx modules from the PYZ archive (a.pure) to force loading from source/filesystem.
# This bypasses the frozen importer (pyimod02) for wx, preventing the 'partially initialized module' error.
# The files are already in 'wx_datas' (from collect_all), so they will be present in the dist directory.
a.pure = [x for x in a.pure if not x[0].startswith("wx.")]

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
