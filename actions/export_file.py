"""Handler: export_file — exporta un archivo desde SAP al sistema local."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.workflow import WorkflowStep
from core.action_registry import ActionRegistry
from .base import BaseActionHandler


# Rutas estándar del diálogo de exportación SAP
_DY_PATH: str = "wnd[1]/usr/ctxtDY_PATH"
_DY_FILENAME: str = "wnd[1]/usr/ctxtDY_FILENAME"


@ActionRegistry.register("export_file")
class ExportFileHandler(BaseActionHandler):
    """Exporta un archivo desde SAP al sistema de archivos local.

    Establece la ruta de exportación desde la configuración del
    Framework (``settings.json``) y el nombre de archivo desde
    el workflow. El botón de exportación lo presiona el paso
    siguiente (``press_button`` sobre ``btn[11]``).
    """

    def execute(self, step: WorkflowStep, session_com: Any) -> None:
        """Ejecuta la exportación del archivo.

        Parameters
        ----------
        step : WorkflowStep
            Paso con ``filename`` y ``export_path``.
        session_com : Any
            Sesión COM SAP.
        """
        filename: str = step.data.get("filename", "")
        export_path: str = step.data.get("export_path", "")

        if not filename:
            raise ValueError("export_file: falta 'filename'")
        if not export_path:
            raise ValueError(
                "export_file: falta 'export_path'. "
                "Verifique settings.json → python main.py configure."
            )

        # Crear directorio de exportación si no existe
        export_dir = Path(export_path)
        if not export_dir.exists():
            export_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n  Carpeta de exportación creada: {export_path}")

        # Eliminar archivo existente para evitar popup "¿Desea reemplazar?"
        full_path = export_dir / filename
        if full_path.exists():
            print(f"  Archivo existente encontrado: {filename}")
            print(f"  Eliminando... ", end="", flush=True)
            full_path.unlink()
            print("OK")

        # Sobrescribir ruta del VBS con la ruta de configuración
        session_com.findById(_DY_PATH).text = export_path

        # Establecer nombre de archivo desde el workflow
        session_com.findById(_DY_FILENAME).text = filename
