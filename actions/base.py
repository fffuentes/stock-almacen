"""Handler base para acciones del Execution Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.workflow import WorkflowStep


class BaseActionHandler(ABC):
    """Clase base abstracta para handlers de acciones SAF.

    Cada subclase implementa ``execute()``, que recibe el paso
    del workflow y la referencia COM de la sesión SAP.
    """

    @abstractmethod
    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Ejecuta la acción sobre la sesión SAP.

        Parameters
        ----------
        step : WorkflowStep
            Paso del workflow con los datos de la acción.
        session_com : Any
            Referencia COM a la sesión SAP (``GuiSession``).

        Raises
        ------
        Exception
            Si la acción falla.
        """
        ...
