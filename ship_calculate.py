# ship_calculate.py
import logging
import json
from vika_client import VikaClient

logger = logging.getLogger("ship_calculate")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

SAFE_LOG_SAMPLE = 5  # 列表日志最多展示多少条样本


def _j(obj):
    """安全的 JSON 序列化（失败就用 repr）"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return repr(obj)


def _sample_list(lst, n=SAFE_LOG_SAMPLE):
    """列表取样展示"""
    if not isinstance(lst, list):
        return lst
    if len(lst) <= n:
        return lst
    return lst[:n] + [f"...(total {len(lst)})"]


# ========== 1️⃣ 读取 & 更新 metadata ==========
def get_last_upload_id(vika_metadata: VikaClient) -> int:
    """从 metadata 表读取上次同步 ID"""
    logger.info("🔎 [metadata] 准备读取 receiver_last_upload_id ...")
    result = vika_metadata.query_records(params={"fieldKey": "name"})
    logger.info(f"🔁 [metadata] query_records 返回: success={result.get('success')}, "
                f"code={result.get('code')}, msg={result.get('message')}")

    if not result.get("success"):
        logger.info(f"❌ 查询 metadata 失败: {result.get('message')}")
        return 0

    records = result.get("data", [])
    logger.info(f"📊 [metadata] 读取到记录数: {len(records)}，样本: {_j(_sample_list(records))}")

    if not records:
        logger.info("⚠️ metadata 表为空，默认从 ID=0 开始。")
        return 0

    val_raw = records[0].get("receiver_last_upload_id", 0)
    try:
        last_id = int(val_raw)
    except Exception:
        logger.info(f"⚠️ [metadata] receiver_last_upload_id 无法转 int，原值={_j(val_raw)}，按 0 处理")
        last_id = 0

    logger.info(f"📌 上次同步的 receiver ID: {last_id}")
    return last_id


def update_last_upload_id(vika_metadata: VikaClient, new_id: int):
    """更新 metadata 表中 receiver_last_upload_id 字段"""
    logger.info(f"📝 [metadata] 准备写入新的 last_id={new_id}")
    result = vika_metadata.query_records(params={"fieldKey": "name"})
    logger.info(f"🔁 [metadata] query_records 返回: success={result.get('success')}, "
                f"code={result.get('code')}, msg={result.get('message')}")

    if not result.get("success"):
        raise RuntimeError(f"❌ 查询 metadata 失败: {result.get('message')}")

    records = result.get("data", [])
    logger.info(f"📊 [metadata] 当前记录数: {len(records)}，样本: {_j(_sample_list(records))}")

    if not records:
        resp = vika_metadata.add_record({"receiver_last_upload_id": new_id})
        logger.info(f"📤 [metadata] add_record 返回: {_j(resp)}")
        logger.info(f"🆕 创建 metadata 记录，记录 ID={new_id}")
    else:
        rec = records[0]
        record_id = rec.get("recordId")
        logger.info(f"🔗 [metadata] 将更新 recordId={record_id} 的 receiver_last_upload_id={new_id}")
        resp = vika_metadata.update_record(record_id, {"receiver_last_upload_id": new_id})
        logger.info(f"📤 [metadata] update_record 返回: {_j(resp)}")
        logger.info(f"✅ 更新 metadata 记录，记录 ID={new_id}")


# ========== 2️⃣ 聚合 SKU ==========
def group_sku_summary(records: list[dict]) -> list[dict]:
    """对 receiver 表返回的 records 进行 SKU 聚合"""
    logger.info(f"📦 [receiver] 准备聚合 SKU，输入记录数: {len(records)}，样本: {_j(_sample_list(records))}")

    summary = {}
    for rec in records:
        for key, value in rec.items():
            if key.startswith("SKU") and not key.endswith("-数量") and value:
                qty_key = f"{key}-数量"
                qty = rec.get(qty_key, 0) or 0
                # 与原逻辑保持一致，不改动
                qty = int(qty) if isinstance(qty, (int, float, str)) and str(qty).isdigit() else 0
                summary[value] = summary.get(value, 0) + qty

    result = [{"SKU": k, "数量": v} for k, v in summary.items()]
    logger.info(f"📊 [receiver] 聚合完成，SKU 去重数: {len(result)}，样本: {_j(_sample_list(result))}")
    return result


# ========== 3️⃣ 查询 Ship ==========
def fetch_existing_ship_records(vika_ship: VikaClient, sku_list: list[str]) -> list[dict]:
    """从 Ship 表获取指定 SKU 的记录"""
    logger.info(f"🔎 [ship] 准备按 SKU 批量查询，SKU 个数={len(sku_list)}，样本={_j(_sample_list(sku_list))}")

    if not sku_list:
        logger.info("⚠️ [ship] SKU 列表为空，跳过查询。")
        return []

    or_conditions = ", ".join([f"{{产品条码}} = '{sku}'" for sku in sku_list])
    filter_formula = f"OR({or_conditions})"
    logger.info(f"🧮 [ship] filterByFormula = {filter_formula}")

    result = vika_ship.query_records(params={
        "fieldKey": "name",
        "filterByFormula": filter_formula
    })
    logger.info(f"🔁 [ship] query_records 返回: success={result.get('success')}, "
                f"code={result.get('code')}, msg={result.get('message')}")

    if not result.get("success"):
        logger.info(f"❌ 查询 ship 表失败: {result.get('message')}")
        return []

    data = result.get("data", [])
    logger.info(f"📊 [ship] 命中记录数: {len(data)}，样本: {_j(_sample_list(data))}")
    return data


# ========== 4️⃣ 合并结果 ==========
def merge_sku_results(receiver_summary: list[dict], ship_records: list[dict]) -> list[dict]:
    """将 receiver 聚合结果与 ship 表数据合并（以 ship 为准）"""
    logger.info(f"🔗 [merge] 准备合并：receiver_summary={len(receiver_summary)}, ship_records={len(ship_records)}")
    logger.info(f"🧪 [merge] receiver_summary 样本: {_j(_sample_list(receiver_summary))}")
    logger.info(f"🧪 [merge] ship_records 样本: {_j(_sample_list(ship_records))}")

    merged = {}

    # ✅ 先放 ship 表的现有数据（以 ship 为准）
    for rec in ship_records:
        # ship 表里字段是 barcode，不是 产品条码
        sku = rec.get("产品条码") or rec.get("barcode")
        qty = rec.get("数量", 0)
        record_id = rec.get("recordId")
        merged[sku] = {"recordId": record_id, "产品条码": sku, "数量": qty}
        logger.info(f"📦 [merge] 初始化 Ship SKU={sku} 数量={qty} recordId={record_id}")

    # ✅ 再合并 receiver 的数据
    for item in receiver_summary:
        sku = item["SKU"]
        qty = item["数量"]
        if sku in merged:
            old = merged[sku]["数量"]
            merged[sku]["数量"] = old + qty
            logger.info(f"➕ [merge] SKU={sku} 累加: {old} + {qty} = {merged[sku]['数量']} (recordId={merged[sku]['recordId']})")
        else:
            # ship 表中不存在的 SKU 才新增
            merged[sku] = {"recordId": None, "产品条码": sku, "数量": qty}
            logger.info(f"🆕 [merge] 新增 SKU={sku} 数量={qty} (recordId=None)")

    merged_list = list(merged.values())
    logger.info(f"📊 [merge] 合并完成，总条数: {len(merged_list)}，样本: {_j(_sample_list(merged_list))}")
    return merged_list


# ========== 5️⃣ 更新 Ship ==========
def sync_to_ship_table(vika_ship: VikaClient, merged_result: list[dict]):
    """将合并结果写入 ship 表"""
    logger.info(f"📤 [ship] 准备写入 ship 表，记录数={len(merged_result)}，样本={_j(_sample_list(merged_result))}")
    for rec in merged_result:
        if rec["recordId"]:
            logger.info(f"📝 [ship] UPDATE recordId={rec['recordId']} SKU={rec['产品条码']} 数量={rec['数量']}")
            resp = vika_ship.update_record(rec["recordId"], {"数量": rec["数量"]})
            logger.info(f"📨 [ship] update_record 响应: {_j(resp)}")
        else:
            payload = {"产品条码": rec["产品条码"], "数量": rec["数量"]}
            logger.info(f"➕ [ship] INSERT SKU={rec['产品条码']} 数量={rec['数量']}")
            resp = vika_ship.add_record(payload)
            logger.info(f"📨 [ship] add_record 响应: {_j(resp)}")


# ========== 6️⃣ 主逻辑函数 ==========
def process_receiver_to_ship(vika_receiver: VikaClient, vika_ship: VikaClient, vika_metadata: VikaClient):
    """Receiver → Ship 增量同步任务"""
    logger.info("🚀 开始执行 Receiver → Ship 增量同步")

    # 1) 读取 last_id
    last_id = get_last_upload_id(vika_metadata)

    # 2) 读取 receiver 的增量 + 条件
    filter_formula = (
        f"AND("
        f"OR("
        f"AND({{SKU1}} != '', {{SKU1-数量}} >0), "
        f"AND({{SKU2}} != '', {{SKU2-数量}} >0)"
        f"), "
        f"{{ID}} > {last_id}"
        f")"
    )
    logger.info(f"🧮 [receiver] filterByFormula = {filter_formula}")

    result = vika_receiver.query_records(params={
        "fieldKey": "name",
        "filterByFormula": filter_formula
    })
    logger.info(f"🔁 [receiver] query_records 返回: success={result.get('success')}, "
                f"code={result.get('code')}, msg={result.get('message')}")

    if not result.get("success"):
        logger.info(f"❌ 读取 receiver 表失败: {result.get('message')}")
        return

    records = result.get("data", [])
    logger.info(f"📦 [receiver] 命中记录数: {len(records)}，样本: {_j(_sample_list(records))}")

    if not records:
        logger.info("✅ 没有符合条件的新记录。")
        return

    # 3) 聚合
    summary = group_sku_summary(records)
    if not summary:
        logger.info("⚠️ [receiver] 聚合后结果为空，跳过后续流程。")
        return
    sku_list = [item["SKU"] for item in summary]
    logger.info(f"🧾 [receiver] 聚合 SKU 列表（{len(sku_list)}）: {_j(_sample_list(sku_list))}")

    # 4) 查询 ship
    ship_records = fetch_existing_ship_records(vika_ship, sku_list)

    # 5) 合并 & 同步
    merged_result = merge_sku_results(summary, ship_records)
    sync_to_ship_table(vika_ship, merged_result)

    # 6) 更新 metadata
    # 注意：records 中必须含有 ID 字段（name 模式下返回的字段名就是 "ID"）
    ids = [r.get("ID") for r in records if r.get("ID") is not None]
    logger.info(f"🆔 [receiver] 本批次 ID 列表样本: {_j(_sample_list(ids))}")
    if not ids:
        logger.info("⚠️ [receiver] 未在记录中找到 ID 字段，跳过 metadata 更新。")
        return

    try:
        max_id = max(ids)
    except Exception:
        logger.info(f"⚠️ [receiver] 计算 max_id 失败，ids={_j(ids)}")
        return

    update_last_upload_id(vika_metadata, max_id)

    logger.info(f"✅ Receiver → Ship 增量同步完成 (已同步到 ID={max_id})")