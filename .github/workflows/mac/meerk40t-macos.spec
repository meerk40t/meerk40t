# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['../../../mk40t.py'],
             pathex=['../../../build/meerk40t-import'],
             binaries = [],
             datas=[
               ('locale/es/LC_MESSAGES/meerk40t.mo', 'locale/es/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/it/LC_MESSAGES/meerk40t.mo', 'locale/it/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/de/LC_MESSAGES/meerk40t.mo', 'locale/de/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/zh/LC_MESSAGES/meerk40t.mo', 'locale/zh/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/fr/LC_MESSAGES/meerk40t.mo', 'locale/fr/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/hu/LC_MESSAGES/meerk40t.mo', 'locale/hu/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/pt_BR/LC_MESSAGES/meerk40t.mo', 'locale/pt_BR/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/pt_PT/LC_MESSAGES/meerk40t.mo', 'locale/pt_PT/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/ja/LC_MESSAGES/meerk40t.mo', 'locale/ja/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/nl/LC_MESSAGES/meerk40t.mo', 'locale/nl/LC_MESSAGES/meerk40t.mo', 'DATA'),
               ('locale/ru/LC_MESSAGES/meerk40t.mo', 'locale/ru/LC_MESSAGES/meerk40t.mo', 'DATA'),
             ],
             hiddenimports=['usb', 'wx._adv', 'wx._xml', 'barcodes', 'potrace'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

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
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='../../../meerk40t.icns')
