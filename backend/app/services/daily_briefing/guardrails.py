from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Sequence, Tuple

from shared.utils import get_logger

logger = get_logger("daily-briefing-guardrails")


DEFAULT_SENSITIVE_PHRASES = [
    # 这里只放“必须阻断输出”的极少数示例；实际项目请在环境变量或文件中维护
    "绝密",
    "机密",
    "内部资料",
]


def load_sensitive_phrases() -> List[str]:
    env = os.getenv("ZPULSE_SENSITIVE_PHRASES", "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    return list(DEFAULT_SENSITIVE_PHRASES)


def find_sensitive_hits(text: str, phrases: Sequence[str]) -> List[str]:
    if not isinstance(text, str) or not text:
        return []
    hits: List[str] = []
    for p in phrases:
        if p and p in text:
            hits.append(p)
    return hits


def collect_all_text_fields(report_json: Dict[str, Any]) -> str:
    """
    Collect visible text fields for sensitive scanning.
    """
    parts: List[str] = []
    header = report_json.get("header") if isinstance(report_json, dict) else None
    if isinstance(header, dict):
        for k in ("title", "lede"):
            v = header.get(k)
            if isinstance(v, str) and v:
                parts.append(v)
    for k in ("why_it_matters", "big_picture"):
        v = report_json.get(k)
        if isinstance(v, str) and v:
            parts.append(v)
    btn = report_json.get("by_the_numbers")
    if isinstance(btn, list):
        for row in btn:
            if not isinstance(row, dict):
                continue
            for k in ("indicator", "value", "note"):
                v = row.get(k)
                if isinstance(v, str) and v:
                    parts.append(v)
    hw = report_json.get("hotwords")
    if isinstance(hw, list):
        for w in hw:
            if isinstance(w, str) and w:
                parts.append(w)
    return "\n".join(parts)


def sanitize_sensitive(report_json: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    phrases = load_sensitive_phrases()
    blob = collect_all_text_fields(report_json)
    hits = find_sensitive_hits(blob, phrases)
    if not hits:
        return report_json, []
    # Conservative: replace hits with "（已脱敏）" in-place in visible fields.
    def _mask(s: str) -> str:
        out = s
        for h in hits:
            out = out.replace(h, "（已脱敏）")
        return out

    out: Dict[str, Any] = dict(report_json)
    header = out.get("header")
    if isinstance(header, dict):
        header2 = dict(header)
        for k in ("title", "lede"):
            if isinstance(header2.get(k), str):
                header2[k] = _mask(header2[k])
        out["header"] = header2
    for k in ("why_it_matters", "big_picture"):
        if isinstance(out.get(k), str):
            out[k] = _mask(out[k])
    btn = out.get("by_the_numbers")
    if isinstance(btn, list):
        new_rows = []
        for row in btn:
            if not isinstance(row, dict):
                continue
            r2 = dict(row)
            for k in ("indicator", "value", "note"):
                if isinstance(r2.get(k), str):
                    r2[k] = _mask(r2[k])
            new_rows.append(r2)
        out["by_the_numbers"] = new_rows
    hw = out.get("hotwords")
    if isinstance(hw, list):
        out["hotwords"] = [_mask(w) if isinstance(w, str) else w for w in hw]
    logger.warning(f"Sensitive phrases masked: {hits}")
    return out, hits


def extract_numbers_from_report(report_json: Dict[str, Any]) -> List[str]:
    """
    Extract numeric spans from the report output for hallucination checking.
    """
    text = collect_all_text_fields(report_json)
    if not text:
        return []
    # keep numbers with units; avoid extremely common 1/2/3 markers by requiring either unit or decimal/percent
    patterns = [
        r"(?:¥|￥|RMB|CNY)?\s*\d+(?:\.\d+)?\s*(?:万亿元|亿元|万元|元|%|％|万|亿)",
        r"\d+(?:\.\d+)?\s*(?:%|％|个百分点)",
    ]
    out: List[str] = []
    seen: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, text):
            s = (m.group(0) or "").strip()
            if not s:
                continue
            if len(s) > 40:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
    return out


def strip_unverified_numbers_from_by_the_numbers(
    report_json: Dict[str, Any],
    *,
    allowed_numbers: Sequence[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    If a table row contains a number span that doesn't appear in allowed_numbers, drop that row.
    This is conservative and avoids silently altering numeric values.
    """
    if not isinstance(report_json, dict):
        return report_json, []
    allowed = {normalize_number_string(x) for x in allowed_numbers if isinstance(x, str)}
    rows = report_json.get("by_the_numbers")
    if not isinstance(rows, list) or not rows:
        return report_json, []
    kept: List[Dict[str, Any]] = []
    dropped: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("value")
        if not isinstance(value, str):
            kept.append(row)
            continue
        nums = _extract_number_spans_loose(value)
        bad = []
        for n in nums:
            nn = normalize_number_string(n)
            if nn not in allowed:
                bad.append(n)
        if bad:
            dropped.append(f"{row.get('indicator','')}: {', '.join(bad)}")
            continue
        kept.append(row)
    out = dict(report_json)
    out["by_the_numbers"] = kept
    return out, dropped


def normalize_number_string(s: str) -> str:
    if not isinstance(s, str):
        return ""
    t = s.strip()
    # normalize commas and spaces
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)
    # normalize currency symbols
    t = t.replace("￥", "¥")
    t = t.replace("RMB", "CNY")
    return t


def _extract_number_spans_loose(text: str) -> List[str]:
    if not isinstance(text, str) or not text:
        return []
    t = text
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)
    pats = [
        r"(?:¥|￥|RMB|CNY)?\s*\d+(?:\.\d+)?\s*(?:万亿元|亿元|万元|元|%|％|万|亿|个百分点)?",
    ]
    out: List[str] = []
    seen: set[str] = set()
    for pat in pats:
        for m in re.finditer(pat, t):
            s = (m.group(0) or "").strip()
            if not s or not re.search(r"\d", s):
                continue
            if len(s) > 40:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
    return out


