# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../../src/typist/main.py'],
    pathex=['../../src'],
    binaries=[],
    datas=[
        ('../../udev/*.rules', 'udev'),
    ],
    hiddenimports=[
        'typist',
        'typist.config',
        'typist.device',
        'typist.audio_recorder',
        'typist.transcriber',
        'typist.keyboard_emulator',
        'pynput',
        'pynput.keyboard',
        'hid',
        'sounddevice',
        'httpx',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='typist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
