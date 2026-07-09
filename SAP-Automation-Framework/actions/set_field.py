"""Handler: set_field — asigna texto a un campo SAP."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


@ActionRegistry.register("set_field")
class SetFieldHandler(BaseActionHandler):
    """Asigna un valor a un campo SAP mediante findById."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Escribe el valor en el campo especificado.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``target`` (findById), ``value``.
        session_com : Any
            Sesión COM SAP.
        """
        target: str = step.data.get("target", "")
        value: str = step.data.get("value", "")

        if not target:
            raise ValueError("set_field: falta 'target' (findById) en los datos del paso")

        field = session_com.findById(target)
        field.text = str(value)
