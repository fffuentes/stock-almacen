"""Motor de ejecución del SAP Automation Framework.

Proporciona la clase `ExecutionEngine` que ejecuta un
``Workflow`` (lenguaje SAF) sobre una sesión SAP real.

Utiliza el ``ActionRegistry`` para resolver cada acción
a su Handler correspondiente. No conoce clases concretas.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from core.workflow import Workflow, WorkflowStep
from core.action_registry import ActionRegistry
from core.session_manager import SessionManager
from core.sap_session import SAPSession


class ExecutionEngine:
    """Ejecuta workflows SAF sobre sesiones SAP reales.

    Flujo:
    1. Crea una sesión SAP mediante ``SessionManager``.
    2. Recorre los pasos del ``Workflow``.
    3. Para cada paso, consulta el ``ActionRegistry``.
    4. Ejecuta el handler correspondiente.
    5. Si hay error, cierra la sesión y reporta.
    6. Al finalizar, cierra la sesión del Framework.

    Parameters
    ----------
    session_manager : SessionManager
        Administrador de sesiones SAP.
    """

    # ------------------------------------------------------------------
    def __init__(self, session_manager: SessionManager) -> None:
        """Inicializa el motor de ejecución.

        Parameters
        ----------
        session_manager : SessionManager
            Instancia del administrador de sesiones.
        """
        self._session_manager: SessionManager = session_manager
        self._session: Optional[SAPSession] = None

        # Cargar todos los handlers (importa los módulos de acciones)
        self._ensure_actions_loaded()

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def run(self, workflow: Workflow) -> bool:
        """Ejecuta un workflow completo sobre SAP.

        Parameters
        ----------
        workflow : Workflow
            Workflow SAF a ejecutar.

        Returns
        -------
        bool
            ``True`` si el workflow se ejecutó completamente.
        """
        total: int = len(workflow.steps)

        try:
            # 1. Crear sesión del Framework
            print("Abriendo sesión Framework...")
            self._session = self._session_manager.create_session()
            com = self._session._get_com_session()
            print("OK\n")

            # 2. Ejecutar cada paso
            print(f"Ejecutando workflow: {workflow.transaction}")
            print(f"Pasos: {total}\n")

            for step in workflow.steps:
                self._execute_step(step, com, total)

            print("\nWorkflow finalizado exitosamente.")
            return True

        except Exception as exc:
            print(f"\n[ERROR] {exc}")
            return False

        finally:
            # 3. Cerrar sesión del Framework
            if self._session is not None:
                print("\nCerrando sesión Framework...")
                self._session_manager.close_framework_session()
                print("OK")

    # ------------------------------------------------------------------
    # Ejecución de un paso individual
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        step: WorkflowStep,
        com: Any,
        total: int,
    ) -> None:
        """Ejecuta un paso individual del workflow.

        Parameters
        ----------
        step : WorkflowStep
            Paso a ejecutar.
        com : Any
            Referencia COM de la sesión SAP.
        total : int
            Total de pasos del workflow.

        Raises
        ------
        RuntimeError
            Si no hay handler para la acción.
        Exception
            Si el handler falla.
        """
        action: str = step.action
        print(f"Step {step.step}/{total}  {action} ... ", end="", flush=True)

        # Resolver handler
        handler_cls = ActionRegistry.get(action)
        if handler_cls is None:
            print(f"✗ (sin handler)")
            raise RuntimeError(
                f"No hay handler registrado para la acción: {action}"
            )

        # Ejecutar
        handler = handler_cls()
        handler.execute(step, com)

        # Pequeña pausa para que SAP procese
        time.sleep(0.3)

        print("OK")

    # ------------------------------------------------------------------
    # Carga de acciones
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_actions_loaded() -> None:
        """Asegura que todos los módulos de acciones estén importados.

        La importación de cada módulo ejecuta el decorador
        ``@ActionRegistry.register``, registrando el handler.
        """
        import actions.start_transaction  # noqa: F401
        import actions.confirm  # noqa: F401
        import actions.execute  # noqa: F401
        import actions.set_field  # noqa: F401
        import actions.press_button  # noqa: F401
        import actions.select_menu  # noqa: F401
        import actions.send_vkey  # noqa: F401
        import actions.export_file  # noqa: F401
