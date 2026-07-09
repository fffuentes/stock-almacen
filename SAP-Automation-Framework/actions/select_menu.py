"""Handler: select_menu — selecciona una opción de menú SAP."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


@ActionRegistry.register("select_menu")
class SelectMenuHandler(BaseActionHandler):
    """Selecciona una opción de menú SAP mediante findById."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Selecciona el menú especificado.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``target`` (findById).
        session_com : Any
            Sesión COM SAP.
        """
        target: str = step.data.get("target", "")
        if not target:
            raise ValueError("select_menu: falta 'target' (findById) en los datos del paso")

        menu = session_com.findById(target)
        menu.select()
