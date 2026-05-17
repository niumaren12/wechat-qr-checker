# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for 微信二维码扫描检查工具
# Windows打包: pyinstaller qr_checker.spec

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('wechat_ids.txt', '.'),
        ('templates/report.html', 'templates/'),
    ],
    hiddenimports=[
        'paddleocr',
        'paddle',
        'cv2',
        'numpy',
        'PIL',
        'jinja2',
        'httpx',
        'yaml',
        'uiautomator2',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='QRChecker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
