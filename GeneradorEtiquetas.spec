# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=collect_dynamic_libs('pyexpat') + \
             collect_dynamic_libs('PIL'),
    datas=[('data', 'data'), ('config', 'config')],
    hiddenimports=[
        'encodings', 'encodings.utf_8', 'encodings.cp1252', 'encodings.latin_1',
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        'barcode', 'barcode.writer', 'barcode.writer.ImageWriter',
        'reportlab', 'reportlab.pdfgen', 'reportlab.platypus',
        'qrcode', 'openpyxl', 'openpyxl.utils', 'pandas', 'numpy'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['main2'],
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
    name='GeneradorEtiquetas',
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
)