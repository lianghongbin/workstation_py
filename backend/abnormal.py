# backend/abnormal.py
from flask import Blueprint, request, jsonify, render_template
from vika_client import VikaClient

bp = Blueprint("abnormal", __name__)
vika = VikaClient("dstsnDVylQhjuBiSEo")

@bp.route("/abnormal", methods=["GET"])
def abnormal_page():
    """收货页面"""
    return render_template("abnormal.html")


@bp.route("/abnormal", methods=["POST"])
def set_abnormal():
    """
    设置异常包裹状态（打勾/取消）
    - 先查询包裹是否存在；
    - 若状态相同则直接返回成功；
    - 若不同，则更新“异常”字段。
    """
    try:
        data = request.get_json(force=True)
        fields = data.get("fields", {})  # ✅ 保留原前端结构
        package_no = fields.get("packageNo")
        abnormal = bool(fields.get("abnormal"))

        # ✅ 第一步：查询包裹记录
        filter_formula = f"{{入仓包裹单号}} = '{package_no}'"
        query_result = vika.query_records(params={
            "fieldKey": "name",
            "filterByFormula": filter_formula
        })

        if not query_result.get("success"):
            return jsonify({"success": False, "message": "查询失败，请稍后重试"})

        records = query_result.get("data", [])
        print(records)
        if not records:
            return jsonify({"success": False, "message": f"未找到包裹单号：{package_no}"})

        record = records[0]
        record_id = record.get("recordId")
        current_abnormal = record.get("abnormal")

        print(current_abnormal)

        # ✅ 【新增逻辑】防止重复标记相同单号
        # 如果数据库里已经有这个包裹单号，并且状态不是 None，
        # 则说明已经被操作过一次，提示用户无需再次操作。
        if current_abnormal:
            return jsonify({
                "success": False,
                "message": f"包裹单号 {package_no} 已经设置过异常！"
            })

        # ✅ 第二步：如果状态未变化，直接返回成功
        if current_abnormal == abnormal:
            return jsonify({
                "success": True,
                "message": f"包裹 {package_no} 异常状态未变化（已为 {'异常' if abnormal else '正常'}）"
            })

        # ✅ 第三步：更新异常状态（复用现有 update_record）
        update_result = vika.update_record(record_id, {"异常": abnormal})

        # 注意：你的 update_record() 方法默认写死了 {"处理完成": True}
        # 所以我们需要对它稍微优化下（允许外部传入字段）
        # 或者这里直接调用新的轻量方法 update_records_by_formula()
        if not update_result.get("success"):
            return jsonify({
                "success": False,
                "message": f"更新失败：{update_result.get('message', '未知错误')}"
            })

        return jsonify({
            "success": True,
            "message": f"包裹 {package_no} 异常状态已更新为 {'异常' if abnormal else '正常'}"
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})