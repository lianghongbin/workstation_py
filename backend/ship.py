from flask import Blueprint, render_template, request, jsonify
from db.database import Database
from vika_client import VikaClient

# 定义 Blueprint，挂载到 /ship 路径
bp = Blueprint("ship", __name__)
db = Database()


vika = VikaClient("dstl0nkkjrg2hlXfRk")

@bp.route("/ship", methods=["GET"])
def ship_page():
    return render_template("ship.html")

# 2️⃣ 处理表单提交
@bp.route("/ship", methods=["POST"])
def add_ship():
    """
        新增一条出货记录到 Vika 在线表格
        """
    print(['ship add_ship'])
    try:
        data = request.get_json(force=True)
        result = vika.add_record(data.get("fields", {}))
        if not result.get("success"):
            return jsonify({"success": False, "message": "出货申请提交错误"})
        return jsonify({"success": True, "message": "出货申请成功！"})
    except Exception as e:
        return jsonify({"success": False, "message": "出货申请出错！"})