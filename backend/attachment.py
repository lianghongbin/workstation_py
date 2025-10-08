import os
import json
import time
import logging
import threading  # 🟩 新增：全局互斥锁，防止并发任务冲突
from datetime import datetime, timedelta
from vika_client import VikaClient

# ==========================================================
# ========== 日志配置 ==========
# ==========================================================
logger = logging.getLogger("attachment")
logger.setLevel(logging.INFO)

if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    fh = logging.FileHandler("logs/attachment.log", encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [attachment] %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

# ==========================================================
# ========== 缓存配置（已改为 cache 目录） ==========
# ==========================================================
os.makedirs("cache", exist_ok=True)
CACHE_FILE = "cache/attachment_cache.json"
CACHE_TTL_HOURS = 48

# 🟩 新增：全局互斥锁，保证任务不会并行执行
_sync_lock = threading.Lock()


# ==========================================================
# ========== 工具函数 ==========
# ==========================================================
def _load_cache() -> dict:
    """加载缓存文件并清理过期项"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                now = datetime.now()
                for k, v in list(cache.items()):
                    expire = datetime.fromisoformat(v.get("expire")) if v.get("expire") else None
                    if expire and expire < now:
                        del cache[k]
                logger.info(f"🗂️ 已加载缓存 {len(cache)} 条记录")
                return cache
        except Exception as e:
            logger.warning(f"⚠️ 缓存读取失败: {e}")
    return {}


def _save_cache(cache: dict):
    """保存缓存文件"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 缓存写入成功，共 {len(cache)} 条记录")
    except Exception as e:
        logger.error(f"❌ 缓存写入失败: {e}")


def find_photo_by_barcode(watch_root: str, barcode: str) -> list[str]:
    """查找指定包裹号目录下的 jpg/jpeg 图片"""
    folder = os.path.join(watch_root, barcode)
    if not os.path.isdir(folder):
        logger.warning(f"📭 未找到目录: {folder}")
        return []

    photos = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]
    logger.info(f"📸 {barcode} 共找到 {len(photos)} 张图片")
    return photos


# ==========================================================
# ========== 主任务：上传异常记录图片 ==========
# ==========================================================
def run_abnormal_upload_sync(vika_receiver: VikaClient, watch_root: str):
    """
    主任务逻辑：
      1. 查询 “异常=TRUE 且 异常图片为空” 的记录
      2. 查找对应包裹目录
      3. 上传图片
      4. 删除目录及图片
      5. 写入缓存（48 小时）
    """

    # 🟩 新增：加互斥锁，防止多线程重复执行
    if not _sync_lock.acquire(blocking=False):
        logger.warning("⚠️ 检测到已有上传任务在执行，跳过本轮")
        return

    try:
        logger.info("🚀 [主任务] 开始执行异常图片上传任务")

        cache = _load_cache()
        now = datetime.now()
        expire_time = now + timedelta(hours=CACHE_TTL_HOURS)

        # 🟦 修改：Vika 不支持 ISBLANK() 多字段组合，使用 NOT() 规避
        filter_formula = "AND({异常}=TRUE(), NOT({异常图片}))"

        try:
            result = vika_receiver.query_records(params={
                "fieldKey": "name",
                "filterByFormula": filter_formula
            })
        except Exception as e:
            logger.exception(f"❌ 查询 receiver 表异常: {e}")
            return

        if not result.get("success"):
            logger.error(f"❌ 查询失败: {result.get('message')}")
            return

        records = result.get("data", [])
        logger.info(f"📊 共找到 {len(records)} 条异常记录")

        for rec in records:
            record_id = rec.get("recordId")
            barcode = rec.get("入仓包裹单号") or rec.get("packageNo")
            if not record_id or not barcode:
                logger.warning(f"⚠️ 记录缺少 recordId 或 barcode，跳过")
                continue

            folder = os.path.join(watch_root, barcode)
            if not os.path.isdir(folder):
                logger.warning(f"📭 未找到目录: {folder}")
                continue

            photos = find_photo_by_barcode(watch_root, barcode)
            if not photos:
                logger.info(f"📭 {barcode} 没有图片，跳过")
                continue

            try:
                logger.info(f"⬆️ 上传 {len(photos)} 张图片 -> record={record_id}")
                upload_result = vika_receiver.update_record_with_attachment("recordId", record_id, "异常图片", photos)
                logger.info(f"✅ 上传完成 record={record_id}, 上传数={len(upload_result.get('data', []))}")

                # 🟩 新增：详细删除日志和异常安全
                for f in photos:
                    if os.path.exists(f):
                        os.remove(f)
                        logger.info(f"🗑️ 删除文件: {f}")
                    else:
                        logger.warning(f"⚠️ 文件已不存在: {f}")

                try:
                    os.rmdir(folder)
                    logger.info(f"📁 删除目录成功: {folder}")
                except OSError as e:
                    logger.warning(f"⚠️ 删除目录失败: {folder} ({e})")

                # 写入缓存
                cache[record_id] = {
                    "barcode": barcode,
                    "record_id": record_id,
                    "uploaded_files": [os.path.basename(p) for p in photos],
                    "upload_time": now.isoformat(),
                    "expire": expire_time.isoformat()
                }

            except Exception as e:
                logger.exception(f"❌ 上传或删除失败 record={record_id}: {e}")

            time.sleep(1.5)  # 限流保护

        _save_cache(cache)
        logger.info("✅ [主任务] 异常图片上传任务完成\n")

    finally:
        # 🟩 新增：确保锁释放，即使异常也能继续下次任务
        _sync_lock.release()


# ==========================================================
# ========== 补偿任务：检测目录新增并上传 ==========
# ==========================================================
def run_missing_photo_sync(vika_receiver: VikaClient, watch_root: str):
    """
    补偿任务逻辑：
      1. 扫描最近 24 小时内修改的目录
      2. 对比缓存，检测未上传图片
      3. 上传缺失图片
      4. 更新缓存
    """
    logger.info("🔄 [补偿任务] 开始扫描最近 24 小时内的目录变动")

    cache = _load_cache()
    now = datetime.now()
    updated = False

    for barcode in os.listdir(watch_root):
        folder = os.path.join(watch_root, barcode)
        if not os.path.isdir(folder):
            continue

        # 检查目录修改时间（最近 24 小时内）
        mtime = datetime.fromtimestamp(os.path.getmtime(folder))
        if (now - mtime).total_seconds() > 86400:
            continue

        photos = find_photo_by_barcode(watch_root, barcode)
        logger.info(f'24小时变动的文件夹 {barcode}')

        logger.info(f'新增的文件 {photos}')
        if not photos:
            continue

        # 从缓存中查找记录
        record_info = next((v for v in cache.values() if v["barcode"] == barcode), None)
        if not record_info:
            logger.debug(f"🪣 {barcode} 不在缓存中，跳过")
            continue

        record_id = record_info["record_id"]
        uploaded = set(record_info.get("uploaded_files", []))

        new_files = [p for p in photos if os.path.basename(p) not in uploaded]
        if not new_files:
            continue

        logger.info(f"📸 {barcode} 发现 {len(new_files)} 张新增图片，准备补传")

        try:
            result = vika_receiver.update_record_with_attachment("recordId", record_id, "异常图片", new_files)
            logger.info(f"✅ 增量上传成功 record={record_id}, 新增={len(new_files)}")

            uploaded |= set(os.path.basename(p) for p in new_files)
            record_info["uploaded_files"] = list(uploaded)
            record_info["upload_time"] = now.isoformat()
            record_info["expire"] = (now + timedelta(hours=CACHE_TTL_HOURS)).isoformat()
            updated = True

        except Exception as e:
            logger.exception(f"❌ 增量上传失败 barcode={barcode}: {e}")

        time.sleep(1.5)  # 限流保护

    if updated:
        _save_cache(cache)

    logger.info("✅ [补偿任务] 增量图片检查完成\n")