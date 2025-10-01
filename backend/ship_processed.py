# ship_query.py  （完整覆盖）

from flask import Blueprint, render_template, request, jsonify
from vika_client import VikaClient


# === 保持 Blueprint 名称与现有一致 ===
bp = Blueprint("ship_processed", __name__)
vika = VikaClient("dstl0nkkjrg2hlXfRk")

@bp.route("/ship_processed")
def ship_processed_page():
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "").strip()
    page_size = 15

    params = {
        "pageNum": page,
        "pageSize": page_size,
        "sort": '{"field":"提交时间","order":"desc"}'
    }

    if search:
        params["filterByFormula"] = f'AND({{处理完成}}=1, find("{search}", {{产品条码}}) > 0)'
    else:
        params["filterByFormula"] = '{处理完成}=1'

    result = vika.query_records(params)
    args = request.args.to_dict()

    if not result.get("success"):
        # ✅ 在 Vika 返回的基础上封装成你要的结构
        payload = {
            "records": [],
            "page": page,
            "total_pages": 1,
            "total": 0,
            "search": search,
            "query_args": args
        }
        return render_template(
            "ship-processed.html",
            **payload
        )

    records = result["data"]
    total = result['total']

    # 计算总页数（至少为 1）
    total_pages = max(1, (total + page_size - 1) // page_size)

    # 保留查询参数（除了 page）
    args = request.args.to_dict()
    args.pop("page", None)

    # ✅ 在 Vika 返回的基础上封装成你要的结构
    payload = {
        "records": records,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "search": search,
        "query_args": args
    }
    return render_template("ship-processed.html", **payload)


@bp.route("/ship_query/process", methods=["POST"])
def ship_process():
    """
    将退货申请标识已经处理完成
    """
    try:
        data = request.get_json(force=True)  # {record: {...}}
        record = data.get("record") or {}
        record_id = record.get("recordId")
        print("ship_process--------")
        if not record_id:
            return jsonify({"error": "缺少 recordId"}), 400

        # ✅ 调用 Vika 封装类
        result = vika.update_record(record_id, {"处理完成": True})

        print(result)
        if not result.get("success"):
            return jsonify({"error": result}), 502

        return jsonify({"success": True, "message":"设置完成状态成功！"})
    except Exception as e:
        return jsonify({"success": False, "message": e}), 500