from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from shared.utils import get_logger

logger = get_logger("daily-briefing-nlp")


# WeChat / gov-media boilerplate cleanup patterns (line or short phrase level).
# Keep this list conservative: remove obvious CTA/metadata lines without harming正文.
DEFAULT_WECHAT_KILL_PATTERNS: Tuple[str, ...] = (
    r"^\s*阅读原文.*?$",
    r"^\s*点击.*?阅读原文.*?$",
    r"^\s*长按.*?识别.*?二维码.*?$",
    r"^\s*(?:扫码|扫描).{0,6}二维码.*?$",
    r"^\s*(?:关注|关注我们|点亮|在看|点赞|分享|转发).{0,30}$",
    r"^\s*(?:来源|编辑|责任编辑|审核|校对|监制|通讯员|记者|摄影|供图)\s*[:：].*?$",
    r"^\s*本文.*?转载.*?$",
    r"^\s*版权.*?$",
)

# 财政领域关键词（用于"至少2个词进入后续流程"的初筛；保守配置）
DEFAULT_FINANCE_KEYWORDS = [
    "财政",
    "预算",
    "决算",
    "预算执行",
    "转移支付",
    "专项债",
    "国债",
    "债券",
    "税收",
    "税务",
    "减税",
    "降费",
    "收费",
    "补贴",
    "补助",
    "津贴",
    "救助",
    "低保",
    "医保",
    "社保",
    "公积金",
    "政府采购",
    "招标",
    "投标",
    "中标",
    "审计",
    "国资",
    "国企",
    "财政资金",
    "专项资金",
    "经费",
    "拨款",
    "绩效",
]

# 扩展关键词：财政 + 民生 + 科技（用于关键词提取的第一步过滤）
EXTENDED_KEYWORDS = [
    # 财政相关
    "财政", "预算", "决算", "专项债", "国债", "税收", "税务", "减税", "降费",
    "政府采购", "招标", "绩效", "转移支付", "拨款", "专项资金", "财政资金",
    
    # 民生相关
    "医保", "社保", "养老", "就业", "住房", "教育", "救助", "低保", "补贴", "补助",
    "津贴", "公积金", "消费券", "育儿", "托育", "养老服务", "公共服务",
    "应急救灾", "保障房", "安置房", "交通补贴", "残疾人", "困难群众",
    "医疗保障", "社会保障", "民生实事", "惠民", "便民", "利民",
    
    # 科技创新相关
    "研发", "科技", "创新", "专利", "知识产权", "技术攻关", "科研", "科技成果",
    "成果转化", "创新平台", "人才引进", "高新技术", "数字经济", "智能制造",
    "科创", "技术创新", "研发费用", "加计扣除", "科技企业", "高新企业",
    "科技金融", "孵化器", "众创空间", "研发投入", "技术改造",
]


def project_root() -> Path:
    # backend/app/services/daily_briefing/nlp.py -> backend/app/services/daily_briefing -> backend/app/services -> backend/app -> backend
    return Path(__file__).resolve().parents[4]


def _parse_wordlist_text(text: str) -> set[str]:
    """
    Parse a stopword/protected-word text file.
    Supports:
    - one word per line
    - comma/space separated
    - ignore comments (# ...) and section markers starting with '!' (as used in docs)
    """
    out: set[str] = set()
    if not isinstance(text, str) or not text:
        return out
    for raw in text.splitlines():
        line = (raw or "").strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        # allow inline comments: "词条  # note"
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [x.strip() for x in re.split(r"[\s,，;；]+", line) if x and x.strip()]
        for p in parts:
            if p:
                out.add(p)
    return out


def load_wechat_kill_patterns(path: Optional[str] = None) -> List[re.Pattern]:
    """
    Load extra cleanup regex patterns (multiline).
    - default patterns are always applied
    - optional file patterns can be mounted/overridden via env for quick iteration
    """
    p = path or os.getenv("ZPULSE_WECHAT_KILL_PATTERNS_PATH", "")
    patterns: List[str] = list(DEFAULT_WECHAT_KILL_PATTERNS)
    if p:
        try:
            fp = Path(p)
            if fp.exists():
                patterns.extend(list(_parse_wordlist_text(fp.read_text(encoding="utf-8"))))
        except Exception:
            pass
    compiled: List[re.Pattern] = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat, flags=re.M))
        except Exception:
            # ignore invalid patterns; don't break pipeline
            continue
    return compiled


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # remove obvious boilerplate lines commonly found in gov/wechat content
    for rx in load_wechat_kill_patterns():
        t = rx.sub("", t)
    # heuristic: if a production/credits block appears very near the end, drop the tail
    # (common pattern: staff list / "编辑：xx 审核：xx" etc.)
    markers = ("编辑", "责任编辑", "审核", "校对", "监制", "通讯员", "记者", "摄影", "供图", "来源")
    try:
        lines = t.splitlines()
        if len(lines) >= 8:
            # search in last 15 lines to avoid accidental truncation
            tail_start = max(0, len(lines) - 15)
            cut_at = None
            for i in range(len(lines) - 1, tail_start - 1, -1):
                ln = (lines[i] or "").strip()
                if any(ln.startswith(m + "：") or ln.startswith(m + ":") for m in markers):
                    cut_at = i
            if cut_at is not None and cut_at >= tail_start:
                t = "\n".join(lines[:cut_at]).rstrip()
    except Exception:
        pass
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def strip_focus_markers(text: str) -> str:
    """
    Remove legacy section markers like:
    - "为何重要：" / "为什么重要："
    - "【为何重要】" / "【大局】"
    Keep the remaining content as a single paragraph.
    """
    if not isinstance(text, str) or not text:
        return ""
    t = text.strip()
    # remove bracket markers anywhere
    t = re.sub(r"【\s*(?:为何重要|为什么重要|大局)\s*】", "", t)
    # remove leading prefixes (with optional spaces)
    t = re.sub(r"^\s*(?:为何重要|为什么重要)\s*[:：]\s*", "", t)
    t = re.sub(r"^\s*(?:大局)\s*[:：]\s*", "", t)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_number_spans(text: str, max_items: int = 60) -> List[str]:
    """
    Extract numeric strings with common Chinese finance units, to be used as a whitelist in guardrails.
    """
    if not isinstance(text, str) or not text:
        return []
    t = text
    # normalize commas inside numbers (1,000 -> 1000)
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)
    patterns = [
        r"(?:¥|￥|RMB|CNY)?\s*\d+(?:\.\d+)?\s*(?:万亿元|亿元|万元|元|%|％|万|亿)?",
        r"\d+(?:\.\d+)?\s*(?:个百分点|%|％)",
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{4}年\d{1,2}月",
    ]
    out: List[str] = []
    seen: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, t):
            s = (m.group(0) or "").strip()
            if not s:
                continue
            # keep only those that actually contain digits
            if not re.search(r"\d", s):
                continue
            # cap length to avoid capturing long unrelated spans
            if len(s) > 40:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
            if len(out) >= max_items:
                return out
    return out


def _try_jieba():
    try:
        import jieba  # type: ignore
        import jieba.posseg as pseg  # type: ignore

        return jieba, pseg
    except Exception:
        return None, None


def load_custom_dictionary(dict_path: Optional[str] = None) -> None:
    """
    Load a custom dictionary into jieba (if available).
    """
    jieba, _ = _try_jieba()
    if not jieba:
        return
    p = dict_path or os.getenv("ZPULSE_CUSTOM_DICT_PATH", "")
    if not p:
        # default location under repo root
        p = str(project_root() / "data" / "templates" / "zhejiang_finance_dict.txt")
    try:
        if Path(p).exists():
            jieba.load_userdict(p)
            logger.info(f"Loaded jieba user dict: {p}")
    except Exception as e:
        logger.warning(f"Failed to load jieba user dict: {p}, err={e}")


def load_protected_terms(path: Optional[str] = None) -> set[str]:
    """
    Protected terms are NEVER auto-added into stoplist (to prevent killing domain entities).
    Defaults:
    - finance keyword list
    - optional file (one per line) via ZPULSE_STOPLIST_PROTECTED_PATH
    - optional jieba userdict terms (first column) for safety
    """
    protected: set[str] = set(DEFAULT_FINANCE_KEYWORDS)
    # optional explicit protected list
    p = path or os.getenv("ZPULSE_STOPLIST_PROTECTED_PATH", "")
    if not p:
        p = str(project_root() / "data" / "templates" / "stoplist_protected.txt")
    try:
        fp = Path(p)
        if fp.exists():
            protected |= _parse_wordlist_text(fp.read_text(encoding="utf-8"))
    except Exception:
        pass
    # also protect custom dict entries (first column in jieba userdict format)
    try:
        dict_path = os.getenv("ZPULSE_CUSTOM_DICT_PATH", "") or str(project_root() / "data" / "templates" / "zhejiang_finance_dict.txt")
        dfp = Path(dict_path)
        if dfp.exists():
            for raw in dfp.read_text(encoding="utf-8").splitlines():
                line = (raw or "").strip()
                if not line or line.startswith("#"):
                    continue
                w = line.split()[0].strip()
                if w:
                    protected.add(w)
    except Exception:
        pass
    return protected


def finance_keyword_hits(text: str, *, keywords: Sequence[str] = DEFAULT_FINANCE_KEYWORDS) -> int:
    if not isinstance(text, str) or not text:
        return 0
    cnt = 0
    for k in keywords:
        if k and k in text:
            cnt += 1
    return cnt


@dataclass(frozen=True)
class Token:
    w: str
    pos: str = ""


def tokenize_with_pos(text: str) -> List[Token]:
    """
    Tokenize Chinese text.
    - If jieba.posseg is available, return words with POS tags.
    - Otherwise, return a conservative regex-based token list without POS.
    """
    t = clean_text(text)
    if not t:
        return []
    _, pseg = _try_jieba()
    if pseg:
        tokens: List[Token] = []
        for it in pseg.cut(t):
            w = str(getattr(it, "word", "")).strip()
            pos = str(getattr(it, "flag", "")).strip()
            if not w:
                continue
            tokens.append(Token(w=w, pos=pos))
        return tokens
    # fallback: keep CJK words (2-12 chars) + digits
    raw = re.findall(r"[\u4e00-\u9fff]{2,12}|\d+(?:\.\d+)?", t)
    return [Token(w=x, pos="") for x in raw if x]


# Removed: extract_hotwords_tfidf, extract_wordcloud_by_frequency, extract_hotphrases_ngrams (no longer used, stopwords functionality removed)

def extract_key_snippets(text: str, *, max_snippets: int = 10) -> List[str]:
    """
    Pick short, high-signal sentences that contain digits OR "财政/资金/补贴/债/税" signals.
    """
    t = clean_text(text)
    if not t:
        return []
    parts = re.split(r"[。！？；;\n]", t)
    snippets: List[str] = []
    seen: set[str] = set()
    kw = ("财政", "资金", "补贴", "补助", "专项", "债", "税", "预算", "采购", "招标", "中标", "拨付", "下达", "绩效")
    for p in parts:
        s = p.strip()
        if not s:
            continue
        if len(s) < 12:
            continue
        if not (re.search(r"\d", s) or any(k in s for k in kw)):
            continue
        if len(s) > 140:
            s = s[:140].rstrip() + "…"
        if s in seen:
            continue
        seen.add(s)
        snippets.append(s)
        if len(snippets) >= max_snippets:
            break
    return snippets


