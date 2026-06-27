# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Spider-Man: Not Noir

Build with: pyinstaller spiderman_game.spec
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect MediaPipe data files
mediapipe_datas = collect_data_files('mediapipe')

a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Game assets
        ('assets/thwip.png', 'assets'),
        
        # FFNN model
        ('ffnn_classifier/model.pt', 'ffnn_classifier'),
        
        # MediaPipe task files
        ('hand_landmarker.task', '.'),
        ('pose_landmarker.task', '.'),
        ('holistic_landmarker.task', '.'),
        
        # Scores data directory (create empty if needed)
        ('data', 'data'),
    ] + mediapipe_datas,
    hiddenimports=[
        'mediapipe',
        'mediapipe.python',
        'mediapipe.python.solutions',
        'cv2',
        'numpy',
        'torch',
        'PIL',
    ] + collect_submodules('mediapipe'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=True,  # For macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one
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

# For macOS app bundle
app = BUNDLE(
    coll,
    name='SpiderMan-Not-Noir.app',
    icon=None,  # Add .icns icon path if you have one
    bundle_identifier='com.spiderman.notvoir',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'NSCameraUsageDescription': 'Spider-Man: Not Noir requires camera access for hand gesture detection.',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
