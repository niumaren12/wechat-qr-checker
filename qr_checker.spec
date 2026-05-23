# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 微信二维码扫描检查工具 Windows 打包"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集 uiautomator2 的数据文件
u2_datas = collect_data_files('uiautomator2')
u2_subs = collect_submodules('adbutils')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('wechat_ids.txt', '.'),
        ('templates/report.html', 'templates/'),
    ] + u2_datas,
    hiddenimports=[
        # PaddlePaddle 核心模块（完整列表）
        'paddle',
        'paddle.fluid',
        'paddle.fluid.core',
        'paddle.fluid.core_avx',
        'paddle.fluid.framework',
        'paddle.fluid.executor',
        'paddle.fluid.io',
        'paddle.fluid.layers',
        'paddle.fluid.optimizer',
        'paddle.fluid.param_attr',
        'paddle.fluid.initializer',
        'paddle.fluid.data_feeder',
        'paddle.fluid.unique_name',
        'paddle.fluid.dygraph',
        'paddle.fluid.dygraph.base',
        'paddle.fluid.dygraph.layer_object',
        'paddle.fluid.dygraph.tracer',
        'paddle.fluid.proto',
        'paddle.fluid.proto.framework_pb2',
        'paddle.base',
        'paddle.base.core',
        'paddle.base.framework',
        'paddle.base.executor',
        'paddle.base.io',
        'paddle.nn',
        'paddle.nn.functional',
        'paddle.nn.layer',
        'paddle.nn.initializer',
        'paddle.tensor',
        'paddle.framework',
        'paddle.optimizer',
        'paddle.incubate',
        'paddle.distributed',
        'paddle.sysconfig',
        'paddle.device',
        'paddle.data',
        'paddle.jit',
        'paddle.static',
        'paddle.autograd',
        'paddle._C',
        'paddle._internal_ops',
        'paddle.libs',
        'paddle.ops',
        'paddle.py_func',

        # PaddleOCR
        'paddleocr',
        'paddleocr.paddleocr',
        'paddleocr.ppocr',
        'paddleocr.ppocr.utils',
        'paddleocr.ppocr.data',
        'paddleocr.ppocr.modeling',
        'paddleocr.ppocr.postprocess',
        'paddleocr.pipeline',
        'paddleocr.tools',
        'ppocr',
        'ppocr.utils',
        'ppocr.data',
        'ppocr.modeling',
        'ppocr.postprocess',
        'paddlex',
        'paddlex.pipelines',

        # OpenCV / NumPy
        'cv2', 'cv2.cv2',
        'numpy', 'numpy.core', 'numpy.core._methods',
        'numpy.lib', 'numpy.lib.format', 'numpy.random',
        'numpy._typing',

        # PIL
        'PIL', 'PIL.Image', 'PIL._imaging', 'PIL.ImageDraw',

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
        'ctypes', 'ctypes.util', 'logging', 'logging.handlers',
    ] + u2_subs,
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
