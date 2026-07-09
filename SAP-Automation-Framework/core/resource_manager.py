"""Administrador de recursos del SAP Automation Framework.

Proporciona la clase `ResourceManager` responsable de descubrir,
gestionar y monitorear los recursos del Framework (archivos VBS),
detectando cambios, generando metadata y administrando workflows.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.resource import Resource, ResourceStatus
from core.workflow_definition import WorkflowDefinition, WorkflowStatus
from core.resource_extractor import ResourceExtractor
from core.workflow_raw import WorkflowRaw
from core.workflow_normalizer import WorkflowNormalizer


class ResourceManager:
    """Administrador de recursos del Framework.

    Responsable de:
    - Descubrir automáticamente todos los recursos en ``resources/``.
    - Calcular y verificar hashes SHA256.
    - Detectar recursos nuevos, modificados, sin cambios o eliminados.
    - Generar ``metadata.json`` para cada recurso.
    - Generar ``workflow.json`` placeholder para cada recurso.

    NO interpreta el contenido de los archivos VBS.
    NO ejecuta transacciones SAP.

    Parameters
    ----------
    base_dir : Path
        Directorio raíz del proyecto.
    """

    # ------------------------------------------------------------------
    def __init__(self, base_dir: Path) -> None:
        """Inicializa el administrador de recursos.

        Parameters
        ----------
        base_dir : Path
            Ruta al directorio raíz del proyecto.
        """
        self._base_dir: Path = base_dir
        self._resources_dir: Path = base_dir / "resources"
        self._resources: Dict[str, Resource] = {}
        self._extraction_stats: Dict[str, Dict[str, int]] = {}
        self._normalized: bool = False

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def resources(self) -> Dict[str, Resource]:
        """Diccionario de recursos descubiertos (clave = transacción)."""
        return self._resources

    @property
    def extraction_stats(self) -> Dict[str, Dict[str, int]]:
        """Estadísticas de extracción por transacción.

        Returns
        -------
        dict
            Diccionario con estadísticas por transacción:
            ``{"MB52": {"total": 17, "recognized": 14, "ignored": 3}}``
        """
        return self._extraction_stats

    @property
    def normalized(self) -> bool:
        """Indica si se ejecutó la normalización en este escaneo."""
        return self._normalized

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def scan(self) -> Dict[str, Resource]:
        """Escanea y procesa todos los recursos del Framework.

        Flujo:
        1. Descubre todos los archivos VBS en ``resources/``.
        2. Para cada recurso, compara su hash con metadata.json.
        3. Clasifica como: Nuevo, Sin cambios, Actualizado, Eliminado.
        4. Genera/actualiza metadata.json y workflow.json según corresponda.
        5. Si el recurso es nuevo o actualizado, ejecuta el extractor.

        Returns
        -------
        dict[str, Resource]
            Diccionario de recursos procesados (clave = transacción).
        """
        self._resources.clear()
        self._extraction_stats.clear()

        # 1. Descubrir recursos
        discovered: List[Resource] = self._discover_resources()

        # 2. Clasificar cada recurso
        for resource in discovered:
            transaction: str = resource.transaction
            self._classify_resource(resource)
            self._resources[transaction] = resource

            # 3. Generar/actualizar metadata
            self._save_metadata(resource)

            # 4. Generar/actualizar workflow si es necesario
            self._ensure_workflow(resource)

            # 5. Extraer pasos del VBS si es nuevo o fue actualizado
            if resource.status in (ResourceStatus.NEW, ResourceStatus.UPDATED):
                self._extract_resource(resource)

        # 5. Detectar recursos eliminados (metadata sin archivo VBS)
        self._detect_deleted()

        return self._resources

    # ------------------------------------------------------------------
    # Descubrimiento
    # ------------------------------------------------------------------

    def _discover_resources(self) -> List[Resource]:
        """Descubre todos los recursos VBS en el directorio resources/.

        Recorre recursivamente ``resources/`` buscando archivos ``.vbs``.
        Cada archivo encontrado genera un ``Resource``.

        Returns
        -------
        list[Resource]
            Lista de recursos descubiertos.
        """
        discovered: List[Resource] = []

        if not self._resources_dir.exists():
            return discovered

        for vbs_file in self._resources_dir.rglob("*.vbs"):
            if vbs_file.is_file():
                resource: Resource = Resource(
                    name=vbs_file.name,
                    path=vbs_file,
                    resource_type="vbs",
                )
                discovered.append(resource)

        return discovered

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------

    def _classify_resource(self, resource: Resource) -> None:
        """Clasifica un recurso comparando su hash con la metadata guardada.

        Parameters
        ----------
        resource : Resource
            Recurso a clasificar.
        """
        saved_metadata: Optional[dict] = self._load_metadata(resource)

        if saved_metadata is None:
            # No existe metadata previa → recurso nuevo
            resource.status = ResourceStatus.NEW
            return

        saved_hash: str = saved_metadata.get("hash", "")

        if saved_hash == resource.hash_sha256:
            resource.status = ResourceStatus.UNCHANGED
        else:
            resource.status = ResourceStatus.UPDATED

    # ------------------------------------------------------------------

    def _detect_deleted(self) -> None:
        """Detecta recursos cuya metadata existe pero el VBS fue eliminado.

        Recorre ``resources/`` buscando directorios con ``metadata.json``
        cuyo archivo ``.vbs`` asociado ya no existe.
        """
        if not self._resources_dir.exists():
            return

        for subdir in self._resources_dir.iterdir():
            if not subdir.is_dir():
                continue

            metadata_file: Path = subdir / "metadata.json"
            if not metadata_file.exists():
                continue

            # Buscar si hay un .vbs en este directorio
            vbs_files: list = list(subdir.glob("*.vbs"))
            if vbs_files:
                continue  # El VBS existe, ya fue procesado

            # El metadata existe pero no hay VBS → recurso eliminado
            try:
                saved: dict = json.loads(metadata_file.read_text("utf-8"))
                transaction: str = saved.get("transaction", subdir.name)
                resource_name: str = saved.get("resource", "")

                deleted_resource: Resource = Resource(
                    name=resource_name or f"{transaction}.vbs",
                    path=subdir / (resource_name or f"{transaction}.vbs"),
                    resource_type="vbs",
                )
                deleted_resource.status = ResourceStatus.DELETED
                deleted_resource.hash_sha256 = saved.get("hash", "")
                self._resources[transaction] = deleted_resource
            except (json.JSONDecodeError, OSError):
                pass

    # ------------------------------------------------------------------
    # Extracción de recursos
    # ------------------------------------------------------------------

    def _extract_resource(self, resource: Resource) -> None:
        """Ejecuta el ResourceExtractor y el WorkflowNormalizer.

        1. Extrae pasos del VBS → ``workflow.raw.json``
        2. Normaliza a lenguaje SAF → ``workflow.json``

        Parameters
        ----------
        resource : Resource
            Recurso a procesar.
        """
        # 1. Extraer
        extractor: ResourceExtractor = ResourceExtractor(resource)
        raw_path: Path = extractor.save_raw_workflow()

        transaction: str = resource.transaction
        self._extraction_stats[transaction] = {
            "total": extractor.recognized_count + extractor.ignored_count,
            "recognized": extractor.recognized_count,
            "ignored": extractor.ignored_count,
        }

        # 2. Normalizar a lenguaje SAF
        raw_wf: WorkflowRaw = WorkflowRaw.load(raw_path)
        normalizer: WorkflowNormalizer = WorkflowNormalizer()
        saf_wf: Any = normalizer.normalize(raw_wf)

        saf_path: Path = resource.workflow_path
        saf_wf.save(saf_path)
        self._normalized = True

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _load_metadata(self, resource: Resource) -> Optional[dict]:
        """Carga la metadata guardada de un recurso.

        Parameters
        ----------
        resource : Resource
            Recurso cuya metadata se desea cargar.

        Returns
        -------
        dict or None
            Metadata como diccionario, o ``None`` si no existe.
        """
        metadata_path: Path = resource.metadata_path
        if not metadata_path.exists():
            return None

        try:
            return json.loads(metadata_path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------

    def _save_metadata(self, resource: Resource) -> None:
        """Guarda (o actualiza) el archivo metadata.json del recurso.

        Solo guarda si el recurso no está eliminado.

        Parameters
        ----------
        resource : Resource
            Recurso cuya metadata se desea persistir.
        """
        if resource.status == ResourceStatus.DELETED:
            return

        metadata: dict = {
            "transaction": resource.transaction,
            "resource": resource.name,
            "hash": resource.hash_sha256,
            "last_modified": resource.last_modified.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "workflow_version": self._get_workflow_version(resource),
        }

        resource.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        resource.metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def _ensure_workflow(self, resource: Resource) -> None:
        """Asegura que exista un workflow.json para el recurso.

        Si el recurso es nuevo o fue actualizado, genera/regenera
        el workflow.json. Si no ha cambiado, lo deja intacto.

        Parameters
        ----------
        resource : Resource
            Recurso para el cual generar workflow.
        """
        if resource.status == ResourceStatus.DELETED:
            return

        workflow_path: Path = resource.workflow_path

        # Si el recurso no cambió y ya existe workflow, no hacer nada
        if resource.status == ResourceStatus.UNCHANGED and workflow_path.exists():
            return

        # Crear definición de workflow placeholder
        workflow: WorkflowDefinition = WorkflowDefinition(
            transaction=resource.transaction,
            source_file=resource.name,
        )

        # Si el recurso fue actualizado, marcar como necesita regeneración
        if resource.status == ResourceStatus.UPDATED:
            workflow.status = WorkflowStatus.NEEDS_REGENERATION
            # Intentar mantener el número de versión anterior
            workflow.version = self._get_workflow_version(resource) + 1

        # Guardar workflow.json
        data: dict = workflow.to_dict()
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------

    def _get_workflow_version(self, resource: Resource) -> int:
        """Obtiene la versión actual del workflow desde workflow.json.

        Parameters
        ----------
        resource : Resource
            Recurso del cual obtener la versión.

        Returns
        -------
        int
            Número de versión (1 si no existe).
        """
        workflow_path: Path = resource.workflow_path
        if not workflow_path.exists():
            return 1

        try:
            data: dict = json.loads(workflow_path.read_text("utf-8"))
            return int(data.get("version", 1))
        except (json.JSONDecodeError, OSError, ValueError):
            return 1

    # ------------------------------------------------------------------

    def get_workflow_status(self, resource: Resource) -> str:
        """Obtiene el estado legible del workflow de un recurso.

        Parameters
        ----------
        resource : Resource
            Recurso del cual consultar el estado.

        Returns
        -------
        str
            Estado del workflow (``"Normalizado"``, ``"Pendiente"``, etc.).
        """
        workflow_path: Path = resource.workflow_path
        if not workflow_path.exists():
            return "No generado"

        try:
            data: dict = json.loads(workflow_path.read_text("utf-8"))

            # Nuevo formato SAF (tiene "steps")
            if "steps" in data:
                return f"Normalizado ({len(data['steps'])} pasos)"

            # Formato antiguo (placeholder con "status")
            status: str = data.get("status", "")
            mapping: Dict[str, str] = {
                "pending_parser": "Pendiente",
                "ready": "Listo",
                "needs_regeneration": "Requiere regeneración",
            }
            return mapping.get(status, status)
        except (json.JSONDecodeError, OSError):
            return "Error"
