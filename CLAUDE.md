# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

微信二维码扫描检查工具 — 通过 uiautomator2 控制 Android 手机微信，批量扫描相册中的二维码照片，在微信内置浏览器中打开链接并检测页面状态（封禁、弹窗、空白等）。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行扫描（需连接 Android 手机，开启 USB 调试）
python main.py --config config.yaml --wechat-ids wechat_ids.txt

# 仅检查配置，不实际扫描
python main.py --dry-run

# Windows 打包为 exe
build.bat
# 或手动执行
pyinstaller qr_checker.spec
```

## 架构

```
main.py                 # 入口，编排 4 阶段流程：初始化 → 扫描 → 报告 → 通知

core/
├── wechat_controller.py   # 手机控制：清缓存、启动扫一扫、选照片、抓链接、截图
├── page_checker.py        # 页面检测：PaddleOCR + 像素分析，判断页面状态
├── report_generator.py    # HTML 报告生成，截图嵌入 base64
└── notifier.py            # 异常通知：蜂鸣告警 + Telegram Bot

templates/report.html      # Jinja2 报告模板
config.yaml               # 运行配置（敏感，不提交）
config.example.yaml       # 配置模板
```

## 核心模块职责

### WeChatController
- 通过 uiautomator2 连接 Android 设备
- 清理微信缓存（完整清理 / 轻量清理）
- 控制扫一扫流程：打开 → 选相册 → 选照片 → 等待识别 → 点击打开
- 截取屏幕

### PageChecker
- PaddleOCR 提取页面文字
- 按优先级检测页面状态：
  1. `blocked` — 命中封禁关键词（"已停止访问"、"风险提示"等）
  2. `dialog` — 弹窗遮罩（暗像素占比 + 弹窗关键词）
  3. `blank` — 空白页（像素方差极低 / 白像素占比极高）
  4. `short` — 文字极少（< min_text_length）
  5. `normal` — 正常

### ReportGenerator
- Jinja2 渲染自包含 HTML 报告
- 截图压缩为 JPEG base64 嵌入
- 统计汇总

### Notifier
- 系统蜂鸣告警（Windows/macOS/Linux）
- Telegram Bot 通知（汇总或逐条）

## 配置说明

复制 `config.example.yaml` 为 `config.yaml`：

```yaml
device:
  serial: null           # Android 设备序列号，null=自动检测

wechat:
  page_load_wait: 3      # 页面加载等待秒数
  operation_delay_min/max: 1.0/2.0  # 操作间随机延时

detection:
  min_text_length: 10    # 文字少于此数量视为异常
  blank_variance_threshold: 5.0
  blocked_keywords: [...] # 封禁页关键词
  dialog_keywords: [...]  # 弹窗关键词

telegram:
  enabled: false
  bot_token: "..."
  chat_id: "..."
```

## 环境要求

- Python 3.11+
- Android 手机开启 USB 调试
- 微信已登录
- 首次运行 PaddleOCR 会下载模型 (~15MB)

## CI/CD

GitHub Actions 自动构建 Windows exe：推送到 main 分支触发，产物为 `QRChecker-Windows`。

## 注意事项

- `config.yaml` 含 Telegram Bot Token，已在 .gitignore 中
- 输出目录 `output/` 不提交
- Windows 打包禁用 UPX，避免损坏 PaddlePaddle DLL
