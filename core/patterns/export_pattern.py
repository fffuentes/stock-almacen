"""Patrón: exportación (``DY_PATH`` + ``DY_FILENAME``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePattern, PatternMatch

_RE_FIND_BY_ID: str = r'session\.findById\("(?P<path>[^"]+)"\)'
_RE_SET_TEXT: str = _RE_FIND_BY_ID + r'\.text\s*=\s*"(?P<value>[^"]*)"'

# Estado acumulativo: solo puede haber una exportación activa a la vez
_export_path: Optional[str] = None
_export_filename: Optional[str] = None


class ExportPattern(BasePattern):
    """Reconoce y acumula ``DY_PATH`` y ``DY_FILENAME``.

    Combina ambos en un único paso de tipo ``export`` cuando
    ambos valores están disponibles.
    """

    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer DY_PATH o DY_FILENAME.

        Parameters
        ----------
        line : str
            Línea del VBS.

        Returns
        -------
        PatternMatch or None
            Solo devuelve resultado cuando se completa el par path+filename.
        """
        global _export_path, _export_filename

        match: Optional[re.Match] = re.search(_RE_SET_TEXT, line)
        if not match:
            return None

        path: str = match.group("path")
        value: str = match.group("value")

        if "DY_PATH" in path:
            _export_path = value
            # Línea consumida, pero no generar paso todavía
            return PatternMatch(type="", strategy="", skip=True)

        if "DY_FILENAME" in path:
            _export_filename = value
            if _export_path is not None:
                result: PatternMatch = PatternMatch(
                    type="export",
                    strategy="local_file",
                    data={
                        "path": _export_path,
                        "filename": _export_filename,
                    },
                )
                _export_path = None
                _export_filename = None
                return result
            # Filename sin path: consumir pero no generar paso aún
            return PatternMatch(type="", strategy="", skip=True)

    @staticmethod
    def flush() -> Optional[PatternMatch]:
        """Fuerza la generación del paso de exportación pendiente.

        Returns
        -------
        PatternMatch or None
        """
        global _export_path, _export_filename
        if _export_path is not None or _export_filename is not None:
            result: PatternMatch = PatternMatch(
                type="export",
                strategy="local_file",
                data={
                    "path": _export_path or "",
                    "filename": _export_filename or "",
                },
            )
            _export_path = None
            _export_filename = None
            return result
        return None
