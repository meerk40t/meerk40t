# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['../../../mk40t.py'],
             pathex=['D:/a/meerk40t/meerk40t/build/meerk40t-import'],
             binaries = [
                ('D:/a/meerk40t/meerk40t/.github/workflows/win/libusb0.dll', '.'),
                ('D:/a/meerk40t/meerk40t/.github/workflows/win/CH341DLL.DLL', '.'),
             ],
             datas=[],
             hiddenimports=['usb'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
a.datas += [('locale/es/LC_MESSAGES/meerk40t.mo', '../../../locale/es/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/it/LC_MESSAGES/meerk40t.mo', '../../../locale/it/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/de/LC_MESSAGES/meerk40t.mo', '../../../locale/de/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/zh/LC_MESSAGES/meerk40t.mo', '../../../locale/zh/LC_MESSAGES/meerk40t.mo', 'DATA')]
a.datas += [('locale/fr/LC_MESSAGES/meerk40t.mo', '../../../locale/fr/LC_MESSAGES/meerk40t.mo', 'DATA')]

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
