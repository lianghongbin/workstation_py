# ship_query.py  （完整覆盖）

from flask import Blueprint, render_template, request, jsonify
from db.database import Database
from vika_client import VikaClient

import requests
import math

# === 保持 Blueprint 名称与现有一致 ===
bp = Blueprint("ship_processed", __name__)
db = Database()

vika = VikaClient("dstl0nkkjrg2hlXfRk")

@bp.route("/ship_processed", endpoint="ship_processed_page")
def ship_processed_page():
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "").strip()
    page_size = 3

    params = {
        "pageNum": page,
        "pageSize": page_size,
        "sort": '{"field":"提交时间","order":"desc"}'
    }
    if search:
        params["filterByFormula"] = f'AND({{处理完成}}=1, find("{search}", {{产品条码}}) > 0)'

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

@bp.route("/ship-query/api/shipments", methods=["GET"])
def api_query_shipments():
    """
    查询接口：等价于 VikaShipment.queryShipments
    参数：
      - page: 默认 1
      - pageSize: 默认 20
      - search: 模糊查询（产品条码）
    返回：
      { page, totalPages, records: [ {barcode, cartons, qty, weight, spec, remark, createdAt, files[]} ] }
    """
    try:
        page = max(int(request.args.get("page", 1)), 1)
        page_size = max(int(request.args.get("pageSize", 20)), 1)
        search = (request.args.get("search") or "").strip()

        params = {
            "pageNum": page,
            "pageSize": page_size,
            "fieldKey": "name",  # 返回中文字段名
            "sort": '{"field": "提交时间", "order": "desc"}',
        }
        if search:
            params["filterByFormula"] = f'find("{search}", {{{_FIELD_MAP["barcode"]}}}) > 0'

        url = f"https://api.vika.cn/fusion/v1/datasheets/{_DATASHEET_ID}/records"
        resp = requests.get(url, headers=_vika_headers(), params=params, timeout=20)
        data = resp.json()

        if not data.get("success"):
            code = data.get("code")
            msg = data.get("message") or "Vika API 查询失败"
            return jsonify({"error": f"Vika API 查询失败: code={code}, msg={msg}"}), 502

        raw_records = (data.get("data") or {}).get("records") or []
        total = (data.get("data") or {}).get("total") or 0

        records = []
        for rec in raw_records:
            fields = rec.get("fields") or {}

            change_files = []
            fba_files = []
            for f in fields.get(_FIELD_MAP["changeLabels"], []) or []:
                change_files.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "url": f.get("url"),
                    "preview": f.get("preview"),
                    "mimeType": f.get("mimeType"),
                    "size": f.get("size"),
                })

            for f in fields.get(_FIELD_MAP["fbaLabels"], []) or []:
                fba_files.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "url": f.get("url"),
                    "preview": f.get("preview"),
                    "mimeType": f.get("mimeType"),
                    "size": f.get("size"),
                })

            records.append({
                "recordId": rec.get("recordId"),
                "barcode": fields.get(_FIELD_MAP["barcode"], ""),
                "processed": fields.get(_FIELD_MAP['processed'], ""),
                "cartons": fields.get(_FIELD_MAP["cartons"], ""),
                "qty": fields.get(_FIELD_MAP["qty"], ""),
                "weight": fields.get(_FIELD_MAP["weight"], ""),
                "spec": fields.get(_FIELD_MAP["spec"], ""),
                "remark": fields.get(_FIELD_MAP["remark"], ""),
                "createdAt": fields.get(_FIELD_MAP["createdAt"]) or rec.get("createdAt"),
                "changeLabels": change_files,
                "fbaLabels": fba_files,
            })

        return jsonify({
            "page": page,
            "totalPages": math.ceil(total / page_size) if page_size else 0,
            "records": records,
        })
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500


@bp.route("/ship-query/api/print", methods=["POST"])
def api_print_label():
    """
    打印接口占位：保持交互不变（点击“打印”会调用该接口）
    这里仅回传成功。若后续需要真正调用打印机，可在此实现。
    """
    try:
        _ = request.get_json(force=True)  # 结构：{record: {...}}
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"打印失败: {e}"}), 400


@bp.route("/ship-query/process", methods=["POST"])
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

        url = f"https://api.vika.cn/fusion/v1/datasheets/{_DATASHEET_ID}/records"
        headers = _vika_headers()
        payload = {
            "records": [
                {
                    "recordId": record_id,
                    "fields": {
                        "处理完成": True
                    }
                }
            ],
            "fieldKey": "name"
        }

        resp = requests.patch(url, headers=headers, json=payload, timeout=10)
        result = resp.json()
        print(result)
        if not resp.ok or not result.get("success"):
            return jsonify({"error": result}), 502

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"处理失败: {e}"}), 500