# ==========================================================
# ========== logger_config.py：统一日志配置 ==========
# ==========================================================
import os
import gzip
import shutil
import logging
from logging.handlers import RotatingFileHandler


def workstation_logger(
    name: str = "app",
    log_dir: str = "logs",
    max_size_mb: int = 10,
    backup_count: int = 7
) -> logging.Logger:
    """
    创建并返回一个带轮转、压缩的日志记录器。
    可供多个模块共享。
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{name}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 防止重复添加 Handler
    if logger.handlers:
        return logger

    # === 格式 ===
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

    # === 文件日志（支持轮转） ===
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # === 控制台日志 ===
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # === 自动压缩旧日志 ===
    compress_old_logs(log_dir, f"{name}.log", logger)

    return logger


def compress_old_logs(log_dir: str, prefix: str, logger: logging.Logger):
    """
    查找旧日志（.log.N），压缩为 .gz 并删除原文件。
    """
    for name in os.listdir(log_dir):
        path = os.path.join(log_dir, name)
        if name.startswith(prefix) and not name.endswith(".gz") and os.path.isfile(path):
            gz_path = path + ".gz"
            try:
                with open(path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(path)
                logger.info(f"🗜️ 已压缩旧日志：{gz_path}")
            except Exception as e:
                logger.warning(f"⚠️ 日志压缩失败 {path}: {e}")