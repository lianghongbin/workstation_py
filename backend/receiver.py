# backend/receiver.py
from flask import Blueprint, request, jsonify, render_template
from db.database import Database

bp = Blueprint("receiver", __name__)
db = Database()

@bp.route("/receiver", methods=["GET"])
def receiver_page():
    """收货页面"""
    return render_template("receiver.html")

@bp.route("/receiver", methods=["POST"])
def add_receiver():
    """
    提交收货表单
    请求体（application/json 或表单）应包含:
    {
        "entryDate": "2025-09-30",
        "customerId": "CUST001",
        "packageNo": "PKG123",
        "packageQty": 5,
        "remark": "测试备注"
    }
    """
    try:
        data = request.get_json() if request.is_json else request.form

        entryDate = data.get("entryDate")
        customerId = data.get("customerId")
        packageNo = data.get("packageNo")
        packageQty = data.get("packageQty")
        remark = data.get("remark", "")

        if not (entryDate and customerId and packageNo and packageQty):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400

        db.add_receive(entryDate, customerId, packageNo, int(packageQty), remark)

        return jsonify({"success": True, "message": "收货记录添加成功"})
    except Exception as e:
        return jsonify({"success": False, "message": f"添加失败: {str(e)}"}), 500

@bp.route("/receiver/list", methods=["GET"])
def list_receiver():
    """获取收货记录列表"""
    try:
        records = db.get_all_receive()
        result = []
        for r in records:
            result.append({
                "id": r[0],
                "entryDate": r[1],
                "customerId": r[2],
                "packageNo": r[3],
                "packageQty": r[4],
                "remark": r[5],
                "synced": r[6],
                "createdAt": r[7],
            })
        return jsonify({"success": True, "records": result})
    except Exception as e:
        return jsonify({"success": False, "message": f"查询失败: {str(e)}"}), 500