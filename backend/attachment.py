# backend/receiver.py
import threading
from photo_manage import find_photos_by_barcode
from loguru import logger


from flask import Blueprint, request, jsonify
from vika_client import VikaClient

bp = Blueprint("attachment", __name__)
vika = VikaClient("dstsnDVylQhjuBiSEo")
photo_path = "./images"

@bp.route("/attachment", methods=["POST"])
def trigger_upload():
    """
    HTTP 请求入口：触发 barcode 附件上传任务
    """
    data = request.get_json(force=True)
    barcode = data.get("barcode")
    if not barcode:
        return jsonify({"success": False, "message": "缺少 barcode 参数"}), 400

    # 启动后台线程
    thread = threading.Thread(target=async_upload_task, args=(barcode,))
    thread.daemon = True
    thread.start()

    # 立即响应
    return jsonify({
        "success": True,
        "message": f"已触发 barcode={barcode} 的附件上传任务"
    })

#后台进程
def async_upload_task(barcode: str):
    """后台线程任务：查找并上传附件"""

    logger.info(f"[任务开始] barcode={barcode}")

    try:
        # 找目录下所有 jpg/jpeg 文件
        file_paths = find_photos_by_barcode(barcode)
        if not file_paths:
            logger.info(f"没有找到 {barcode} 相关联的图片.")
            return

        # 调用 Vika 上传绑定
        result = vika.update_record_with_attachment(
            match_field_name="产品条码",
            match_field_value=barcode,
            attachment_field_name="异常照片",
            file_paths=file_paths
        )

        logger.info(f"[任务完成] {barcode} 关联图片上传结果: {result}")

    except Exception as e:
        logger.error(f"上传 {barcode} 的异常图片时出错：{e}")
