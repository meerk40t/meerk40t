# -*- mode: python ; coding: utf-8 -*-

import os

# Dynamically generate locale data
def get_locale_data():
    locale_base = './locale'
    datas = []
    if os.path.exists(locale_base):
        for lang in os.listdir(locale_base):
            mo_path = os.path.join(locale_base, lang, 'LC_MESSAGES', 'meerk40t.mo')
            if os.path.exists(mo_path):
                datas.append((f'locale/{lang}/LC_MESSAGES/meerk40t.mo', f'locale/{lang}/LC_MESSAGES/meerk40t.mo', 'DATA'))
    return datas

block_cipher = None


a = Analysis(['../../../mk40t.py'],
             pathex=['../../../build/meerk40t-import'],
             binaries = [
                ('./libusb0.dll', '.'),
             ],
             datas=[],
             hiddenimports=['usb', 'wx._adv', 'wx._xml', 'barcodes'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Add locale data
a.datas += get_locale_data()


pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
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
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , version='file_version.txt', icon='../../../meerk40t.ico')
