"""Handler: press_button — presiona un botón SAP."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


@ActionRegistry.register("press_button")
class PressButtonHandler(BaseActionHandler):
    """Presiona un botón SAP mediante findById."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Presiona el botón especificado.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``target`` (findById).
        session_com : Any
            Sesión COM SAP.
        """
        target: str = step.data.get("target", "")
        if not target:
            raise ValueError("press_button: falta 'target' (findById) en los datos del paso")

        button = session_com.findById(target)
        button.press()
