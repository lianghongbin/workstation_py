# vika_client.py
import os
import requests
import threading  # [RATE LIMIT ADDED] 线程锁用于限速
import time       # [RATE LIMIT ADDED] 控制时间间隔
from vika_schema import translate_fields
from backend.rate_limiter import limit  # ✅ 新增：全局限速器


class VikaClient:
    def __init__(self, datasheet_id: str, view_id: str = None):
        self.token = "uskI2CEJkCSNZNU2KArVUTU"
        self.datasheet_id = datasheet_id
        self.view_id = view_id
        self.base_url = f"https://api.vika.cn/fusion/v1/datasheets/{datasheet_id}/records"
        self.attachment_url = f"https://api.vika.cn/fusion/v1/datasheets/{datasheet_id}/attachments"

    def _headers(self, is_json=True):
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        if is_json:
            headers["Content-Type"] = "application/json"
        return headers

    def add_record(self, fields: dict):
        fields_mapped = translate_fields(self.datasheet_id, fields, direction="en2zh")
        payload = {
            "records": [{"fields": fields_mapped}],
            "fieldKey": "name",
        }
        limit()  # [RATE LIMIT ADDED]
        resp = requests.post(self.base_url, headers=self._headers(), json=payload, timeout=10)
        return resp.json()

    def update_record(self, record_id: str, fields: dict, convert:str = 'zh2en'):
        # ✅ 如果字段名已经是中文，就不要再映射
        # 判断方式：第一个 key 含中文字符
        first_key = list(fields.keys())[0] if fields else ""
        if any('\u4e00' <= ch <= '\u9fff' for ch in first_key) or not convert:
            fields_mapped = fields  # 已是中文，不映射
        else:
            fields_mapped = translate_fields(self.datasheet_id, fields, direction =convert)

        print(fields_mapped)
        payload = {
            "records": [{"recordId": record_id, "fields": fields_mapped}],
            "fieldKey": "name"
        }

        limit()  # [RATE LIMIT ADDED]
        resp = requests.patch(self.base_url, headers=self._headers(), json=payload, timeout=10)
        return resp.json()

    # === 查询 ===
    def query_records(self, params: dict | None = None):
        """
        查询 Vika 数据，并自动做 schema 映射/类型转换
        """
        # 默认参数
        q = {"fieldKey": "name"}
        if self.view_id:
            q["viewId"] = self.view_id
        if params:
            q.update(params)

        limit()  # [RATE LIMIT ADDED]
        resp = requests.get(self.base_url, headers=self._headers(), params=q, timeout=15)
        try:
            data = resp.json()
        except Exception:
            return {"success": False, "code": resp.status_code, "message": "Invalid JSON from Vika"}

        if not resp.ok or not data.get("success"):
            return {
                "success": False,
                "code": data.get("code") or resp.status_code,
                "message": data.get("message"),
                "data": data.get("data"),
                "total": 0
            }

        # === 做 schema 映射 ===
        records = []
        for rec in data["data"].get("records", []):
            fields = rec.get("fields", {})
            mapped = translate_fields(self.datasheet_id, fields)
            mapped["recordId"] = rec.get("recordId")
            records.append(mapped)

        return {
            "success": True,
            "code": 200,
            "message": "ok",
            "data": records,
            "total": data.get("data").get("total")
        }

    # 文件上传
    def upload_attachment(self, file_path: str) -> dict:
        """
        上传附件到 Vika datasheet，返回文件信息
        """
        with open(file_path, "rb") as f:
            files = {"file": f}
            limit()  # [RATE LIMIT ADDED]
            resp = requests.post(self.attachment_url, headers=self._headers(False), files=files, timeout=30)

        result = resp.json()
        if not resp.ok or not result.get("success"):
            raise RuntimeError(f'附件上传失败: {resp.status_code}, {result}')

        # data 是一个 list，取第一个文件
        return result["data"]

    # 批量上传附件
    def upload_attachments(self, file_paths: list[str]) -> list[dict]:
        """
        批量上传多个附件（仅上传，不绑定记录）。
        :param file_paths: 本地文件路径列表
        :return: 每个上传成功文件的 data 对象列表
        """
        if not file_paths:
            raise ValueError("file_paths 不能为空")

        uploaded_files: list[dict] = []

        for file_path in file_paths:
            if not os.path.isfile(file_path):
                print(f"[WARN] 跳过无效文件路径: {file_path}")
                continue

            file_info = self.upload_attachment(file_path)  # 内部已限速
            uploaded_files.append(file_info)
            time.sleep(1.2)  # ⚠️ 加这一句，每张图之间等待 1.2s，彻底防止 429
        return uploaded_files

    # 上传附件，并直接绑定到收货记录上
    def update_record_with_attachment(
        self,
        match_field_name: str,
        match_field_value: str,
        attachment_field_name: str,
        file_paths: list[str],
    ) -> dict:
        """
        根据任意字段匹配记录，并上传多个附件追加到指定字段。
        示例：
          update_record_with_attachment("产品条码", "A123456", "附件", [...])
          update_record_with_attachment("recordId", "recXXXXXX", "异常图片", [...]) ✅ 兼容 recordId 模式

        参数:
            match_field_name: 匹配字段名（例如 '产品条码' 或 'recordId'）
            match_field_value: 匹配字段的值（例如 'A123456' 或 'recXXXXXX'）
            attachment_field_name: 要更新的字段名（例如 '异常图片'）
            file_paths: 要上传的本地文件路径列表
        """
        if not file_paths:
            raise ValueError("file_paths 不能为空")

        # 1️⃣ 上传多个附件
        uploaded_files = self.upload_attachments(file_paths)

        # 2️⃣ 查询匹配记录
        # =====================================================
        # ⚠️ 关键修复：
        # 如果 match_field_name == "recordId"，不能用 filterByFormula，
        # 否则会报 “参数异常”。要改用 recordIds 参数。
        # =====================================================
        if match_field_name == "recordId":
            params = {
                "fieldKey": "name",
                "recordIds": match_field_value
            }
        else:
            params = {
                "fieldKey": "name",
                "filterByFormula": f'{{{match_field_name}}} = "{match_field_value}"'
            }

        limit()  # [RATE LIMIT ADDED]
        resp = requests.get(self.base_url, headers=self._headers(), params=params, timeout=10)

        try:
            data = resp.json()
        except Exception:
            raise RuntimeError(f"❌ 查询返回非法 JSON: {resp.text[:300]}")

        if not resp.ok or not data.get("success"):
            raise RuntimeError(f'查询记录失败: {resp.status_code}, {data}')

        records = data["data"].get("records", [])
        if not records:
            raise ValueError(f'未找到匹配记录: {match_field_name}={match_field_value}')

        # ✅ recordId 精确匹配时，直接取第一条记录
        target_record_id = records[0]["recordId"]
        old_fields = records[0].get("fields", {})
        old_attachments = old_fields.get(attachment_field_name, []) or []

        # 3️⃣ 合并旧附件 + 新附件
        new_attachments = old_attachments + uploaded_files

        # 4️⃣ 更新记录（PATCH）
        payload = {
            "records": [
                {
                    "recordId": target_record_id,
                    "fields": {
                        attachment_field_name: new_attachments
                    }
                }
            ]
        }

        limit()  # [RATE LIMIT ADDED]
        resp = requests.patch(self.base_url, headers=self._headers(), json=payload, timeout=30)
        try:
            result = resp.json()
        except Exception:
            raise RuntimeError(f"❌ 更新返回非法 JSON: {resp.text[:300]}")

        if not resp.ok or not result.get("success"):
            raise RuntimeError(f'更新记录失败: {resp.status_code}, {result}')

        # 5️⃣ 返回详细结果
        return {
            "success": True,
            "message": f"文件追加成功（新增 {len(uploaded_files)} 个）",
            "record_id": target_record_id,
            "matched_field": match_field_name,
            "matched_value": match_field_value,
            "uploaded": [f.get('name') for f in uploaded_files],
            "data": result.get("data"),
        }

    def query_abnormal_records(self):
        """
        查询 receiver 表中异常字段为 True 的记录。
        """
        filter_formula = "{异常} = TRUE()"
        return self.query_records(params={
            "fieldKey": "name",
            "filterByFormula": filter_formula
        })