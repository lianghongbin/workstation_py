# monitor.py
import time
import logging
from threading import Thread
from ship_calculate import process_receiver_to_ship
from vika_client import VikaClient

logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def schedule_task(vika_receiver, vika_ship, vika_metadata, interval=300):
    """守护线程定时执行同步任务"""
    while True:
        try:
            process_receiver_to_ship(vika_receiver, vika_ship, vika_metadata)
        except Exception as e:
            logger.exception(f"❌ 任务执行异常: {e}")
        time.sleep(interval)


def start_monitor(interval=60):
    """
    启动后台定时任务线程
    （Receiver → Ship 自动同步）
    """
    receiver = VikaClient("dstsnDVylQhjuBiSEo")   # receiver 表
    ship = VikaClient("dstl0nkkjrg2hlXfRk")       # ship 表
    metadata = VikaClient("dstyZybgPZi0tL8aNY")    # metadata 表

    t = Thread(
        target=schedule_task,
        args=(receiver, ship, metadata, interval),
        daemon=True
    )
    t.start()
    logger.info(f"🟢 后台监控线程已启动，每 {interval // 60} 分钟执行一次同步任务")