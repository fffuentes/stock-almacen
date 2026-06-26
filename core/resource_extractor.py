"""Extractor de recursos VBS del SAP Automation Framework.

Proporciona la clase `ResourceExtractor` que lee un archivo VBS
generado por SAP GUI Recorder y genera una representación
estructurada en formato ``workflow.raw.json``.

Utiliza patrones desacoplados en ``core/patterns/`` para el
reconocimiento de instrucciones. No interpreta lógica SAP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.resource import Resource
from core.patterns import ALL_PATTERNS, BasePattern, PatternMatch
from core.patterns.export_pattern import ExportPattern


class ResourceExtractor:
    """Extrae pasos estructurados desde un archivo VBS de SAP.

    Recorre línea por línea el VBS y aplica cada patrón registrado
    en ``core.patterns.ALL_PATTERNS``. Las líneas de infraestructura
    y las no reconocidas se registran en la sección ``ignored``.

    Parameters
    ----------
    resource : Resource
        Recurso VBS a procesar.
    """

    # ------------------------------------------------------------------
    def __init__(self, resource: Resource) -> None:
        """Inicializa el extractor.

        Parameters
        ----------
        resource : Resource
            Recurso que contiene el archivo VBS a extraer.
        """
        self._resource: Resource = resource
        self._vbs_path: Path = resource.path
        self._steps: List[Dict[str, Any]] = []
        self._ignored_list: List[Dict[str, Any]] = []
        self._recognized: int = 0
        self._ignored_count: int = 0
        self._total_lines: int = 0

        # Instanciar patrones una sola vez
        self._patterns: List[BasePattern] = [
            p() for p in ALL_PATTERNS
        ]
        # ExportPattern se maneja aparte por su estado acumulativo
        self._export_pattern: ExportPattern = ExportPattern()

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def steps(self) -> List[Dict[str, Any]]:
        """Lista de pasos extraídos."""
        return self._steps

    @property
    def recognized_count(self) -> int:
        """Cantidad de instrucciones reconocidas."""
        return self._recognized

    @property
    def ignored_count(self) -> int:
        """Cantidad de instrucciones ignoradas (infraestructura + no reconocidas)."""
        return self._ignored_count

    @property
    def total_lines(self) -> int:
        """Total de líneas procesadas del VBS."""
        return self._total_lines

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def extract(self) -> Dict[str, Any]:
        """Ejecuta la extracción completa del recurso VBS.

        Returns
        -------
        dict
            Estructura ``workflow.raw.json`` lista para serializar.
        """
        self._steps.clear()
        self._ignored_list.clear()
        self._recognized = 0
        self._ignored_count = 0
        self._total_lines = 0

        # Leer el archivo VBS (UTF-16 LE, generado por SAP)
        raw_text: str = self._read_vbs()
        lines: List[str] = raw_text.splitlines()
        self._total_lines = len(lines)

        # Procesar línea por línea
        for line_number, raw_line in enumerate(lines, start=1):
            stripped: str = raw_line.strip()

            # Ignorar líneas vacías o comentarios
            if not stripped or stripped.startswith("'"):
                continue

            # Detectar infraestructura VBS
            if self._is_infrastructure_line(stripped):
                self._ignored_list.append({
                    "line": line_number,
                    "reason": "infrastructure",
                    "source": stripped,
                })
                self._ignored_count += 1
                continue

            # Intentar reconocer — ExportPattern primero (estado acumulativo)
            matched: bool = False

            # ExportPattern tiene prioridad: acumula DY_PATH/DY_FILENAME
            export_result: Optional[PatternMatch] = (
                self._export_pattern.matches(stripped)
            )
            if export_result is not None:
                if not export_result.skip:
                    self._add_step(export_result, line_number, stripped)
                matched = True  # línea consumida, no probar otros patrones

            # Luego probar el resto de patrones
            if not matched:
                for pattern in self._patterns:
                    result: Optional[PatternMatch] = pattern.matches(stripped)
                    if result is not None:
                        self._add_step(result, line_number, stripped)
                        matched = True
                        break

            if not matched:
                self._ignored_list.append({
                    "line": line_number,
                    "reason": "unrecognized",
                    "source": stripped,
                })
                self._ignored_count += 1

        # Forzar exportación pendiente (si quedó path sin filename)
        flush_result: Optional[PatternMatch] = ExportPattern.flush()
        if flush_result is not None:
            self._add_step(flush_result, 0, "(export flush)")

        # Construir el documento final
        return self._build_document()

    # ------------------------------------------------------------------
    # Lectura del VBS
    # ------------------------------------------------------------------

    def _read_vbs(self) -> str:
        """Lee el archivo VBS con detección de encoding.

        SAP genera VBS en UTF-16 LE con BOM.

        Returns
        -------
        str
            Contenido del archivo VBS como texto.
        """
        raw_bytes: bytes = self._vbs_path.read_bytes()

        # Detectar BOM UTF-16 LE (FF FE)
        if raw_bytes[:2] == b"\xff\xfe":
            return raw_bytes.decode("utf-16-le")
        # Intentar UTF-8 como fallback
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("utf-16-le")

    # ------------------------------------------------------------------
    # Detección de infraestructura VBS
    # ------------------------------------------------------------------

    @staticmethod
    def _is_infrastructure_line(line: str) -> bool:
        """Determina si una línea es infraestructura VBS.

        Parameters
        ----------
        line : str
            Línea a evaluar.

        Returns
        -------
        bool
            ``True`` si es infraestructura.
        """
        infra_patterns: Tuple[str, ...] = (
            "Set ",
            "If ",
            "End If",
            "WScript.",
            ".maximize",
            ".caretPosition",
            ".setFocus",
            ".CreateSession",
        )
        return any(line.startswith(p) or p in line for p in infra_patterns)

    # ------------------------------------------------------------------
    # Construcción de pasos
    # ------------------------------------------------------------------

    def _add_step(
        self,
        match: PatternMatch,
        line_number: int,
        source: str,
    ) -> None:
        """Agrega un paso reconocido a la lista.

        Parameters
        ----------
        match : PatternMatch
            Resultado del patrón.
        line_number : int
            Número de línea en el VBS original.
        source : str
            Contenido original de la línea.
        """
        self._recognized += 1
        step: Dict[str, Any] = {
            "step": self._recognized,
            "source_line": line_number,
            "source": source,
            "type": match.type,
            "strategy": match.strategy,
            "data": match.data,
        }
        self._steps.append(step)

    # ------------------------------------------------------------------

    def _build_document(self) -> Dict[str, Any]:
        """Construye el documento workflow.raw.json.

        Returns
        -------
        dict
            Estructura completa del workflow raw.
        """
        return {
            "resource": self._resource.name,
            "transaction": self._resource.transaction,
            "statistics": {
                "recognized": self._recognized,
                "ignored": self._ignored_count,
                "lines": self._total_lines,
            },
            "steps": self._steps,
            "ignored": self._ignored_list,
        }

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save_raw_workflow(self) -> Path:
        """Guarda el workflow extraído en ``workflow.raw.json``.

        Returns
        -------
        Path
            Ruta al archivo guardado.
        """
        document: Dict[str, Any] = self.extract()
        output_path: Path = self._vbs_path.parent / "workflow.raw.json"

        output_path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path
