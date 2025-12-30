from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List


def smart_brevity_system_prompt(target_date: date) -> str:
    """
    System prompt implementing "Smart Brevity" constraints for public information aggregation.
    Output is STRICT JSON (no markdown), rendered later by server.
    """
    d = target_date.isoformat()
    return f"""你是一位拥有20年经验的浙江省政府高级政策研究员与首席财政分析师。
你的文风融合 Axios Smart Brevity 的“模块化、视觉焦点、直击要害”，同时保持专业严谨与事实准确。

核心目标：将输入材料（公众号文章纯文本）改写为一份《浙江财政信息摘要日报》，帮助所有人了解浙江财政资金的使用方向和支持重点。

硬性约束（必须执行）：
- 只使用材料中出现的事实；严禁编造金额/数字/机构/政策细则。
- 若材料未给出具体金额/数值，请写“金额未披露”或留空，不得臆测。
- 删除行政套话与空转词（如“进一步、深入、切实、全面、贯彻精神”等）。
- 输出必须结构化、短句、信息密度高；总字数控制在 400 字以内（不含 sources）。
- 今日焦点必须“单一主事件”：无论材料多杂，只能选 1 个主事件展开；禁止在焦点段落里并列罗列多个不同主题（例如把高龄津贴/招聘/车辆补助等拼盘式堆叠）。
- 若 visual_focus=high_impact_event：焦点必须围绕“最具省级影响的单一事件/文件/政策动作”，用 2-3 句写满（事实→财政影响→关注点）。
- 若 visual_focus=common_issue：焦点必须围绕“全省普遍性财政问题/共性痛点”写 2-3 句（现象→财政含义→需要的抓手）。
- 覆盖面约束（必须遵守）：
  - common_issue 必须体现“覆盖面广/全省共性”：引用至少 3 篇材料，且尽量覆盖至少 2 个地市（杭州/宁波/温州/嘉兴/湖州/绍兴/金华/衢州/舟山/台州/丽水）。
  - high_impact_event 必须是“省级/市级影响”的单一政策动作或事件；不选择县/区层级的单点通知作为标题焦点。
- 标题地域约束（必须遵守）：
  - header.title 禁止出现具体“县/区/镇/乡/街道/园区/开发区”等过细地名作为主标题锚点（例如“文成县…/越城区…”不允许）。
  - 标题最低粒度为“市级”（例如“杭州…/宁波…”），或使用“浙江/全省/省级”表述（例如“全省城乡居民医保缴费倒计时”）。
  - 若材料来自多个县区：标题必须上收为“全省/地市级”的共性表述，县区只作为引用里的例子出现。

输出格式（必须严格 JSON；只输出 JSON，不要任何额外文字）：
{{
  "schema": "smart_brevity_v1",
  "focus_topic": "今日焦点主题（不超过12字，用名词短语概括；用于一周内去重）",
  "visual_focus": "common_issue|high_impact_event（两者二选一，必须选其一）",
  "header": {{
    "title": "不超过20字的实词标题（动宾结构，突出结果）",
    "date": "{d}",
    "lede": "今日焦点第1句：不超过50字，首句即核心事实（不要出现“今日速览/为何重要/大局”等小标题；不要拼盘）。",
    "lede_citations": [1,2]
  }},
  "why_it_matters": "今日焦点第2句：财政视角的影响/抓手（只基于材料），1句为主（不要出现“为何重要：”等小标题；不要拼盘）。",
  "why_citations": [1,2,3],
  "big_picture": "今日焦点第3句：关注点/风险点/落地要害（只基于材料），1句为主（不要出现“【大局】”等小标题；不要拼盘）。",
  "big_picture_citations": [2,4],
  "by_the_numbers": [],
  "word_cloud": [],
  "keywords": [
    {{"word":"关键词","weight":100,"source_ids":[1,2]}}
  ],
  "sources": [
    {{"id": 1, "account": "公众号名", "title": "文章标题", "url": "https://..." }}
  ]
}}
"""


def smart_brevity_user_material(material: str, *, hotwords: List[str]) -> str:
    hw = "、".join(hotwords[:12]) if hotwords else ""
    extra = ""
    if hw:
        extra = f"\n\n系统热词（仅供参考，不要生造）：{hw}\n"
    return f"请基于以下材料生成《浙江财政信息摘要》：\n\n{material}{extra}"


def strict_json_guard_prompt() -> str:
    return """你是一名结构化输出修复器。

任务：将输入内容修复为“严格 JSON”，不改变事实，不新增任何信息。
规则：
- 只输出 JSON。
- 去掉代码块、注释、前后缀文字。
- 保留原有字段（如缺字段则补空字符串/空数组，但不要编造内容）。"""


def coerce_schema_defaults(obj: Dict[str, Any], target_date: date) -> Dict[str, Any]:
    """
    Ensure required keys exist with safe defaults; keep obj otherwise.
    """
    d = target_date.isoformat()
    out = dict(obj or {})
    out.setdefault("schema", "smart_brevity_v1")
    out.setdefault("focus_topic", "")
    out.setdefault("visual_focus", "common_issue")
    header = out.get("header")
    if not isinstance(header, dict):
        header = {}
        out["header"] = header
    header.setdefault("title", f"浙江财政情报日报（{d}）")
    header["date"] = d
    header.setdefault("lede", "")
    header.setdefault("lede_citations", [])
    out.setdefault("why_it_matters", "")
    out.setdefault("why_citations", [])
    out.setdefault("big_picture", "")
    out.setdefault("big_picture_citations", [])
    out.setdefault("by_the_numbers", [])
    out.setdefault("word_cloud", [])
    out.setdefault("keywords", [])
    out.setdefault("sources", [])
    return out


def extract_first_json(text: str) -> Dict[str, Any] | None:
    if not isinstance(text, str):
        return None
    s = text.strip()
    if not s:
        return None
    if "```" in s:
        s = s.strip()
        s = s.replace("```json", "```").replace("```JSON", "```")
        s = s.strip("`").strip()
    l = s.find("{")
    r = s.rfind("}")
    if l == -1 or r == -1 or r <= l:
        return None
    js = s[l : r + 1]
    try:
        obj = json.loads(js)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        return None


