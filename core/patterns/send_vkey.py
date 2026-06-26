"""Patrón: envío de tecla virtual (``sendVKey N``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_SEND_VKEY: str = _RE_FIND_BY_ID + r'\.sendVKey\s+(?P<value>\d+)'


class SendVKeyPattern(BasePattern):
    """Reconoce ``session.findById("...").sendVKey N``."""

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer un sendVKey.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        match: Optional[re.Match] = re.search(_RE_SEND_VKEY, line)
        if not match:
            return None

        return PatternMatch(
            type="send_vkey",
            strategy="vkey",
            data={
                "find_by_id": match.group("path"),
                "value": int(match.group("value")),
            },
        )
