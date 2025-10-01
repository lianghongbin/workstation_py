# vika_client.py
import requests
from vika_schema import translate_fields

class VikaClient:
    def __init__(self, datasheet_id: str, view_id: str = None):
        self.token = "uskI2CEJkCSNZNU2KArVUTU"
        self.datasheet_id = datasheet_id
        self.view_id = view_id
        self.base_url = f"https://api.vika.cn/fusion/v1/datasheets/{datasheet_id}/records"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def add_record(self, fields: dict):
        fields_mapped = translate_fields(self.datasheet_id, fields, direction="en2zh")
        payload = {
            "records": [{"fields": fields_mapped}],
            "fieldKey": "name",
        }
        resp = requests.post(self.base_url, headers=self._headers(), json=payload, timeout=10)
        return resp.json()

    def update_record(self, record_id: str, fields: dict):
        fields_mapped = translate_fields(self.datasheet_id, fields)
        payload = {
            "records": [{"recordId": record_id, "fields": {"处理完成": True}}],
            "fieldKey": "name"
        }

        resp = requests.patch(self.base_url, headers=self._headers(), json=payload, timeout=10)
        return resp.json()

    # === 新增：查询 ===
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