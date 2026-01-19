# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# wxPython wheels vendor critical shared libraries in-package (typically in
# wx/.libs). If these are not collected, importing wx may fail on systems that
# do not have matching system-wide wx libraries installed.
wx_datas = collect_data_files("wx")
wx_binaries = collect_dynamic_libs("wx")

a = Analysis(
    ["../../../meerk40t.py"],
    pathex=["../../../build/meerk40t-import"],
    binaries=wx_binaries,
    datas=wx_datas,
    hiddenimports=[
        "usb",
        "barcodes",
        "potrace",
        "wx._core",
        "wx._adv",
        "wx._xml",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='MeerK40t',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False, icon='../../../meerk40t.ico')
