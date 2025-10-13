"""
===========================================================
🏷️ 文件名: sorting.py
📘 功能: 智能分拣系统后端（Flask + JSON 数据）
===========================================================

后端包含 5 个主要交互接口：
1️⃣ 页面加载时初始化篮子与日志 (/api/init)
2️⃣ 添加 / 删除最后一个篮子 (/api/basket)
3️⃣ 删除 / 恢复中间篮子 (/api/basket_toggle)
4️⃣ 重置所有篮子 (/api/reset)
5️⃣ 扫码 / 手动输入 SKU 分配篮子 (/api/assign)

数据存储结构：baskets.json
{
  "baskets": [ { "id": 1, "count": 0, "deleted": false }, ... ],
  "logs": [ { "time": "2025-10-09 08:00:00", "sku": "ABC123", "basket": 5 } ],
  "sku_map": { "ABC123": 5 }
}
===========================================================
"""

from flask import Flask, Blueprint, jsonify, render_template, request
import json, os
from datetime import datetime

# ==========================================================
# ✅ 基础配置
# ==========================================================
bp = Blueprint("sorting", __name__, url_prefix="/sorting")
DATA_FILE = "baskets.json"


# ==========================================================
# ✅ 通用数据加载与保存函数
# ==========================================================
def load_data():
    """加载 JSON 数据文件（若不存在则初始化 50 个篮子）"""
    if not os.path.exists(DATA_FILE):
        data = {
            "baskets": [{"id": i + 1, "count": 0, "deleted": False} for i in range(50)],
            "logs": [],
            "sku_map": {}
        }
        save_data(data)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    """保存 JSON 数据"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==========================================================
# ✅ 功能 1：页面加载时初始化数据
# 前端：GET /sorting/api/init
# 返回：当前所有篮子信息 + 最近操作日志
# ==========================================================
@bp.route("/api/init", methods=["GET"])
def api_init():
    data = load_data()
    baskets = data["baskets"]

    # ✅ 确保返回时带上正确数量和 SKU 状态
    enriched_baskets = []
    for b in baskets:
        enriched_baskets.append({
            "id": b["id"],
            "count": b.get("count", 0),
            "deleted": b.get("deleted", False),
            "sku": b.get("sku", "")
        })

    return jsonify({
        "success": True,
        "baskets": enriched_baskets,
        "logs": data.get("logs", [])
    })

# ==========================================================
# ✅ 功能 2：添加 / 删除最后一个篮子
# 前端：POST /sorting/api/basket  {action: "add" | "remove"}
# ==========================================================
@bp.route("/api/basket", methods=["POST"])
def api_basket_modify():
    req = request.get_json()
    action = req.get("action")
    data = load_data()
    baskets = data["baskets"]

    if action == "add":
        # 新增篮子（编号递增）
        new_id = baskets[-1]["id"] + 1 if baskets else 1
        baskets.append({"id": new_id, "count": 0, "deleted": False})

    elif action == "remove" and baskets:
        # 删除最后一个篮子
        baskets.pop()

    save_data(data)
    return jsonify({"success": True, "total": len(baskets)})


# ==========================================================
# ✅ 功能 3：删除 / 恢复中间篮子
# 前端：POST /sorting/api/basket_toggle
# 参数：{id: 3, action: "delete" | "restore"}
# ==========================================================
@bp.route("/api/basket_toggle", methods=["POST"])
def api_toggle_basket():
    """
    启用 / 禁用 / 清空篮子
    前端参数：
        { id: 3, action: "delete" | "restore" | "clear" }

    功能：
        - delete: 禁用篮子（但不清空 SKU 或数量）
        - restore: 恢复篮子（保持数量和 SKU 不变）
        - clear: 清空篮子的 SKU 和数量
    """
    req = request.get_json()
    bid = req.get("id")
    action = req.get("action")

    if bid is None or action not in ["delete", "restore", "clear"]:
        return jsonify({"success": False, "message": "参数错误"}), 400

    # 统一转换 ID 类型，避免字符串比较错误
    try:
        bid = int(bid)
    except ValueError:
        return jsonify({"success": False, "message": "无效的篮子 ID"}), 400

    data = load_data()
    baskets = data.get("baskets", [])
    sku_map = data.get("sku_map", {})

    target_basket = next((b for b in baskets if b["id"] == bid), None)
    if not target_basket:
        return jsonify({"success": False, "message": f"未找到 {bid} 号篮子"}), 404

    # 🟨 操作逻辑
    if action == "delete":
        target_basket["deleted"] = True

    elif action == "restore":
        target_basket["deleted"] = False

    elif action == "clear":
        # 清空数量和 SKU，同时更新 sku_map
        old_sku = target_basket.get("sku")
        target_basket["count"] = 0
        target_basket["sku"] = ""
        target_basket["deleted"] = False  # 确保不是禁用状态
        # 从映射表中移除旧 SKU
        if old_sku and old_sku in sku_map:
            del sku_map[old_sku]

    # 保存数据
    data["baskets"] = baskets
    data["sku_map"] = sku_map
    save_data(data)

    # ✅ 返回执行结果
    return jsonify({
        "success": True,
        "id": bid,
        "action": action,
        "message": f"{bid}号篮子操作成功：{action}"
    })


# ==========================================================
# ✅ 功能 4：重置所有篮子数量
# 前端：POST /sorting/api/reset
# ==========================================================
@bp.route("/api/reset", methods=["POST"])
def api_reset():
    data = load_data()
    baskets = data["baskets"]
    for b in baskets:
        b["count"] = 0
        b["skus"] = []     # 已有：清空篮内明细（如果你有这个字段）
        b["sku"] = ""      # 🟩 新增：清空该篮当前 SKU（给前端 hover 用）

    data["sku_map"] = {}    # 🟩 新增：清空映射，确保重置后从 1 号起重新分配

    save_data(data)
    return jsonify({"success": True, "message": "篮子重置完成"})


# ==========================================================
# ✅ 功能 5：扫码 / 手动输入 SKU 分配篮子（扩展版）
# 规则：
#   - 若 SKU 已存在：直接放入原篮子（若篮子未删除）
#   - 若 SKU 不存在：
#       1️⃣ 查找第一个未删除且空的篮子；
#       2️⃣ 若无空篮：
#             - 若总篮子数 < 80 → 自动新增篮子并分配；
#             - 若总篮子数 ≥ 80 → 返回提示“无空篮可用”
# ==========================================================
# ==========================================================
# ✅ 功能 5：扫码 / 手动输入 SKU 分配篮子（无自动扩容版）
# 规则：
#   - 若 SKU 已存在且篮子未删除 → 放回原篮子
#   - 若 SKU 不存在 → 分配第一个空篮子
#   - 若无空篮 → 提示用户“篮子数量不足，请手动添加”
# ==========================================================
# ==========================================================
# ✅ 功能 5：扫码 / 手动输入 SKU 分配篮子（升级版）
# 规则：
#   1️⃣ SKU 不区分大小写（统一转大写）
#   2️⃣ 若 SKU 已存在但篮子被禁用 → 返回提示，不重新分配
#   3️⃣ 若 SKU 不存在 → 分配第一个空篮
# ==========================================================
@bp.route("/api/assign", methods=["POST"])
def api_assign():
    req = request.get_json()
    sku = req.get("sku", "").strip()
    if not sku:
        return jsonify({"success": False, "message": "SKU 不能为空"})

    # ✅ 统一转小写，确保一致性
    sku = sku.lower()

    data = load_data()
    baskets = data["baskets"]
    sku_map = data.setdefault("sku_map", {})
    logs = data.setdefault("logs", [])

    # ==========================================================
    # ✅ STEP 1：优先检查所有篮子（包括禁用的）
    # ==========================================================
    # 有时候 sku_map 不完全同步，用篮子数据兜底
    basket_by_sku = next(
        (b for b in baskets if b.get("sku", "").lower() == sku),
        None
    )

    # 优先从 sku_map 获取
    basket_id = sku_map.get(sku)
    if basket_id:
        basket = next((b for b in baskets if b["id"] == basket_id), None)
    else:
        basket = basket_by_sku

    # ==========================================================
    # ✅ STEP 2：命中已存在的 SKU
    # ==========================================================
    if basket:
        if basket.get("deleted"):
            # 🟥 被禁用
            return jsonify({
                "success": False,
                "reason": "BASKET_DISABLED",
                "message": f"SKU {sku} 对应的 {basket['id']} 号篮子已被暂停，请先恢复再使用。"
            })

        # ✅ 启用状态 → 增加数量
        basket["count"] = basket.get("count", 0) + 1
        basket["sku"] = sku
        sku_map[sku] = basket["id"]

        # ✅ 写入日志
        logs.insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sku": sku,
            "basket": basket["id"]
        })
        logs[:] = logs[:50]

        save_data(data)
        return jsonify({
            "success": True,
            "basket": basket["id"],
            "count": basket["count"],
            "total": len(baskets),
            "logs": logs,
            "sku": sku
        })

    # ==========================================================
    # ✅ STEP 3：未分配 → 分配第一个空篮
    # ==========================================================
    available_baskets = sorted(
        [b for b in baskets if not b.get("deleted") and b.get("count", 0) == 0],
        key=lambda x: int(x["id"])
    )

    if not available_baskets:
        return jsonify({
            "success": False,
            "reason": "NO_EMPTY",
            "message": "篮子数量不足，请添加篮子后再试。"
        })

    empty_basket = available_baskets[0]
    basket_id = empty_basket["id"]
    empty_basket["sku"] = sku
    empty_basket["count"] = 1
    sku_map[sku] = basket_id

    logs.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sku": sku,
        "basket": basket_id
    })
    logs[:] = logs[:50]

    save_data(data)
    return jsonify({
        "success": True,
        "basket": basket_id,
        "count": 1,
        "total": len(baskets),
        "logs": logs,
        "sku": sku
    })


# ==========================================================
# ✅ 页面路由
# 打开 /sorting 直接加载前端 sorting.html
# ==========================================================
@bp.route("/")
def sorting_page():
    return render_template("sorting.html")


# ==========================================================
# ✅ 应用启动
# ==========================================================
def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)