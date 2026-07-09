"""Handler: execute — presiona F8 en la ventana activa."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


@ActionRegistry.register("execute")
class ExecuteHandler(BaseActionHandler):
    """Presiona F8 (sendVKey 8) en la ventana principal."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Envía VKey 8 (F8).

        Parameters
        ----------
        step : WorkflowStep
            Paso (sin datos adicionales).
        session_com : Any
            Sesión COM SAP.
        """
        session_com.findById("wnd[0]").sendVKey(8)
