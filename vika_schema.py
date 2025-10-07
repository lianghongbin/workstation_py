# vika_schema.py

from __future__ import annotations

# 英文 -> 中文 的“设计映射”（你原来就有）
FIELD_MAPS = {
    "dstl0nkkjrg2hlXfRk": {   # 出货数据表
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
    },

    # ✅ 新增收货数据表
    "dstsnDVylQhjuBiSEo": {
        "entryDate": "入仓时间",
        "customerId": "客户代码",
        "packageNo": "入仓包裹单号",
        "packageQty": "单个包裹数量",
        "remark": "备注",
        "abnormalPhotos": "异常图片",
        "abnormal": "异常",
    },
}

# 字段类型（用于类型转换；按需补全）
FIELD_TYPES = {
    "dstl0nkkjrg2hlXfRk": {
        "barcode": "text",
        "processed": "boolean",   # 如果是勾选/单选返回布尔
        "cartons": "number",
        "qty": "number",
        "weight": "number",
        "spec": "text",
        "remark": "text",
        "createdAt": "datetime",  # 这里先不做复杂解析，保持原值即可
        "changeLabels": "text",
        "fbaLabels": "text",
    },

    "dstsnDVylQhjuBiSEo": {
        "entryDate": "datetime",   # 入仓时间
        "customerId": "text",      # 客户代码
        "packageNo": "text",       # 入仓包裹单号
        "packageQty": "number",    # 单个包裹数量
        "remark": "text",          # 备注
        "abnormalPhotos": "text",
        "abnormal": "boolean"
    },
}

def _coerce_value(ftype: str | None, v):
    if ftype == "number":
        # 空字符串 -> None；其余尽量转 int/float，失败保留原值
        try:
            if isinstance(v, str) and v.strip() == "":
                return None
            s = str(v)
            return float(s) if "." in s else int(s)
        except Exception:
            return v
    if ftype == "boolean":
        # 兼容 'true'/'false'/'1'/'0'/True/False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "yes", "y", "on"):
                return True
            if s in ("false", "0", "no", "n", "off", ""):
                return False
        return bool(v)
    # 其他类型（text/datetime/array/attachment…）先原样返回
    return v

def translate_fields(datasheet_id: str, fields: dict, *, direction: str = "zh2en") -> dict:
    """
    把 Vika 返回的 fields 做键名翻译 + 类型转换。
    direction:
      - 'zh2en': 中文 -> 英文（**大多数场景用这个**）
      - 'en2zh': 英文 -> 中文
    """
    type_map = FIELD_TYPES.get(datasheet_id, {})
    fmap = FIELD_MAPS.get(datasheet_id)

    if not fmap:
        raise KeyError(f"[translate_fields] 未配置 datasheet 映射: {datasheet_id}")
    # 方向选择：默认把中文键翻成英文键
    if direction == "zh2en":
        mapping = {zh: en for en, zh in fmap.items()}   # 反向字典
    elif direction == "en2zh":
        mapping = dict(fmap)
    else:
        raise ValueError(f"非法 direction: {direction}")
    out = {}

    # 逐个把“源键 -> 目标键”
    for src_key, value in (fields or {}).items():
        target_key = mapping.get(src_key, src_key)
        if direction == "en2zh":
            # target_key=中文，类型表里只有英文 -> 用 src_key
            ftype = type_map.get(src_key)
        else:
            # target_key=英文，直接查
            ftype = type_map.get(target_key)
        out[target_key] = _coerce_value(ftype, value)

    return out