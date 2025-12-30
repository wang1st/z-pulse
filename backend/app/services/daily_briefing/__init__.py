"""
Daily briefing (财政信息聚合) generation package.

Design goals:
- Modular pipeline (NLP preprocess -> LLM drafting -> guardrails -> render-ready JSON)
- Stateless functions where possible; persist only via existing Report storage.
"""

from .generator import DailyBriefingGenerator

__all__ = ["DailyBriefingGenerator"]


