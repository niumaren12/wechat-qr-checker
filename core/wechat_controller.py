"""
微信扫一扫自动化控制器
通过uiautomator2控制手机微信：清缓存→扫一扫→选照片→抓链接→打开页面→截图
"""
import re
import subprocess
import time
import random
from pathlib import Path
from typing import Optional

import uiautomator2 as u2


class WeChatController:
    """微信扫一扫自动化控制器"""

    def __init__(self, config: dict):
        cfg = config["wechat"]
        dev_cfg = config["device"]

        self.scan_activity = cfg["scan_activity"]
        self.page_load_wait = cfg["page_load_wait"]
        self.delay_min = cfg["operation_delay_min"]
        self.delay_max = cfg["operation_delay_max"]

        # 连接设备
        serial = dev_cfg.get("serial")
        self.serial = serial
        self.d = u2.connect(serial) if serial else u2.connect()
        print(f"[设备] 已连接: {self.d.info.get('productName', 'Unknown')}")

    # ============================================================
    # 缓存清理
    # ============================================================

    def _adb_shell(self, cmd: str):
        """执行ADB shell命令，自动带上设备序列号"""
        if self.serial:
            return subprocess.run(
                f"adb -s {self.serial} shell {cmd}",
                shell=True, capture_output=True
            )
        else:
            return subprocess.run(
                f"adb shell {cmd}",
                shell=True, capture_output=True
            )

    def clear_cache_full(self):
        """会话开始：完整清缓存（不影响登录状态）"""
        print("[缓存] 完整清理...")

        # 1. 杀微信进程，清除内存中的扫一扫缓存
        self._adb_shell("am force-stop com.tencent.mm")
        time.sleep(1)

        # 2. 删外部WebView缓存
        self._adb_shell("rm -rf /sdcard/Android/data/com.tencent.mm/cache/*")

        # 3. 删X5内核缓存
        self._adb_shell("rm -rf /sdcard/Android/data/com.tencent.mm/files/xwalk_cache/*")

        print("[缓存] 清理完成")

    def clear_cache_light(self):
        """每张照片间：杀进程快速清内存缓存"""
        self.d.app_stop("com.tencent.mm")
        time.sleep(1)

    # ============================================================
    # 微信启动
    # ============================================================

    def start_wechat(self):
        """启动微信并等待就绪"""
        self.d.app_start("com.tencent.mm")
        time.sleep(3)
        self._random_delay()

    # ============================================================
    # 扫一扫流程
    # ============================================================

    def open_scanner(self):
        """直接启动扫一扫Activity"""
        self.d.app_start("com.tencent.mm", activity=self.scan_activity)
        time.sleep(1.5)
        self._random_delay()

    def click_album_button(self) -> bool:
        """点击扫一扫界面的"相册"按钮"""
        # 尝试多种定位方式
        selectors = [
            dict(text="相册"),
            dict(text="Album"),
            dict(description="相册"),
            dict(description="Album"),
        ]
        for sel in selectors:
            try:
                elem = self.d(**sel)
                if elem.exists(timeout=2):
                    elem.click()
                    time.sleep(0.8)
                    return True
            except Exception:
                continue

        # 兜底：右下角坐标（常见位置，需在真机确认）
        w, h = self.d.window_size()
        self.d.click(w * 0.85, h * 0.88)
        time.sleep(0.8)
        return True

    def select_photo_by_index(self, index: int) -> bool:
        """在系统文件选择器中选取第index张照片

        Android系统文件选择器UI因厂商而异，采用多重策略：
        1. 尝试定位图片列表中的第index个ImageView
        2. 如果相册视图是网格布局，计算行列坐标
        """
        # 策略1：尝试点击第一个可见的图片缩略图
        # 大多数选择器打开后默认显示最近的照片
        try:
            # 查找所有ImageView（照片缩略图）
            images = self.d.xpath('//android.widget.ImageView')
            if images.exists:
                # 跳过第一个（可能是返回按钮等），取第 index+1 个
                target_idx = index + 1
                img_list = images.all()
                if len(img_list) > target_idx:
                    img_list[target_idx].click()
                    time.sleep(1)
                    return True
        except Exception as e:
            print(f"[选择器] ImageView策略失败: {e}")

        # 策略2：网格坐标点击
        # 假设3列网格，第0张在左上角
        col = index % 3
        row = index // 3
        w, h = self.d.window_size()
        # 图片网格通常从屏幕上方1/4处开始
        start_y = h * 0.22
        cell_w = w / 3
        cell_h = cell_w  # 正方形缩略图
        x = cell_w * (col + 0.5)
        y = start_y + cell_h * (row + 0.5)
        self.d.click(x, y)
        time.sleep(1)
        return True

    def wait_for_qr_popup(self, timeout: float = 5.0) -> bool:
        """等待微信识别二维码并弹出结果弹窗"""
        # 弹窗中通常包含链接（含"http"字样）或"打开"按钮
        try:
            has_link = self.d(textContains="http").wait(timeout=timeout)
            if has_link:
                return True
        except Exception:
            pass
        # 有些二维码不含http（如小程序），用"打开"按钮判断
        try:
            has_open = self.d(text="打开").wait(timeout=timeout)
            return has_open
        except Exception:
            return False

    def get_popup_link(self) -> Optional[str]:
        """从识别结果弹窗中抓取链接文字"""
        # 方法1：通过XPath找包含http的文本元素
        try:
            elem = self.d.xpath('//*[contains(@text, "http")]')
            if elem.wait(timeout=2):
                el = elem.get()
                if el is not None:
                    text = el.attrib.get("text", "")
                    if text:
                        return text.strip()
        except Exception:
            pass

        # 方法2：dump UI层级，搜索所有文本节点中的URL
        try:
            xml = self.d.dump_hierarchy()
            urls = re.findall(r'text="(https?://[^"]+)"', xml)
            if urls:
                return urls[0]
        except Exception:
            pass

        # 方法3：直接读取弹窗中最大的文本块
        try:
            all_texts = self.d.xpath('//android.widget.TextView')
            if all_texts.exists:
                for tv in all_texts.all():
                    txt = tv.attrib.get("text", "")
                    if txt and ("http" in txt or "www" in txt or len(txt) > 20):
                        return txt.strip()
        except Exception:
            pass

        return None

    def click_open_button(self) -> bool:
        """点击弹窗中的"打开"按钮，在微信内置浏览器加载页面"""
        try:
            open_btn = self.d(text="打开")
            if open_btn.wait(timeout=3):
                open_btn.click()
                time.sleep(self.page_load_wait)
                self._random_delay()
                return True
        except Exception:
            pass
        return False

    def take_screenshot(self) -> bytes:
        """截取当前屏幕（PNG格式bytes）"""
        return self.d.screenshot(format="raw")

    # ============================================================
    # 工具方法
    # ============================================================

    def _random_delay(self):
        """随机延时，模拟人类操作速度"""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)

    def go_back(self, times: int = 1):
        """按返回键"""
        for _ in range(times):
            self.d.press("back")
            time.sleep(0.3)
