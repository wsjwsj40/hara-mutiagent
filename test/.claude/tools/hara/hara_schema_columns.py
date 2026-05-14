from __future__ import annotations

from typing import Any, Mapping

NAN_VALUES = {"", "nan", "none", "null", "n/a", "na", "不适用", "无"}

DERIVE_MF_COLUMNS = [
    "No.",
    "子功能",
    "功能丧失",
    "过大",
    "过早",
    "过小",
    "过晚",
    "非预期激活",
    "卡滞",
    "方向错误",
]

MF_VEHICLE_HAZARDS_COLUMNS = [
    "No.",
    "Milf_ID",
    "故障描述",
    "整车级危害",
    "备注",
]

HARA_COLUMNS = [
    "List_No",
    "MF_ID",
    "故障描述",
    "整车危害",
    "道路类型",
    "道路条件",
    "环境条件",
    "车辆状态",
    "车速（km/h）",
    "特殊要素",
    "附加条件",
    "驾驶员是否在车上",
    "危害事件",
    "E-解释",
    "暴露频率'E'",
    "有风险的人员",
    "可能的后果('S'的理由)",
    "Severity 'S'",
    "C-解释",
    "控制能力 'C'",
    "结果ASIL",
    "安全目标",
    "安全状态",
    "FTTI(ms)",
    "备注",
]

SG_SUM_COLUMNS = [
    "SG_No",
    "MF_ID",
    "安全目标",
    "ASIL Level",
    "安全状态",
    "操作模式",
    "FTTI(ms)",
    "Comments",
]

SHEET_COLUMNS = {
    "DeriveMF": DERIVE_MF_COLUMNS,
    "MF and Vehicle Hazards": MF_VEHICLE_HAZARDS_COLUMNS,
    "HARA": HARA_COLUMNS,
    "SG_Sum": SG_SUM_COLUMNS,
}

EXCEL_DISPLAY_HEADERS = {
    "暴露频率'E'": "暴露频率\n'E'",
    "可能的后果('S'的理由)": "可能的后果\n('S'的理由)",
}

ALIASES = {
    "List_No": ["List_No", "List No", "ListNo", "序号"],
    "MF_ID": ["MF_ID", "MF ID", "MFID", "mf_id"],
    "故障描述": ["故障描述", "功能故障", "malfunction", "malfunction_description"],
    "整车危害": ["整车危害", "整车级危害", "vehicle_hazard", "Vehicle Hazard"],
    "整车级危害": ["整车级危害", "整车危害", "vehicle_hazard", "Vehicle Hazard"],
    "道路类型": ["道路类型", "road_type"],
    "道路条件": ["道路条件", "road_condition"],
    "环境条件": ["环境条件", "environment_condition"],
    "车辆状态": ["车辆状态", "vehicle_state"],
    "车速（km/h）": ["车速（km/h）", "车速(km/h)", "车速", "speed", "vehicle_speed"],
    "特殊要素": ["特殊要素", "special_element", "special_elements"],
    "附加条件": ["附加条件", "additional_condition", "additional_conditions"],
    "驾驶员是否在车上": ["驾驶员是否在车上", "driver_present", "driver_in_vehicle"],
    "危害事件": ["危害事件", "hazardous_event"],
    "E-解释": ["E-解释", "E解释", "E_reason", "E rationale"],
    "暴露频率'E'": ["暴露频率'E'", "暴露频率 'E'", "暴露频率\n'E'", "暴露频率‘E’", "暴露频率 E", "暴露频率", "E", "'E'", "Exposure", "exposure"],
    "有风险的人员": ["有风险的人员", "risk_persons", "persons_at_risk"],
    "可能的后果('S'的理由)": ["可能的后果('S'的理由)", "可能的后果\n('S'的理由)", "可能的后果", "('S'的理由)", "S-解释", "S解释", "S_reason", "S rationale"],
    "Severity 'S'": ["Severity 'S'", "Severity\n'S'", "Severity", "S", "'S'", "severity"],
    "C-解释": ["C-解释", "C解释", "C_reason", "C rationale"],
    "控制能力 'C'": ["控制能力 'C'", "控制能力\n'C'", "控制能力", "C", "'C'", "controllability"],
    "结果ASIL": ["结果ASIL", "结果 ASIL", "ASIL", "ASIL等级", "ASIL Level", "asil", "result_asil"],
    "安全目标": ["安全目标", "safety_goal"],
    "安全状态": ["安全状态", "safe_state"],
    "FTTI(ms)": ["FTTI(ms)", "FTTI", "ftti_ms", "FTTI_ms"],
    "备注": ["备注", "comment", "comments", "note", "notes"],
    "Milf_ID": ["Milf_ID", "MF_ID", "MFID", "milf_id"],
    "MF_ID": ["MF_ID", "MF ID", "MFID", "milf_id", "Milf_ID"],
    "ASIL Level": ["ASIL Level", "ASIL", "结果ASIL", "结果 ASIL"],
    "Comments": ["Comments", "备注", "comment", "comments"],
    "过大": ["过大", "过大/过早", "more_than_intended", "too_much"],
    "过早": ["过早", "过大/过早", "too_early"],
    "过小": ["过小", "过小/过晚", "less_than_intended", "too_little"],
    "过晚": ["过晚", "过小/过晚", "too_late"],
}


def is_nan_like(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in NAN_VALUES


def normalize_value(value: Any) -> Any:
    return "nan" if is_nan_like(value) else value


def compact_key(key: str) -> str:
    return str(key).replace("\n", "").replace(" ", "").replace("　", "").strip()


def build_key_index(row: Mapping[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key in row.keys():
        index[str(key)] = str(key)
        index[compact_key(str(key))] = str(key)
    return index


def get_by_alias(row: Mapping[str, Any], canonical: str) -> Any:
    key_index = build_key_index(row)
    candidates = [canonical] + ALIASES.get(canonical, [])
    for candidate in candidates:
        if candidate in row:
            return row[candidate]
        compact = compact_key(candidate)
        if compact in key_index:
            return row[key_index[compact]]
    return None


def normalize_row(row: Mapping[str, Any], columns: list[str]) -> dict[str, Any]:
    normalized = {}
    for column in columns:
        normalized[column] = normalize_value(get_by_alias(row, column))
    return normalized


def normalize_rows(rows: list[Mapping[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    return [normalize_row(row, columns) for row in rows if isinstance(row, Mapping)]
