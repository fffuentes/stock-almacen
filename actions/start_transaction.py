"""Handler: start_transaction — inicia una transacción SAP."""

from __future__ import annotations

from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


@ActionRegistry.register("start_transaction")
class StartTransactionHandler(BaseActionHandler):
    """Inicia una transacción SAP escribiendo en el campo okcd."""

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Escribe el código de transacción en okcd y presiona Enter.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``transaction``.
        session_com : Any
            Sesión COM SAP.
        """
        transaction: str = step.data.get("transaction", "")
        if not transaction:
            raise ValueError("start_transaction: falta 'transaction' en los datos del paso")

        # Escribir en el campo de comandos
        okcd = session_com.findById("wnd[0]/tbar[0]/okcd")
        okcd.text = transaction

        # Enviar Enter para ejecutar
        session_com.findById("wnd[0]").sendVKey(0)
