@echo off
chcp 65001 >nul
echo ============================================================
echo   微信二维码扫描检查工具 - Windows 打包脚本
echo ============================================================
echo.

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 安装PyInstaller
echo [2/3] 安装PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo [错误] PyInstaller安装失败
    pause
    exit /b 1
)

:: 打包
echo [3/3] 打包...
pyinstaller qr_checker.spec
if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   打包完成!
echo   输出目录: dist\QRChecker.exe
echo ============================================================
echo.
echo 注意:
echo   1. 手机需开启USB调试并连接电脑
echo   2. 首次运行PaddleOCR会自动下载模型(~15MB)
echo   3. 建议先开scrcpy --no-control 做实时监控
echo.
pause
