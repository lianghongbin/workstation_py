# ship_query.py  （完整覆盖）

from flask import Blueprint, render_template, request, jsonify
from backend.print_service import PrintService
from vika_client import VikaClient

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
    print(result)

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


# ========================================
# 🚀 2️⃣ 修改装箱数据
# ========================================
@bp.route("/ship_query/packing/update", methods=["POST"])
def update_packing_data():
    """
    修改装箱数据（数量、箱数、QTY、重量、箱规）
    """
    try:
        data = request.get_json(force=True)
        record_id = data.get("recordId")
        fields = data.get("fields", {})

        # ✅ 更新数据
        update_result = vika.update_record(record_id, fields, convert='en2zh')
        if not update_result.get("success"):
            print(update_result)
            return jsonify({"success": False, "message": f"更新失败：{update_result}"})

        return jsonify({"success": True, "message": "装箱数据已更新"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


import requests
from flask import Response, request

@bp.route("/ship_query/file/view", methods=["GET"])
def proxy_vika_file():
    """
    🔄 从 Vika CDN 拉取文件并转发（去掉 Referer 限制）
    示例：
        /ship_query/file/view?url=https://s1.vika.cn/space/2025/10/10/xxxxxx
    """
    file_url = request.args.get("url")
    if not file_url:
        return Response("缺少参数 url", status=400)

    try:
        headers = {
            "User-Agent": request.headers.get("User-Agent", "Mozilla/5.0"),
            "Referer": "",  # ✅ 不带 Referer 绕过403
        }
        resp = requests.get(file_url, headers=headers, stream=True, timeout=15)
        if resp.status_code != 200:
            return Response(f"下载失败: {resp.status_code}", status=resp.status_code)

        return Response(
            resp.iter_content(8192),
            content_type=resp.headers.get("Content-Type", "application/octet-stream"),
        )
    except Exception as e:
        return Response(f"访问异常: {e}", status=500)