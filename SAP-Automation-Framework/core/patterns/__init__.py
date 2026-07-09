"""Patrones de reconocimiento de instrucciones VBS para el Resource Extractor.

Cada módulo en este paquete implementa un patrón específico de
SAP GUI Scripting. El extractor recorre estos patrones para
cada línea del VBS y construye los pasos del workflow.
"""

from .base import BasePattern, PatternMatch
from .set_text import SetTextPattern
from .send_vkey import SendVKeyPattern
from .press import PressPattern
from .select import SelectPattern
from .export_pattern import ExportPattern
from .double_click import DoubleClickPattern
from .rows import RowsPattern

# Registro de patrones en orden de prioridad (más específicos primero).
# ExportPattern se maneja por separado en el extractor porque necesita
# estado acumulativo (DY_PATH + DY_FILENAME).
ALL_PATTERNS: list[type[BasePattern]] = [
    SendVKeyPattern,
    RowsPattern,
    DoubleClickPattern,
    PressPattern,
    SelectPattern,
    SetTextPattern,
]

__all__ = [
    "BasePattern",
    "PatternMatch",
    "ALL_PATTERNS",
    "SetTextPattern",
    "SendVKeyPattern",
    "PressPattern",
    "SelectPattern",
    "ExportPattern",
    "DoubleClickPattern",
    "RowsPattern",
]
