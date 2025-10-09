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

    # 🟩 确保每个篮子都带上 sku 字段
    enriched_baskets = []
    for b in baskets:
        enriched_baskets.append({
            "id": b["id"],
            "count": b.get("count", 0),
            "deleted": b.get("deleted", False),
            "sku": b.get("sku", "")  # 🟩 新增关键字段
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
    req = request.get_json()
    bid = req.get("id")
    action = req.get("action")

    data = load_data()
    for b in data["baskets"]:
        if b["id"] == bid:
            if action == "delete":
                b["deleted"] = True
                b["count"] = 0
            elif action == "restore":
                b["deleted"] = False
            break

    save_data(data)
    return jsonify({"success": True, "id": bid, "action": action})


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
@bp.route("/api/assign", methods=["POST"])
def api_assign():
    req = request.get_json()
    sku = req.get("sku", "").strip()
    if not sku:
        return jsonify({"success": False, "message": "SKU 不能为空"})

    data = load_data()
    baskets = data["baskets"]
    sku_map = data.setdefault("sku_map", {})
    logs = data.setdefault("logs", [])

    # 🟩 STEP 1: 判断 SKU 是否已有归属
    if sku in sku_map:
        basket_id = sku_map[sku]
        # 原篮子若已删除，重新分配
        valid_basket = next((b for b in baskets if b["id"] == basket_id and not b["deleted"]), None)
        if not valid_basket:
            basket_id = None
        else:
            # 🟩 新增：如果历史数据里没存过该篮子的 sku，则补上（用于前端 hover 提示）
            if not valid_basket.get("sku"):
                valid_basket["sku"] = sku
    else:
        basket_id = None

    # 🟩 STEP 2: 无归属 → 分配空篮（修改后：按编号升序找最小可用篮子）
    if basket_id is None:
        # 🟢 原逻辑是 next(...)，现在改为排序后取编号最小的空篮
        available_baskets = sorted(
            [b for b in baskets if not b["deleted"] and b["count"] == 0],
            key=lambda x: int(x["id"])
        )
        if available_baskets:
            empty_basket = available_baskets[0]
            basket_id = empty_basket["id"]
            sku_map[sku] = basket_id
            empty_basket["sku"] = sku  # 🟩 新增：把该篮子的 sku 记录下来（用于前端 hover 提示）
        else:
            # 🟥 无空篮可用 → 提示前端手动增加
            return jsonify({
                "success": False,
                "reason": "NO_EMPTY",
                "message": "篮子数量不足，请添加篮子后再试。"
            })

    # 🟩 STEP 3: 数量 +1 并确保写回 sku
    for b in baskets:
        if b["id"] == basket_id:
            b["count"] += 1
            b["sku"] = sku  # 🟩 新增：确保当前篮子的 SKU 一定写回
            count = b["count"]
            break

    # 🟩 STEP 4: 写入日志
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
        "count": count,
        "total": len(baskets),
        "logs": logs,
        "sku": sku  # 🟩 已有：让前端能记录 SKU
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