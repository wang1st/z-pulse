from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
import hashlib

from openai import OpenAI

from shared.database import Article
from shared.utils import get_logger

from .guardrails import sanitize_sensitive, strip_unverified_numbers_from_by_the_numbers
from .nlp import (
    clean_text,
    extract_number_spans,
    extract_key_snippets,
    finance_keyword_hits,
    load_custom_dictionary,
    strip_focus_markers,
    EXTENDED_KEYWORDS,
)
from .hotspots import cluster_recent_hotspots_llm, get_or_compute_one_liners
from .prompts import coerce_schema_defaults, extract_first_json, smart_brevity_system_prompt

logger = get_logger("daily-briefing-generator")


@dataclass(frozen=True)
class DailyBriefingConfig:
    min_finance_kw_hits: int = 2
    max_input_chars: int = 180000
    per_article_chars: int = 8000
    top_hotwords: int = 18
    max_snippets_per_article: int = 10


class DailyBriefingGenerator:
    """
    Generate daily briefing (Smart Brevity) as structured JSON for public information aggregation.
    """

    # Zhejiang prefecture-level cities for "too local" checks (best-effort).
    _ZJ_CITIES: List[str] = [
        "杭州",
        "宁波",
        "温州",
        "嘉兴",
        "湖州",
        "绍兴",
        "金华",
        "衢州",
        "舟山",
        "台州",
        "丽水",
    ]

    _COUNTY_EXCLUDE_MARKERS: List[str] = [
        "开发区",
        "新区",
        "园区",
        "经开",
        "经开区",
        "高新",
        "高新区",
        "产业园",
    ]

    def __init__(
        self,
        *,
        qwen_client: OpenAI,
        model: str,
        keywords_model: Optional[str] = None,
        config: Optional[DailyBriefingConfig] = None,
    ):
        self.client = qwen_client
        self.model = model
        self.keywords_model = (keywords_model or os.getenv("QWEN_KEYWORDS_MODEL", "qwen-flash")).strip() or "qwen-flash"
        self.cfg = config or DailyBriefingConfig()
        # load NLP resources (no-op if jieba missing)
        load_custom_dictionary()

    def generate(
        self,
        *,
        target_date: date,
        finance_articles: Sequence[Article],
        all_articles: Sequence[Article],
        recent_hotwords_end_utc: Optional[datetime] = None,
        recent_hotwords_window_days: int = 3,
        recent_focus_styles: Optional[List[str]] = None,
        recent_lead_variants: Optional[List[str]] = None,
        recent_focus_topics: Optional[List[str]] = None,
    ) -> Dict[str, Any] | None:
        if not finance_articles:
            return None

        # Step 1: rule-based prefilter (conservative; only used to prioritize/condense input)
        finance_candidates = self._prefilter_articles(finance_articles)

        # Step 2a: build compact material for LLM using FINANCE sources only (so focus must be finance-related)
        material, sources_fin, source_articles_fin = self._build_material(finance_candidates)
        # Step 2: per-article one-sentence summaries (cheap).
        per_article = self._summarize_per_article(
            sources=sources_fin,
            source_articles=source_articles_fin,
        )

        # Choose writing style (5 main) + lead micro-variant (10)
        focus_type, focus_style, lead_variant = self._choose_focus_style(
            target_date=target_date,
            per_article=per_article,
            recent_focus_styles=recent_focus_styles or [],
            recent_lead_variants=recent_lead_variants or [],
        )

        # Step 3 (new): today focus from all summaries (QWEN_DAILY_MODEL)
        recent_topics = [t.strip() for t in (recent_focus_topics or []) if isinstance(t, str) and t.strip()]

        # retry if focus_topic semantically overlaps recent weekly topics OR focus is too local/narrow (best-effort)
        raw = ""
        obj_try: Dict[str, Any] | None = None
        last_reason = ""
        for attempt in range(3):
            extra = ""
            if attempt >= 1 and last_reason == "too_local":
                extra += (
                    "\n重要：你上一版“今日焦点”过于县/区级或覆盖面过窄。"
                    "请改为省级/市级表述（标题不得出现县/区/镇/乡/街道/园区/开发区等），"
                    "并在 citations 中覆盖至少 2 个地市（common_issue 需多地市共性）。\n"
                )
            if attempt == 1:
                extra = (
                    "\n重要：你上一版输出的 focus_topic 仍与本周已用主题重复/高度重叠。"
                    "请更换为不同主题（仍需单一主事件），并更新 title/lede/引用以匹配新主题。\n"
                ) + extra
            if attempt == 2:
                extra = (
                    "\n重要：你仍在重复近3天已用焦点（语义相近也算重复）。"
                    "请务必选择不同主题，并尽量使用不同来源文章支撑。\n"
                ) + extra
            raw = self._call_llm(
                system_prompt=smart_brevity_system_prompt(target_date),
                user_prompt=self._smart_brevity_user_from_summaries(
                    per_article,
                    focus_type=focus_type,
                    focus_style=focus_style,
                    lead_variant=lead_variant,
                    recent_focus_topics=recent_topics,
                    extra_instructions=extra,
                ),
                temperature=0.2,
                timeout=120,
            ) or ""
            if not raw:
                break
            obj_try = extract_first_json(raw)
            if not obj_try:
                break
            ft = str(obj_try.get("focus_topic") or "").strip()
            if not ft:
                continue
            if self._is_topic_semantic_duplicate(topic=ft, recent_topics=recent_topics):
                last_reason = "semantic_dup"
                continue
            if self._is_focus_too_local_or_narrow(obj_try=obj_try, sources_for_prompt=sources_fin):
                last_reason = "too_local"
                continue
            last_reason = ""
            break
        if not raw:
            return None
        if not raw:
            return None

        # Build a combined source pool (finance first, then non-finance) for cross-day citations & hotspots.
        sources_all, source_articles_all = self._build_sources_index_with_finance_first(
            finance_sources=sources_fin,
            finance_source_articles=source_articles_fin,
            all_articles=all_articles,
        )

        obj = extract_first_json(raw)
        if not obj:
            # fallback: wrap minimal structure (keeps system from breaking)
            obj = {
                "schema": "smart_brevity_v1",
                "visual_focus": "common_issue",
                "header": {"title": f"浙江财政情报日报（{target_date.isoformat()}）", "date": target_date.isoformat(), "lede": raw[:200], "lede_citations": []},
                "why_it_matters": "",
                "why_citations": [],
                "big_picture": "",
                "big_picture_citations": [],
                "by_the_numbers": [],
                "sources": sources_all,
            }

        obj = coerce_schema_defaults(obj, target_date)
        # UI-v2: only three sections
        obj["by_the_numbers"] = []
        obj["word_cloud"] = []
        # Keywords will be generated after recent_hotspots extraction
        obj["keywords"] = []
        obj["article_summaries"] = per_article
        obj["focus_type"] = focus_type
        obj["focus_style"] = focus_style
        obj["lead_variant"] = lead_variant
        if not isinstance(obj.get("focus_topic"), str) or not str(obj.get("focus_topic") or "").strip():
            # fallback: use a short stable label from title
            try:
                ht = obj.get("header") or {}
                if isinstance(ht, dict):
                    obj["focus_topic"] = str(ht.get("title") or "").strip()[:12]
            except Exception:
                obj["focus_topic"] = ""

        # Strip legacy markers from focus components
        try:
            header = obj.get("header")
            if isinstance(header, dict):
                header2 = dict(header)
                header2["lede"] = strip_focus_markers(str(header2.get("lede") or ""))
                obj["header"] = header2
        except Exception:
            pass
        obj["why_it_matters"] = strip_focus_markers(str(obj.get("why_it_matters") or ""))
        obj["big_picture"] = strip_focus_markers(str(obj.get("big_picture") or ""))

        # Step 3.5: recent hotwords (近日热词，近N天，允许跨天来源支撑)
        try:
            end_utc = recent_hotwords_end_utc
            if not isinstance(end_utc, datetime):
                end_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            # Product rename: “近日热点”（事件聚类）
            window_days = max(1, int(recent_hotwords_window_days or 3))
            recent_hotspots = self._extract_recent_hotspots(
                sources_for_prompt=sources_all,
                source_articles=source_articles_all,
                end_utc=end_utc,
                window_days=window_days,
            )
            obj["recent_hotspots_meta"] = {
                "window_days": window_days,
                "total_hotspots": len(recent_hotspots),
                "window_end_utc": end_utc.isoformat(),
            }
            obj["recent_hotspots"] = recent_hotspots
        except Exception as e:
            logger.warning(f"Recent hotspots extraction failed; err={e}")
            obj["recent_hotspots_meta"] = {"window_days": int(recent_hotwords_window_days or 3), "total_hotspots": 0}
            obj["recent_hotspots"] = []

        # Step 4: normalize citations & sources to only used ones (and remap to 1..N)
        obj = self._normalize_sources_and_citations(obj=obj, sources_for_prompt=sources_all)

        # Step 4.5: Generate "今日关键词" from recent hotspots (after normalization)
        obj["keywords"] = self._extract_today_keywords(
            recent_hotspots=obj.get("recent_hotspots") or [],
            sources_all=sources_all,
            source_articles_all=source_articles_all,
        )

        # Step 5: guardrails
        # - Sensitive masking
        obj, _hits = sanitize_sensitive(obj)
        # - Numeric hallucination check (table only, conservative)
        allowed_numbers = extract_number_spans(material, max_items=80)
        obj, _dropped = strip_unverified_numbers_from_by_the_numbers(obj, allowed_numbers=allowed_numbers)

        # Ensure shape
        if not isinstance(obj.get("keywords"), list):
            obj["keywords"] = []
        obj["by_the_numbers"] = []
        obj["word_cloud"] = []

        obj["sources"] = obj.get("sources") or []
        return obj

    def _build_sources_index_with_finance_first(
        self,
        *,
        finance_sources: List[Dict[str, Any]],
        finance_source_articles: Dict[int, Article],
        all_articles: Sequence[Article],
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Article]]:
        """
        Build a combined sources list for the final report JSON:
        - Finance sources keep their original ids (1..Nf) so focus citations remain valid.
        - Non-finance articles are appended with new ids (Nf+1..).
        This allows "近日热点" to cite cross-day sources while keeping "今日焦点" finance-grounded.
        """
        sources_out: List[Dict[str, Any]] = []
        source_articles_out: Dict[int, Article] = {}

        existing_urls: set[str] = set()
        max_id = 0

        for s in finance_sources or []:
            if not isinstance(s, dict) or not s.get("id"):
                continue
            try:
                sid = int(s.get("id"))
            except Exception:
                continue
            if sid <= 0:
                continue
            a = finance_source_articles.get(sid)
            sources_out.append(
                {
                    "id": sid,
                    "account": str(s.get("account") or ""),
                    "title": str(s.get("title") or ""),
                    "url": str(s.get("url") or ""),
                    "date": self._date_str_for_article(a),
                }
            )
            if sources_out[-1]["url"]:
                existing_urls.add(str(sources_out[-1]["url"]))
            if a is not None:
                source_articles_out[sid] = a
            max_id = max(max_id, sid)

        # Append remaining (non-finance and finance not included due to prefilter) by URL uniqueness.
        next_id = max_id + 1
        for a in all_articles or []:
            url = str(getattr(a, "article_url", "") or "").strip()
            if not url or url in existing_urls:
                continue
            account_name = ""
            try:
                if getattr(a, "account", None) and getattr(a.account, "name", None):
                    account_name = a.account.name
            except Exception:
                account_name = ""
            title = str(getattr(a, "title", "") or "").strip()
            sources_out.append(
                {
                    "id": next_id,
                    "account": account_name or "",
                    "title": title or "",
                    "url": url,
                    "date": self._date_str_for_article(a),
                }
            )
            source_articles_out[next_id] = a
            existing_urls.add(url)
            next_id += 1

        return sources_out, source_articles_out

    def _date_str_for_article(self, a: Optional[Article]) -> str:
        """
        Format article published_at as Beijing YYYY-MM-DD. Best-effort only.
        Assumptions:
        - Article.published_at is stored as naive UTC in DB (existing code compares against UTC naive).
        """
        if a is None:
            return ""
        dt = getattr(a, "published_at", None)
        if not isinstance(dt, datetime):
            return ""
        try:
            bj = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
            return bj.date().isoformat()
        except Exception:
            return ""

    def _extract_recent_hotspots(
        self,
        *,
        sources_for_prompt: List[Dict[str, Any]],
        source_articles: Dict[int, Article],
        end_utc: datetime,
        window_days: int = 5,
        top_k: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Extract "近日热点" (TopN) from the last `window_days` days of ALL articles (already windowed by caller).
        LLM-first + LLM-only:
        - Step A: per-article one_liner (<=20字) + tags + keep, with persistent DB cache
        - Step B: LLM clustering on one_liners to output热点事件
        Output items: {event, hotness, source_ids, coverage_docs, coverage_accounts, last_seen, why_hot, category, one_liners?}
        """
        window_days = max(1, int(window_days or 3))
        top_k = int(os.getenv("RECENT_HOTSPOTS_TOP_K", str(top_k or 8)) or str(top_k or 8))
        top_k = max(3, min(8, top_k))

        # Prepare per-article one_liners (cached in DB by article_id+prompt_version)
        sid_to_article_id: Dict[int, int] = {}
        sid_meta: Dict[int, Dict[str, Any]] = {}
        articles: List[Article] = []
        for s in sources_for_prompt or []:
            if not isinstance(s, dict):
                continue
            try:
                sid = int(s.get("id"))
            except Exception:
                continue
            if sid <= 0:
                continue
            a = source_articles.get(sid)
            if not a or not getattr(a, "id", None):
                continue
            articles.append(a)
            sid_to_article_id[sid] = int(a.id)
            sid_meta[sid] = {"account": str(s.get("account") or "").strip(), "title": str(s.get("title") or "").strip()}

        if not articles:
            return []

        # NOTE: "全部交给大模型" - we only do validation/scoring locally.
        one_liners = get_or_compute_one_liners(client=self.client, model=self.keywords_model, articles=articles)
        aid_to_ol = {int(x.article_id): x for x in (one_liners or [])}

        # Build items for clustering (LLM-first): gate by tag sum threshold (finance+minsheng+tech >= 2)
        # Product decision: do NOT require literal keyword hits in original text (avoid false negatives).
        try:
            tag_sum_th = int(os.getenv("RECENT_HOTSPOTS_TAG_SUM_THRESHOLD", "2") or "2")
        except Exception:
            tag_sum_th = 2
        tag_sum_th = max(1, min(6, int(tag_sum_th)))

        cluster_items: List[Dict[str, Any]] = []
        for sid, a in source_articles.items():
            aid = int(getattr(a, "id", 0) or 0)
            if aid <= 0:
                continue
            ol = aid_to_ol.get(aid)
            if not ol or not str(ol.one_liner or "").strip():
                continue
            tags0 = ol.tags if isinstance(ol.tags, dict) else {}
            tag_sum = int(tags0.get("finance") or 0) + int(tags0.get("minsheng") or 0) + int(tags0.get("tech") or 0)
            if tag_sum < tag_sum_th:
                continue
            cluster_items.append(
                {
                    "source_id": int(sid),
                    "one_liner": str(ol.one_liner or "").strip(),
                    "tags": tags0,
                    "account": (sid_meta.get(int(sid), {}) or {}).get("account") or "",
                    "title": (sid_meta.get(int(sid), {}) or {}).get("title") or "",
                }
            )

        if len(cluster_items) < 3:
            return []

        # Guardrail: clustering prompt must be small enough; otherwise model times out.
        # Keep this lightweight (not "local keyword extraction"): prioritize by tags + recency + a few policy markers.
        try:
            max_cluster_items = int(os.getenv("RECENT_HOTSPOTS_CLUSTER_MAX_ITEMS", "120") or "120")
        except Exception:
            max_cluster_items = 120
        max_cluster_items = max(40, min(220, int(max_cluster_items)))
        if len(cluster_items) > max_cluster_items:
            policy_marks = ("补贴", "补助", "津贴", "退税", "减免", "专项债", "消费券", "以旧换新", "报销", "医保", "社保", "托育", "研发", "专利", "高新")

            def _score_item(it: Dict[str, Any]) -> float:
                tags = it.get("tags") if isinstance(it.get("tags"), dict) else {}
                tag_sum = float(int(tags.get("finance") or 0) + int(tags.get("minsheng") or 0) + int(tags.get("tech") or 0))
                sid = int(it.get("source_id") or 0)
                a = source_articles.get(sid)
                dt = getattr(a, "published_at", None)
                rec = 0.0
                if isinstance(dt, datetime):
                    try:
                        days = int((end_utc - dt).total_seconds() // 86400)
                    except Exception:
                        days = 9
                    rec = 3.0 if days <= 0 else (2.0 if days == 1 else (1.0 if days == 2 else 0.2))
                title = str(it.get("title") or "")
                mark = 1.2 if any(m in title for m in policy_marks) else 0.0
                return tag_sum * 10.0 + rec + mark

            cluster_items.sort(key=_score_item, reverse=True)
            cluster_items = cluster_items[:max_cluster_items]

        # LLM clustering & naming
        events = cluster_recent_hotspots_llm(client=self.client, model=self.keywords_model, items=cluster_items, target_n=top_k)
        if not events:
            return []

        # Local hotness score: coverage + breadth + recency (display only)
        def _hotness(source_ids: List[int]) -> Tuple[int, int, str]:
            sids = [int(x) for x in (source_ids or []) if isinstance(x, int) or str(x).isdigit()]
            sids = [int(x) for x in sids if int(x) > 0]
            docs = len(set(sids))
            accs = len(set([str(sid_meta.get(int(sid), {}).get("account") or "") for sid in sids if str(sid_meta.get(int(sid), {}).get("account") or "")]))
            # last_seen
            last_dt = None
            last_sid = None
            for sid in sids:
                dt = getattr(source_articles.get(int(sid)), "published_at", None)
                if isinstance(dt, datetime) and (last_dt is None or dt > last_dt):
                    last_dt = dt
                    last_sid = sid
            last_seen = self._date_str_for_article(source_articles.get(int(last_sid)) if last_sid else None)
            # map to 0..100
            score = int(min(100, 20 + docs * 18 + accs * 10))
            return score, docs, last_seen

        out: List[Dict[str, Any]] = []
        for ev in events:
            sids = ev.get("source_ids") or []
            if not isinstance(sids, list) or len(sids) < 2:
                continue
            hot, docs, last_seen = _hotness([int(x) for x in sids if isinstance(x, int) or str(x).isdigit()])
            accs = len(set([str(sid_meta.get(int(sid), {}).get("account") or "") for sid in sids if str(sid_meta.get(int(sid), {}).get("account") or "")]))
            out.append(
                {
                    "event": str(ev.get("event") or ""),
                    "hotness": int(hot),
                    "source_ids": [int(x) for x in sids if isinstance(x, int) or str(x).isdigit()][:6],
                    "coverage_docs": int(docs),
                    "coverage_accounts": int(accs),
                    "last_seen": str(last_seen or ""),
                    "why_hot": str(ev.get("why_hot") or ""),
                    "category": str(ev.get("category") or "other"),
                }
            )

        out.sort(key=lambda x: int(x.get("hotness") or 0), reverse=True)
        return out[:top_k]

    def _is_focus_too_local_or_narrow(self, *, obj_try: Dict[str, Any], sources_for_prompt: List[Dict[str, Any]]) -> bool:
        """
        Enforce product positioning:
        - Title should not be county/district/town level. Prefer province-wide or at least city-level framing.
        - For common_issue, citations should span multiple prefecture-level cities (best-effort).
        """
        if not isinstance(obj_try, dict):
            return False
        header = obj_try.get("header") or {}
        title = ""
        try:
            if isinstance(header, dict):
                title = str(header.get("title") or "").strip()
        except Exception:
            title = ""
        visual_focus = str(obj_try.get("visual_focus") or "").strip()

        # Markers implying county/district-level anchoring in headline.
        local_markers = ["县", "区", "镇", "乡", "街道", "开发区", "新区", "园区", "经开", "高新"]
        allow_broad = any(x in title for x in ["全省", "浙江", "省级"])
        has_city = any(c in title for c in self._ZJ_CITIES)

        # If headline contains a local marker, reject unless it is explicitly province-level framing.
        if title and any(m in title for m in local_markers) and not allow_broad:
            return True

        # For common_issue: ensure multi-city coverage in citations (best-effort).
        if visual_focus == "common_issue":
            cited_ids: List[int] = []
            try:
                lede_cits = header.get("lede_citations") if isinstance(header, dict) else []
                for arr in (lede_cits, obj_try.get("why_citations"), obj_try.get("big_picture_citations")):
                    if isinstance(arr, list):
                        for x in arr:
                            try:
                                n = int(x)
                            except Exception:
                                continue
                            if n > 0 and n not in cited_ids:
                                cited_ids.append(n)
            except Exception:
                cited_ids = []

            id2src: Dict[int, Dict[str, Any]] = {}
            for s in sources_for_prompt or []:
                if isinstance(s, dict) and s.get("id"):
                    try:
                        id2src[int(s["id"])] = s
                    except Exception:
                        pass

            cities: set[str] = set()
            for sid in cited_ids:
                s = id2src.get(int(sid)) or {}
                blob = f"{s.get('account') or ''} {s.get('title') or ''}"
                for c in self._ZJ_CITIES:
                    if c in blob:
                        cities.add(c)
            # If we cannot detect at least 2 cities and title isn't broadly framed, treat as too narrow.
            if len(cities) < 2 and not allow_broad:
                # If title is city-level but common_issue still only cites that city, it's still too narrow.
                if has_city:
                    return True
                return True

        # For high_impact_event: allow city-level or province-level; reject if neither and looks local.
        if visual_focus == "high_impact_event":
            if title and any(m in title for m in local_markers) and not (allow_broad or has_city):
                return True

        return False

    def _summarize_per_article(
        self,
        *,
        sources: List[Dict[str, Any]],
        source_articles: Dict[int, Article],
    ) -> List[Dict[str, Any]]:
        """
        Summary-only pipeline (cheaper):
        For each filtered article, generate 1-sentence summary (<=80 chars).
        Output: [{"source_id":sid, "title":..., "summary":...}]
        """
        out: List[Dict[str, Any]] = []
        for s in sources:
            try:
                sid = int(s.get("id"))
            except Exception:
                continue
            if not sid:
                continue
            a = source_articles.get(sid)
            if not a:
                continue
            title = str(getattr(a, "title", "") or "").strip()
            body = str(getattr(a, "content", "") or "").strip()
            clip = clean_text(body)[: self.cfg.per_article_chars]
            # Keep prompt cheap. Summary must be grounded in title/body.
            system = (
                "你是浙江财政晨报系统的“逐篇总结器”。\n"
                "请对输入文章生成一句话总结（<=80字），不得编造事实。\n"
                "只输出严格JSON：{\"summary\":\"...\"}\n"
            )
            user = f"[{sid}] 标题：{title}\n正文：{clip}\n"
            summary = ""
            try:
                resp = self.client.chat.completions.create(
                    model=self.keywords_model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.1,
                    timeout=45,
                )
                txt = (resp.choices[0].message.content or "").strip()
                obj = extract_first_json(txt) or {}
                summary = str(obj.get("summary") or "").strip()
            except Exception as e:
                logger.warning(f"Per-article summary failed: id={sid}, model={self.keywords_model}, err={e}")
                summary = ""

            if not summary:
                # Fallback: use key snippets / first sentence from cleaned body, then fallback to title.
                try:
                    snips = extract_key_snippets(clip, max_snippets=self.cfg.max_snippets_per_article)
                    summary = (snips[0] if snips else "").strip()
                except Exception:
                    summary = ""
            if not summary:
                summary = title[:80]

            out.append(
                {
                    "source_id": sid,
                    "title": title[:120],
                    "summary": summary[:120],
                }
            )
        return out
    def _smart_brevity_user_from_summaries(
        self,
        per_article: List[Dict[str, Any]],
        *,
        focus_type: str,
        focus_style: str,
        lead_variant: str,
        recent_focus_topics: List[str],
        extra_instructions: str = "",
    ) -> str:
        """
        Step 3 input: only per-article summaries, to reduce cost.
        """
        lines: List[str] = []
        for it in per_article:
            sid = it.get("source_id")
            summ = str(it.get("summary") or "").strip()
            title = str(it.get("title") or "").strip()
            if not sid:
                continue
            # fallback to title if summary empty
            core = summ or title
            if not core:
                continue
            lines.append(f"[{sid}] {core}")

        material = "\n".join(lines)
        # 5 main styles (avoid mechanical writing by rotating style)
        style_rules = {
            "data_snapshot": "主写法：硬事实快照。lede=一句话主事实；why=2-4个硬点（数字/范围/对象/时间）；big=口径/边界/未披露项（若材料未披露就写“未披露”）。",
            "action_chain": "主写法：动作链。lede=发布/启动的主动作；why=对象+条件；big=流程/渠道/时间表（只写材料有的）。",
            "what_changed": "主写法：变化对比。lede=现在发生了什么；why=与以往相比的变化点1；big=变化点2或边界/缺口（材料没有就写未披露）。",
            "timeline": "主写法：时间轴。lede=最关键时间节点+动作；why=第二时间节点；big=第三时间节点或截止/目标年（没有就写未披露）。",
            "qna_gaps": "主写法：Q&A+缺口。lede=用一个问句引出主事件（不超过20字问句）；why=用事实回答；big=材料未披露/仍待明确的缺口（不下判断）。",
        }
        micro_variants = {
            "v1_numbers_first": "微变体：数字/指标开场（若材料有数字/目标则优先）。",
            "v2_time_first": "微变体：时间节点开场（“即日起/2026年/截至…”）。",
            "v3_actor_first": "微变体：主体开场（“浙江×部门/×市/×地”）。",
            "v4_doc_first": "微变体：文件/政策名开场（“《××方案》明确…”）。",
            "v5_scope_first": "微变体：对象/覆盖开场（“面向××人群/车辆/企业…”）。",
            "v6_threshold_first": "微变体：条件/门槛开场（“符合××条件可…”）。",
            "v7_change_first": "微变体：变化点开场（“新增/调整/扩大/提高…”）。",
            "v8_process_first": "微变体：流程开场（“申报→审核→发放…”但只写材料有的）。",
            "v9_quote_first": "微变体：若材料有一句最硬的原句，可用引号开场（必须是材料原句/可定位）。",
            "v10_plain": "微变体：朴素直述开场（无修辞、无评价）。",
        }

        style_hint = style_rules.get(focus_style, style_rules["data_snapshot"])
        variant_hint = micro_variants.get(lead_variant, micro_variants["v10_plain"])

        dedupe = ""
        if recent_focus_topics:
            topics = "、".join(recent_focus_topics[:10]) if recent_focus_topics else "（无）"
            dedupe = (
                "\n焦点去重约束（必须遵守）：\n"
                f"- 最近3天已用焦点主题 focus_topic：{topics}\n"
                "- 今日必须选择不同的 focus_topic（不重复/不高度重叠）。\n"
            )

        return (
            "请基于以下“逐篇总结”生成《浙江财政信息摘要》JSON。\n"
            "注意：你只能引用方括号里的编号作为 citations；不要编造来源。\n"
            f"今日焦点类型：{focus_type}\n"
            f"{style_hint}\n"
            f"{variant_hint}\n\n"
            f"{dedupe}"
            f"{extra_instructions}"
            f"{material}\n"
        )

    def _is_topic_semantic_duplicate(self, *, topic: str, recent_topics: List[str]) -> bool:
        """
        Use cheap model to judge whether topic is semantically overlapping with recent topics.
        """
        t = (topic or "").strip()
        if not t:
            return False
        r = [x.strip() for x in (recent_topics or []) if isinstance(x, str) and x.strip()]
        if not r:
            return False
        # quick exact check
        if t in set(r):
            return True
        system = (
            "你是主题去重判定器。\n"
            "判断“候选主题”是否与“历史主题列表”语义相近（同一政策/同一补贴/同一领域同一事件），相近则视为重复。\n"
            "只输出严格JSON：{\"duplicate\":true|false}\n"
        )
        user = json.dumps({"candidate": t, "history": r[:10]}, ensure_ascii=False)
        try:
            resp = self.client.chat.completions.create(
                model=self.keywords_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0,
                timeout=30,
            )
            txt = (resp.choices[0].message.content or "").strip()
            obj = extract_first_json(txt) or {}
            return bool(obj.get("duplicate") is True)
        except Exception:
            return False

    def _choose_focus_style(
        self,
        *,
        target_date: date,
        per_article: List[Dict[str, Any]],
        recent_focus_styles: List[str],
        recent_lead_variants: List[str],
    ) -> Tuple[str, str, str]:
        """
        Choose 1 of 5 main focus styles + 1 of 10 micro lead variants.
        This is rule-based (cheap, deterministic) to avoid extra model calls.
        """
        text = " ".join([str(it.get("summary") or "") for it in (per_article or [])]).strip()
        text2 = text[:8000]

        # focus_type heuristic
        has_num = bool(re.search(r"\d", text2))
        has_time = bool(re.search(r"(即日起|日起|截至|截止|目标|到\\d{4}年|\\d{4}年|\\d{1,2}月|\\d{1,2}日)", text2))
        has_change = bool(re.search(r"(新增|调整|扩大|提高|下调|上调|优化|完善|修订|更新|取消|暂停)", text2))
        has_process = bool(re.search(r"(申报|申请|审核|发放|补贴|补助|办理|材料|渠道|流程|公示|兑付)", text2))
        has_q = bool(re.search(r"(如何|怎么|什么条件|怎么领|是否|能否|哪里办|需要什么)", text2))

        # decide focus_type + primary style, and also produce ranked alternatives (for dedupe)
        if has_q and has_process:
            focus_type = "qna_heavy"
            ranked = ["qna_gaps", "action_chain", "timeline", "data_snapshot", "what_changed"]
        elif has_time and has_process:
            focus_type = "timeline_heavy"
            ranked = ["timeline", "action_chain", "data_snapshot", "what_changed", "qna_gaps"]
        elif has_change:
            focus_type = "change_heavy"
            ranked = ["what_changed", "data_snapshot", "timeline", "action_chain", "qna_gaps"]
        elif has_process:
            focus_type = "process_heavy"
            ranked = ["action_chain", "timeline", "data_snapshot", "qna_gaps", "what_changed"]
        elif has_num:
            focus_type = "data_heavy"
            ranked = ["data_snapshot", "timeline", "what_changed", "action_chain", "qna_gaps"]
        else:
            focus_type = "general"
            ranked = ["data_snapshot", "action_chain", "timeline", "what_changed", "qna_gaps"]

        # de-dup main style vs recent days (avoid repeating the same style)
        recent_main = [x for x in (recent_focus_styles or []) if isinstance(x, str)]
        avoid = set(recent_main[:2])  # only avoid last 2 days to keep stability
        focus_style = next((s for s in ranked if s not in avoid), ranked[0])

        # micro variant: stable rotation by date + focus_style
        key = f"{target_date.isoformat()}|{focus_style}".encode("utf-8")
        h = int(hashlib.md5(key).hexdigest(), 16)
        idx = h % 10
        lead_variants = [
            "v1_numbers_first",
            "v2_time_first",
            "v3_actor_first",
            "v4_doc_first",
            "v5_scope_first",
            "v6_threshold_first",
            "v7_change_first",
            "v8_process_first",
            "v9_quote_first",
            "v10_plain",
        ]
        lead_variant = lead_variants[idx]
        # de-dup micro variant vs recent (avoid repeating last day)
        recent_lv = [x for x in (recent_lead_variants or []) if isinstance(x, str)]
        if recent_lv and lead_variant == recent_lv[0]:
            lead_variant = lead_variants[(idx + 1) % 10]

        return focus_type, focus_style, lead_variant

    def _prefilter_articles(self, articles: Sequence[Article]) -> List[Article]:
        """
        Conservative prefilter:
        - Keep all if too few would remain.
        - Otherwise prioritize those with >= min_finance_kw_hits in title+content.
        """
        hits: List[Tuple[int, Article]] = []
        for a in articles:
            blob = f"{a.title or ''}\n{a.content or ''}"
            h = finance_keyword_hits(blob)
            hits.append((h, a))
        hits.sort(key=lambda x: x[0], reverse=True)
        kept = [a for h, a in hits if h >= self.cfg.min_finance_kw_hits]
        # Avoid over-filtering: ensure at least 8 articles for breadth if possible
        if len(kept) >= 8:
            return kept
        # fallback to top-N by hits
        return [a for _, a in hits[: min(len(hits), 20)]]

    def _build_material(self, articles: Sequence[Article]) -> Tuple[str, List[Dict[str, Any]] , Dict[int, Article]]:
        max_total = int(os.getenv("DAILY_REPORT_MAX_INPUT_CHARS", str(self.cfg.max_input_chars)))
        per_article = int(os.getenv("DAILY_REPORT_PER_ARTICLE_MAX_CHARS", str(self.cfg.per_article_chars)))

        blocks: List[str] = []
        sources: List[Dict[str, Any]] = []
        source_articles: Dict[int, Article] = {}
        total = 0

        for idx, a in enumerate(articles, start=1):
            account_name = ""
            try:
                if getattr(a, "account", None) and getattr(a.account, "name", None):
                    account_name = a.account.name
            except Exception:
                account_name = ""
            url = getattr(a, "article_url", "") or ""
            pub = ""
            try:
                if getattr(a, "published_at", None):
                    pub = a.published_at.isoformat()
            except Exception:
                pub = ""

            body = clean_text(a.content or "")
            if len(body) > per_article:
                # keep head + key snippets
                head = body[: int(per_article * 0.7)].rstrip()
                snippets = extract_key_snippets(body, max_snippets=self.cfg.max_snippets_per_article)
                snip_block = ""
                if snippets:
                    snip_block = "关键句（原文摘录）：\n- " + "\n- ".join(snippets)
                body = (head + ("\n\n" + snip_block if snip_block else "")).strip()
                body = body[:per_article].rstrip()

            nums = extract_number_spans(body, max_items=12)
            nums_block = ""
            if nums:
                nums_block = "关键数字（原文摘录）：\n- " + "\n- ".join(nums)

            block = "\n".join(
                [
                    f"[{idx}] 标题: {a.title or ''}",
                    f"公众号: {account_name or '（未知）'}",
                    f"URL: {url or '（未知）'}",
                    f"发布时间: {pub or '（未知）'}",
                    f"正文: {body}",
                    nums_block,
                ]
            ).strip()

            if total + len(block) > max_total:
                break
            total += len(block)
            blocks.append(block)
            sources.append({"id": idx, "account": account_name, "title": a.title or "", "url": url})
            source_articles[idx] = a

        return "\n\n---\n\n".join(blocks), sources, source_articles

    def _call_llm(self, *, system_prompt: str, user_prompt: str, temperature: float, timeout: int) -> str | None:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                timeout=timeout,
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as e:
            logger.error(f"Daily briefing LLM call failed: {e}")
            return None

    def _normalize_sources_and_citations(self, *, obj: Dict[str, Any], sources_for_prompt: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Keep only cited source ids; remap to 1..N; update sources and citations arrays.
        """
        used_old: List[int] = []
        seen: set[int] = set()

        def consume(x):
            if isinstance(x, list):
                for v in x:
                    try:
                        n = int(v)
                    except Exception:
                        continue
                    if n not in seen:
                        seen.add(n)
                        used_old.append(n)

        header = obj.get("header")
        if isinstance(header, dict):
            consume(header.get("lede_citations"))
        consume(obj.get("why_citations"))
        consume(obj.get("big_picture_citations"))
        btn = obj.get("by_the_numbers")
        if isinstance(btn, list):
            for row in btn:
                if isinstance(row, dict):
                    consume(row.get("citations"))
        # Keep sources referenced by keywords
        kws = obj.get("keywords")
        if isinstance(kws, list):
            for it in kws:
                if isinstance(it, dict):
                    consume(it.get("source_ids"))
        # Keep sources referenced by recent hotwords (近日热词)
        rhw = obj.get("recent_hotwords")
        if isinstance(rhw, list):
            for it in rhw:
                if isinstance(it, dict):
                    consume(it.get("source_ids"))
        # Keep sources referenced by recent hotspots (近日热点)
        rhs = obj.get("recent_hotspots")
        if isinstance(rhs, list):
            for it in rhs:
                if isinstance(it, dict):
                    consume(it.get("source_ids"))

        id_to_source: Dict[int, Dict[str, Any]] = {}
        for s in sources_for_prompt or []:
            if not isinstance(s, dict):
                continue
            try:
                sid = int(s.get("id"))
            except Exception:
                continue
            id_to_source[sid] = s

        mapping: Dict[int, int] = {}
        new_sources: List[Dict[str, Any]] = []
        next_id = 1
        for old in used_old:
            src = id_to_source.get(old)
            if not src:
                continue
            mapping[old] = next_id
            new_sources.append(
                {
                    "id": next_id,
                    "account": src.get("account") or "",
                    "title": src.get("title") or "",
                    "url": src.get("url") or "",
                    "date": src.get("date") or "",
                }
            )
            next_id += 1

        def remap_list(lst):
            if not isinstance(lst, list):
                return []
            out: List[int] = []
            seen2: set[int] = set()
            for v in lst:
                try:
                    old = int(v)
                except Exception:
                    continue
                if old not in mapping:
                    continue
                nid = mapping[old]
                if nid in seen2:
                    continue
                seen2.add(nid)
                out.append(nid)
            return out

        out = dict(obj)
        header2 = out.get("header")
        if isinstance(header2, dict):
            header2 = dict(header2)
            header2["lede_citations"] = remap_list(header2.get("lede_citations"))
            out["header"] = header2
        out["why_citations"] = remap_list(out.get("why_citations"))
        out["big_picture_citations"] = remap_list(out.get("big_picture_citations"))
        btn2 = out.get("by_the_numbers")
        if isinstance(btn2, list):
            new_rows = []
            for row in btn2:
                if not isinstance(row, dict):
                    continue
                r2 = dict(row)
                r2["citations"] = remap_list(r2.get("citations"))
                new_rows.append(r2)
            out["by_the_numbers"] = new_rows

        # remap keywords source_ids
        kws2 = out.get("keywords")
        if isinstance(kws2, list):
            new_kws = []
            for it in kws2:
                if not isinstance(it, dict):
                    continue
                it2 = dict(it)
                it2["source_ids"] = remap_list(it2.get("source_ids"))
                new_kws.append(it2)
            out["keywords"] = new_kws

        # remap recent hotwords source_ids
        rhw2 = out.get("recent_hotwords")
        if isinstance(rhw2, list):
            new_rhw = []
            for it in rhw2:
                if not isinstance(it, dict):
                    continue
                it2 = dict(it)
                it2["source_ids"] = remap_list(it2.get("source_ids"))
                new_rhw.append(it2)
            out["recent_hotwords"] = new_rhw

        # remap recent hotspots source_ids
        rhs2 = out.get("recent_hotspots")
        if isinstance(rhs2, list):
            new_rhs = []
            for it in rhs2:
                if not isinstance(it, dict):
                    continue
                it2 = dict(it)
                it2["source_ids"] = remap_list(it2.get("source_ids"))
                new_rhs.append(it2)
            out["recent_hotspots"] = new_rhs

        out["sources"] = new_sources
        return out

    def _extract_today_keywords(
        self,
        *,
        recent_hotspots: List[Dict[str, Any]],
        sources_all: List[Dict[str, Any]],
        source_articles_all: Dict[int, Article],
    ) -> List[Dict[str, Any]]:
        """
        Extract top 3 keywords from recent hotspots for "今日关键词" section.
        Each keyword should have: word, weight (hotness), source_ids, citations count.
        """
        if not recent_hotspots:
            return []
        
        # Take top 3 hotspots and convert to keywords format
        keywords: List[Dict[str, Any]] = []
        for hotspot in recent_hotspots[:3]:
            if not isinstance(hotspot, dict):
                continue
            event = str(hotspot.get("event") or "").strip()
            if not event:
                continue
            hotness = int(hotspot.get("hotness") or 0)
            source_ids = hotspot.get("source_ids") or []
            if not isinstance(source_ids, list):
                source_ids = []
            source_ids = [int(x) for x in source_ids if isinstance(x, (int, str)) and str(x).isdigit()]
            
            # Get snippets from source articles (first 2 sources)
            snippets: List[str] = []
            for sid in source_ids[:2]:
                article = source_articles_all.get(sid)
                if article:
                    title = str(getattr(article, "title", "") or "").strip()
                    if title:
                        snippets.append(title)
            
            keywords.append({
                "word": event,
                "weight": hotness,  # Use hotness as weight
                "hotness": hotness,
                "citations": len(source_ids),
                "source_ids": source_ids[:6],  # Limit to 6 sources
                "snippets": snippets[:4],  # Limit to 4 snippets
            })
        
        return keywords
