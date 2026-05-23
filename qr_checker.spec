# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 微信二维码扫描检查工具 Windows 打包"""
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# 收集 PaddlePaddle 和 PaddleOCR 的所有内容
paddle_datas, paddle_binaries, paddle_hidden = collect_all('paddle')
paddleocr_datas, paddleocr_binaries, paddleocr_hidden = collect_all('paddleocr')

# 收集 uiautomator2 的数据文件
u2_datas = collect_data_files('uiautomator2')
u2_subs = collect_submodules('adbutils')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=paddle_binaries + paddleocr_binaries,
    datas=[
        ('wechat_ids.txt', '.'),
        ('templates/report.html', 'templates/'),
    ] + u2_datas + paddle_datas + paddleocr_datas,
    hiddenimports=[
        # 标准库
        'asyncio', 'webbrowser', 'winsound', 'concurrent.futures',
        'ctypes', 'ctypes.util', 'logging', 'logging.handlers',

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

        # NumPy
        'numpy', 'numpy.core', 'numpy.core._methods',
        'numpy.lib', 'numpy.lib.format', 'numpy.random',

        # PIL
        'PIL', 'PIL.Image', 'PIL._imaging',
    ] + u2_subs + paddle_hidden + paddleocr_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'paddle.fluid.tests', 'paddle.tests', 'unittest', 'pytest',
    ],
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
