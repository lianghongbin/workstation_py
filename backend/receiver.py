# backend/receiver.py
from flask import Blueprint, request, jsonify, render_template
from vika_client import VikaClient

bp = Blueprint("receiver", __name__)
vika = VikaClient("dstsnDVylQhjuBiSEo")

@bp.route("/receiver", methods=["GET"])
def receiver_page():
    """收货页面"""
    return render_template("receiver.html")


@bp.route("/receiver", methods=["POST"])
def add_receiver():
    """
    提交收货表单 -> 写入 Vika 在线表格
    """
    try:
        data = request.get_json(force=True)
        fields = data.get("fields", {})
        package_no = fields.get("packageNo")

        # ✅ 非空检查
        if not package_no:
            return jsonify({"success": False, "message": "入仓包裹单号不能为空"})

        # ✅ 重复检查
        filter_formula = f"{{入仓包裹单号}} = '{package_no}'"
        check = vika.query_records(params={"fieldKey": "name", "filterByFormula": filter_formula})
        if check.get("success") and check.get("data"):
            return jsonify({"success": False, "message": f"入仓包裹单号重复：{package_no}"})

        # ⬇️ 下面全是你原来的逻辑，不动
        result = vika.add_record(fields)

        if not result.get("success"):
            return jsonify({"success": False, "message": "收货提交错误"})
        return jsonify({"success": True, "message": "收货提交成功！"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@bp.route("/receiver/list", methods=["GET"])
def list_receiver():
    """
    获取收货记录列表 -> 直接查询 Vika 在线表格
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
        params["filterByFormula"] = 'find("{search}", {{产品条码}}) > 0)'

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
            "receiver-query.html",
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
    return render_template("receiver-query.html", **payload)