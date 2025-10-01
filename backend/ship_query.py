# ship_query.py  （完整覆盖）

from flask import Blueprint, render_template, request, jsonify
from db.database import Database
from backend.print_service import PrintService

import requests
import math

# === 保持 Blueprint 名称与现有一致 ===
bp = Blueprint("ship_query", __name__)
db = Database()
printer = PrintService()


# === Vika 配置（与 VikaShipment 业务逻辑保持一致） ===
_VIKA_TOKEN = "uskI2CEJkCSNZNU2KArVUTU"
_DATASHEET_ID = "dstl0nkkjrg2hlXfRk"
_FIELD_MAP = {
    "barcode": "产品条码",
    "processed": "处理完成",
    "cartons": "箱数",
    "qty": "每箱数量",
    "weight": "重量",
    "spec": "箱规",
    "remark": "备注",
    "createdAt": "提交时间",
    "changeLabels": "换标标签",
    "fbaLabels": "FBA标签",
}


def _vika_headers():
    return {
        "Authorization": f"Bearer {_VIKA_TOKEN}",
        "Content-Type": "application/json",
    }


@bp.route("/ship_query", methods=["GET"])
def ship_query_page():
    """
    页面：保持 ship-query.html 界面不变
    """
    return render_template("ship-query.html")


@bp.route("/ship_query/api/shipments", methods=["GET"])
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