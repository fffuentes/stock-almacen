"""Handler: send_vkey — envía una tecla virtual a SAP."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from actions.base import BaseActionHandler


@ActionRegistry.register("send_vkey")
class SendVKeyHandler(BaseActionHandler):
    """Envía una tecla virtual (sendVKey) a la ventana principal."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Envía la tecla virtual especificada.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``value`` (código de tecla).
        session_com : Any
            Sesión COM SAP.
        """
        value: int = int(step.data.get("value", 0))
        session_com.findById("wnd[0]").sendVKey(value)
