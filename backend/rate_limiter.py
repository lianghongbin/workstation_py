# backend/rate_limiter.py
import threading
import time
import random
import logging

logger = logging.getLogger("rate_limiter")

_LOCK = threading.Lock()
_LAST_CALL = 0.0
_MIN_INTERVAL = 1.2   # ⬅️ 每次间隔 1.2 秒（远低于 2 QPS）
_JITTER = 0.4         # ⬅️ ±0.4 秒随机扰动，防止节奏一致触发风控

def limit():
    """
    全局限速器：确保任意 API 调用间隔 > 1.2±0.4 秒。
    支持多线程调用，线程安全。
    """
    global _LAST_CALL
    with _LOCK:
        now = time.time()
        elapsed = now - _LAST_CALL
        min_interval = _MIN_INTERVAL + random.uniform(0, _JITTER)
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(f"[rate_limiter] 等待 {wait_time:.2f}s 再请求")
            time.sleep(wait_time)
        _LAST_CALL = time.time()