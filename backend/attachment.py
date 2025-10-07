# attachment.py
import os
import time
import json
import logging
from datetime import datetime
from vika_client import VikaClient

# ========== 日志初始化 ==========
logger = logging.getLogger("attachment")
logger.setLevel(logging.INFO)

# 若无 Handler，则添加控制台和文件日志输出
if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    fh = logging.FileHandler("logs/attachment.log", encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [attachment] %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

# ========== 全局缓存，用于避免重复上传 ==========
CACHE_FILE = "logs/attachment_cache.json"
CACHE_TTL_HOURS = 24


def _load_cache():
    """加载本地缓存，记录24小时内已处理的记录"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                logger.info(f"🗂️ 载入缓存，共 {len(cache)} 条记录")
                return cache
        except Exception as e:
            logger.warning(f"⚠️ 缓存读取失败: {e}")
    return {}


def _save_cache(cache):
    """保存缓存到本地"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 缓存已更新，共 {len(cache)} 条记录")
    except Exception as e:
        logger.error(f"❌ 缓存写入失败: {e}")


def find_photo_by_barcode(watch_root: str, barcode: str) -> list[str]:
    """
    根据 barcode 查找本地文件夹中的 jpg/jpeg 图片。
    """
    folder = os.path.join(watch_root, barcode)
    logger.info(f"🔍 查找条码目录: {folder}")
    if not os.path.isdir(folder):
        logger.warning(f"⚠️ 未找到目录: {folder}")
        return []

    photos = []
    for f in os.listdir(folder):
        if f.lower().endswith((".jpg", ".jpeg")):
            full_path = os.path.join(folder, f)
            photos.append(full_path)

    logger.info(f"📸 共找到 {len(photos)} 张图片（barcode={barcode}）")
    return photos


def run_abnormal_attachment_sync(vika_receiver: VikaClient, watch_root: str):
    """
    每次执行扫描 receiver 表：
      - 找出 “异常” 字段为 True 的记录
      - 根据包裹单号找本地照片文件夹
      - 上传附件（异常图片）
      - 24小时内仅重复上传若文件有新增
    """
    logger.info("🚀 [attachment] 开始执行异常附件同步任务")

    cache = _load_cache()
    now = datetime.now()

    # 查询条件（异常字段为 True）
    filter_formula = "AND({异常}=TRUE())"
    logger.info(f"🧾 查询 filterByFormula: {filter_formula}")

    try:
        result = vika_receiver.query_records(params={
            "fieldKey": "name",
            "filterByFormula": filter_formula
        })
    except Exception as e:
        logger.exception(f"❌ 查询 receiver 表异常: {e}")
        return

    if not result.get("success"):
        logger.error(f"❌ 查询 receiver 表失败: {result.get('message')}")
        return

    records = result.get("data", [])
    logger.info(f"📊 共找到异常记录 {len(records)} 条")

    for rec in records:
        record_id = rec.get("recordId")
        barcode = rec.get("入仓包裹单号") or rec.get("packageNo")
        if not barcode:
            logger.warning(f"⚠️ 记录 {record_id} 缺少包裹单号，跳过")
            continue

        # 检查缓存是否过期
        last_time_str = cache.get(record_id, {}).get("last_sync")
        last_time = datetime.fromisoformat(last_time_str) if last_time_str else None
        time_diff = (now - last_time).total_seconds() / 3600 if last_time else None

        # 如果超过24小时或未缓存，则重新检查
        if (time_diff is None) or (time_diff > CACHE_TTL_HOURS):
            photos = find_photo_by_barcode(watch_root, barcode)
            if not photos:
                logger.info(f"📭 没有找到 {barcode} 的图片，跳过")
                continue

            try:
                # 上传图片
                logger.info(f"⬆️ 开始上传 {len(photos)} 张图片至 record={record_id}")
                upload_results = vika_receiver.update_record_with_attachment("recordId", record_id, "异常图片", photos)
                logger.info(f"✅ 上传完成 record={record_id}, 文件数={len(upload_results.get('data', []))}")
            except Exception as e:
                logger.exception(f"❌ 上传图片失败 record={record_id}: {e}")
                continue

            # 更新缓存
            cache[record_id] = {
                "barcode": barcode,
                "last_sync": now.isoformat(),
                "photo_count": len(photos)
            }

        else:
            logger.info(f"⏸️ 记录 {record_id} 已在 {round(time_diff, 2)} 小时内同步过，跳过")

        time.sleep(1.5)
        logger.debug(f"🌙 暂停 1.5 秒，准备处理下一条记录（record={record_id}）")
    # 保存缓存
    _save_cache(cache)
    logger.info("✅ [attachment] 异常附件同步任务执行完毕\n")