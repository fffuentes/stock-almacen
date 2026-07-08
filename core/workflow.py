"""Modelo de workflow SAF del SAP Automation Framework.

Proporciona las clases que representan un workflow en el lenguaje
interno del SAF. A diferencia del workflow raw (lenguaje VBS),
el workflow SAF contiene instrucciones interpretadas del dominio SAP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class WorkflowStep:
    """Un paso del workflow en lenguaje SAF.

    Attributes
    ----------
    step : int
        Número secuencial del paso.
    action : str
        Acción SAF a ejecutar (``"start_transaction"``, ``"set_field"``,
        ``"confirm"``, ``"execute"``, ``"press_button"``, etc.).
    data : dict
        Datos asociados a la acción (campos, valores, etc.).
    """

    step: int
    action: str
    data: Dict[str, Any] = field(default_factory=dict)


class Workflow:
    """Representa un workflow en el lenguaje interno del SAF.

    Contiene pasos interpretados listos para ser ejecutados por
    el Execution Engine. Ya no contiene información específica
    del VBS (find_by_id, source_line, etc.).

    Parameters
    ----------
    transaction : str
        Código de transacción SAP.
    """

    # ------------------------------------------------------------------
    def __init__(self, transaction: str = "") -> None:
        """Inicializa un workflow SAF.

        Parameters
        ----------
        transaction : str
            Código de transacción.
        """
        self.transaction: str = transaction
        self.steps: List[WorkflowStep] = []

    # ------------------------------------------------------------------
    # Métodos de fábrica
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        """Carga un workflow SAF desde un archivo JSON.

        Parameters
        ----------
        path : Path
            Ruta al archivo ``workflow.json``.

        Returns
        -------
        Workflow
            Instancia con los datos cargados.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data: dict = json.load(fh)

        wf = cls(transaction=data.get("transaction", ""))

        for step_data in data.get("steps", []):
            step = WorkflowStep(
                step=step_data.get("step", 0),
                action=step_data.get("action", ""),
                data={
                    k: v
                    for k, v in step_data.items()
                    if k not in ("step", "action")
                },
            )
            wf.steps.append(step)

        return wf

    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Guarda el workflow SAF en un archivo JSON.

        Parameters
        ----------
        path : Path
            Ruta de destino.
        """
        steps_data: List[Dict[str, Any]] = []
        for s in self.steps:
            step_dict: Dict[str, Any] = {
                "step": s.step,
                "action": s.action,
            }
            step_dict.update(s.data)
            steps_data.append(step_dict)

        data: Dict[str, Any] = {
            "transaction": self.transaction,
            "steps": steps_data,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------

    def add_step(self, action: str, **kwargs: Any) -> WorkflowStep:
        """Agrega un paso al workflow.

        Parameters
        ----------
        action : str
            Acción SAF.
        **kwargs
            Datos adicionales del paso.

        Returns
        -------
        WorkflowStep
            El paso creado.
        """
        step_number: int = len(self.steps) + 1
        step = WorkflowStep(step=step_number, action=action, data=kwargs)
        self.steps.append(step)
        return step
