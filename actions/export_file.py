"""Handler: export_file — exportación de archivo (pendiente)."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from actions.base import BaseActionHandler


@ActionRegistry.register("export_file")
class ExportFileHandler(BaseActionHandler):
    """Exportación de archivo desde SAP — pendiente de implementar.

    Esta fase no ejecuta exportaciones. El handler está registrado
    para que el workflow no falle, pero no realiza ninguna acción.
    """

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """No-op: la exportación no se ejecuta en esta fase.

        Parameters
        ----------
        step : WorkflowStep
            Paso del workflow (ignorado).
        session_com : Any
            Sesión COM SAP (no utilizada).
        """
        # Pendiente de implementación en fases futuras
        pass
