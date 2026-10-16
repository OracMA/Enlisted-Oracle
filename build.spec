# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# === АВТОСБОР chrome_lens_py ===
cl_datas, cl_binaries, cl_hiddenimports = collect_all('chrome_lens_py')

datas = [
    ('enlisted_players_full.csv', '.'),
    ('limits.csv', '.'),
    ('scan_done.wav', '.'),
    ('compare_done.wav', '.'),
    ('scan_empty_1.wav', '.'),
    ('scan_empty_2.wav', '.'),
    ('scan_empty_3.wav', '.'),
    ('cat.jpeg', '.'),
    ('cat.png', '.'),
    ('icon.ico', '.'),
    ('icon_data.py', '.'),
]
datas = [(src, dst) for src, dst in datas if os.path.exists(src)]
datas += cl_datas

hiddenimports = [
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'rapidfuzz',
    'jellyfish',
    'wcwidth',
    'qdarkstyle',
    'psutil',
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'numpy',
    'main',
    'utils',
    'fuzzy_search',
    'output',
    'nick_matcher',
    'analyzer',
    'compare',
    'lang',
    'icon_data',
] + cl_hiddenimports

excludes = [
    'tkinter', '_tkinter',
    'matplotlib', 'scipy', 'pandas',
    'IPython', 'notebook', 'jupyter', 'pytest',
    'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineQuick',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets',
    'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.Qt3DAnimation',
    'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtTest', 'PyQt6.QtXml',
    'PyQt6.QtSql', 'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
    'PyQt6.QtPositioning', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
]

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=cl_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EnlistedOracle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EnlistedOracle',
)