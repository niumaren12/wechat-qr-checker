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
import traceback
from pathlib import Path

import yaml

from core.logger import logger
from core.wechat_controller import WeChatController
from core.page_checker import PageChecker, CheckResult
from core.report_generator import ReportGenerator
from core.notifier import Notifier


def load_config(config_path: str) -> dict:
    """加载YAML配置文件"""
    path = Path(config_path)
    if not path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        logger.info(f"配置加载成功: {config_path}")
        return config


def load_wechat_ids(filepath: str) -> list[str]:
    """加载微信号列表（跳过注释和空行）"""
    path = Path(filepath)
    if not path.exists():
        logger.error(f"微信号文件不存在: {filepath}")
        sys.exit(1)
    ids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    logger.info(f"已加载 {len(ids)} 个微信号")
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

    logger.info("=" * 50)
    logger.info("微信二维码扫描检查工具启动")
    logger.info("=" * 50)

    # 加载配置
    config = load_config(args.config)
    wechat_ids = load_wechat_ids(args.wechat_ids)

    if args.dry_run:
        logger.info("[DRY RUN] 配置检查完成")
        return

    # ============================================================
    # Phase 1: 初始化
    # ============================================================
    logger.info("Phase 1: 初始化")

    controller = WeChatController(config)
    checker = PageChecker(config)
    reporter = ReportGenerator(config)
    notifier = Notifier(config)

    # ============================================================
    # Phase 2: 清缓存 + 扫描
    # ============================================================
    logger.info("Phase 2: 开始扫描")

    # 会话开始：完整清缓存
    controller.clear_cache_full()
    controller.start_wechat()

    results = []
    for i, wechat_id in enumerate(wechat_ids):
        logger.info(f"[{i+1}/{len(wechat_ids)}] 扫描: {wechat_id}")

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
                logger.warning(f"未识别到二维码: {wechat_id}")
                results.append(result)
                controller.clear_cache_light()
                controller.start_wechat()
                continue

            # 5. 抓链接
            link = controller.get_popup_link()
            result["link"] = link
            logger.info(f"链接: {link[:80] if link else '(未能读取)'}")

            # 6. 点打开
            if not controller.click_open_button():
                result["detail"] = "无法点击'打开'按钮"
                result["status"] = "unknown"
                logger.warning(f"无法点击打开按钮: {wechat_id}")
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

            logger.info(f"检测结果: {check_result.status.value} - {check_result.detail}")

        except Exception as e:
            # 设备断连或其他异常，记录并继续
            result["status"] = "unknown"
            result["detail"] = f"扫描过程异常: {e}"
            logger.error(f"扫描异常 [{wechat_id}]: {e}\n{traceback.format_exc()}")

        results.append(result)

        # 8. 每张照片间轻量清缓存
        try:
            controller.clear_cache_light()
            controller.start_wechat()
        except Exception as e:
            logger.warning(f"缓存清理失败: {e}")
            time.sleep(2)

    # ============================================================
    # Phase 3: 生成报告
    # ============================================================
    logger.info("Phase 3: 生成报告")

    stats = reporter.compute_stats(results)
    report_path = reporter.generate(results, stats)
    logger.info(f"报告已生成: {report_path}")

    # ============================================================
    # Phase 4: 通知
    # ============================================================
    logger.info("Phase 4: 异常通知")

    await notifier.notify_anomalies(results)

    # ============================================================
    # 总览
    # ============================================================
    print_summary(results, stats)
    logger.info(f"扫描完成: 总数={stats['total']}, 正常={stats['normal']}, 异常={stats['anomaly_count']}")

    # 打开报告
    import webbrowser
    webbrowser.open(f"file:///{report_path}")

    logger.info(f"报告已打开: {report_path}")


def run():
    """入口函数，捕获所有异常"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断")
    except SystemExit:
        raise
    except Exception as e:
        logger.critical(f"程序崩溃: {e}\n{traceback.format_exc()}")
        print("\n" + "=" * 60)
        print("  程序发生错误，请查看日志文件")
        print("  日志位置: logs/qr_checker.log")
        print("=" * 60)
        print(f"\n错误信息: {e}")
        input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    run()
