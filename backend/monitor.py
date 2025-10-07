import threading
import logging
from backend.attachment import run_abnormal_attachment_sync
from vika_client import VikaClient

logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class AbnormalAttachmentMonitor:
    """
    后台任务：定时检测 receiver 表中异常包裹并上传异常图片
    """

    def __init__(self, watch_root: str, interval_minutes: int):
        """
        :param watch_root: 图片根目录
        :param interval_sec: 定时扫描周期（秒）
        """
        self.vika_receiver = VikaClient("dstsnDVylQhjuBiSEo")  # ✅ Receiver 表固定 ID
        self.watch_root = watch_root
        self.interval_sec = interval_minutes * 60
        self._stop = threading.Event()

    def _loop(self):
        """后台定时循环执行任务"""
        logger.info(f"[abnormal-monitor] 启动；周期={self.interval_sec}s，目录={self.watch_root}")
        while not self._stop.is_set():
            try:
                run_abnormal_attachment_sync(self.vika_receiver, self.watch_root)
            except Exception as e:
                logger.exception(f"[abnormal-monitor] 本轮执行异常: {e}")
            # 等待下个周期（可中断）
            self._stop.wait(self.interval_sec)
        logger.info("[abnormal-monitor] 已停止")

    def start(self):
        """启动后台线程"""
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        logger.info("[abnormal-monitor] 后台线程已启动")

    def stop(self):
        """停止后台任务"""
        self._stop.set()


def start_all_monitors(photo_root: str, interval_minutes: int):
    """
    启动所有后台任务（在 bootstrap 中调用）
    """
    logger.info("[monitor] 准备启动所有后台任务...")
    abnormal_monitor = AbnormalAttachmentMonitor(photo_root, interval_minutes)
    abnormal_monitor.start()
    logger.info("[monitor] ✅ 所有后台任务启动完毕")