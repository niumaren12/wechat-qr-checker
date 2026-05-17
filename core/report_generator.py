"""
报告生成器
用Jinja2渲染自包含HTML报告：汇总卡片+可筛选表格+截图展开
"""
import sys
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """HTML报告生成器"""

    def __init__(self, config: dict):
        cfg = config["report"]
        self.title = cfg["title"]
        self.output_dir = Path(cfg["output_dir"])
        self.filename_template = cfg["filename_template"]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载Jinja2模板（适配PyInstaller打包环境）
        if getattr(sys, 'frozen', False):
            template_dir = Path(sys._MEIPASS) / "templates"
        else:
            template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("report.html")

    def generate(self, results: list[dict], stats: dict,
                 output_path: Optional[str] = None) -> str:
        """生成HTML报告

        Args:
            results: 每条结果dict，需含 wechat_id, link, status, detail,
                     ocr_text, screenshot_bytes (可选)
            stats: 统计dict，含 total, normal, blocked, dialog, blank, short, no_qr
            output_path: 输出路径，None则自动生成
        Returns:
            生成的HTML文件路径
        """
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.filename_template.format(timestamp=ts)
            output_path = str(self.output_dir / filename)

        # 截图转base64嵌入HTML
        for r in results:
            if r.get("screenshot_bytes"):
                r["screenshot_b64"] = self._bytes_to_data_uri(
                    r["screenshot_bytes"]
                )
                # 不保留原始bytes在序列化中
                del r["screenshot_bytes"]

        html = self.template.render(
            title=self.title,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results=results,
            stats=stats,
            status_labels={
                "normal": "正常", "blocked": "已封禁", "dialog": "弹窗",
                "blank": "空白页", "short": "极少文字", "no_qr": "无二维码",
                "unknown": "未知"
            },
            status_css_class={
                "normal": "status-normal", "blocked": "status-error",
                "dialog": "status-warning", "blank": "status-error",
                "short": "status-warning", "no_qr": "status-skip",
                "unknown": "status-error"
            }
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def compute_stats(self, results: list[dict]) -> dict:
        """计算汇总统计"""
        stats = {
            "total": len(results),
            "normal": 0, "blocked": 0, "dialog": 0,
            "blank": 0, "short": 0, "no_qr": 0, "unknown": 0
        }
        for r in results:
            st = r.get("status", "unknown")
            if st in stats:
                stats[st] += 1
            else:
                stats["unknown"] += 1
        stats["anomaly_count"] = stats["total"] - stats["normal"] - stats["no_qr"]
        return stats

    def _bytes_to_data_uri(self, data: bytes) -> str:
        """PNG bytes 转 JPEG data URI（压缩体积）"""
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(data))
        # 缩放宽不超过400px的缩略图
        w, h = img.size
        if w > 400:
            ratio = 400 / w
            img = img.resize((400, int(h * ratio)), Image.LANCZOS)
        buf = _io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=60)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
