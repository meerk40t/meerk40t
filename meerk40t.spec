# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['meerk40t.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Utenti\\EtaBeta\\Desktop\\Meerk40tBox\\GitMeerk40t\\meerk40t\\.github\\workflows\\win\\libusb-1.0.dll', '.'), ('D:\\Utenti\\EtaBeta\\Desktop\\Meerk40tBox\\GitMeerk40t\\meerk40t\\locale', 'locale')],
    hiddenimports=['wx.richtext'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='meerk40t',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\Utenti\\EtaBeta\\Desktop\\Meerk40tBox\\GitMeerk40t\\meerk40t\\meerk40t.ico'],
)
