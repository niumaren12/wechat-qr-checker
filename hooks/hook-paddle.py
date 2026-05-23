# PyInstaller hook for paddle
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集 paddle 的所有内容
datas, binaries, hiddenimports = collect_all('paddle')
