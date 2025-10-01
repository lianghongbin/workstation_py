# ship_query.py  （完整覆盖）

from flask import Blueprint, render_template, request, jsonify
from backend.print_service import PrintService
from vika_client import VikaClient

import requests
import math

# === 保持 Blueprint 名称与现有一致 ===
bp = Blueprint("ship_query", __name__)
printer = PrintService()
vika = VikaClient("dstl0nkkjrg2hlXfRk")

@bp.route("/ship_query", methods=["GET"])
def ship_query_page():
    """
    页面：保持 ship-query.html 界面不变
    """
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "").strip()
    page_size = 15

    params = {
        "pageNum": page,
        "pageSize": page_size,
        "sort": '{"field":"提交时间","order":"desc"}'
    }
    if search:
        params["filterByFormula"] = f'AND({{处理完成}}=0, find("{search}", {{产品条码}}) > 0)'
    else:
        params["filterByFormula"] = '{处理完成}=0'

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
            "ship-query.html",
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
    return render_template("ship-query.html", **payload)

@bp.route("/ship_query/api/print", methods=["POST"])
def api_print_label():
    """
    接收前端打印申请，调用本机默认打印机
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "message": "缺少打印申请"}), 400

        ok = printer.print_label(data)
        if ok:
            return jsonify({"success": True, "message": "打印任务已提交"})
        else:
            return jsonify({"success": False, "message": "未检测到打印机，已打开系统设置"})

    except Exception as e:
        return jsonify({"success": False, "message": f"打印接口异常: {e}"}), 500


@bp.route("/ship_query/process", methods=["POST"])
def ship_process():
    """
    将退货申请标识已经处理完成
    """
    try:
        data = request.get_json(force=True)  # {record: {...}}
        record = data.get("record") or {}
        record_id = record.get("recordId")
        print(record_id)

        if not record_id:
            return jsonify({"success":False, "message": "缺少 recordId"}), 400

        # 直接调用我们封装好的 class 方法
        resp = vika.update_record(record_id, {"处理完成": True})

        if not resp.get("success"):
            print(resp.get("message"))
            return jsonify({"success": False, "message": resp.get("message")}), 502

        return jsonify({"success": True, "message": "成功设置处理完成状态！"})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"处理失败: {e}"}), 500