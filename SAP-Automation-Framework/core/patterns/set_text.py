"""Patrón: asignación de texto (``.text = "..."``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

# session.findById("...").text = "valor"
_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_SET_TEXT: str = _RE_FIND_BY_ID + r'\.text\s*=\s*"(?P<value>[^"]*)"'


class SetTextPattern(BasePattern):
    """Reconoce ``session.findById("...").text = "valor"``.

    No interpreta el significado del campo (ej. okcd).
    Registra exactamente lo encontrado.
    """

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer una asignación de texto.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
        """
        match: Optional[re.Match] = re.search(_RE_SET_TEXT, line)
        if not match:
            return None

        path: str = match.group("path")
        value: str = match.group("value")

        # Extraer nombre corto del campo
        parts: list[str] = path.split("/")
        field_name: str = parts[-1] if parts else path

        return PatternMatch(
            type="set_text",
            strategy="field",
            data={
                "find_by_id": path,
                "field": field_name,
                "value": value,
            },
        )
