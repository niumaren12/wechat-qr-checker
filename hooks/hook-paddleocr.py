# PyInstaller hook for paddleocr
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集 paddleocr 的所有内容
datas, binaries, hiddenimports = collect_all('paddleocr')
