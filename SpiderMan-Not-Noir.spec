# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('assets/thwip.png', 'assets'), ('ffnn_classifier/model.pt', 'ffnn_classifier'), ('hand_landmarker.task', '.'), ('pose_landmarker.task', '.'), ('data', 'data')]
datas += collect_data_files('mediapipe')


a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['mediapipe', 'cv2', 'torch'],
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
    [],
    exclude_binaries=True,
    name='SpiderMan-Not-Noir',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpiderMan-Not-Noir',
)
app = BUNDLE(
    coll,
    name='SpiderMan-Not-Noir.app',
    icon=None,
    bundle_identifier=None,
)
