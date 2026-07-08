"""Patrón: doble clic en celda (``doubleClickCurrentCell``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_DOUBLE_CLICK: str = _RE_FIND_BY_ID + r'\.doubleClickCurrentCell'


class DoubleClickPattern(BasePattern):
    """Reconoce ``session.findById("...").doubleClickCurrentCell``."""

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer un doble clic.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        match: Optional[re.Match] = re.search(_RE_DOUBLE_CLICK, line)
        if not match:
            return None

        return PatternMatch(
            type="double_click",
            strategy="grid",
            data={"find_by_id": match.group("path")},
        )
