from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from openai import OpenAI

from shared.database import SessionLocal
from shared.database.models import Article, ArticleOneLiner
from shared.utils import get_logger

from .nlp import clean_text, extract_key_snippets, EXTENDED_KEYWORDS
from .prompts import extract_first_json

logger = get_logger("daily-briefing-hotspots")


@dataclass
class OneLinerResult:
    article_id: int
    one_liner: str
    tags: Dict[str, int]
    keep: bool


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clip_for_llm(a: Article, *, max_chars: int = 1600) -> str:
    title = str(getattr(a, "title", "") or "").strip()
    body = str(getattr(a, "content", "") or "").strip()
    body2 = clean_text(body)
    # Use a few key snippets to keep signal without paying full text cost
    try:
        snips = extract_key_snippets(body2, max_snippets=6)
    except Exception:
        snips = []
    snippet_text = "\n".join([s for s in (snips or []) if isinstance(s, str) and s.strip()])
    merged = (title + "\n" + (snippet_text or body2[: max_chars])).strip()
    return merged[:max_chars]


def _prompt_version() -> str:
    return (os.getenv("RECENT_HOTSPOTS_ONELINER_PROMPT_VERSION", "v1") or "v1").strip()


def _oneliner_system_prompt() -> str:
    """
    LLM-first + LLM-only oneliner + tag judgement.
    Must be stable and JSON-only.
    """
    return (
        "你是《浙江财政情报晨报》的“逐篇热点事件浓缩器”。\n"
        "输入是一篇公众号文章的标题与正文片段（含关键句）。\n"
        "\n目标：把每篇文章压缩成“可聚类的事件标签”，用于生成【近日热点】。\n"
        "\n你必须输出：\n"
        "1) one_liner：<=20字的一句话，回答“发生了什么”（必须是事实、像事件）。\n"
        "2) tags：三个相关性评分（0-3）\n"
        "   - finance：财政/资金/税费/专项债/政府采购/补贴给付等\n"
        "   - minsheng：民生保障/社保医保/救助补贴/就业住房教育等\n"
        "   - tech：科技创新/研发/专利/成果转化/数字经济/智能制造等\n"
        "3) keep：true/false（是否进入【近日热点】聚类。宁可少，不能滥。）\n"
        "\none_liner 质量规则（强制）：\n"
        "- 必须是“对象+动作/政策工具+动作”的结构：例如“发放育儿补贴”“开通医保报销”“启动专项债申报”“上线以旧换新补贴”。\n"
        "- 词尽量具体：不要只写“补贴申领/补助申请”这类泛化短语；必须点明对象（如“育儿/社保/扩岗/消费券/以旧换新/专项债/退税”）。\n"
        "- 避免模板/口号/评价：如“实干争先/决定性进展/世界一流/典型案例/高质量发展”。\n"
        "- 必须排除：会议/座谈会/部署会/学习教育；党建/组织/人事任免表彰；领导活动；纯地名/人名/机构名为主体。\n"
        "\nkeep 判定建议：\n"
        "- true：事件性强、读者关心、可执行/可感知，且可能在多地/多账号重复出现。\n"
        "- false：只是一篇通稿、会议报道、宣传口号、或缺乏具体动作/对象。\n"
        "\n只输出严格JSON，不要解释。\n"
        "输出格式：{\"one_liner\":\"...\",\"tags\":{\"finance\":0,\"minsheng\":0,\"tech\":0},\"keep\":true}\n"
    )


def _normalize_one_liner(s: str) -> str:
    t = (s or "").strip()
    t = re.sub(r"\s+", "", t)
    # strip trailing punctuation
    t = re.sub(r"[。！？；;：:，,]+$", "", t).strip()
    # hard clip: 20 chars
    if len(t) > 20:
        t = t[:20].strip()
    return t


def _default_keep(tags: Dict[str, int]) -> bool:
    """
    Fallback keep rule when model didn't output keep.
    """
    # Product rule: total score >= 2 (finance+minsheng+tech)
    try:
        th = int(os.getenv("RECENT_HOTSPOTS_TAG_SUM_THRESHOLD", "2") or "2")
    except Exception:
        th = 2
    th = max(1, min(6, th))
    s = int(tags.get("finance") or 0) + int(tags.get("minsheng") or 0) + int(tags.get("tech") or 0)
    return s >= th


def get_or_compute_one_liners(
    *,
    client: OpenAI,
    model: str,
    articles: Sequence[Article],
    db=None,
) -> List[OneLinerResult]:
    """
    Compute per-article one_liner + tags, with persistent DB cache keyed by (article_id, prompt_version).
    If db is not provided, opens a short-lived SessionLocal.
    """
    if not articles:
        return []

    prompt_ver = _prompt_version()
    article_ids = [int(a.id) for a in articles if getattr(a, "id", None)]
    article_ids = [x for x in article_ids if x > 0]
    if not article_ids:
        return []

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        cached_rows = (
            db.query(ArticleOneLiner)
            .filter(ArticleOneLiner.article_id.in_(article_ids), ArticleOneLiner.prompt_version == prompt_ver)
            .all()
        )
        cached: Dict[int, ArticleOneLiner] = {int(r.article_id): r for r in cached_rows if r and r.article_id}

        need: List[Article] = [a for a in articles if int(getattr(a, "id", 0) or 0) not in cached]

        # Batch model calls to reduce overhead
        batch_size = int(os.getenv("RECENT_HOTSPOTS_ONELINER_BATCH", "8") or "8")
        batch_size = max(1, min(12, batch_size))

        system = _oneliner_system_prompt()

        def call_batch(batch: List[Article]) -> Dict[int, Dict[str, Any]]:
            items = []
            for idx, a in enumerate(batch, start=1):
                aid = int(getattr(a, "id", 0) or 0)
                if aid <= 0:
                    continue
                clip = _clip_for_llm(a)
                items.append({"n": idx, "article_id": aid, "text": clip})
            if not items:
                return {}
            user = json.dumps({"items": items}, ensure_ascii=False)
            # Ask model to output list aligned to article_id to avoid ordering ambiguity
            system2 = system + "\n补充：请输出列表，逐条对应 article_id。输出格式：{\"items\":[{\"article_id\":1,...}]}\n"
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system2}, {"role": "user", "content": user}],
                temperature=0.0,
                timeout=60,
            )
            txt = (resp.choices[0].message.content or "").strip()
            obj = extract_first_json(txt) or {}
            out = {}
            arr = obj.get("items")
            if isinstance(arr, list):
                for it in arr:
                    if not isinstance(it, dict):
                        continue
                    try:
                        aid2 = int(it.get("article_id") or 0)
                    except Exception:
                        continue
                    if aid2 > 0:
                        out[aid2] = it
            return out

        for i in range(0, len(need), batch_size):
            batch = need[i : i + batch_size]
            try:
                res_map = call_batch(batch)
            except Exception as e:
                logger.warning(f"one_liner batch call failed: size={len(batch)} err={e}")
                res_map = {}

            for a in batch:
                aid = int(getattr(a, "id", 0) or 0)
                if aid <= 0:
                    continue
                it = res_map.get(aid) or {}
                one = _normalize_one_liner(str(it.get("one_liner") or ""))

                tags = it.get("tags") if isinstance(it.get("tags"), dict) else {}
                tags2 = {
                    "finance": int(tags.get("finance") or 0),
                    "minsheng": int(tags.get("minsheng") or 0),
                    "tech": int(tags.get("tech") or 0),
                }
                for k in list(tags2.keys()):
                    tags2[k] = max(0, min(3, int(tags2[k] or 0)))

                keep = it.get("keep")
                if isinstance(keep, bool):
                    keep2 = keep
                else:
                    keep2 = _default_keep(tags2)

                # If model produced empty one_liner, fallback to a compact title-based phrase (still cached)
                if not one:
                    title = str(getattr(a, "title", "") or "").strip()
                    one = _normalize_one_liner(title[:20])

                row = ArticleOneLiner(
                    article_id=aid,
                    one_liner=one or "",
                    tags=tags2,
                    keep=bool(keep2),
                    model=str(model or "")[:100],
                    prompt_version=prompt_ver,
                )
                try:
                    db.add(row)
                    db.commit()
                except Exception:
                    db.rollback()
                    # best-effort update if already inserted concurrently
                    try:
                        existing = (
                            db.query(ArticleOneLiner)
                            .filter(ArticleOneLiner.article_id == aid, ArticleOneLiner.prompt_version == prompt_ver)
                            .first()
                        )
                        if existing:
                            existing.one_liner = one
                            existing.tags = tags2
                            existing.keep = bool(keep2)
                            existing.model = str(model or "")[:100]
                            db.commit()
                    except Exception:
                        db.rollback()

        # Build final results from cache+new rows
        rows2 = (
            db.query(ArticleOneLiner)
            .filter(ArticleOneLiner.article_id.in_(article_ids), ArticleOneLiner.prompt_version == prompt_ver)
            .all()
        )
        out: List[OneLinerResult] = []
        for r in rows2:
            if not r:
                continue
            try:
                aid = int(r.article_id)
            except Exception:
                continue
            out.append(
                OneLinerResult(
                    article_id=aid,
                    one_liner=str(r.one_liner or "").strip(),
                    tags=(r.tags if isinstance(r.tags, dict) else {"finance": 0, "minsheng": 0, "tech": 0}),
                    keep=bool(r.keep),
                )
            )
        return out
    finally:
        if close_db:
            try:
                db.close()
            except Exception:
                pass


def cluster_recent_hotspots_llm(
    *,
    client: OpenAI,
    model: str,
    items: List[Dict[str, Any]],
    target_n: int,
) -> List[Dict[str, Any]]:
    """
    LLM-only clustering: input is a list of per-article one_liner items.
    Output: [{"event": "...", "source_ids":[...], "why_hot":"...", "category":"..."}]
    """
    if not items:
        return []
    # Product: threshold-based, at most Top8
    target_n = max(3, min(8, int(target_n or 8)))

    system = (
        "你是【近日热点】的“聚类+命名编辑”。\n"
        "输入是一组文章 one_liner（每条<=20字）与来源信息。\n"
        "任务：把相同/相近事件聚成少量热点，并给出更像编辑写的事件名。\n"
        "\n强制规则：\n"
        "- 事件名 event：优先4-8字（最多12字），必须像事件（对象+动作/政策工具+动作），不要口号/评价。\n"
        "- source_ids：每个事件必须给出 2-6 个，且必须来自输入。\n"
        "- 只保留真正热点：必须“重复出现/覆盖多来源”才算热点；孤立事件不要输出。\n"
        "- 去同义：不同事件之间不能只是换一种说法（例如不要同时输出“育儿补贴申领”和“申领育儿补贴”）。\n"
        "- 去模板：避免一屏都是“补贴申领/补助申请”。如果出现多条申领类，请优先保留最具体的2条，其余合并或舍弃。\n"
        "- 排除：会议/党建/人事/组织/领导活动；纯地名/人名；口号/成效类。\n"
        "\n多样性约束（尽量做到）：\n"
        "- 在候选充足时，尽量覆盖：民生(welfare)/财政工具(fiscal)/消费促进(consumption)/科创(tech) 这几类。\n"
        "- category 必须是 welfare|fiscal|consumption|tech|other 之一。\n"
        "\n输出严格JSON，不要解释。\n"
        "输出格式：{\"events\":[{\"event\":\"...\",\"source_ids\":[1,2],\"why_hot\":\"<=12字\",\"category\":\"welfare|fiscal|consumption|tech|other\"}]}\n"
    )

    user = json.dumps({"target_n": target_n, "items": items}, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        timeout=80,
    )
    txt = (resp.choices[0].message.content or "").strip()
    obj = extract_first_json(txt) or {}
    evs = obj.get("events")
    if not isinstance(evs, list):
        return []

    out: List[Dict[str, Any]] = []
    seen_names: set[str] = set()
    valid_ids = set([int(it.get("source_id")) for it in items if isinstance(it, dict) and str(it.get("source_id") or "").isdigit()])
    for it in evs:
        if not isinstance(it, dict):
            continue
        name = str(it.get("event") or "").strip()
        name = re.sub(r"\s+", "", name)
        name = re.sub(r"[。！？；;：:，,]+$", "", name).strip()
        if not name or len(name) < 2:
            continue
        if len(name) > 12:
            name = name[:12].strip()
        if name in seen_names:
            continue

        sids = it.get("source_ids")
        if not isinstance(sids, list):
            continue
        sids2: List[int] = []
        for x in sids:
            try:
                n = int(x)
            except Exception:
                continue
            if n in valid_ids and n not in sids2:
                sids2.append(n)
        if len(sids2) < 2:
            continue

        why = str(it.get("why_hot") or "").strip()
        why = re.sub(r"\s+", "", why)
        if len(why) > 12:
            why = why[:12]
        cat = str(it.get("category") or "").strip() or "other"
        out.append({"event": name, "source_ids": sids2[:6], "why_hot": why, "category": cat})
        seen_names.add(name)
        if len(out) >= target_n:
            break

    return out


