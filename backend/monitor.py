# monitor.py
# =========================================================
# 说明：
# - 后台定时任务控制；
# - 每 10 分钟执行一次 run_abnormal_attachment_sync；
# - 提供启动与停止控制，避免重复启动。
# =========================================================
import threading
import logging
from typing import Optional
from attachment import run_abnormal_attachment_sync
from vika_client import VikaClient

logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(_h)
vika_receiver = VikaClient('dstsnDVylQhjuBiSEo')

# ======== [NEW] 异常附件监控任务 ========
class AbnormalAttachmentMonitor:
    """
    [NEW] 每 interval_minutes 分钟执行一次异常附件同步的后台线程。
    """
    def __init__(self, vika_receiver: VikaClient, watch_root: str, interval_minutes: int = 10):
        self.vika_receiver = vika_receiver
        self.watch_root = watch_root
        self.interval_sec = max(60, interval_minutes * 60)  # 至少 60 秒，防止误填
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _loop(self):
        logger.info(f"[abnormal-monitor] 启动；周期={self.interval_sec}s")
        while not self._stop.is_set():
            try:
                run_abnormal_attachment_sync(self.vika_receiver, self.watch_root)
            except Exception as e:
                logger.exception(f"[abnormal-monitor] 本轮执行异常: {e}")
            # 等待下个周期（可中断）
            self._stop.wait(self.interval_sec)
        logger.info("[abnormal-monitor] 已停止")

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.info("[abnormal-monitor] 已在运行（忽略重复启动）")
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="abnormal-attach-monitor", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval_sec + 5)

# ======== [NEW] 外部便捷启动函数 ========
_monitor_singleton: Optional[AbnormalAttachmentMonitor] = None

def start_abnormal_attachment_monitor(watch_root: str, interval_minutes: int = 10):
    """
    [NEW] 便捷启动方法；避免外部多处重复构造。
    """
    global _monitor_singleton
    if _monitor_singleton is None:
        _monitor_singleton = AbnormalAttachmentMonitor(vika_receiver, watch_root, interval_minutes)
    _monitor_singleton.start()
    return _monitor_singleton

def stop_abnormal_attachment_monitor():
    global _monitor_singleton
    if _monitor_singleton:
        _monitor_singleton.stop()
        _monitor_singleton = None