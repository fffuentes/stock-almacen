"""Abstracción de una sesión SAP GUI.

Proporciona la clase `SAPSession` que encapsula una sesión SAP
real obtenida mediante SAP GUI Scripting (COM). Esta clase es la
ÚNICA vía de acceso a una sesión SAP desde el resto del Framework.

Nunca expone el objeto COM subyacente directamente.
"""

from __future__ import annotations

from typing import Any


class SAPSession:
    """Encapsula una sesión SAP GUI activa.

    Proporciona acceso de solo lectura a la información básica
    de la sesión (sistema, mandante, usuario, transacción, etc.)
    y permite cerrar únicamente esta sesión.

    El objeto COM subyacente es privado y nunca se expone
    al resto del Framework.

    Parameters
    ----------
    com_session : Any
        Objeto COM ``GuiSession`` obtenido mediante SAP GUI Scripting.
    """

    # ------------------------------------------------------------------
    def __init__(self, com_session: Any) -> None:
        """Inicializa la abstracción de sesión SAP.

        Parameters
        ----------
        com_session : Any
            Objeto COM de sesión SAP (``GuiSession``).
        """
        self._com_session: Any = com_session
        self._id: str = ""
        self._system: str = ""
        self._client: str = ""
        self._user: str = ""
        self._transaction: str = ""
        self._program: str = ""
        self._screen: int = 0

        self._load_info()

    # ------------------------------------------------------------------
    # Propiedades de solo lectura
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Identificador único de la sesión en SAP GUI.

        Ejemplo: ``/app/con[0]/ses[1]``
        """
        return self._id

    @property
    def system(self) -> str:
        """Sistema SAP al que pertenece la sesión (ej. ``'PS4'``)."""
        return self._system

    @property
    def client(self) -> str:
        """Mandante/cliente SAP (ej. ``'600'``)."""
        return self._client

    @property
    def user(self) -> str:
        """Usuario autenticado en la sesión."""
        return self._user

    @property
    def transaction(self) -> str:
        """Transacción activa en la sesión (ej. ``'SESSION_MANAGER'``)."""
        return self._transaction

    @property
    def program(self) -> str:
        """Programa ABAP en ejecución."""
        return self._program

    @property
    def screen(self) -> int:
        """Número de dynpro (pantalla) actual."""
        return self._screen

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def _get_com_session(self) -> Any:
        """Devuelve la referencia COM interna.

        Uso exclusivo del Execution Engine. No exponer fuera del core.

        Returns
        -------
        Any
            Objeto COM ``GuiSession``.
        """
        return self._com_session

    def close(self) -> bool:
        """Cierra esta sesión SAP.

        Solo cierra la sesión encapsulada por esta instancia.
        No afecta a ninguna otra sesión.

        Estrategia de cierre (en orden de intento):
        1. ``session.Close()`` — método directo de GuiSession.
        2. ``session.CloseSession()`` — nombre alternativo.
        3. ``session.findById("wnd[0]").Close()`` — cierre vía ventana
           principal (patrón usado frecuentemente en scripts SAP).

        Returns
        -------
        bool
            ``True`` si la sesión se cerró correctamente.
        """
        # Intento 1: Close() directo
        try:
            self._com_session.Close()
            return True
        except Exception:
            pass

        # Intento 2: CloseSession()
        try:
            self._com_session.CloseSession()
            return True
        except Exception:
            pass

        # Intento 3: Cerrar vía la ventana principal (patrón VBS)
        try:
            window = self._com_session.findById("wnd[0]")
            if window is not None:
                window.Close()
                return True
        except Exception:
            pass

        return False

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _load_info(self) -> None:
        """Carga la información de solo lectura desde ``session.Info``.

        Toda la información se obtiene mediante SAP GUI Scripting
        de forma consultiva. No modifica ningún estado.
        """
        # ID de sesión
        try:
            self._id = str(self._com_session.ID or "")
        except Exception:
            self._id = ""

        # Información de sesión (Info)
        try:
            sinfo: Any = self._com_session.Info
            if sinfo is not None:
                self._system = str(sinfo.SystemName or "")
                self._client = str(sinfo.Client or "")
                self._user = str(sinfo.User or "")
                self._transaction = str(sinfo.Transaction or "")
                self._program = str(sinfo.Program or "")
                try:
                    self._screen = int(sinfo.ScreenNumber or 0)
                except (ValueError, TypeError):
                    self._screen = 0
        except Exception:
            pass

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Representación textual de la sesión."""
        return (
            f"SAPSession(id={self._id!r}, system={self._system!r}, "
            f"client={self._client!r}, user={self._user!r}, "
            f"transaction={self._transaction!r})"
        )

    def __str__(self) -> str:
        """Descripción legible de la sesión."""
        parts: list[str] = [
            f"Sesión SAP: {self._id}",
            f"  Sistema:      {self._system}",
            f"  Mandante:     {self._client}",
            f"  Usuario:      {self._user}",
            f"  Transacción:  {self._transaction}",
            f"  Programa:     {self._program}",
            f"  Dynpro:       {self._screen}",
        ]
        return "\n".join(parts)
