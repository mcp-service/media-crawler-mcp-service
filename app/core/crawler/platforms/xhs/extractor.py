# -*- coding: utf-8 -*-
"""Fallback HTML extractor for Xiaohongshu note detail."""

from __future__ import annotations

import json
import re
from typing import Dict, Optional

from app.providers.logger import get_logger

logger = get_logger()


class XiaoHongShuExtractor:
    """Utility to extract note detail from rendered HTML when API fails."""

    _pattern = re.compile(r"window\.__INITIAL_STATE__=(\{.*?\})</script>", re.DOTALL)

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        if not html:
            return None

        state = self._extract_state(html)
        if not state:
            return None

        try:
            return (
                state.get("note", {})
                .get("noteDetailMap", {})
                .get(note_id, {})
                .get("note")
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("[xhs.extractor] parse note detail failed: %s", exc)
            return None

    def extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        state = self._extract_state(html)
        if not state:
            return None
        return state.get("user", {}).get("userPageData")

    def _extract_state(self, html: str) -> Optional[Dict]:
        match = self._pattern.search(html or "")
        if not match:
            logger.debug("[xhs.extractor] initial state not found")
            return None

        payload = match.group(1)
        try:
            sanitized = payload.replace(":undefined", ":null")
            data = json.loads(sanitized)
        except json.JSONDecodeError as exc:
            logger.debug("[xhs.extractor] parse json failed: %s", exc)
            return None

        return data


__all__ = ["XiaoHongShuExtractor"]
