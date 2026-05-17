# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 微信二维码扫描检查工具"""
from PyInstaller.utils.hooks import (
    collect_data_files, collect_all, collect_submodules,
    collect_delvewheel_libs_directory,
)

# ============================================================
# 收集动态模块和数据文件（处理类型兼容）
# ============================================================

# PaddleOCR（paddle是paddleocr的依赖，只collect paddleocr即可）
try:
    paddleocr_datas, paddleocr_bins, paddleocr_hidden = collect_all('paddleocr')
except Exception:
    paddleocr_datas, paddleocr_bins, paddleocr_hidden = [], [], []

# uiautomator2 的 APK/atx-agent 等数据文件
u2_datas = collect_data_files('uiautomator2')
# adbutils 子模块
try:
    u2_subs = collect_submodules('adbutils')
except Exception:
    u2_subs = []

# opencv-python 的 delvewheel DLL
cv2_bins = list(collect_delvewheel_libs_directory('cv2'))

# ============================================================
# 合并 data 和 binaries
# ============================================================

all_datas = [('wechat_ids.txt', '.'), ('templates/report.html', 'templates/')]
all_datas.extend(u2_datas)
all_datas.extend(paddleocr_datas)

all_binaries = list(cv2_bins)
all_binaries.extend(paddleocr_bins)

# ============================================================
# Analysis
# ============================================================

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=[
        # PaddleOCR / PaddlePaddle
        'paddleocr', 'paddleocr.pipeline', 'paddleocr.ppocr',
        'paddlex', 'paddlex.pipelines',
        'paddle', 'paddle.fluid', 'paddle.fluid.core',
        'paddle.incubate', 'paddle.distributed', 'paddle.sysconfig',
        'paddle.base', 'paddle.base.core',
        'ppocr',

        # OpenCV / NumPy
        'cv2', 'cv2.cv2',
        'numpy', 'numpy.core', 'numpy.core._methods',
        'numpy.lib', 'numpy.lib.format', 'numpy.random',

        # PIL
        'PIL', 'PIL.Image', 'PIL._imaging', 'PIL.ImageDraw',

        # Jinja2
        'jinja2', 'jinja2.ext',

        # httpx / httpcore
        'httpx', 'httpcore', 'h11', 'anyio',

        # yaml
        'yaml',

        # uiautomator2 / adbutils 及其依赖
        'uiautomator2', 'adbutils', 'adbutils.shell', 'adbutils.adb',
        'retry', 'lxml', 'lxml.etree', 'urllib3', 'requests',
        'cryptography',

        # 标准库
        'asyncio', 'webbrowser', 'winsound', 'concurrent.futures',
    ] + paddleocr_hidden + u2_subs,
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
    upx=False,                          # 禁用UPX，避免压缩损坏PaddlePaddle DLL
    console=True,
    disable_windowed_traceback=False,   # 让错误信息可见
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
