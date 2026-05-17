# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 微信二维码扫描检查工具 Windows 打包"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('wechat_ids.txt', '.'),
        ('templates/report.html', 'templates/'),
    ],
    hiddenimports=[
        # PaddleOCR
        'paddleocr', 'paddleocr.pipeline', 'paddleocr.ppocr',
        'paddlex', 'paddlex.pipelines',
        'paddle', 'paddle.fluid', 'paddle.base', 'paddle.base.core',
        'ppocr',

        # OpenCV / NumPy
        'cv2', 'cv2.cv2',
        'numpy', 'numpy.core', 'numpy.core._methods',
        'numpy.lib', 'numpy.lib.format', 'numpy.random',

        # PIL
        'PIL', 'PIL.Image', 'PIL._imaging',

        # Jinja2
        'jinja2', 'jinja2.ext',

        # httpx + async support
        'httpx', 'httpcore', 'httpcore._async', 'h11', 'anyio',

        # yaml
        'yaml',

        # uiautomator2 + 依赖
        'uiautomator2', 'adbutils', 'adbutils.adb', 'adbutils.shell',
        'retry', 'lxml', 'lxml.etree', 'urllib3', 'requests',
        'cryptography',

        # 标准库
        'asyncio', 'webbrowser', 'winsound', 'concurrent.futures',
        'ctypes', 'ctypes.util',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'pytest'],
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
    upx=False,                         # 禁用UPX，避免损坏PaddlePaddle DLL
    console=True,                      # 显示控制台窗口
    disable_windowed_traceback=False,  # 显示Python错误
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
