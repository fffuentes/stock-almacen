"""Native Dialog Manager — gestiona diálogos nativos de Windows en SAP.

Proporciona ``NativeDialogManager`` que detecta y cierra el diálogo
de error de conexión nativo de SAP Logon (clase ``#32770``, proceso
``saplogon.exe``). Utiliza exclusivamente Win32 API via pywin32.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class NativeDialogResult:
    """Resultado de la operación sobre un diálogo nativo.

    Attributes
    ----------
    found : bool
        Si se encontró el diálogo.
    handled : bool
        Si se manejó correctamente (cerrado, etc.).
    window_title : str
        Título de la ventana encontrada.
    message : str
        Texto del mensaje en el diálogo.
    button_pressed : str
        Texto del botón presionado.
    process : str
        Nombre del proceso dueño.
    class_name : str
        Clase de la ventana.
    """

    found: bool = False
    handled: bool = False
    window_title: str = ""
    message: str = ""
    button_pressed: str = ""
    process: str = ""
    class_name: str = ""


class NativeDialogManager:
    """Administra diálogos nativos de Windows en procesos SAP.

    Detecta y cierra diálogos de error de conexión (clase ``#32770``,
    proceso ``saplogon.exe``) utilizando Win32 API. No utiliza mouse
    ni coordenadas — solo IDs de control y mensajes de Windows.
    """

    # Textos de error de conexión SAP
    _CONNECTION_ERROR_TEXTS: list[str] = [
        "No se puede establecer conexión",
        "Error de distribución de carga",
        "rc=",
        "no fue posible establecer conexión",
        "cannot connect to",
        "could not connect",
        "connection attempt failed",
    ]

    # Títulos de diálogos de error de conexión
    _ERROR_TITLES: list[str] = [
        "SAP GUI for Windows",
    ]

    # ------------------------------------------------------------------
    def find_connection_error(self) -> NativeDialogResult:
        """Busca el diálogo de error de conexión de SAP Logon.

        Returns
        -------
        NativeDialogResult
            Resultado con los datos del diálogo encontrado.
        """
        import win32gui
        import win32process

        result = NativeDialogResult()

        def _callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True

            class_name: str = win32gui.GetClassName(hwnd)
            if class_name != "#32770":
                return True

            title: str = win32gui.GetWindowText(hwnd)
            # Solo diálogos de error (no ventana principal de SAP Logon)
            is_error_title = any(
                et in title for et in self._ERROR_TITLES
            )
            if not is_error_title:
                return True

            # Verificar proceso
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                import win32api
                handle = win32api.OpenProcess(0x0400, False, pid)
                proc_name = win32process.GetModuleFileNameEx(
                    handle, 0
                ).split("\\")[-1].lower()
                win32api.CloseHandle(handle)
            except Exception:
                proc_name = ""

            if "saplogon" not in proc_name:
                return True

            # Verificar texto del diálogo
            message: str = self._get_dialog_text(hwnd)
            if not self._is_connection_error(message, title):
                return True

            result.found = True
            result.window_title = title
            result.message = message
            result.process = proc_name
            result.class_name = class_name
            return False  # Encontrado, detener enumeración

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    def close_connection_error(self) -> NativeDialogResult:
        """Cierra el diálogo de error de conexión presionando el botón "No".

        Flujo:
        1. Buscar el diálogo.
        2. Encontrar botón ID=2 (No).
        3. Enviar click via ``SendMessage`` (sin mouse).
        4. Esperar 300 ms.
        5. Verificar que desapareció.

        Returns
        -------
        NativeDialogResult
            Resultado de la operación.
        """
        result: NativeDialogResult = self.find_connection_error()

        if not result.found:
            return result

        import win32gui
        import win32con

        # Encontrar hwnd del diálogo
        dlg_hwnd = self._find_dialog_hwnd()
        if dlg_hwnd is None:
            return result

        # Encontrar botón ID=2 (No)
        btn_hwnd = self._find_button_by_id(dlg_hwnd, 2)
        if btn_hwnd is None:
            # Intentar con ID=1 (Sí) como fallback
            btn_hwnd = self._find_button_by_id(dlg_hwnd, 1)

        if btn_hwnd is None:
            return result

        # Obtener texto del botón
        btn_text: str = win32gui.GetWindowText(btn_hwnd)

        # Enviar click via BM_CLICK
        win32gui.SendMessage(btn_hwnd, win32con.BM_CLICK, 0, 0)

        # Esperar
        time.sleep(0.3)

        # Verificar que desapareció
        still_visible: bool = False
        try:
            still_visible = win32gui.IsWindowVisible(dlg_hwnd)
        except Exception:
            pass

        result.handled = not still_visible
        result.button_pressed = btn_text or f"ID=2 ({btn_text})"
        return result

    # ------------------------------------------------------------------
    # Utilidades privadas
    # ------------------------------------------------------------------

    @staticmethod
    def _get_dialog_text(hwnd: int) -> str:
        """Extrae el texto principal de un diálogo nativo."""
        import win32gui

        texts: list[str] = []

        def _callback(child_hwnd: int, _: Any) -> bool:
            try:
                cls = win32gui.GetClassName(child_hwnd)
                if cls in ("Static", "Edit"):
                    text = win32gui.GetWindowText(child_hwnd)
                    if text.strip():
                        texts.append(text.strip())
                elif cls == "Button":
                    text = win32gui.GetWindowText(child_hwnd)
                    if text.strip():
                        texts.append(f"[Button: {text}]")
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(hwnd, _callback, None)
        except Exception:
            pass

        return " | ".join(texts)

    # ------------------------------------------------------------------

    @staticmethod
    def _is_connection_error(text: str, title: str) -> bool:
        """Verifica si el texto corresponde a un error de conexión."""
        combined: str = (title + " " + text).lower()
        for pattern in NativeDialogManager._CONNECTION_ERROR_TEXTS:
            if pattern.lower() in combined:
                return True
        return False

    # ------------------------------------------------------------------

    @staticmethod
    def _find_dialog_hwnd() -> Optional[int]:
        """Encuentra el HWND del diálogo de error de conexión."""
        import win32gui
        import win32process

        result: Optional[int] = None

        def _callback(hwnd: int, _: Any) -> bool:
            nonlocal result
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetClassName(hwnd) != "#32770":
                return True

            title = win32gui.GetWindowText(hwnd)
            if "SAP" not in title:
                return True

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                import win32api
                h = win32api.OpenProcess(0x0400, False, pid)
                pname = win32process.GetModuleFileNameEx(h, 0).split("\\")[-1].lower()
                win32api.CloseHandle(h)
            except Exception:
                pname = ""

            if "saplogon" in pname:
                result = hwnd
                return False  # Detener
            return True

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------

    @staticmethod
    def _find_button_by_id(parent_hwnd: int, target_id: int) -> Optional[int]:
        """Encuentra un botón por su Control ID."""
        import win32gui

        result: Optional[int] = None

        def _callback(hwnd: int, _: Any) -> bool:
            nonlocal result
            try:
                cid = win32gui.GetDlgCtrlID(hwnd)
                if cid == target_id:
                    cls = win32gui.GetClassName(hwnd)
                    if cls == "Button":
                        result = hwnd
                        return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(parent_hwnd, _callback, None)
        except Exception:
            pass

        return result
