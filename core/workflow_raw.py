"""Modelo de workflow raw del SAP Automation Framework.

Proporciona las clases que representan el contenido de un archivo
``workflow.raw.json`` generado por el Resource Extractor. Trabaja
con objetos tipados en lugar de diccionarios.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class WorkflowRawStep:
    """Un paso extraído directamente del VBS.

    Attributes
    ----------
    step : int
        Número secuencial del paso.
    source_line : int
        Línea del VBS de donde proviene.
    source : str
        Contenido original de la línea VBS.
    type : str
        Tipo de instrucción detectada (``"set_text"``, ``"press_button"``, etc.).
    strategy : str
        Estrategia de interacción (``"field"``, ``"button"``, ``"vkey"``, etc.).
    data : dict
        Datos extraídos (campos, valores, find_by_id).
    """

    step: int
    source_line: int
    source: str
    type: str
    strategy: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IgnoredInstruction:
    """Una instrucción VBS que no fue reconocida como acción SAP.

    Attributes
    ----------
    line : int
        Número de línea en el VBS.
    reason : str
        Motivo por el cual fue ignorada (``"infrastructure"``, ``"unrecognized"``).
    source : str
        Contenido original de la línea.
    """

    line: int
    reason: str
    source: str


@dataclass
class WorkflowStatistics:
    """Estadísticas de la extracción.

    Attributes
    ----------
    recognized : int
        Instrucciones reconocidas.
    ignored : int
        Instrucciones ignoradas.
    lines : int
        Total de líneas del archivo VBS.
    """

    recognized: int = 0
    ignored: int = 0
    lines: int = 0


class WorkflowRaw:
    """Representa un workflow extraído directamente del VBS.

    Contiene los pasos tal cual fueron detectados por el
    Resource Extractor, sin ningún tipo de interpretación
    del dominio SAP.

    Parameters
    ----------
    resource : str
        Nombre del archivo VBS de origen.
    transaction : str
        Código de transacción SAP.
    """

    # ------------------------------------------------------------------
    def __init__(self, resource: str = "", transaction: str = "") -> None:
        """Inicializa un workflow raw.

        Parameters
        ----------
        resource : str
            Nombre del recurso VBS.
        transaction : str
            Código de transacción.
        """
        self.resource: str = resource
        self.transaction: str = transaction
        self.statistics: WorkflowStatistics = WorkflowStatistics()
        self.steps: List[WorkflowRawStep] = []
        self.ignored: List[IgnoredInstruction] = []

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "WorkflowRaw":
        """Carga un workflow raw desde un archivo JSON.

        Parameters
        ----------
        path : Path
            Ruta al archivo ``workflow.raw.json``.

        Returns
        -------
        WorkflowRaw
            Instancia con los datos cargados.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data: dict = json.load(fh)

        wf = cls(
            resource=data.get("resource", ""),
            transaction=data.get("transaction", ""),
        )

        # Estadísticas
        stats: dict = data.get("statistics", {})
        wf.statistics = WorkflowStatistics(
            recognized=stats.get("recognized", 0),
            ignored=stats.get("ignored", 0),
            lines=stats.get("lines", 0),
        )

        # Pasos
        for step_data in data.get("steps", []):
            wf.steps.append(WorkflowRawStep(
                step=step_data.get("step", 0),
                source_line=step_data.get("source_line", 0),
                source=step_data.get("source", ""),
                type=step_data.get("type", ""),
                strategy=step_data.get("strategy", ""),
                data=step_data.get("data", {}),
            ))

        # Ignoradas
        for ign_data in data.get("ignored", []):
            wf.ignored.append(IgnoredInstruction(
                line=ign_data.get("line", 0),
                reason=ign_data.get("reason", ""),
                source=ign_data.get("source", ""),
            ))

        return wf

    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Guarda el workflow raw en un archivo JSON.

        Parameters
        ----------
        path : Path
            Ruta de destino.
        """
        data: Dict[str, Any] = {
            "resource": self.resource,
            "transaction": self.transaction,
            "statistics": {
                "recognized": self.statistics.recognized,
                "ignored": self.statistics.ignored,
                "lines": self.statistics.lines,
            },
            "steps": [
                {
                    "step": s.step,
                    "source_line": s.source_line,
                    "source": s.source,
                    "type": s.type,
                    "strategy": s.strategy,
                    "data": s.data,
                }
                for s in self.steps
            ],
            "ignored": [
                {"line": i.line, "reason": i.reason, "source": i.source}
                for i in self.ignored
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
