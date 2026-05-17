#!/usr/bin/env python3
"""
微信二维码扫描检查工具 - 主入口
通过uiautomator2控制手机微信，扫描相册二维码照片，
在微信内置浏览器中打开链接并检测页面状态。
"""
import sys
import time
import asyncio
import argparse
from pathlib import Path

import yaml

from core.wechat_controller import WeChatController
from core.page_checker import PageChecker, CheckResult
from core.report_generator import ReportGenerator
from core.notifier import Notifier


def load_config(config_path: str) -> dict:
    """加载YAML配置文件"""
    path = Path(config_path)
    if not path.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_wechat_ids(filepath: str) -> list[str]:
    """加载微信号列表（跳过注释和空行）"""
    path = Path(filepath)
    if not path.exists():
        print(f"[错误] 微信号文件不存在: {filepath}")
        sys.exit(1)
    ids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    return ids


def print_summary(results: list[dict], stats: dict):
    """打印控制台汇总"""
    print()
    print("=" * 60)
    print("  扫描完成")
    print("=" * 60)
    print(f"  总数: {stats['total']}  |  "
          f"正常: {stats['normal']}  |  "
          f"警告: {stats['dialog'] + stats['short']}  |  "
          f"异常: {stats['blocked'] + stats['blank'] + stats['unknown']}  |  "
          f"无码: {stats['no_qr']}")
    print()

    anomalies = [r for r in results if r.get("status") not in ("normal", "no_qr")]
    if anomalies:
        print(f"!! 发现 {len(anomalies)} 个异常:")
        for r in anomalies:
            status_cn = {
                "blocked": "封禁", "dialog": "弹窗",
                "blank": "空白", "short": "极少字",
                "unknown": "未知"
            }.get(r.get("status"), r.get("status", "?"))
            print(f"   [{status_cn}] {r['wechat_id']}  {r.get('link', '无')[:80]}")
    else:
        print("  所有链接正常 ✓")


async def main():
    parser = argparse.ArgumentParser(description="微信二维码扫描检查工具")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--wechat-ids", default="wechat_ids.txt", help="微信号列表文件")
    parser.add_argument("--dry-run", action="store_true", help="仅加载配置，不实际扫描")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    wechat_ids = load_wechat_ids(args.wechat_ids)
    print(f"[配置] 已加载 {len(wechat_ids)} 个微信号")

    if args.dry_run:
        print("[DRY RUN] 配置检查完成")
        return

    # ============================================================
    # Phase 1: 初始化
    # ============================================================
    print("\n" + "=" * 60)
    print("  Phase 1: 初始化")
    print("=" * 60)

    controller = WeChatController(config)
    checker = PageChecker(config)
    reporter = ReportGenerator(config)
    notifier = Notifier(config)

    # ============================================================
    # Phase 2: 清缓存 + 扫描
    # ============================================================
    print("\n" + "=" * 60)
    print("  Phase 2: 开始扫描")
    print("=" * 60)

    # 会话开始：完整清缓存
    controller.clear_cache_full()
    controller.start_wechat()

    results = []
    for i, wechat_id in enumerate(wechat_ids):
        print(f"\n[{i+1}/{len(wechat_ids)}] 扫描: {wechat_id}")

        result = {
            "wechat_id": wechat_id,
            "link": None,
            "status": "no_qr",
            "detail": "",
            "ocr_text": "",
            "text_length": 0,
            "screenshot_bytes": None
        }

        try:
            # 1. 打开扫一扫
            controller.open_scanner()

            # 2. 点相册
            controller.click_album_button()

            # 3. 选照片
            controller.select_photo_by_index(i)

            # 4. 等待识别
            if not controller.wait_for_qr_popup(timeout=6):
                result["detail"] = "未识别到二维码"
                print(f"  ⚠ 未识别到二维码")
                results.append(result)
                controller.clear_cache_light()
                controller.start_wechat()
                continue

            # 5. 抓链接
            link = controller.get_popup_link()
            result["link"] = link
            print(f"  链接: {link[:80] if link else '(未能读取)'}")

            # 6. 点打开
            if not controller.click_open_button():
                result["detail"] = "无法点击'打开'按钮"
                result["status"] = "unknown"
                results.append(result)
                controller.clear_cache_light()
                controller.start_wechat()
                continue

            # 7. 截图 + 检测
            screenshot = controller.take_screenshot()
            # 截图存盘
            ss_dir = Path("./output/screenshots")
            ss_dir.mkdir(parents=True, exist_ok=True)
            ss_path = ss_dir / f"{wechat_id}.png"
            with open(ss_path, "wb") as f:
                f.write(screenshot)
            result["screenshot_bytes"] = screenshot
            check_result: CheckResult = checker.check(screenshot)
            result["status"] = check_result.status.value
            result["detail"] = check_result.detail
            result["ocr_text"] = check_result.text
            result["text_length"] = check_result.text_length

            status_cn = {
                "normal": "✓ 正常", "blocked": "⛔ 已封禁", "dialog": "⚠ 弹窗",
                "blank": "🈳 空白页", "short": "📝 极少文字", "unknown": "❓ 未知"
            }.get(check_result.status.value, check_result.status.value)
            print(f"  结果: {status_cn}")

        except Exception as e:
            # 设备断连或其他异常，记录并继续
            result["status"] = "unknown"
            result["detail"] = f"扫描过程异常: {e}"
            print(f"  ❌ 异常: {e}")

        results.append(result)

        # 8. 每张照片间轻量清缓存
        try:
            controller.clear_cache_light()
            controller.start_wechat()
        except Exception:
            print("  ⚠ 缓存清理失败，尝试继续...")
            time.sleep(2)

    # ============================================================
    # Phase 3: 生成报告
    # ============================================================
    print("\n" + "=" * 60)
    print("  Phase 3: 生成报告")
    print("=" * 60)

    stats = reporter.compute_stats(results)
    report_path = reporter.generate(results, stats)
    print(f"[报告] {report_path}")

    # ============================================================
    # Phase 4: 通知
    # ============================================================
    print("\n" + "=" * 60)
    print("  Phase 4: 异常通知")
    print("=" * 60)

    await notifier.notify_anomalies(results)

    # ============================================================
    # 总览
    # ============================================================
    print_summary(results, stats)

    # 打开报告
    import webbrowser
    webbrowser.open(f"file:///{report_path}")

    print(f"\n报告已打开: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
