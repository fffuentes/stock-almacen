"""SAP Recovery Engine — lleva SAP al estado AUTHENTICATED automáticamente.

Proporciona ``SAPRecoveryEngine`` que recibe el estado actual de SAP
(vía ``SAPStateDetector``) y decide qué acción tomar para alcanzar
el estado ``AUTHENTICATED``. Utiliza ``SAPConnector``, ``LoginManager``
y ``SAPWaiter`` como ejecutores, sin tomar decisiones por ellos.
"""

from __future__ import annotations

from typing import Optional

from config.config_manager import ConfigManager
from core.sap_state_detector import SAPState, SAPStateDetector


class SAPRecoveryEngine:
    """Lleva SAP al estado AUTHENTICATED automáticamente.

    Recibe el diagnóstico del ``SAPStateDetector`` y ejecuta las
    acciones necesarias para alcanzar un estado donde SAP esté
    listo para recibir comandos. Todos los componentes subyacentes
    (SAPConnector, LoginManager) son meros ejecutores — toda la
    inteligencia de recuperación reside aquí.

    Parameters
    ----------
    config_manager : ConfigManager
        Gestor de configuración del Framework.
    """

    MAX_CYCLES: int = 5

    # ------------------------------------------------------------------
    def __init__(self, config_manager: ConfigManager) -> None:
        """Inicializa el recovery engine.

        Parameters
        ----------
        config_manager : ConfigManager
            Instancia del gestor de configuración.
        """
        self._config: ConfigManager = config_manager
        self._detector: SAPStateDetector = SAPStateDetector()

    # ------------------------------------------------------------------
    def ensure_ready(self) -> None:
        """Garantiza que SAP esté en estado AUTHENTICATED o FRAMEWORK_SESSION.

        Ejecuta hasta ``MAX_CYCLES`` iteraciones de detección-acción.
        Después de cada acción, vuelve a detectar el estado.

        Raises
        ------
        RuntimeError
            Si no se alcanza el estado deseado tras los ciclos máximos,
            o si se encuentra un estado irrecuperable.
        """
        for cycle in range(1, self.MAX_CYCLES + 1):
            info = self._detector.detect()
            state: SAPState = info.state

            if state in (SAPState.AUTHENTICATED, SAPState.FRAMEWORK_SESSION):
                print(f"  SAP listo. (ciclo {cycle})")
                return

            print(f"\n  Estado detectado: {state.name}")
            print(f"  Ciclo {cycle}/{self.MAX_CYCLES}")

            success: bool = self._handle_state(state, info)

            if not success:
                # Estado terminal (error popup, unknown)
                raise RuntimeError(
                    f"No fue posible recuperar automáticamente el estado "
                    f"de SAP. Estado final: {state.name}"
                )

        raise RuntimeError(
            f"No fue posible recuperar automáticamente el estado de SAP "
            f"tras {self.MAX_CYCLES} intentos."
        )

    # ------------------------------------------------------------------
    def _handle_state(self, state: SAPState, info) -> bool:
        """Ejecuta la acción correspondiente a cada estado.

        Returns
        -------
        bool
            ``False`` si el estado es terminal (no recuperable).
        """
        if state == SAPState.CLOSED:
            print("  Acción: Abriendo SAP Logon...")
            self._open_sap_logon()
            return True

        elif state == SAPState.LOGON:
            print("  Acción: Abriendo conexión...")
            self._open_connection()
            return True

        elif state == SAPState.LOGIN_SCREEN:
            print("  Acción: Realizando Login...")
            self._perform_login()
            return True

        elif state == SAPState.CONNECTING:
            print("  Acción: Esperando conexión...")
            self._wait_connecting()
            return True

        elif state == SAPState.ERROR_POPUP:
            print(f"  ⚠ Popup de error detectado.")
            print(f"  Mensaje: {info.message}")
            print("  (La recuperación de popups no está implementada aún.)")
            return False

        elif state == SAPState.UNKNOWN:
            print("  ⚠ No fue posible determinar el estado actual de SAP.")
            return False

        # AUTHENTICATED y FRAMEWORK_SESSION ya se manejan en ensure_ready()
        return True

    # ------------------------------------------------------------------
    # Acciones específicas
    # ------------------------------------------------------------------

    def _open_sap_logon(self) -> None:
        """Abre SAP Logon si está cerrado."""
        from core.sap_connector import SAPConnector
        connector = SAPConnector(self._config)
        connector.ensure_running()

    # ------------------------------------------------------------------

    def _open_connection(self) -> None:
        """Abre la conexión SAP configurada.

        Si falla por un error de conectividad, intenta cerrar el
        diálogo nativo de error y lanza ``ConnectionUnavailableError``.
        """
        import win32com.client

        connection_name: str = self._config.config.sap_connection
        if not connection_name:
            raise RuntimeError(
                "No hay conexión SAP configurada. "
                "Ejecute: python main.py configure"
            )

        print(f"  Intentando abrir conexión: {connection_name} ... ",
              end="", flush=True)

        try:
            sap_gui = win32com.client.GetObject("SAPGUI")
            application = sap_gui.GetScriptingEngine
            application.OpenConnection(connection_name)
            print("OK")
        except Exception as exc:
            print("ERROR")
            # Intentar cerrar diálogo nativo de error de conexión
            self._try_close_native_error_dialog()

            # Si se cerró el diálogo, la causa es falta de conectividad
            from core.exceptions import ConnectionUnavailableError
            raise ConnectionUnavailableError(
                f"No fue posible establecer conexión con SAP.\n"
                f"Conexión: {connection_name}\n"
                f"El diálogo de error fue cerrado automáticamente.\n"
                f"Workflow cancelado. Estado final: CONNECTION_UNAVAILABLE"
            ) from exc

    # ------------------------------------------------------------------

    def _try_close_native_error_dialog(self) -> None:
        """Intenta cerrar el diálogo nativo de error de conexión."""
        print("  Buscando diálogo nativo de error...")
        from core.native_dialog_manager import NativeDialogManager
        mgr = NativeDialogManager()
        result = mgr.close_connection_error()

        if result.handled:
            print("  Diálogo encontrado y cerrado automáticamente.")
            print("  Conexión no disponible.")
        elif result.found:
            print("  Diálogo encontrado pero no se pudo cerrar.")
        else:
            print("  No se detectó diálogo nativo de error.")

    # ------------------------------------------------------------------

    def _perform_login(self) -> None:
        """Ejecuta el login en la pantalla de autenticación."""
        from core.login_manager import LoginManager
        login = LoginManager(self._config)
        login.login()

    # ------------------------------------------------------------------

    def _wait_connecting(self) -> None:
        """Espera mientras SAP se conecta."""
        import time
        import win32com.client

        try:
            sap_gui = win32com.client.GetObject("SAPGUI")
            application = sap_gui.GetScriptingEngine

            # Intentar obtener una sesión y usar SAPWaiter
            conn = application.Children(0)
            session = conn.Children(0)
            from core.sap_waiter import SAPWaiter
            waiter = SAPWaiter(session)
            waiter.wait_not_busy(timeout=30.0)
        except Exception:
            # Si no hay sesión, esperar con sleep corto
            time.sleep(3)
