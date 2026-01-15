"""
Report rendering helpers.

Goal:
- AI outputs structured JSON (not Markdown) for daily reports.
- Backend renders safe HTML for both web display and email.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any, Dict, List, Optional


def _esc(s: Any) -> str:
    return escape("" if s is None else str(s), quote=True)


def _render_citations(citations: Optional[List[int]]) -> str:
    if not citations:
        return ""
    # e.g. [1][3]
    parts = []
    for cid in citations:
        try:
            n = int(cid)
        except Exception:
            continue
        parts.append(
            f'<a href="#src-{n}" style="color:#2563eb;text-decoration:none;">[{n}]</a>'
        )
    if not parts:
        return ""
    return f'<sup style="margin-left:6px;font-size:12px;vertical-align:top;">{"".join(parts)}</sup>'


def _linkify_inline_citations(escaped_text: str) -> str:
    """
    Convert inline citation markers like [12] inside already-escaped text into clickable anchors.
    """
    if not escaped_text:
        return ""
    return re.sub(
        r"\[(\d+)\]",
        r'<a href="#src-\1" style="color:#2563eb;text-decoration:none;">[\1]</a>',
        escaped_text,
    )


def render_daily_report_html(report_json: Dict[str, Any], for_email: bool = True) -> str:
    """
    Render report JSON to a compact, email-safe HTML string (inline styles).

    Args:
        report_json: The report data in JSON format
        for_email: If True, returns HTML fragment (without <html>/<body> tags) for email template
                   If False, returns complete HTML document
    """
    header = report_json.get("header") or {}
    title = _esc(header.get("title") or "财政日报")
    date = _esc(header.get("date") or "")

    brief = header.get("brief") or []
    if isinstance(brief, str):
        brief = [brief]
    brief = [b for b in brief if b]

    # Smart Brevity schema (财政信息聚合)
    schema = report_json.get("schema") if isinstance(report_json, dict) else None
    if schema == "smart_brevity_v1":
        lede = str(header.get("lede") or "").strip()
        why = str(report_json.get("why_it_matters") or "").strip()
        big = str(report_json.get("big_picture") or "").strip()
        # Prefer recent hotspots ("近日热点") if available; fallback to legacy "recent_hotwords"/"keywords"
        hotspots = report_json.get("recent_hotspots") or []
        hot_meta = report_json.get("recent_hotspots_meta") or {}
        keywords = report_json.get("recent_hotwords") or report_json.get("keywords") or []
        sources = report_json.get("sources") or []
        easter_egg = report_json.get("easter_egg") or {}

        # Build sources lookup
        sources_by_id: Dict[int, Dict[str, Any]] = {}
        for s in sources:
            if not isinstance(s, dict):
                continue
            try:
                sid = int(s.get("id", 0))
                if sid > 0:
                    sources_by_id[sid] = s
            except Exception:
                continue

        # Format date for Hero: "12月25日"
        hero_date = date
        try:
            from datetime import datetime
            if date:
                d = datetime.strptime(date, "%Y-%m-%d")
                hero_date = f"{d.month}月{d.day}日"
        except Exception:
            pass

        html: List[str] = []

        # Only add complete HTML structure if not for email
        if not for_email:
            html.append('<!DOCTYPE html>')
            html.append('<html>')
            html.append('<head>')
            html.append('<meta charset="UTF-8">')
            html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            html.append('<style>')
            html.append('@media only screen and (min-width: 600px) {')
            html.append('  .container { max-width: 800px !important; margin: 0 auto !important; }')
            html.append('  .hero-padding { padding: 32px 48px !important; }')
            html.append('  .hero-title { font-size: 56px !important; }')
            html.append('  .hero-subtitle { font-size: 20px !important; }')
            html.append('  .hero-date { font-size: 28px !important; }')
            html.append('  .hero-label { font-size: 22px !important; }')
            html.append('  .section-padding { padding: 32px 40px !important; }')
            html.append('  .focus-headline { font-size: 28px !important; }')
            html.append('  .focus-text { font-size: 16px !important; }')
            html.append('  .hotspot-title { font-size: 22px !important; }')
            html.append('  .hotspot-text { font-size: 15px !important; }')
            html.append('}')
            html.append('</style>')
            html.append('</head>')
            html.append('<body style="margin:0;padding:0;background-color:#f9fafb;">')

        html.append('<div class="container" style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;color:#111827;line-height:1.65;width:100%;max-width:100%;margin:0 auto;padding:0;">')
        
        # Hero Section - Mobile-first, dark gradient background matching frontend
        html.append('<div style="position:relative;overflow:hidden;border-radius:16px;background:linear-gradient(135deg, #0f172a 0%, #0f172a 100%);color:#ffffff;box-shadow:0 10px 25px -5px rgba(0,0,0,0.2);margin-bottom:16px;">')
        html.append('<div class="hero-padding" style="position:relative;padding:20px 16px;">')
        html.append('<div style="display:flex;flex-direction:column;align-items:flex-start;gap:12px;">')
        html.append('<div style="width:100%;">')
        html.append('<h1 class="hero-title" style="font-size:36px;font-weight:700;letter-spacing:-0.025em;color:#ffffff;margin:0 0 8px 0;line-height:1.05;">浙财脉动</h1>')
        html.append('<p class="hero-subtitle" style="font-size:14px;color:rgba(255,255,255,0.8);margin:0;line-height:1.5;">大模型聚合的财政情报 · 每日10点更新</p>')
        html.append("</div>")
        html.append('<div style="text-align:left;width:100%;">')
        html.append(f'<div class="hero-date" style="font-size:12px;font-weight:700;color:#ffffff;margin-bottom:4px;">{_esc(hero_date)}</div>')
        html.append('<div class="hero-label" style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.9);">晨报</div>')
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")

        # 今日焦点 Section - Matching frontend style
        if lede or why or big:
            # Strip markers from text
            def strip_markers(t: str) -> str:
                return re.sub(r'【\s*(为何重要|为什么重要|大局)\s*】', '', t).replace('为何重要:', '').replace('为什么重要:', '').replace('大局:', '').strip()
            
            # Merge lede, why, big into single paragraph
            focus_parts = []
            if lede:
                focus_parts.append(strip_markers(lede))
            if why:
                focus_parts.append(strip_markers(why))
            if big:
                focus_parts.append(strip_markers(big))
            focus_text = " ".join([p for p in focus_parts if p])
            
            # Extract first sentence for highlighting
            first_sentence = ""
            rest_text = focus_text
            if focus_text:
                first_match = re.match(r'^[^。！？]+[。！？]', focus_text)
                if first_match:
                    first_sentence = first_match.group(0)
                    rest_text = focus_text[len(first_sentence):].strip()
                else:
                    # Fallback: first sentence until first period
                    parts = focus_text.split('。', 1)
                    if len(parts) > 1:
                        first_sentence = parts[0] + '。'
                        rest_text = parts[1].strip()
                    else:
                        first_sentence = focus_text.split('。')[0] + ('。' if '。' in focus_text else '')
                        rest_text = focus_text[len(first_sentence):].strip()
            
            focus_citations = list(set((header.get("lede_citations") or []) + (report_json.get("why_citations") or []) + (report_json.get("big_picture_citations") or [])))
            
            html.append('<div style="background-color:#ffffff;border-radius:16px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -2px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;border-left:4px solid #d97706;">')
            
            # Title bar with gradient - Mobile-first (low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(254, 243, 199, 0.3) 100%);padding:16px 16px 12px 16px;">')
            html.append('<div style="display:flex;align-items:center;gap:10px;">')
            html.append('<div style="width:32px;height:32px;border-radius:50%;background-color:#d97706;display:flex;align-items:center;justify-content:center;color:#ffffff;font-weight:700;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);flex-shrink:0;">i</div>')
            html.append('<div style="min-width:0;flex:1;">')
            html.append('<div style="font-size:18px;font-weight:700;color:#111827;">今日焦点</div>')
            html.append('<div style="font-size:12px;color:#6b7280;margin-top:2px;">近24小时最值得关注的财政动态</div>')
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")

            # Content area - Mobile-first
            html.append('<div class="section-padding" style="padding:20px 16px;background-color:rgba(248,250,252,0.2);">')
            
            # Headline (title from header) - Mobile-first
            if title:
                html.append(f'<h2 class="focus-headline" style="font-size:24px;font-weight:500;color:#111827;margin:0 0 16px 0;line-height:1.2;">{_esc(title)}</h2>')
            
            # Main body text with first sentence highlight - Mobile-first
            if focus_text:
                html.append('<div class="focus-text" style="font-size:14px;line-height:1.6;color:#111827;margin-bottom:20px;font-weight:300;">')
                if first_sentence:
                    html.append(f'<span style="background-color:rgba(254, 243, 199, 0.5);padding:4px 8px;border-radius:4px;">{_esc(first_sentence)}</span>')
                if rest_text:
                    html.append(f'<span style="margin-left:4px;">{_esc(rest_text)}</span>')
                html.append("</div>")
            
            # Citation sources - Badge style
            if focus_citations:
                html.append('<div style="margin-top:24px;">')
                html.append('<div style="display:flex;flex-wrap:wrap;gap:8px;">')
                # Show all sources in email (no "more" button)
                for cid in focus_citations:
                    try:
                        sid = int(cid)
                        src = sources_by_id.get(sid)
                        if src:
                            account = _esc(str(src.get("account") or ""))
                            stitle = _esc(str(src.get("title") or ""))
                            url = str(src.get("url") or "")
                            display_text = f"{account} · {stitle}" if account else stitle
                            if url:
                                html.append(f'<a href="{_esc(url)}" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</a>')
                            else:
                                html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</span>')
                    except Exception:
                        continue
                html.append("</div>")
                html.append("</div>")
            
            html.append("</div>")
            html.append("</div>")

        # 近日热点 Section - Matching frontend style
        hotspots_list = hotspots if isinstance(hotspots, list) else []
        if not hotspots_list and isinstance(keywords, list):
            # Fallback to keywords format
            hotspots_list = [{"event": str(k.get("word") or ""), "source_ids": k.get("source_ids") or []} for k in keywords if isinstance(k, dict) and k.get("word")]
        
        if hotspots_list:
            # Filter: only coverage_accounts >= 3
            filtered_hotspots = []
            for h in hotspots_list:
                if not isinstance(h, dict):
                    continue
                event = str(h.get("event") or "").strip()
                if not event:
                    continue
                coverage_accounts = int(h.get("coverage_accounts") or 0)
                if coverage_accounts >= 3:
                    # Calculate hotness if not present: 20 + 文档数 × 18 + 账号数 × 10, max 100
                    if "hotness" not in h or not h.get("hotness"):
                        coverage_docs = int(h.get("coverage_docs") or 0)
                        calculated_hotness = min(100, 20 + coverage_docs * 18 + coverage_accounts * 10)
                        h["hotness"] = calculated_hotness
                    filtered_hotspots.append(h)
            
            # Sort by hotness and take top 3
            def get_hotness(h: Dict[str, Any]) -> int:
                try:
                    return int(h.get("hotness") or 0)
                except Exception:
                    return 0
            filtered_hotspots.sort(key=get_hotness, reverse=True)
            display_hotspots = filtered_hotspots[:3]
            
            html.append('<div style="background-color:#ffffff;border-radius:16px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -2px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;">')
            
            # Title bar with gradient - Mobile-first (low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(209, 250, 229, 0.3) 100%);padding:16px 16px 12px 16px;">')
            html.append('<div style="display:flex;align-items:center;gap:10px;">')
            html.append('<div style="width:32px;height:32px;border-radius:50%;background-color:#059669;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 4px rgba(0,0,0,0.1);flex-shrink:0;">')
            html.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>')
            html.append("</div>")
            html.append('<div style="min-width:0;flex:1;">')
            html.append('<div style="font-size:18px;font-weight:700;color:#111827;">近日热点</div>')
            html.append('<div style="font-size:12px;color:#6b7280;margin-top:2px;">近3天覆盖3个不同公众号的话题</div>')
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")
            
            # Content area - Single column cards - Mobile-first
            html.append('<div class="section-padding" style="padding:20px 16px;">')
            html.append('<div style="display:flex;flex-direction:column;gap:12px;">')
            
            for hotspot in display_hotspots:
                event = str(hotspot.get("event") or "").strip()
                why_hot = str(hotspot.get("why_hot") or "").strip()
                source_ids = hotspot.get("source_ids") or []
                if not isinstance(source_ids, list):
                    source_ids = []
                
                # Sort sources: prioritize different accounts, then by date descending
                sorted_source_ids = sorted(source_ids, key=lambda sid: (
                    sources_by_id.get(int(sid), {}).get("account", ""),
                    -int(sources_by_id.get(int(sid), {}).get("date", "0").replace("-", "").replace(":", "").replace(" ", "")) if sources_by_id.get(int(sid), {}).get("date") else 0
                ))
                
                # Get one latest source per account
                account_map: Dict[str, int] = {}
                prioritized_sources = []
                for sid in sorted_source_ids:
                    try:
                        sid_int = int(sid)
                        src = sources_by_id.get(sid_int)
                        if src:
                            account = str(src.get("account") or "")
                            if account and account not in account_map:
                                account_map[account] = sid_int
                                prioritized_sources.append(sid_int)
                    except Exception:
                        continue
                
                # Add remaining sources
                for sid in sorted_source_ids:
                    try:
                        sid_int = int(sid)
                        if sid_int not in prioritized_sources:
                            prioritized_sources.append(sid_int)
                    except Exception:
                        continue
                
                # Show first 3 sources (increased from 2 for better coverage)
                default_sources = prioritized_sources[:3]
                
                html.append('<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:linear-gradient(to bottom right, #f9fafb, #ffffff);">')
                
                # Event name - Mobile-first
                if event:
                    html.append(f'<div class="hotspot-title" style="font-size:18px;font-weight:500;color:#111827;margin-bottom:6px;">{_esc(event)}</div>')
                
                # Why hot explanation - Mobile-first
                if why_hot:
                    html.append(f'<div class="hotspot-text" style="font-size:13px;color:#475569;line-height:1.6;margin-bottom:10px;font-weight:300;">{_esc(why_hot)}</div>')
                
                # Sources - Badge style (matching frontend, max 3 sources)
                html.append('<div style="display:flex;flex-wrap:wrap;gap:8px;">')
                for sid in default_sources:
                    src = sources_by_id.get(int(sid))
                    if not src:
                        continue
                    account = _esc(str(src.get("account") or ""))
                    stitle = _esc(str(src.get("title") or ""))
                    url = str(src.get("url") or "")
                    display_text = f"{account} · {stitle}" if account else stitle
                    if url:
                        html.append(f'<a href="{_esc(url)}" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</a>')
                    else:
                        html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</span>')
                html.append("</div>")
                
                html.append("</div>")
            
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")

        # 今日彩蛋 Section - Matching frontend style
        if easter_egg and isinstance(easter_egg, dict) and (easter_egg.get("url") or easter_egg.get("title") or easter_egg.get("teaser")):
            egg_title = str(easter_egg.get("title") or "").strip()
            egg_teaser = str(easter_egg.get("teaser") or "").strip()
            egg_url = str(easter_egg.get("url") or "")
            egg_account = str(easter_egg.get("account") or "").strip()
            
            html.append('<div style="background-color:#ffffff;border-radius:16px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -2px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;">')
            
            # Title bar with gradient - Mobile-first (low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(252, 231, 243, 0.3) 100%);padding:16px 16px 12px 16px;">')
            html.append('<div style="display:flex;align-items:center;gap:10px;">')
            html.append('<div style="width:32px;height:32px;border-radius:50%;background-color:#be185d;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 4px rgba(0,0,0,0.1);flex-shrink:0;">')
            html.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>')
            html.append("</div>")
            html.append('<div style="min-width:0;flex:1;">')
            html.append('<div style="font-size:18px;font-weight:700;color:#111827;">今日彩蛋</div>')
            if egg_account:
                html.append(f'<div style="font-size:12px;color:#6b7280;margin-top:2px;">来自: {_esc(egg_account)}</div>')
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")
            
            # Content area - Only teaser is clickable (badge format) - Mobile-first
            html.append('<div class="section-padding" style="padding:20px 16px;">')
            if egg_title:
                html.append(f'<div style="font-size:16px;font-weight:500;color:#111827;margin-bottom:6px;">{_esc(egg_title)}</div>')
            if egg_teaser:
                if egg_url and egg_url.startswith(("http://", "https://")):
                    # Use badge format for teaser (only teaser is clickable, matching frontend)
                    html.append(f'<a href="{_esc(egg_url)}" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(egg_teaser)}</a>')
                else:
                    html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:12px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(egg_teaser)}</span>')
            html.append("</div>")
            
            html.append("</div>")

        html.append("</div>")
        html.append("</body>")
        html.append("</html>")
        return "".join(html)

    body = report_json.get("body") or []
    highlights = report_json.get("highlights") or []
    sections = report_json.get("sections") or []
    # watchlist / low_relevance_notes intentionally not rendered (用户要求去掉)
    sources = report_json.get("sources") or []

    html: List[str] = []
    html.append('<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;color:#111827;line-height:1.65;">')
    html.append(f'<div style="margin-bottom:14px;"><div style="font-size:20px;font-weight:800;">{title}</div>')
    if date:
        html.append(f'<div style="font-size:12px;color:#6b7280;margin-top:4px;">{date}</div>')
    html.append("</div>")

    if brief:
        html.append('<div style="padding:12px 14px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:14px;">')
        html.append('<div style="font-weight:700;margin-bottom:6px;">简报概览</div>')
        for p in brief:
            html.append(f'<div style="margin:6px 0;">{_esc(p)}</div>')
        html.append("</div>")

    # New voice format: body paragraphs (3-5 themed segments)
    if isinstance(body, list) and any(isinstance(x, dict) for x in body):
        for seg in body:
            if not isinstance(seg, dict):
                continue
            topic = _esc(seg.get("topic") or "")
            text = _esc(seg.get("text") or "")
            # Inline citations like “湖州[2]” are linkified; do NOT append stacked citations at paragraph end.
            text = _linkify_inline_citations(text)
            if not topic and not text:
                continue
            if topic:
                html.append(f'<div style="margin:18px 0 6px;font-weight:800;font-size:16px;">{topic}</div>')
            if text:
                html.append(f'<div style="margin:6px 0;color:#111827;">{text}</div>')

    # Legacy format: highlights + sections
    elif highlights:
        html.append('<div style="margin:14px 0 8px;font-weight:800;font-size:16px;">今日要点</div>')
        html.append('<ul style="margin:8px 0 0 18px;padding:0;">')
        for it in highlights:
            text = _esc((it or {}).get("text") or "")
            cits = _render_citations((it or {}).get("citations"))
            if text:
                html.append(f'<li style="margin:8px 0;">{text}{cits}</li>')
        html.append("</ul>")

        for sec in sections:
            name = _esc((sec or {}).get("name") or "")
            items = (sec or {}).get("items") or []
            if not name or not items:
                continue
            html.append(f'<div style="margin:18px 0 8px;font-weight:800;font-size:16px;">{name}</div>')
            html.append('<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;background:#ffffff;">')
            for item in items:
                what = _esc((item or {}).get("what") or "")
                explanation = _esc((item or {}).get("explanation") or "")
                signals = (item or {}).get("signals") or []
                cits = _render_citations((item or {}).get("citations"))
                if not what and not explanation:
                    continue
                html.append('<div style="margin:10px 0 12px;">')
                if what:
                    html.append(f'<div style="font-weight:700;">{what}{cits}</div>')
                if explanation:
                    html.append(f'<div style="margin-top:4px;color:#374151;">{explanation}</div>')
                if signals:
                    html.append('<ul style="margin:6px 0 0 18px;padding:0;color:#4b5563;">')
                    for s in signals[:5]:
                        if s:
                            html.append(f'<li style="margin:3px 0;">{_esc(s)}</li>')
                    html.append("</ul>")
                html.append("</div>")
            html.append("</div>")

        # 今日彩蛋 Section (Rose Icon - Matching Frontend)
        easter_egg = report_json.get("easter_egg")
        if easter_egg and isinstance(easter_egg, dict) and (easter_egg.get("url") or easter_egg.get("title") or easter_egg.get("teaser")):
            html.append('<div style="background-color:#ffffff;border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px;">')
            html.append('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">')
            html.append('<div style="width:32px;height:32px;border-radius:50%;background-color:#be185d;display:flex;align-items:center;justify-content:center;">')
            html.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>')
            html.append("</div>")
            html.append('<div>')
            html.append('<div style="font-size:18px;font-weight:600;color:#111827;">今日彩蛋</div>')
            egg_account = easter_egg.get("account")
            if egg_account:
                html.append(f'<div style="font-size:14px;color:#6b7280;margin-top:4px;">来自: {_esc(str(egg_account))}</div>')
            html.append("</div>")
            html.append("</div>")
            
            egg_title = easter_egg.get("title")
            egg_teaser = easter_egg.get("teaser")
            if egg_title:
                html.append(f'<div style="font-size:18px;font-weight:600;color:#111827;margin-bottom:12px;">{_esc(str(egg_title))}</div>')
            if egg_teaser:
                html.append(f'<div style="font-size:14px;line-height:1.6;color:#374151;margin-bottom:16px;">{_esc(str(egg_teaser))}</div>')
            
            egg_url = easter_egg.get("url")
            if egg_url:
                html.append(f'<a href="{_esc(str(egg_url))}" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;gap:8px;padding:10px 16px;background-color:#1e3a8a;color:#ffffff;border-radius:8px;text-decoration:none;font-size:14px;font-weight:500;">')
                html.append('<span>🔗</span>')
                html.append('<span>打开原文</span>')
                html.append("</a>")
            html.append("</div>")

    if sources:
        html.append('<div style="margin:20px 0 8px;font-weight:800;font-size:16px;">来源</div>')
        # 用文本显式编号（防止某些环境/样式不显示列表序号）
        html.append('<div style="margin:8px 0 0;color:#374151;">')
        for s in sources:
            if not isinstance(s, dict):
                continue
            sid = s.get("id")
            try:
                sid_int = int(sid)
            except Exception:
                continue
            account = _esc(s.get("account") or "")
            stitle = _esc(s.get("title") or "")
            url = _esc(s.get("url") or "")
            anchor = f'src-{sid_int}'
            label = f'{account}｜{stitle}' if account else stitle
            if url:
                html.append(
                    f'<div id="{anchor}" style="margin:8px 0;">'
                    f'<span style="display:inline-block;width:22px;color:#6b7280;">{sid_int}.</span>'
                    f'<a href="{url}" style="color:#2563eb;text-decoration:none;">{label}</a>'
                    f"</div>"
                )
            else:
                html.append(
                    f'<div id="{anchor}" style="margin:8px 0;">'
                    f'<span style="display:inline-block;width:22px;color:#6b7280;">{sid_int}.</span>'
                    f'{label}'
                    f"</div>"
                )
        html.append("</div>")

    html.append("</div>")
    return "".join(html)


def render_daily_report_text(report_json: Dict[str, Any]) -> str:
    """
    Render a compact, high-signal plain text for subscribers.
    Requirement:
    - 今日焦点：标题+正文+前5条来源（格式：公众号名 · 文章标题，不显示URL）
    - 近日热点：只显示 coverage_accounts >= 3 的热点，每个热点最多3条来源（格式：公众号名 · 文章标题，不显示URL）
    - 今日彩蛋：最多5条来源（格式：公众号名 · 文章标题，不显示URL）
    """
    import re
    
    header = report_json.get("header") or {}
    title = str(header.get("title") or "财政晨报").strip()
    date = str(header.get("date") or "").strip()
    sources = report_json.get("sources") or []
    id2src: Dict[int, Dict[str, Any]] = {}
    for s in sources:
        if not isinstance(s, dict):
            continue
        try:
            sid = int(s.get("id"))
        except Exception:
            continue
        if sid > 0:
            id2src[sid] = s

    # Helper function to strip markers
    def strip_markers(t: str) -> str:
        return re.sub(r'【\s*(为何重要|为什么重要|大局)\s*】', '', t).replace('为何重要:', '').replace('为什么重要:', '').replace('大局:', '').strip()

    lines: List[str] = []
    if title:
        lines.append(title)
    if date:
        lines.append(date)
    lines.append("")

    # Schema check
    schema = report_json.get("schema") if isinstance(report_json, dict) else None
    if schema == "smart_brevity_v1":
        lede = str(header.get("lede") or "").strip()
        why = str(report_json.get("why_it_matters") or "").strip()
        big = str(report_json.get("big_picture") or "").strip()
        
        # 今日焦点 Section
        if title or lede or why or big:
            lines.append("【今日焦点】")
            if title:
                lines.append(title)
            # Merge lede + why + big
            focus_parts = []
            if lede:
                focus_parts.append(strip_markers(lede))
            if why:
                focus_parts.append(strip_markers(why))
            if big:
                focus_parts.append(strip_markers(big))
            focus_text = " ".join([p for p in focus_parts if p])
            if focus_text:
                lines.append(focus_text)
            
            # 前5条参考来源
            focus_citations = list(set((header.get("lede_citations") or []) + (report_json.get("why_citations") or []) + (report_json.get("big_picture_citations") or [])))
            if focus_citations:
                lines.append("")
                for cid in focus_citations[:5]:  # Max 5 sources
                    try:
                        sid = int(cid)
                        src = id2src.get(sid)
                        if src:
                            account = str(src.get("account") or "").strip()
                            stitle = str(src.get("title") or "").strip()
                            display_text = f"{account} · {stitle}" if account else stitle
                            if display_text:
                                lines.append(f"  - {display_text}")
                    except Exception:
                        continue
            lines.append("")

    hotspots = report_json.get("recent_hotspots") or []
    meta = report_json.get("recent_hotspots_meta") or {}
    try:
        wd = int(meta.get("window_days") or 0)
    except Exception:
        wd = 0

    # 近日热点 Section - 只显示 coverage_accounts >= 3 的热点
    if isinstance(hotspots, list) and hotspots:
        # Filter: only coverage_accounts >= 3
        filtered_hotspots = []
        for h in hotspots:
            if not isinstance(h, dict):
                continue
            event = str(h.get("event") or "").strip()
            if not event:
                continue
            coverage_accounts = int(h.get("coverage_accounts") or 0)
            if coverage_accounts >= 3:
                # Calculate hotness if not present
                if "hotness" not in h or not h.get("hotness"):
                    coverage_docs = int(h.get("coverage_docs") or 0)
                    calculated_hotness = min(100, 20 + coverage_docs * 18 + coverage_accounts * 10)
                    h["hotness"] = calculated_hotness
                filtered_hotspots.append(h)
        
        # Sort by hotness and take top 5
        def get_hotness(h: Dict[str, Any]) -> int:
            try:
                return int(h.get("hotness") or 0)
            except Exception:
                return 0
        filtered_hotspots.sort(key=get_hotness, reverse=True)
        display_hotspots = filtered_hotspots[:5]
        
        if display_hotspots:
            lines.append("【近日热点】")
            for i, it in enumerate(display_hotspots, start=1):
                ev = str(it.get("event") or "").strip()
                if not ev:
                    continue
                lines.append(f"{i}) {ev}")
                
                # 每个热点最多3条来源（格式：公众号名 · 文章标题，不显示URL）
                sids = it.get("source_ids")
                if isinstance(sids, list) and sids:
                    shown_sources = 0
                    for x in sids[:3]:  # Max 3 sources per hotspot
                        try:
                            sid = int(x)
                            if sid > 0:
                                src = id2src.get(sid)
                                if src:
                                    account = str(src.get("account") or "").strip()
                                    stitle = str(src.get("title") or "").strip()
                                    display_text = f"{account} · {stitle}" if account else stitle
                                    if display_text:
                                        lines.append(f"  - {display_text}")
                                        shown_sources += 1
                                        if shown_sources >= 3:
                                            break
                        except Exception:
                            continue
                lines.append("")
        else:
            lines.append("【近日热点】（暂无）")
            lines.append("")
    else:
        # legacy fallback
        hotwords = report_json.get("recent_hotwords") or report_json.get("keywords") or []
        meta2 = report_json.get("recent_hotwords_meta") or {}
        try:
            wd2 = int(meta2.get("window_days") or 0)
        except Exception:
            wd2 = 0
        if isinstance(hotwords, list) and hotwords:
            hdr = f"【近日热词】（近{wd2}天）" if wd2 > 0 else "【近日热词】"
            lines.append(hdr)
            for i, it in enumerate(hotwords[:10], start=1):
                if not isinstance(it, dict):
                    continue
                w = str(it.get("word") or "").strip()
                if w:
                    lines.append(f"{i}) {w}")
            lines.append("")
        else:
            lines.append("【近日热点】（暂无）")
        lines.append("")

    # 今日彩蛋 Section
    if schema == "smart_brevity_v1":
        easter_egg = report_json.get("easter_egg") or {}
        if easter_egg and isinstance(easter_egg, dict) and (easter_egg.get("url") or easter_egg.get("title") or easter_egg.get("teaser")):
            egg_title = str(easter_egg.get("title") or "").strip()
            egg_teaser = str(easter_egg.get("teaser") or "").strip()
            egg_account = str(easter_egg.get("account") or "").strip()
            egg_source_ids = easter_egg.get("source_ids") or []
            
            lines.append("【今日彩蛋】")
            if egg_title:
                lines.append(egg_title)
            if egg_teaser:
                lines.append(egg_teaser)
            
            # 最多5条来源（格式：公众号名 · 文章标题，不显示URL）
            if isinstance(egg_source_ids, list) and egg_source_ids:
                shown_sources = 0
                for sid in egg_source_ids[:5]:  # Max 5 sources
                    try:
                        sid_int = int(sid)
                        if sid_int > 0:
                            src = id2src.get(sid_int)
                            if src:
                                account = str(src.get("account") or "").strip()
                                stitle = str(src.get("title") or "").strip()
                                display_text = f"{account} · {stitle}" if account else stitle
                                if display_text:
                                    lines.append(f"  - {display_text}")
                                    shown_sources += 1
                                    if shown_sources >= 5:
                                        break
                    except Exception:
                        continue
            lines.append("")

    # Add web link at the end
    from shared.config.settings import settings
    web_url = settings.WEB_URL
    lines.append("")
    lines.append(f"查看网页版: {web_url}/reports/daily")
    lines.append("")
    
    # Keep tail short: sources are already embedded above per word.
    return "\n".join(lines).strip() + "\n"


def render_markdown_to_html(markdown_text: str) -> str:
    """
    Convert Markdown text to safe HTML for weekly reports.

    Args:
        markdown_text: Raw Markdown string

    Returns:
        Safe HTML string with inline styles
    """
    if not markdown_text:
        return ""

    import markdown

    # Configure markdown with safe extensions only
    md = markdown.Markdown(
        extensions=[
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists',
        ],
        strip=True  # Strip HTML tags for security
    )

    # Convert to HTML
    html = md.convert(markdown_text)

    # Add inline styles for better display
    styled_html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;color:#111827;line-height:1.65;">
{html}
</div>"""

    return styled_html


def render_weekly_report_text(summary_markdown: str, report_date: str, date_range_str: Optional[str] = None) -> str:
    """
    Render weekly report Markdown to plain text for email body.
    
    Args:
        summary_markdown: Markdown content of the weekly report
        report_date: Report date string (e.g., "2025-12-22")
        date_range_str: Optional date range string for display (e.g., "12月16日-12月22日")
    
    Returns:
        Plain text string with web link at the end
    """
    if not summary_markdown:
        return ""
    
    import re
    from datetime import datetime
    
    # Format date for header
    header_date = date_range_str or report_date
    if not date_range_str:
        try:
            d = datetime.strptime(report_date, "%Y-%m-%d")
            from datetime import timedelta
            start_date = d - timedelta(days=6)
            header_date = f"{start_date.strftime('%Y年%m月%d日')} 至 {d.strftime('%m月%d日')}"
        except Exception:
            pass
    
    lines: List[str] = []
    lines.append("浙财脉动周报")
    lines.append(header_date)
    lines.append("")
    
    # Convert Markdown to plain text
    text = summary_markdown
    
    # Remove Markdown formatting
    # Remove headers (keep the text)
    text = re.sub(r'^#+\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    lines.append(text)
    lines.append("")
    
    # Add web link at the end
    from shared.config.settings import settings
    web_url = settings.WEB_URL
    lines.append(f"查看网页版: {web_url}/reports/weekly")
    
    return "\n".join(lines)


def render_weekly_report_html(summary_markdown: str, report_date: str, date_range_str: Optional[str] = None, for_email: bool = False) -> str:
    """
    Render weekly report Markdown to HTML with card-based UI matching frontend WeeklyReview component.
    Uses low-saturation amber color scheme (Scheme 2).

    Args:
        summary_markdown: Markdown content of the weekly report
        report_date: Report date string (e.g., "2025-12-22")
        date_range_str: Optional date range string for display (e.g., "12月16日-12月22日")
        for_email: If True, returns content-only HTML (no <html>/<body> tags) for email template embedding

    Returns:
        HTML string with card-based UI and inline styles
    """
    if not summary_markdown:
        return ""

    import markdown
    from datetime import datetime

    # Format date for Hero: calculate range or use provided
    hero_date = date_range_str or report_date
    if not date_range_str:
        try:
            d = datetime.strptime(report_date, "%Y-%m-%d")
            # Calculate 7 days before
            from datetime import timedelta
            start_date = d - timedelta(days=6)
            hero_date = f"{start_date.month}月{start_date.day}日-{d.month}月{d.day}日"
        except Exception:
            pass

    # Convert Markdown to HTML
    md = markdown.Markdown(
        extensions=[
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists',
        ],
        strip=True
    )
    content_html = md.convert(summary_markdown)

    html: List[str] = []
    
    # For email, don't include <html>/<body> tags (will be embedded in email template)
    if not for_email:
        html.append('<!DOCTYPE html>')
        html.append('<html>')
        html.append('<head>')
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html.append('</head>')
        html.append('<body style="margin:0;padding:0;background-color:#f9fafb;">')
    
    html.append('<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;color:#111827;line-height:1.65;width:100%;max-width:100%;margin:0 auto;padding:0;">')
    
    # Hero Section - use left-right layout for PDF (for_email=False), vertical stack for web/email
    if for_email:
        # For email: vertical stack (mobile-friendly)
        html.append('<div style="position:relative;overflow:hidden;border-radius:16px;background:linear-gradient(135deg, #0f172a 0%, #0f172a 100%);color:#ffffff;box-shadow:0 10px 25px -5px rgba(0,0,0,0.2);margin-bottom:16px;">')
        html.append('<div style="position:relative;padding:20px 16px;">')
        html.append('<div style="display:flex;flex-direction:column;align-items:flex-start;gap:12px;">')
        html.append('<div style="width:100%;">')
        html.append('<h1 style="font-size:36px;font-weight:700;letter-spacing:-0.025em;color:#ffffff;margin:0 0 8px 0;line-height:1.05;">浙财脉动</h1>')
        html.append('<p style="font-size:14px;color:rgba(255,255,255,0.8);margin:0;line-height:1.5;">大模型聚合的财政情报 · 每周一11点更新</p>')
        html.append("</div>")
        html.append('<div style="text-align:left;width:100%;">')
        html.append(f'<div style="font-size:12px;font-weight:700;color:#ffffff;margin-bottom:4px;">{_esc(hero_date)}</div>')
        html.append('<div style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.9);">周报</div>')
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")
    else:
        # For PDF: left-right layout (left: title+subtitle, right: date+type)
        html.append('<div style="position:relative;overflow:hidden;border-radius:16px;background:linear-gradient(135deg, #0f172a 0%, #0f172a 100%);color:#ffffff;box-shadow:0 10px 25px -5px rgba(0,0,0,0.2);margin-bottom:16px;">')
        html.append('<div style="position:relative;padding:20px 24px;">')
        html.append('<div style="display:flex;align-items:center;justify-content:space-between;gap:20px;">')
        html.append('<div style="flex:1;">')
        html.append('<h1 style="font-size:36px;font-weight:700;letter-spacing:-0.025em;color:#ffffff;margin:0 0 8px 0;line-height:1.05;">浙财脉动</h1>')
        html.append('<p style="font-size:14px;color:rgba(255,255,255,0.8);margin:0;line-height:1.5;">大模型聚合的财政情报 · 每周一11点更新</p>')
        html.append("</div>")
        html.append('<div style="text-align:right;flex-shrink:0;">')
        html.append(f'<div style="font-size:14px;font-weight:700;color:#ffffff;margin-bottom:6px;">{_esc(hero_date)}</div>')
        html.append('<div style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.9);">周报</div>')
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")

    # 一周述评 Section - same style as 今日焦点 (low saturation amber)
    html.append('<div style="background-color:#ffffff;border-radius:16px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -2px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;border-left:4px solid #d97706;">')
    
    # Title bar
    html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(254, 243, 199, 0.3) 100%);padding:16px 16px 12px 16px;">')
    html.append('<div style="display:flex;align-items:center;gap:10px;">')
    html.append('<div style="width:32px;height:32px;border-radius:50%;background-color:#d97706;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 4px rgba(0,0,0,0.1);flex-shrink:0;">')
    html.append('<svg style="width:16px;height:16px;color:#ffffff;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>')
    html.append("</div>")
    html.append('<div>')
    html.append('<div style="font-size:18px;font-weight:700;color:#111827;">一周述评</div>')
    html.append('<div style="font-size:12px;color:#6b7280;margin-top:2px;">全面梳理本周财政动态的整体脉络</div>')
    html.append("</div>")
    html.append("</div>")
    html.append("</div>")
    
    # Content area
    html.append('<div style="padding:32px 40px 32px 40px;background-color:rgba(248, 250, 252, 0.2);">')
    
    # Markdown content with styled headings and paragraphs
    # Wrap content in a div with prose-like styles
    styled_content = f"""<div style="color:#1e293b;line-height:1.75;">
{content_html}
</div>"""
    
    # Add custom styles for markdown elements
    styled_content = styled_content.replace(
        '<h1>',
        '<h1 style="font-size:28px;font-weight:700;color:#0f172a;margin-bottom:16px;margin-top:0;line-height:1.2;">'
    )
    styled_content = styled_content.replace(
        '<h2>',
        '<h2 style="font-size:22px;font-weight:600;color:#1e293b;margin-bottom:12px;margin-top:24px;line-height:1.3;">'
    )
    styled_content = styled_content.replace(
        '<h3>',
        '<h3 style="font-size:18px;font-weight:600;color:#334155;margin-bottom:8px;margin-top:16px;line-height:1.4;">'
    )
    styled_content = styled_content.replace(
        '<p>',
        '<p style="font-size:15px;line-height:1.75;color:#475569;margin-bottom:16px;margin-top:0;text-indent:2em;">'
    )
    styled_content = styled_content.replace(
        '<ul>',
        '<ul style="list-style-type:disc;padding-left:24px;margin-bottom:16px;margin-top:0;color:#475569;">'
    )
    styled_content = styled_content.replace(
        '<ol>',
        '<ol style="list-style-type:decimal;padding-left:24px;margin-bottom:16px;margin-top:0;color:#475569;">'
    )
    styled_content = styled_content.replace(
        '<li>',
        '<li style="font-size:15px;line-height:1.75;margin-bottom:8px;">'
    )
    styled_content = styled_content.replace(
        '<strong>',
        '<strong style="font-weight:600;color:#0f172a;">'
    )
    styled_content = styled_content.replace(
        '<code>',
        '<code style="background-color:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:14px;font-family:monospace;color:#1e293b;">'
    )
    
    html.append(styled_content)
    html.append("</div>")
    html.append("</div>")

    html.append("</div>")
    
    # For email, don't include closing tags
    if not for_email:
        html.append("</body>")
        html.append("</html>")
    
    return "".join(html)


def render_daily_report_html_for_pdf(report_json: Dict[str, Any]) -> str:
    """
    Render report JSON to compact HTML optimized for PDF (single A4 page).
    - Removes badge styles, uses simple text lists
    - Compresses spacing
    - Filters hotspots: only coverage_accounts >= 3, max 3 items
    """
    header = report_json.get("header") or {}
    title = _esc(header.get("title") or "财政日报")
    date = _esc(header.get("date") or "")

    schema = report_json.get("schema") if isinstance(report_json, dict) else None
    if schema == "smart_brevity_v1":
        lede = str(header.get("lede") or "").strip()
        why = str(report_json.get("why_it_matters") or "").strip()
        big = str(report_json.get("big_picture") or "").strip()
        hotspots = report_json.get("recent_hotspots") or []
        keywords = report_json.get("recent_hotwords") or report_json.get("keywords") or []
        sources = report_json.get("sources") or []
        easter_egg = report_json.get("easter_egg") or {}

        # Build sources lookup
        sources_by_id: Dict[int, Dict[str, Any]] = {}
        for s in sources:
            if not isinstance(s, dict):
                continue
            try:
                sid = int(s.get("id", 0))
                if sid > 0:
                    sources_by_id[sid] = s
            except Exception:
                continue

        # Format date for Hero: "12月25日"
        hero_date = date
        try:
            from datetime import datetime
            if date:
                d = datetime.strptime(date, "%Y-%m-%d")
                hero_date = f"{d.month}月{d.day}日"
        except Exception:
            pass

        html: List[str] = []
        html.append('<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;color:#111827;line-height:1.4;">')
        
        # Hero Section - Compact for PDF
        html.append('<div style="background:linear-gradient(135deg, #0f172a 0%, #0f172a 100%);color:#ffffff;border-radius:12px;padding:16px 20px;margin-bottom:12px;">')
        html.append('<div style="display:flex;align-items:center;justify-content:space-between;">')
        html.append('<div>')
        html.append('<h1 style="font-size:32px;font-weight:700;color:#ffffff;margin:0 0 6px 0;line-height:1.1;">浙财脉动</h1>')
        html.append('<p style="font-size:13px;color:rgba(255,255,255,0.8);margin:0;line-height:1.3;">大模型聚合的财政情报 · 每日10点更新</p>')
        html.append("</div>")
        html.append('<div style="text-align:right;">')
        html.append(f'<div style="font-size:12px;font-weight:700;color:#ffffff;margin-bottom:4px;">{_esc(hero_date)}</div>')
        html.append('<div style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.9);">晨报</div>')
        html.append("</div>")
        html.append("</div>")
        html.append("</div>")

        # 今日焦点 Section - Compact
        if lede or why or big:
            def strip_markers(t: str) -> str:
                return re.sub(r'【\s*(为何重要|为什么重要|大局)\s*】', '', t).replace('为何重要:', '').replace('为什么重要:', '').replace('大局:', '').strip()
            
            focus_parts = []
            if lede:
                focus_parts.append(strip_markers(lede))
            if why:
                focus_parts.append(strip_markers(why))
            if big:
                focus_parts.append(strip_markers(big))
            focus_text = " ".join([p for p in focus_parts if p])
            
            # Extract first sentence for highlighting
            first_sentence = ""
            rest_text = focus_text
            if focus_text:
                first_match = re.match(r'^[^。！？]+[。！？]', focus_text)
                if first_match:
                    first_sentence = first_match.group(0)
                    rest_text = focus_text[len(first_sentence):].strip()
            
            focus_citations = list(set((header.get("lede_citations") or []) + (report_json.get("why_citations") or []) + (report_json.get("big_picture_citations") or [])))
            
            html.append('<div style="background-color:#ffffff;border-radius:12px;border-left:3px solid #d97706;padding:12px 16px;margin-bottom:12px;">')
            
            # Title bar - Compact with gradient background (matching frontend - low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(254, 243, 199, 0.3) 100%);padding:8px 12px;margin:-12px -16px 8px -16px;border-radius:12px 12px 0 0;">')
            html.append('<div style="display:flex;align-items:center;gap:8px;">')
            html.append('<div style="width:28px;height:28px;border-radius:50%;background-color:#d97706;display:flex;align-items:center;justify-content:center;color:#ffffff;font-weight:700;font-size:14px;">i</div>')
            html.append('<div>')
            html.append('<div style="font-size:16px;font-weight:700;color:#111827;">今日焦点</div>')
            html.append('<div style="font-size:11px;color:#6b7280;margin-top:1px;">近24小时最值得关注的财政动态</div>')
            html.append('</div>')
            html.append('</div>')
            html.append('</div>')
            
            # Content area - Compact
            html.append('<div style="padding-left:8px;">')
            if title:
                html.append(f'<h2 style="font-size:20px;font-weight:500;color:#111827;margin:0 0 8px 0;line-height:1.2;">{_esc(title)}</h2>')
            
            # Main body text - Compact
            if focus_text:
                html.append('<div style="font-size:13px;line-height:1.5;color:#111827;margin-bottom:10px;font-weight:300;">')
                if first_sentence:
                    html.append(f'<span style="background-color:rgba(254, 243, 199, 0.5);padding:2px 4px;border-radius:3px;">{_esc(first_sentence)}</span>')
                if rest_text:
                    html.append(f'<span style="margin-left:3px;">{_esc(rest_text)}</span>')
                html.append("</div>")
            
            # Citation sources - Badge style (matching frontend) - Max 5 sources, clickable but no URL text
            if focus_citations:
                html.append('<div style="margin-top:8px;">')
                html.append('<div style="display:flex;flex-wrap:wrap;gap:6px;">')
                for cid in focus_citations[:5]:  # Max 5 sources
                    try:
                        sid = int(cid)
                        src = sources_by_id.get(sid)
                        if src:
                            account = _esc(str(src.get("account") or ""))
                            stitle = _esc(str(src.get("title") or ""))
                            url = str(src.get("url") or "")
                            display_text = f"{account} · {stitle}" if account else stitle
                            if url and url.startswith(("http://", "https://")):
                                # Clickable link but no URL text displayed
                                html.append(f'<a href="{_esc(url)}" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</a>')
                            else:
                                html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</span>')
                    except Exception:
                        continue
                html.append("</div>")
                html.append("</div>")
            html.append("</div>")
            html.append("</div>")

        # 近日热点 Section - Compact, only coverage_accounts >= 3, max 3
        hotspots_list = hotspots if isinstance(hotspots, list) else []
        if not hotspots_list and isinstance(keywords, list):
            hotspots_list = [{"event": str(k.get("word") or ""), "source_ids": k.get("source_ids") or [], "coverage_accounts": int(k.get("coverage_accounts") or 0)} for k in keywords if isinstance(k, dict) and k.get("word")]
        
        # Filter: only coverage_accounts >= 3
        filtered_hotspots = []
        for h in hotspots_list:
            if not isinstance(h, dict):
                continue
            event = str(h.get("event") or "").strip()
            if not event:
                continue
            coverage_accounts = int(h.get("coverage_accounts") or 0)
            if coverage_accounts >= 3:
                # Calculate hotness if not present: 20 + 文档数 × 18 + 账号数 × 10, max 100
                if "hotness" not in h or not h.get("hotness"):
                    coverage_docs = int(h.get("coverage_docs") or 0)
                    calculated_hotness = min(100, 20 + coverage_docs * 18 + coverage_accounts * 10)
                    h["hotness"] = calculated_hotness
                filtered_hotspots.append(h)
        
        # Sort by hotness and take top 3
        def get_hotness(h: Dict[str, Any]) -> int:
            try:
                return int(h.get("hotness") or 0)
            except Exception:
                return 0
        filtered_hotspots.sort(key=get_hotness, reverse=True)
        display_hotspots = filtered_hotspots[:3]
        
        if display_hotspots:
            html.append('<div style="background-color:#ffffff;border-radius:12px;padding:12px 16px;margin-bottom:12px;">')
            
            # Title bar - Compact with gradient background (matching frontend - low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(209, 250, 229, 0.3) 100%);padding:8px 12px;margin:-12px -16px 8px -16px;border-radius:12px 12px 0 0;">')
            html.append('<div style="display:flex;align-items:center;gap:8px;">')
            html.append('<div style="width:28px;height:28px;border-radius:50%;background-color:#059669;display:flex;align-items:center;justify-content:center;color:#ffffff;font-weight:700;font-size:12px;">热</div>')
            html.append('<div>')
            html.append('<div style="font-size:16px;font-weight:700;color:#111827;">近日热点</div>')
            html.append('<div style="font-size:11px;color:#6b7280;margin-top:1px;">近3天覆盖3个不同公众号的话题</div>')
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")
            
            # Content area - Compact single column
            html.append('<div style="display:flex;flex-direction:column;gap:8px;">')
            
            for hotspot in display_hotspots:
                event = str(hotspot.get("event") or "").strip()
                why_hot = str(hotspot.get("why_hot") or "").strip()
                source_ids = hotspot.get("source_ids") or []
                if not isinstance(source_ids, list):
                    source_ids = []
                
                # Sort sources: prioritize different accounts, then by date descending
                sorted_source_ids = sorted(source_ids, key=lambda sid: (
                    sources_by_id.get(int(sid), {}).get("account", ""),
                    -int(sources_by_id.get(int(sid), {}).get("date", "0").replace("-", "").replace(":", "").replace(" ", "")) if sources_by_id.get(int(sid), {}).get("date") else 0
                ))
                
                # Get one latest source per account
                account_map: Dict[str, int] = {}
                prioritized_sources = []
                for sid in sorted_source_ids:
                    try:
                        sid_int = int(sid)
                        src = sources_by_id.get(sid_int)
                        if src:
                            account = str(src.get("account") or "")
                            if account and account not in account_map:
                                account_map[account] = sid_int
                                prioritized_sources.append(sid_int)
                    except Exception:
                        continue
                
                # Add remaining sources
                for sid in sorted_source_ids:
                    try:
                        sid_int = int(sid)
                        if sid_int not in prioritized_sources:
                            prioritized_sources.append(sid_int)
                    except Exception:
                        continue
                
                # Show first 3 sources (max 3 per hotspot)
                default_sources = prioritized_sources[:3]
                
                html.append('<div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:#f9fafb;">')
                
                # Event name - Compact
                if event:
                    html.append(f'<div style="font-size:14px;font-weight:500;color:#111827;margin-bottom:4px;">{_esc(event)}</div>')
                
                # Why hot explanation - Compact
                if why_hot:
                    html.append(f'<div style="font-size:11px;color:#475569;line-height:1.4;margin-bottom:6px;font-weight:300;">{_esc(why_hot)}</div>')
                
                # Sources - Badge style (matching frontend) - Max 3 sources per hotspot, clickable but no URL text
                if default_sources:
                    html.append('<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;">')
                    for sid in default_sources:
                        src = sources_by_id.get(int(sid))
                        if not src:
                            continue
                        account = _esc(str(src.get("account") or ""))
                        stitle = _esc(str(src.get("title") or ""))
                        url = str(src.get("url") or "")
                        display_text = f"{account} · {stitle}" if account else stitle
                        if url and url.startswith(("http://", "https://")):
                            # Clickable link but no URL text displayed
                            html.append(f'<a href="{_esc(url)}" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</a>')
                        else:
                            html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(display_text)}</span>')
                    html.append("</div>")
                
                html.append("</div>")
            
            html.append("</div>")
            html.append("</div>")

        # 今日彩蛋 Section - Compact
        if easter_egg and isinstance(easter_egg, dict) and (easter_egg.get("url") or easter_egg.get("title") or easter_egg.get("teaser")):
            egg_title = str(easter_egg.get("title") or "").strip()
            egg_teaser = str(easter_egg.get("teaser") or "").strip()
            egg_url = str(easter_egg.get("url") or "")
            egg_account = str(easter_egg.get("account") or "").strip()
            
            html.append('<div style="background-color:#ffffff;border-radius:12px;padding:12px 16px;margin-bottom:12px;">')
            
            # Title bar - Compact with gradient background (matching frontend - low saturation)
            html.append('<div style="background:linear-gradient(to right, #f8fafc 0%, rgba(252, 231, 243, 0.3) 100%);padding:8px 12px;margin:-12px -16px 8px -16px;border-radius:12px 12px 0 0;">')
            html.append('<div style="display:flex;align-items:center;gap:8px;">')
            html.append('<div style="width:28px;height:28px;border-radius:50%;background-color:#be185d;display:flex;align-items:center;justify-content:center;color:#ffffff;font-weight:700;font-size:12px;">蛋</div>')
            html.append('<div>')
            html.append('<div style="font-size:16px;font-weight:700;color:#111827;">今日彩蛋</div>')
            if egg_account:
                html.append(f'<div style="font-size:11px;color:#6b7280;margin-top:1px;">来自: {_esc(egg_account)}</div>')
            html.append("</div>")
            html.append("</div>")
            html.append("</div>")
            
            # Content area - Compact, use badge format for teaser (only teaser is clickable)
            html.append('<div style="padding-left:8px;">')
            if egg_title:
                html.append(f'<div style="font-size:14px;font-weight:500;color:#111827;margin-bottom:6px;">{_esc(egg_title)}</div>')
            if egg_teaser:
                if egg_url and egg_url.startswith(("http://", "https://")):
                    # Use badge format for teaser (only teaser is clickable, matching frontend)
                    html.append(f'<a href="{_esc(egg_url)}" target="_blank" rel="noreferrer" style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;text-decoration:none;transition:background-color 0.2s;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(egg_teaser)}</a>')
                else:
                    html.append(f'<span style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;font-size:10px;background-color:#f1f5f9;color:#374151;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">{_esc(egg_teaser)}</span>')
            html.append("</div>")
            html.append("</div>")

        html.append("</div>")
        return "".join(html)

    # Fallback to regular render for non-smart-brevity format
    return render_daily_report_html(report_json)


def render_daily_report_pdf(report_json: Dict[str, Any], report_date: str) -> bytes:
    """
    Render daily report to PDF using WeasyPrint.

    Args:
        report_json: Structured report data (same as render_daily_report_html)
        report_date: Report date string for title

    Returns:
        PDF file as bytes
    """
    import weasyprint
    from datetime import datetime

    # Get HTML content optimized for PDF
    html_content = render_daily_report_html_for_pdf(report_json)

    # Enhanced CSS for PDF (A4 size, single page, compact)
    pdf_css = weasyprint.CSS(string="""
    @page {
        size: A4;
        margin: 0.8cm;
        @bottom-center {
            content: "浙财脉动 - 第 " counter(page) " 页";
            font-size: 8pt;
            color: #6b7280;
        }
    }

    body {
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'Microsoft YaHei', 'SimSun', sans-serif;
        font-size: 9pt;
        line-height: 1.4;
        color: #111827;
        margin: 0;
        padding: 0;
    }

    h1, h2, h3 {
        color: #1f2937;
        margin-top: 0.3em;
        margin-bottom: 0.2em;
    }

    a {
        color: #2563eb;
        text-decoration: underline;
    }
    
    a:link {
        color: #2563eb;
    }
    
    a:visited {
        color: #7c3aed;
    }

    /* Support for rounded corners in PDF */
    div[style*="border-radius"] {
        border-radius: 12px;
    }

    /* Ensure gradients display properly (fallback to solid colors in PDF) */
    div[style*="linear-gradient"] {
        background-color: #f8fafc;
    }

    @media print {
        .no-print {
            display: none;
        }
    }
    """)

    # Create complete HTML document (no extra header, content already includes hero)
    complete_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>浙财脉动晨报</title>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Generate PDF (WeasyPrint 60+ API)
    pdf_bytes = weasyprint.HTML(
        string=complete_html,
        base_url='file://'
    ).write_pdf(
        stylesheets=[pdf_css],
        presentational_hints=True
    )

    return pdf_bytes


def render_weekly_report_pdf(summary_markdown: str, report_date: str, date_range_str: Optional[str] = None) -> bytes:
    """
    Render weekly report (Markdown) to PDF using WeasyPrint.
    Uses the same card-based UI as HTML rendering for consistency.

    Args:
        summary_markdown: Markdown content of the weekly report
        report_date: Report date string (e.g., "2025-12-22")
        date_range_str: Optional date range string for title (e.g., "12月16日-12月22日")

    Returns:
        PDF file as bytes
    """
    import weasyprint
    from datetime import datetime

    # Use the same HTML rendering function as web/email for consistency
    # Set for_email=False to get full HTML document
    html_content = render_weekly_report_html(summary_markdown, report_date, date_range_str, for_email=False)

    # Enhanced CSS for PDF (A4 size, optimized for card-based UI)
    pdf_css = weasyprint.CSS(string="""
    @page {
        size: A4;
        margin: 0.8cm;
        @bottom-center {
            content: "浙财脉动周报 - 第 " counter(page) " 页";
            font-size: 8pt;
            color: #6b7280;
        }
    }

    body {
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'Microsoft YaHei', 'SimSun', sans-serif;
        font-size: 9pt;
        line-height: 1.5;
        color: #111827;
        margin: 0;
        padding: 0;
        background-color: #f9fafb;
    }

    /* Hero Section styles for PDF - ensure left-right layout */
    div[style*="background:linear-gradient(135deg, #0f172a"] {
        background: #0f172a !important;
        border-radius: 12px;
        padding: 16px 20px !important;
        margin-bottom: 12px;
    }
    
    /* Ensure hero content uses flex layout for left-right alignment */
    div[style*="display:flex"][style*="align-items:center"][style*="justify-content:space-between"] {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-direction: row !important;
    }

    /* Card Section styles for PDF */
    div[style*="background-color:#ffffff"][style*="border-radius:16px"] {
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        border-left: 4px solid #d97706;
    }

    /* Title bar gradient fallback for PDF */
    div[style*="background:linear-gradient(to right, #f8fafc"] {
        background: #f8fafc !important;
        padding: 12px 16px !important;
    }

    /* Content area */
    div[style*="padding:32px 40px"] {
        padding: 16px 20px !important;
        background-color: rgba(248, 250, 252, 0.2) !important;
    }

    h1 {
        color: #0f172a;
        font-size: 18pt;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 0.5em;
        line-height: 1.2;
    }

    h2 {
        color: #1e293b;
        font-size: 14pt;
        font-weight: 600;
        margin-top: 1em;
        margin-bottom: 0.5em;
        line-height: 1.3;
    }

    h3 {
        color: #334155;
        font-size: 12pt;
        font-weight: 600;
        margin-top: 0.8em;
        margin-bottom: 0.3em;
        line-height: 1.4;
    }

    p {
        margin-top: 0.5em;
        margin-bottom: 0.5em;
        text-align: justify;
        font-size: 9pt;
        line-height: 1.6;
        color: #475569;
        text-indent: 2em;
    }

    ul, ol {
        margin-top: 0.5em;
        margin-bottom: 0.5em;
        padding-left: 1.5em;
        color: #475569;
    }

    li {
        margin-top: 0.3em;
        margin-bottom: 0.3em;
        font-size: 9pt;
        line-height: 1.6;
    }

    a {
        color: #2563eb;
        text-decoration: underline;
    }

    code {
        background: #f1f5f9;
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        color: #1e293b;
    }

    strong {
        font-weight: 600;
        color: #0f172a;
    }

    /* Ensure SVG icons don't break layout in PDF */
    svg {
        display: inline-block;
        vertical-align: middle;
    }

    @media print {
        .no-print {
            display: none;
        }
    }
    """)

    # Generate PDF (WeasyPrint 60+ API)
    # html_content already includes full HTML document structure
    pdf_bytes = weasyprint.HTML(
        string=html_content,
        base_url='file://'
    ).write_pdf(
        stylesheets=[pdf_css],
        presentational_hints=True
    )

    return pdf_bytes


