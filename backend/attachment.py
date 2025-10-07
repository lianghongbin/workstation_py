# attachment.py
import os
import time
import logging
from datetime import datetime, timedelta
from vika_client import VikaClient

logger = logging.getLogger("attachment")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ----------------------------------------------------------
# 全局配置
# ----------------------------------------------------------
WATCH_ROOT = "D:/warehouse_photos"  # [可配置] 本地图片根目录，每个 barcode 为子文件夹
CACHE_EXPIRY_HOURS = 24  # 缓存有效期（小时）


# ==========================================================
# [ADDED] 1️⃣ 查找包裹图片
# ==========================================================
def find_images_by_package(barcode: str) -> list[str]:
    """
    在 WATCH_ROOT 下查找与包裹号（barcode）同名文件夹中的 JPG/JPEG 图片。
    返回图片完整路径数组。
    """
    package_dir = os.path.join(WATCH_ROOT, barcode)
    if not os.path.isdir(package_dir):
        logger.warning(f"[attachment] ⚠️ 未找到包裹目录: {package_dir}")
        return []

    images = []
    for fname in os.listdir(package_dir):
        if fname.lower().endswith((".jpg", ".jpeg")):
            full_path = os.path.join(package_dir, fname)
            images.append(full_path)

    logger.info(f"[attachment] ✅ 找到 {len(images)} 张图片于 {package_dir}")
    return images


# ==========================================================
# [ADDED] 2️⃣ 缓存机制（避免重复上传）
# ==========================================================
class AttachmentCache:
    """
    本地缓存：记录每个 recordId 上次上传时间 & 已上传图片数量。
    存储格式：{ recordId: {"timestamp": 1700000000, "file_count": 5} }
    """

    def __init__(self, cache_file="attachment_cache.json"):
        import json
        self.cache_file = cache_file
        self._data = {}
        self._json = json
        self._load()

    def _load(self):
        """加载本地缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._data = self._json.load(f)
                logger.info(f"[attachment] 📂 加载缓存: {len(self._data)} 条记录")
            except Exception as e:
                logger.warning(f"[attachment] ⚠️ 缓存加载失败: {e}")
                self._data = {}

    def save(self):
        """保存缓存"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                self._json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[attachment] ❌ 保存缓存失败: {e}")

    def is_recent(self, record_id: str) -> bool:
        """判断记录是否在有效期内"""
        if record_id not in self._data:
            return False
        last_time = datetime.fromtimestamp(self._data[record_id]["timestamp"])
        return datetime.now() - last_time < timedelta(hours=CACHE_EXPIRY_HOURS)

    def update(self, record_id: str, file_count: int):
        """更新记录缓存"""
        self._data[record_id] = {
            "timestamp": time.time(),
            "file_count": file_count
        }
        self.save()


# ==========================================================
# [ADDED] 3️⃣ 异常图片自动上传逻辑
# ==========================================================
def upload_abnormal_images(vika_receiver: VikaClient, field_name: str = "异常图片"):
    """
    扫描 receiver 表中【异常=TRUE】的记录：
      1️⃣ 根据 包裹单号 找图片文件夹；
      2️⃣ 上传文件夹中所有 JPG/JPEG 图片；
      3️⃣ 更新到记录的 “异常图片” 字段；
      4️⃣ 使用缓存控制，24 小时内重复更新时仅检测新增图片；
      5️⃣ 超过 24 小时并且已有图片的，不再更新。
    """
    logger.info("[attachment] 🚀 开始扫描异常记录...")
    cache = AttachmentCache()

    # 1️⃣ 查询异常记录
    result = vika_receiver.query_abnormal_records()
    if not result.get("success"):
        logger.warning(f"[attachment] ❌ 查询异常记录失败: {result.get('message')}")
        return

    records = result.get("data", [])
    if not records:
        logger.info("[attachment] ✅ 当前无异常记录。")
        return

    # 2️⃣ 遍历每条异常记录
    for rec in records:
        record_id = rec.get("recordId")
        barcode = rec.get("入仓包裹单号") or rec.get("packageNo")

        if not record_id or not barcode:
            logger.warning(f"[attachment] ⚠️ 跳过无效记录: {rec}")
            continue

        # 检查缓存有效期
        if cache.is_recent(record_id):
            logger.info(f"[attachment] ⏸️ 跳过 {barcode}（24小时内已处理）")
            continue

        # 查找包裹对应图片
        images = find_images_by_package(barcode)
        if not images:
            logger.info(f"[attachment] ⚠️ {barcode} 无图片文件，跳过。")
            continue

        # 上传图片到 Vika
        try:
            uploaded_files = vika_receiver.upload_attachments(images)
            if not uploaded_files:
                logger.warning(f"[attachment] ❌ 图片上传失败: {barcode}")
                continue

            vika_receiver.update_record_with_attachment(record_id, field_name, uploaded_files)
            logger.info(f"[attachment] ✅ 已为 {barcode} 上传 {len(uploaded_files)} 张异常图片")

            # 更新缓存
            cache.update(record_id, len(uploaded_files))

        except Exception as e:
            logger.error(f"[attachment] ❌ 上传异常: {barcode} - {e}")

    logger.info("[attachment] 🏁 异常图片上传任务完成。")