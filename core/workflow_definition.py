"""Definición de workflow del SAP Automation Framework.

Proporciona la clase `WorkflowDefinition` que representa la
definición interna de un workflow generada a partir de un
recurso VBS. En esta fase no contiene acciones SAP, solo
metadatos de identificación.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class WorkflowStatus(Enum):
    """Estados posibles de un workflow."""

    PENDING_PARSER = "pending_parser"
    READY = "ready"
    NEEDS_REGENERATION = "needs_regeneration"


class WorkflowDefinition:
    """Definición interna de un workflow del Framework.

    Representa la versión procesada de un recurso VBS lista
    para ser utilizada por el motor de ejecución. En esta fase
    solo contiene metadatos de identificación.

    Parameters
    ----------
    transaction : str
        Código de transacción SAP (ej. ``"MB52"``).
    source_file : str
        Nombre del archivo VBS de origen.
    """

    # ------------------------------------------------------------------
    def __init__(self, transaction: str, source_file: str) -> None:
        """Inicializa la definición de workflow.

        Parameters
        ----------
        transaction : str
            Código de transacción SAP.
        source_file : str
            Archivo VBS de origen.
        """
        self.transaction: str = transaction
        self.source_file: str = source_file
        self.name: str = transaction
        self.version: int = 1
        self.created: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status: WorkflowStatus = WorkflowStatus.PENDING_PARSER

    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convierte la definición a diccionario para serialización JSON.

        Returns
        -------
        dict
            Representación en diccionario.
        """
        return {
            "transaction": self.transaction,
            "name": self.name,
            "version": self.version,
            "source_file": self.source_file,
            "status": self.status.value,
            "generated": self.created,
        }

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Representación textual del workflow."""
        return (
            f"WorkflowDefinition(transaction={self.transaction!r}, "
            f"version={self.version}, status={self.status.value!r})"
        )
