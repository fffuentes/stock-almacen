"""Patrón: selección de menú (``.select``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_SELECT: str = _RE_FIND_BY_ID + r'\.select'


class SelectPattern(BasePattern):
    """Reconoce ``session.findById("...").select``."""

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer una selección.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        match: Optional[re.Match] = re.search(_RE_SELECT, line)
        if not match:
            return None

        return PatternMatch(
            type="select_menu",
            strategy="menu",
            data={"find_by_id": match.group("path")},
        )
