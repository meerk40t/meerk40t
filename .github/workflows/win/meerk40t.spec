# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['../../../mk40t.py'],
             pathex=['../../../build/meerk40t-import'],
             binaries = [
                ('./libusb0.dll', '.'),
             ],
             datas=[],
             hiddenimports=['usb', 'wx._adv', 'wx._xml'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
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
