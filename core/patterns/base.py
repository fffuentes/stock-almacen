"""Patrón base para el reconocimiento de instrucciones VBS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PatternMatch:
    """Resultado de un patrón reconocido.

    Attributes
    ----------
    type : str
        Tipo de instrucción (``"set_text"``, ``"press_button"``, etc.).
    strategy : str
        Estrategia utilizada (``"field"``, ``"button"``, ``"vkey"``, etc.).
    data : dict
        Datos extraídos de la instrucción.
    skip : bool
        Si es ``True``, la línea fue consumida por el patrón pero no
        debe agregarse como paso (útil para acumuladores como export).
    """

    type: str
    strategy: str
    data: Dict[str, Any] = field(default_factory=dict)
    skip: bool = False


class BasePattern(ABC):
    """Clase base abstracta para patrones de reconocimiento VBS.

    Cada subclase implementa el método ``matches`` que intenta
    reconocer una línea VBS y devuelve un ``PatternMatch`` si
    coincide, o ``None`` en caso contrario.
    """

    @abstractmethod
    def matches(self, line: str) -> Optional[PatternMatch]:
        """Intenta reconocer la línea como este patrón.

        Parameters
        ----------
        line : str
            Línea del VBS a analizar (ya limpia de espacios).

        Returns
        -------
        PatternMatch or None
            Resultado si coincide, ``None`` si no.
        """
        ...
