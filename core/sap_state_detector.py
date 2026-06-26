"""SAP State Detector v2 — análisis jerárquico del estado SAP.

Detecta el estado actual de SAP GUI sin modificarlo, recorriendo
la jerarquía completa: Connection → Session → Window → Controls.

Cada ventana determina su propio estado. No se mezclan controles
entre sesiones. El estado global se determina por prioridad.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Estados de ventana / globales
# ---------------------------------------------------------------------------

class SAPState(Enum):
    """Estados posibles de una ventana SAP o del entorno global."""

    CLOSED = auto()
    LOGON = auto()
    LOGIN_SCREEN = auto()
    AUTHENTICATED = auto()
    FRAMEWORK_SESSION = auto()
    CONNECTING = auto()
    ERROR_POPUP = auto()
    UNKNOWN = auto()


# Prioridad: mayor valor = mayor prioridad para el estado global
_STATE_PRIORITY = {
    SAPState.ERROR_POPUP: 70,
    SAPState.LOGIN_SCREEN: 60,
    SAPState.CONNECTING: 50,
    SAPState.FRAMEWORK_SESSION: 40,
    SAPState.AUTHENTICATED: 30,
    SAPState.LOGON: 20,
    SAPState.CLOSED: 10,
    SAPState.UNKNOWN: 0,
}


# ---------------------------------------------------------------------------
# Modelos de análisis jerárquico
# ---------------------------------------------------------------------------

@dataclass
class WindowInfo:
    """Información de una ventana SAP y sus controles.

    Attributes
    ----------
    window_id : str
        Identificador (``"wnd[0]"``, ``"wnd[1]"``, etc.).
    state_detected : SAPState
        Estado detectado para esta ventana.
    controls : list[str]
        Nombres cortos de controles encontrados.
    title : str
        Título o texto de la ventana.
    """

    window_id: str = ""
    state_detected: SAPState = SAPState.UNKNOWN
    controls: List[str] = field(default_factory=list)
    title: str = ""


@dataclass
class SessionInfo:
    """Información de una sesión SAP.

    Attributes
    ----------
    session_id : str
        ID de sesión COM.
    transaction : str
        Transacción activa.
    system : str
        Nombre del sistema (SystemName).
    client : str
        Mandante.
    user : str
        Usuario autenticado.
    program : str
        Programa ABAP en ejecución.
    screen : int
        Dynpro actual.
    windows : list[WindowInfo]
        Ventanas de esta sesión.
    """

    session_id: str = ""
    transaction: str = ""
    system: str = ""
    client: str = ""
    user: str = ""
    program: str = ""
    screen: int = 0
    windows: List[WindowInfo] = field(default_factory=list)


@dataclass
class ConnectionInfo:
    """Información de una conexión SAP.

    Attributes
    ----------
    connection_id : str
        Identificador (índice).
    description : str
        Descripción de la conexión.
    sessions : list[SessionInfo]
        Sesiones de esta conexión.
    """

    connection_id: str = ""
    description: str = ""
    sessions: List[SessionInfo] = field(default_factory=list)


@dataclass
class SAPStateInfo:
    """Información completa del estado SAP detectado.

    Attributes
    ----------
    state : SAPState
        Estado global (mayor prioridad entre todas las ventanas).
    confidence : int
        Porcentaje de confianza.
    message : str
        Descripción legible.
    connection_id : str
        ID de la conexión principal.
    session_id : str
        ID de la sesión principal.
    window_id : str
        ID de la ventana principal.
    analysis : list[ConnectionInfo]
        Árbol completo del análisis jerárquico.
    """

    state: SAPState = SAPState.UNKNOWN
    confidence: int = 0
    message: str = ""
    connection_id: str = ""
    session_id: str = ""
    window_id: str = ""
    analysis: List[ConnectionInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Controles característicos por tipo de ventana
# ---------------------------------------------------------------------------

_LOGIN_CONTROLS: List[str] = [
    "wnd[0]/usr/txtRSYST-MANDT",
    "wnd[0]/usr/txtRSYST-BNAME",
    "wnd[0]/usr/pwdRSYST-BCODE",
]
_AUTH_CONTROLS: List[str] = [
    "wnd[0]/tbar[0]/okcd",
]
_ERROR_KEYWORDS: List[str] = [
    "Error", "error", "distribución", "carga",
    "Logon", "License", "Licencia",
]


# ---------------------------------------------------------------------------
# SAPStateDetector v2
# ---------------------------------------------------------------------------

class SAPStateDetector:
    """Detecta el estado SAP con análisis jerárquico.

    Recorre Connection → Session → Window → Controls sin mezclar
    información entre sesiones. Cada ventana determina su propio
    estado. El estado global es el de mayor prioridad.
    """

    # ------------------------------------------------------------------
    def __init__(self) -> None:
        self._sap_gui: Any = None
        self._application: Any = None

    # ------------------------------------------------------------------
    def detect(self) -> SAPStateInfo:
        """Ejecuta la detección jerárquica completa.

        Returns
        -------
        SAPStateInfo
            Informe completo del análisis.
        """
        # 1. ¿Proceso?
        if not self._is_process_running():
            return SAPStateInfo(
                state=SAPState.CLOSED,
                confidence=100,
                message="SAP Logon no está en ejecución.",
            )

        # 2. Conectar COM
        if not self._try_connect_com():
            return SAPStateInfo(
                state=SAPState.CLOSED,
                confidence=70,
                message="Proceso detectado pero COM no disponible.",
            )

        # 3. Análisis jerárquico
        analysis: List[ConnectionInfo] = self._analyze_hierarchy()

        if not analysis:
            return SAPStateInfo(
                state=SAPState.LOGON,
                confidence=95,
                message="SAP Logon abierto. Sin conexiones activas.",
                analysis=analysis,
            )

        # 4. Prioridad global
        return self._compute_global_state(analysis)

    # ------------------------------------------------------------------
    # Proceso
    # ------------------------------------------------------------------

    @staticmethod
    def _is_process_running() -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq saplogon.exe"],
                capture_output=True, text=True, timeout=5,
            )
            return "saplogon.exe" in result.stdout.lower()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # COM
    # ------------------------------------------------------------------

    def _try_connect_com(self) -> bool:
        import win32com.client
        try:
            self._sap_gui = win32com.client.GetObject("SAPGUI")
            self._application = self._sap_gui.GetScriptingEngine
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Análisis jerárquico: Connection → Session → Window → Controls
    # ------------------------------------------------------------------

    def _analyze_hierarchy(self) -> List[ConnectionInfo]:
        """Construye el árbol completo de análisis."""
        connections: List[ConnectionInfo] = []

        try:
            children = self._application.Children
            conn_count: int = children.Count if children else 0
        except Exception:
            return connections

        for ci in range(conn_count):
            try:
                conn_com = children(ci)
            except Exception:
                continue

            conn_info = ConnectionInfo(
                connection_id=str(ci),
            )
            try:
                conn_info.description = str(conn_com.Description or "")
            except Exception:
                pass

            # Sesiones
            try:
                sessions_com = conn_com.Children
                sess_count: int = sessions_com.Count if sessions_com else 0
            except Exception:
                sess_count = 0

            for si in range(sess_count):
                try:
                    sess_com = sessions_com(si)
                except Exception:
                    continue

                sess_info = self._analyze_session(sess_com, si)
                conn_info.sessions.append(sess_info)

            connections.append(conn_info)

        return connections

    # ------------------------------------------------------------------

    def _analyze_session(self, sess_com: Any, index: int) -> SessionInfo:
        """Analiza una sesión: metadatos + ventanas."""
        info = SessionInfo()

        try:
            info.session_id = str(sess_com.ID or str(index))
        except Exception:
            info.session_id = str(index)

        # Metadatos
        try:
            sinfo = sess_com.Info
            info.system = str(sinfo.SystemName or "")
            info.client = str(sinfo.Client or "")
            info.user = str(sinfo.User or "")
            info.transaction = str(sinfo.Transaction or "")
            info.program = str(sinfo.Program or "")
            try:
                info.screen = int(sinfo.ScreenNumber or 0)
            except (ValueError, TypeError):
                pass
        except Exception:
            pass

        # Ventanas (wnd[0], wnd[1], ...)
        for wi in range(5):
            try:
                sess_com.findById(f"wnd[{wi}]")
            except Exception:
                break  # No más ventanas

            win_info = self._analyze_window(sess_com, wi)
            info.windows.append(win_info)

        return info

    # ------------------------------------------------------------------

    def _analyze_window(self, sess_com: Any, index: int) -> WindowInfo:
        """Analiza una ventana: controles y estado."""
        win = WindowInfo(window_id=f"wnd[{index}]")

        prefix: str = f"wnd[{index}]/usr/"

        # Controles de login (solo en wnd[0])
        if index == 0:
            for ctrl in _LOGIN_CONTROLS:
                try:
                    sess_com.findById(ctrl)
                    name = ctrl.split("/")[-1]
                    win.controls.append(name)
                except Exception:
                    pass

            # Controles de autenticación
            for ctrl in _AUTH_CONTROLS:
                try:
                    sess_com.findById(ctrl)
                    name = ctrl.split("/")[-1]
                    win.controls.append(name)
                except Exception:
                    pass

        # Determinar estado de esta ventana
        win.state_detected = self._classify_window(win, sess_com, index)

        # Título
        try:
            wnd = sess_com.findById(f"wnd[{index}]")
            win.title = str(wnd.Text or "")[:80]
        except Exception:
            pass

        return win

    # ------------------------------------------------------------------
    # Clasificación por ventana
    # ------------------------------------------------------------------

    def _classify_window(
        self, win: WindowInfo, sess_com: Any, index: int
    ) -> SAPState:
        """Determina el estado de una ventana por sus controles."""
        ctrl_set: set = set(win.controls)

        # Login screen: tiene txtRSYST-BNAME (campo usuario)
        if "txtRSYST-BNAME" in ctrl_set:
            return SAPState.LOGIN_SCREEN

        # Error popup: wnd[1] con texto de error
        if index >= 1:
            try:
                text: str = str(win.title or "")
                for kw in _ERROR_KEYWORDS:
                    if kw.lower() in text.lower():
                        return SAPState.ERROR_POPUP
            except Exception:
                pass

        # Autenticado: tiene okcd
        if "okcd" in ctrl_set:
            return SAPState.AUTHENTICATED

        # Sin controles reconocidos: puede ser CONNECTING
        if not win.controls:
            return SAPState.CONNECTING

        return SAPState.UNKNOWN

    # ------------------------------------------------------------------
    # Estado global por prioridad
    # ------------------------------------------------------------------

    def _compute_global_state(
        self, analysis: List[ConnectionInfo]
    ) -> SAPStateInfo:
        """Calcula el estado global como el de mayor prioridad."""
        all_states: List[tuple[SAPState, WindowInfo]] = []

        for conn in analysis:
            for sess in conn.sessions:
                for win in sess.windows:
                    all_states.append((win.state_detected, win))

        if not all_states:
            return SAPStateInfo(
                state=SAPState.UNKNOWN,
                confidence=30,
                message="No se pudo determinar el estado de SAP.",
                analysis=analysis,
            )

        # Mayor prioridad
        best_state, best_win = max(
            all_states, key=lambda x: _STATE_PRIORITY.get(x[0], 0)
        )

        # Buscar la sesión y conexión dueña de esta ventana
        connection_id = ""
        session_id = ""
        for conn in analysis:
            for sess in conn.sessions:
                if best_win in sess.windows:
                    connection_id = conn.connection_id
                    session_id = sess.session_id
                    break

        return SAPStateInfo(
            state=best_state,
            confidence=100 if best_state != SAPState.UNKNOWN else 30,
            message=self._state_message(best_state),
            connection_id=connection_id,
            session_id=session_id,
            window_id=best_win.window_id,
            analysis=analysis,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _state_message(state: SAPState) -> str:
        """Mensaje descriptivo para cada estado."""
        messages = {
            SAPState.CLOSED: "SAP Logon cerrado.",
            SAPState.LOGON: "SAP Logon abierto sin conexiones.",
            SAPState.LOGIN_SCREEN: "Pantalla de autenticación detectada.",
            SAPState.AUTHENTICATED: "Usuario autenticado. SAP listo.",
            SAPState.FRAMEWORK_SESSION: "Framework tiene sesión activa.",
            SAPState.CONNECTING: "SAP conectando al sistema...",
            SAPState.ERROR_POPUP: "Popup de error detectado.",
            SAPState.UNKNOWN: "No se pudo determinar el estado.",
        }
        return messages.get(state, "Desconocido.")
