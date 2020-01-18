# -*- mode: python -*-

block_cipher = None


a = Analysis(['MeerK40t.py'],
             pathex=['C:\\Users\\Tat\\PycharmProjects\\meerk40t'],
             binaries = [
                ('C:\\Windows\\System32\\libusb0.dll', '.'),
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
          runtime_tmpdir=None,
          console=False )
