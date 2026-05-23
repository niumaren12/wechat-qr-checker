"""
页面内容检测器
通过截图+PaddleOCR+像素分析，检测微信内置浏览器中的页面状态
"""
import re
import io
from typing import NamedTuple, Optional
from enum import Enum

import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

from core.logger import logger


class PageStatus(str, Enum):
    NORMAL = "normal"       # 页面正常
    BLOCKED = "blocked"     # 微信封禁页
    DIALOG = "dialog"       # 弹窗提示
    BLANK = "blank"         # 页面空白
    SHORT = "short"         # 文字极少 (<10字)
    NO_QR = "no_qr"         # 未识别到二维码
    UNKNOWN = "unknown"     # 未知异常


class CheckResult(NamedTuple):
    status: PageStatus
    text: str               # OCR识别到的完整文字
    text_length: int        # 有效字符数
    detail: str             # 详细说明


class PageChecker:
    """页面内容检测器"""

    def __init__(self, config: dict):
        cfg = config["detection"]
        self.min_text_length = cfg["min_text_length"]
        self.blank_variance_threshold = cfg["blank_variance_threshold"]
        self.modal_dark_ratio = cfg["modal_dark_pixel_ratio"]
        self.blocked_keywords = cfg["blocked_keywords"]
        self.dialog_keywords = cfg["dialog_keywords"]

        # 初始化PaddleOCR（中文，不使用GPU）
        logger.info("初始化 PaddleOCR（首次运行需下载模型，约15MB）...")
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)
            logger.info("PaddleOCR 初始化完成")
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {e}")
            raise RuntimeError(
                f"PaddleOCR初始化失败: {e}\n"
                "请检查网络连接（首次运行需下载模型），"
                "或手动下载模型放到 ~/.paddleocr/ 目录"
            )

    def check(self, screenshot_bytes: bytes) -> CheckResult:
        """检测页面截图，返回检测结果"""
        logger.debug("开始检测页面截图")
        # 将bytes转为numpy数组
        img = self._bytes_to_image(screenshot_bytes)
        if img is None:
            logger.error("截图数据无效")
            return CheckResult(PageStatus.UNKNOWN, "", 0, "截图数据无效")

        ocr_text = self._ocr_extract(img)
        clean_text = self._clean_text(ocr_text)
        text_len = len(clean_text)

        logger.debug(f"OCR识别文字数: {text_len}")

        # 按优先级逐项检测

        # 1. 微信封禁页
        blocked, blocked_detail = self._check_blocked(ocr_text)
        if blocked:
            logger.warning(f"检测到封禁页: {blocked_detail}")
            return CheckResult(PageStatus.BLOCKED, ocr_text, text_len, blocked_detail)

        # 2. 弹窗提示（像素分析 + OCR关键词）
        dialog, dialog_detail = self._check_dialog(img, ocr_text)
        if dialog:
            logger.warning(f"检测到弹窗: {dialog_detail}")
            return CheckResult(PageStatus.DIALOG, ocr_text, text_len, dialog_detail)

        # 3. 页面空白
        blank, blank_detail = self._check_blank(img, ocr_text)
        if blank:
            logger.warning(f"检测到空白页: {blank_detail}")
            return CheckResult(PageStatus.BLANK, ocr_text, text_len, blank_detail)

        # 4. 文字极少
        if text_len < self.min_text_length:
            preview = clean_text[:50] if clean_text else "(无文字)"
            detail = f"页面文字仅{text_len}个字符: {preview}"
            logger.warning(detail)
            return CheckResult(PageStatus.SHORT, ocr_text, text_len, detail)

        # 5. 正常
        logger.debug(f"页面正常，共 {text_len} 个字符")
        return CheckResult(
            PageStatus.NORMAL, ocr_text, text_len,
            f"页面正常，共{text_len}个字符"
        )

    # ============================================================
    # 内部检测方法
    # ============================================================

    def _check_blocked(self, ocr_text: str) -> tuple:
        """检测是否为微信封禁页"""
        for kw in self.blocked_keywords:
            if kw in ocr_text:
                return True, f"命中封禁关键词: {kw}"
        return False, ""

    def _check_dialog(self, img: np.ndarray, ocr_text: str) -> tuple:
        """检测是否为弹窗提示页"""
        # 像素双峰检测：弹窗=遮罩暗区+中央亮卡片
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        dark_pixels = np.sum(gray < 60)
        total_pixels = gray.size
        dark_ratio = dark_pixels / total_pixels

        # 检查中央是否有亮区
        h, w = gray.shape
        center = gray[h//4:3*h//4, w//4:3*w//4]
        bright_center = np.sum(center > 200) / center.size

        has_overlay = dark_ratio > self.modal_dark_ratio and bright_center > 0.05

        # OCR关键词确认
        has_dialog_text = any(kw in ocr_text for kw in self.dialog_keywords)

        if has_overlay and has_dialog_text:
            return True, f"检测到弹窗遮罩（暗像素{int(dark_ratio*100)}%）+ 弹窗关键词"
        if has_overlay:
            return True, f"检测到弹窗遮罩（暗像素{int(dark_ratio*100)}%）"
        if has_dialog_text and len(self._clean_text(ocr_text)) < 30:
            return True, "检测到弹窗关键词+文字极少"

        return False, ""

    def _check_blank(self, img: np.ndarray, ocr_text: str) -> tuple:
        """检测是否为空白页"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        std = float(np.std(gray))

        # 像素方差极低
        if std < self.blank_variance_threshold:
            return True, f"像素方差极低({std:.1f})，页面空白"

        # 白像素占比极高
        white_pixels = np.sum(gray > 250)
        white_ratio = white_pixels / gray.size
        if white_ratio > 0.95:
            return True, f"白像素占比{white_ratio*100:.0f}%，页面近乎空白"

        # OCR无结果
        clean = self._clean_text(ocr_text)
        if len(clean) == 0:
            return True, "OCR未识别到任何文字"

        return False, ""

    # ============================================================
    # OCR
    # ============================================================

    def _ocr_extract(self, img: np.ndarray) -> str:
        """用PaddleOCR从截图中提取文字"""
        try:
            # PaddleOCR直接处理numpy数组
            result = self.ocr.ocr(img, cls=True)
            if not result or not result[0]:
                return ""

            texts = []
            for line in result[0]:
                text = line[1][0]      # 识别文字
                confidence = line[1][1] # 置信度
                if confidence > 0.7:
                    texts.append(text)

            return "\n".join(texts)
        except Exception as e:
            logger.error(f"OCR识别出错: {e}")
            return ""

    # ============================================================
    # 工具方法
    # ============================================================

    def _bytes_to_image(self, data: bytes) -> Optional[np.ndarray]:
        """将PNG bytes转为OpenCV numpy数组"""
        try:
            img = Image.open(io.BytesIO(data))
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"图像转换失败: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """清理文字：去除空白、数字、标点，只保留中英文字符"""
        # 匹配：空白 | 数字 | 英文标点 | 中文标点 | 其他符号
        return re.sub(
            r'[\s\d'
            r' -/:-@[-`{-~'  # 英文标点
            r'　-〿'   # 中文标点
            r'＀-￯'   # 全角符号
            r']+',
            '', text
        )
