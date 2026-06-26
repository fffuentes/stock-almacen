"""Punto de entrada principal del SAP Automation Framework (SAF).

Uso::

    python main.py                  # Ejecución normal (requiere configuración previa)
    python main.py configure        # Asistente de configuración interactivo
    python main.py config           # Mostrar configuración actual
    python main.py test             # Diagnóstico del entorno SAP
    python main.py test --verbose   # Diagnóstico detallado (exploración COM)
    python main.py session          # Prueba del administrador de sesiones
    python main.py resources        # Escaneo de recursos del Framework
    python main.py run MB52         # Ejecutar workflow SAF sobre SAP
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from core.framework import Framework
from core.sap_diagnostics import SAPDiagnostics
from core.sap_debug import SAPDebug
from core.session_manager import SessionManager
from core.resource_manager import ResourceManager
from core.resource import ResourceStatus
from core.workflow import Workflow
from core.execution_engine import ExecutionEngine
from config.config_wizard import ConfigWizard


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_BASE_DIR: Path = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Funciones de entrada
# ---------------------------------------------------------------------------

def _run_configure(framework: Framework) -> None:
    """Ejecuta el asistente de configuración interactivo.

    Parameters
    ----------
    framework : Framework
        Instancia del framework para acceder al gestor de configuración.
    """
    wizard = ConfigWizard(framework.config_manager)
    wizard.run()


def _run_show_config(framework: Framework) -> None:
    """Muestra la configuración actual del Framework.

    Lee la configuración desde ``ConfigManager`` sin modificarla.

    Parameters
    ----------
    framework : Framework
        Instancia del framework.
    """
    if not framework.config_manager.exists():
        print("\n[!] No hay configuración.")
        print("Ejecute: python main.py configure")
        return

    framework.config_manager.load()
    print(framework.config_manager.get_summary())


def _run_test(framework: Framework, verbose: bool = False) -> None:
    if verbose:
        debug = SAPDebug(framework.config_manager)
        debug.run()
    else:
        diagnostics = SAPDiagnostics(framework.config_manager)
        diagnostics.run()


def _run_session(framework: Framework) -> None:
    """Ejecuta la prueba del administrador de sesiones.

    Crea una nueva sesión SAP para el Framework, muestra su
    información y la cierra tras 5 segundos. No modifica
    ninguna sesión del usuario.

    Parameters
    ----------
    framework : Framework
        Instancia del framework para acceder al gestor de configuración.
    """
    manager = SessionManager(framework.config_manager)

    # 1. Mostrar conexiones
    try:
        conn_count: int = manager.get_connection_count()
    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}")
        return

    if conn_count == 0:
        print("\n[!] No se encontraron conexiones SAP activas.")
        return

    print("Conexión encontrada")

    # 2. Mostrar sesiones existentes
    existing: int = manager.get_session_count()
    print(f"Sesiones existentes: {existing}")

    # 3. Crear nueva sesión
    print("\nCreando nueva sesión...")
    try:
        session = manager.create_session()
    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}")
        return

    print("Nueva sesión creada correctamente")
    print(f"ID: {session.id}")

    # 4. Mostrar información de la nueva sesión
    print("\n----------------------------------------")
    print("Información de la nueva sesión")
    print(f"Sistema:      {session.system}")
    print(f"Mandante:     {session.client}")
    print(f"Usuario:      {session.user}")
    print(f"Transacción:  {session.transaction}")
    print("----------------------------------------")

    # 5. Esperar 5 segundos
    print("\nEsperando 5 segundos...")
    time.sleep(5)

    # 6. Cerrar sesión del Framework
    print("\nCerrando sesión creada por el Framework...")
    closed: bool = manager.close_framework_session()
    if closed:
        print("Sesión cerrada correctamente.")
    else:
        print("[!] No se pudo cerrar la sesión.")

    # 7. Mostrar sesiones restantes
    remaining: int = manager.get_session_count()
    print(f"\nSesiones restantes: {remaining}")

    manager._release_com()


def _run_resources(framework: Framework) -> None:
    """Escanea y muestra el estado de los recursos del Framework.

    Descubre todos los archivos VBS en ``resources/``, calcula
    sus hashes SHA256, los compara con la metadata guardada,
    extrae los pasos del VBS y muestra estadísticas.

    Parameters
    ----------
    framework : Framework
        Instancia del framework para acceder al directorio base.
    """
    manager = ResourceManager(framework.base_dir)
    resources = manager.scan()

    if not resources:
        print("\n[!] No se encontraron recursos en resources/")
        return

    print("\n----------------------------------------")
    print("  Recursos encontrados")
    print("----------------------------------------")

    for transaction, resource in sorted(resources.items()):
        print(f"\n{transaction}")
        print(f"  Estado:    {resource.status.value}")
        print(f"  Hash:      {resource.hash_sha256[:16]}...")
        print(f"  Modificado:{resource.last_modified.strftime('%Y-%m-%d %H:%M:%S')}")

        wf_status: str = manager.get_workflow_status(resource)
        print(f"  Workflow:  {wf_status}")

        # Mostrar estadísticas de extracción si el recurso fue procesado
        stats = manager.extraction_stats.get(transaction)
        if stats:
            print(f"  Workflow RAW generado")
            print(f"  Instrucciones leídas:  {stats['total']}")
            print(f"  Acciones reconocidas:  {stats['recognized']}")
            print(f"  Acciones ignoradas:    {stats['ignored']}")
            status_label: str = "OK" if stats["ignored"] == 0 else "OK (con ignoradas)"
            print(f"  Estado:                {status_label}")

            if manager.normalized:
                print(f"  Workflow SAF generado")
                print(f"  Normalización completada")

    print("\n----------------------------------------")


def _run_workflow(framework: Framework, transaction: str) -> None:
    """Ejecuta un workflow SAF sobre SAP.

    Carga el workflow.json de la transacción, crea una sesión
    del Framework y ejecuta cada paso mediante el Execution Engine.

    Parameters
    ----------
    framework : Framework
        Instancia del framework.
    transaction : str
        Código de transacción a ejecutar (ej. ``"MB52"``).
    """
    workflow_path: Path = (
        framework.base_dir / "resources" / transaction / "workflow.json"
    )

    # Verificar configuración
    print("Verificando configuración...", end=" ")
    if not framework.config_manager.exists():
        print("ERROR")
        print("[!] No hay configuración. Ejecute: python main.py configure")
        return
    # Cargar configuración explícitamente
    try:
        _ = framework.config_manager.load()
    except Exception as exc:
        print(f"ERROR\n[!] {exc}")
        return
    print("OK\n")

    # Cargar workflow
    print(f"Cargando workflow...\n  {workflow_path}")
    if not workflow_path.exists():
        print(f"\n[ERROR] No se encontró workflow.json para {transaction}")
        print("Ejecute primero: python main.py resources")
        return
    try:
        workflow: Workflow = Workflow.load(workflow_path)
    except Exception as exc:
        print(f"\n[ERROR] No se pudo cargar workflow.json: {exc}")
        return
    print(f"OK  ({len(workflow.steps)} pasos)\n")

    # Ejecutar
    session_mgr: SessionManager = SessionManager(framework.config_manager)
    engine: ExecutionEngine = ExecutionEngine(session_mgr)
    engine.run(workflow)
    session_mgr._release_com()


def _run_connections(framework: Framework) -> None:
    """Explora las conexiones SAP Logon visibles via COM.

    Herramienta de diagnóstico independiente. No modifica
    ningún componente del Framework.
    """
    from core.connection_explorer import ConnectionExplorer

    if not framework.config_manager.exists():
        print("\n[!] No hay configuración.")
        return
    framework.config_manager.load()

    explorer = ConnectionExplorer(
        sap_logon_path=framework.config_manager.config.sap_logon_path
    )
    explorer.run()


def _run_login_test(framework: Framework) -> None:
    """Prueba experimentalmente OpenConnection con distintos nombres.

    Herramienta de diagnóstico independiente.
    """
    from core.open_connection_tester import OpenConnectionTester

    if not framework.config_manager.exists():
        print("\n[!] No hay configuración.")
        return
    framework.config_manager.load()

    tester = OpenConnectionTester(
        sap_logon_path=framework.config_manager.config.sap_logon_path,
        sap_system=framework.config_manager.config.sap_system,
    )
    tester.run()


def _run_default(framework: Framework) -> None:
    """Ejecuta el flujo por defecto del framework.

    Si no existe configuración previa, inicia automáticamente
    el asistente de configuración.

    Parameters
    ----------
    framework : Framework
        Instancia del framework a ejecutar.
    """
    if not framework.config_manager.exists():
        print("\n[!] No se encontró configuración previa.")
        print("[!] Iniciando asistente de configuración...")
        _run_configure(framework)

    framework.run()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    """Función principal de entrada al framework.

    Interpreta los argumentos de línea de comandos y dirige el flujo
    hacia la acción correspondiente.
    """
    framework: Framework = Framework(base_dir=_BASE_DIR)

    args: list[str] = sys.argv[1:]

    if len(args) == 0:
        _run_default(framework)
    elif len(args) == 1 and args[0] == "configure":
        _run_configure(framework)
    elif len(args) == 1 and args[0] == "config":
        _run_show_config(framework)
    elif len(args) >= 1 and args[0] == "test":
        verbose: bool = "--verbose" in args or "-v" in args
        _run_test(framework, verbose=verbose)
    elif len(args) == 1 and args[0] == "session":
        _run_session(framework)
    elif len(args) == 1 and args[0] == "resources":
        _run_resources(framework)
    elif len(args) == 2 and args[0] == "run":
        _run_workflow(framework, args[1].upper())
    elif len(args) == 1 and args[0] == "connections":
        _run_connections(framework)
    elif len(args) == 1 and args[0] == "login-test":
        _run_login_test(framework)
    else:
        print(f"Uso: python main.py [configure|config|test|session|resources|run <tx>|connections]")
        print(f"Argumento no reconocido: {' '.join(args)}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
