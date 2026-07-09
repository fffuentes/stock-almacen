"""Modelo de recurso del SAP Automation Framework.

Proporciona la clase `Resource` que representa cualquier recurso
del Framework (archivos VBS, configuraciones, etc.), almacenando
sus metadatos y estado de sincronización.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ResourceStatus(Enum):
    """Estados posibles de un recurso respecto a su metadata."""

    NEW = "Nuevo"
    UNCHANGED = "Sin cambios"
    UPDATED = "Actualizado"
    DELETED = "Eliminado"


class Resource:
    """Representa un recurso gestionado por el Framework.

    Almacena metadatos del archivo fuente (nombre, ruta, tipo,
    fecha de modificación, hash SHA256) y su estado actual respecto
    a la metadata persistida.

    Parameters
    ----------
    name : str
        Nombre del recurso (ej. ``"MB52.vbs"``).
    path : Path
        Ruta absoluta al archivo del recurso.
    resource_type : str
        Tipo de recurso (ej. ``"vbs"``).
    """

    # ------------------------------------------------------------------
    def __init__(
        self, name: str, path: Path, resource_type: str = "vbs"
    ) -> None:
        """Inicializa un recurso.

        Parameters
        ----------
        name : str
            Nombre del archivo del recurso.
        path : Path
            Ruta absoluta al archivo.
        resource_type : str
            Tipo de recurso (por defecto ``"vbs"``).
        """
        self.name: str = name
        self.path: Path = path
        self.type: str = resource_type
        self.last_modified: datetime = datetime.now()
        self.hash_sha256: str = ""
        self.status: ResourceStatus = ResourceStatus.NEW

        # Calcular hash si el archivo existe
        if self.path.exists() and self.path.is_file():
            self.hash_sha256 = self._compute_hash()
            try:
                mtime: float = self.path.stat().st_mtime
                self.last_modified = datetime.fromtimestamp(mtime)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def transaction(self) -> str:
        """Nombre de la transacción, derivado del nombre del recurso."""
        return self.path.parent.name if self.path.parent else ""

    @property
    def metadata_path(self) -> Path:
        """Ruta al archivo metadata.json de este recurso."""
        return self.path.parent / "metadata.json"

    @property
    def workflow_path(self) -> Path:
        """Ruta al archivo workflow.json de este recurso."""
        return self.path.parent / "workflow.json"

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def refresh_hash(self) -> None:
        """Recalcula el hash SHA256 desde el archivo en disco."""
        if self.path.exists() and self.path.is_file():
            self.hash_sha256 = self._compute_hash()
            try:
                mtime: float = self.path.stat().st_mtime
                self.last_modified = datetime.fromtimestamp(mtime)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _compute_hash(self) -> str:
        """Calcula el hash SHA256 del archivo del recurso.

        Returns
        -------
        str
            Hash SHA256 hexadecimal.
        """
        sha256 = hashlib.sha256()
        try:
            with open(self.path, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    sha256.update(chunk)
        except OSError:
            return ""
        return sha256.hexdigest()

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Representación textual del recurso."""
        return (
            f"Resource(name={self.name!r}, type={self.type!r}, "
            f"status={self.status.value!r}, hash={self.hash_sha256[:12]}...)"
        )

    def __str__(self) -> str:
        """Descripción legible del recurso."""
        return (
            f"  {self.transaction}\n"
            f"    Estado:    {self.status.value}\n"
            f"    Hash:      {self.hash_sha256[:16]}...\n"
            f"    Modificado:{self.last_modified.strftime('%Y-%m-%d %H:%M:%S')}"
        )
