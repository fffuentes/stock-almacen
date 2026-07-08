"""Patrón: manipulación de filas (``selectedRows``, ``currentCellRow``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_SELECTED_ROWS: str = (
    _RE_FIND_BY_ID + r'\.selectedRows\s*=\s*(?P<value>\d+)'
)
_RE_CURRENT_ROW: str = (
    _RE_FIND_BY_ID + r'\.currentCellRow\s*=\s*(?P<value>\d+)'
)


class RowsPattern(BasePattern):
    """Reconoce ``selectedRows`` y ``currentCellRow``."""

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer manipulación de filas.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        # selectedRows = N
        match: Optional[re.Match] = re.search(_RE_SELECTED_ROWS, line)
        if match:
            return PatternMatch(
                type="select_rows",
                strategy="grid",
                data={
                    "find_by_id": match.group("path"),
                    "value": int(match.group("value")),
                },
            )

        # currentCellRow = N
        match = re.search(_RE_CURRENT_ROW, line)
        if match:
            return PatternMatch(
                type="current_row",
                strategy="grid",
                data={
                    "find_by_id": match.group("path"),
                    "value": int(match.group("value")),
                },
            )

        return None
