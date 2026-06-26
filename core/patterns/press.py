"""Patrón: pulsación de botón (``.press``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_PRESS: str = _RE_FIND_BY_ID + r'\.press'


class PressPattern(BasePattern):
    """Reconoce ``session.findById("...").press``."""

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer una pulsación de botón.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        match: Optional[re.Match] = re.search(_RE_PRESS, line)
        if not match:
            return None

        return PatternMatch(
            type="press_button",
            strategy="button",
            data={"find_by_id": match.group("path")},
        )
