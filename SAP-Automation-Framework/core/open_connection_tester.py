"""OpenConnection Tester — descubre experimentalmente la llamada correcta.

Prueba automáticamente distintas variantes de ``Application.OpenConnection()``
para descubrir cuál funciona en esta instalación de SAP GUI.
Herramienta de diagnóstico independiente.
"""

from __future__ import annotations

import subprocess
import time
import traceback
from pathlib import Path
from typing import Any, List, Optional, Tuple


class OpenConnectionTester:
    """Prueba experimentalmente OpenConnection con distintos nombres.

    Parameters
    ----------
    sap_logon_path : str
        Ruta a saplogon.exe.
    sap_system : str
        Sistema SAP desde la configuración (ej. "PRD").
    """

    # ------------------------------------------------------------------
    def __init__(self, sap_logon_path: str, sap_system: str) -> None:
        self._sap_path: str = sap_logon_path
        self._config_system: str = sap_system
        self._application: Any = None

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Ejecuta todas las pruebas."""
        self._print_header()

        if not self._ensure_sap_logon():
            return

        if not self._connect_com():
            return

        # Construir candidatos
        candidates: List[str] = self._build_candidates()
        print(f"\nCandidatos a probar: {len(candidates)}")
        for i, c in enumerate(candidates):
            print(f"  [{i}] {c!r}")

        # Prueba 1: OpenConnection(name) — sin Sync
        print(f"\n{'='*54}")
        print("  Prueba: OpenConnection(nombre) — sin parámetro Sync")
        print(f"{'='*54}")
        winner: Optional[Tuple[str, str]] = self._try_candidates(
            candidates, use_sync=False
        )

        if winner is not None:
            self._inspect_connection(winner)
            return

        # Prueba 2: OpenConnection(name, True) — con Sync=True
        print(f"\n{'='*54}")
        print("  Prueba: OpenConnection(nombre, True) — Sync=True")
        print(f"{'='*54}")
        winner = self._try_candidates(candidates, use_sync=True)

        if winner is not None:
            self._inspect_connection(winner)
            return

        print("\n  [RESUMEN] Ningún candidato funcionó.")
        print("  Posibles causas:")
        print("    - SAP GUI Scripting no habilitado en opciones de SAP Logon")
        print("    - El nombre exacto del sistema no está en la lista de candidatos")
        print("    - Se requiere autenticación previa en SAP Logon")

    # ------------------------------------------------------------------
    def _build_candidates(self) -> List[str]:
        """Construye lista de nombres candidatos a probar."""
        candidates: List[str] = []

        # Del config (primero)
        if self._config_system:
            candidates.append(self._config_system)
            candidates.append(self._config_system.upper())

        # Conexión conocida (del diagnóstico anterior)
        known = [
            "SAP S4HANA - PRD - TranS4mar",
            "PS4",
            "PRD",
            "SAP S4HANA",
            "TranS4mar",
            "S4HANA",
            "PRD - TranS4mar",
        ]
        for k in known:
            if k not in candidates:
                candidates.append(k)

        return candidates

    # ------------------------------------------------------------------
    def _try_candidates(
        self, candidates: List[str], use_sync: bool
    ) -> Optional[Tuple[str, str]]:
        """Prueba cada candidato con OpenConnection.

        Parameters
        ----------
        candidates : list[str]
            Lista de nombres a probar.
        use_sync : bool
            Si es True, llama OpenConnection(name, True).

        Returns
        -------
        tuple or None
            (nombre, método_usado) si alguno funcionó.
        """
        for name in candidates:
            sync_str: str = "True" if use_sync else ""
            args_str: str = f'"{name}"' + (f", {sync_str}" if use_sync else "")
            print(f"\n  Probando: OpenConnection({args_str}) ... ", end="", flush=True)

            try:
                if use_sync:
                    self._application.OpenConnection(name, True)
                else:
                    self._application.OpenConnection(name)

                print("OK")
                print(f"  ✓ Conexión abierta correctamente")
                print(f"  Nombre utilizado: {name!r}")
                return (name, f"OpenConnection({args_str})")
            except Exception as exc:
                msg: str = str(exc).split("\n")[0][:100]
                print(f"ERROR")
                print(f"  Mensaje: {msg}")

        return None

    # ------------------------------------------------------------------
    def _inspect_connection(self, winner: Tuple[str, str]) -> None:
        """Inspecciona la conexión recién abierta y la cierra."""
        name, method = winner
        print(f"\n  Esperando 3 segundos para que SAP procese...")
        time.sleep(3)

        # Verificar Children.Count
        try:
            count = self._application.Children.Count
            print(f"\n  Application.Children.Count: {count}")
            if count == 0:
                print("  ⚠ No se detectó conexión activa pese al OK.")
                return
        except Exception:
            print("  ⚠ No se pudo leer Children.Count")
            return

        # Mostrar info de la sesión
        try:
            conn = self._application.Children(0)
            desc = conn.Description if hasattr(conn, "Description") else "?"
            print(f"  Description: {desc}")

            session = conn.Children(0)
            sinfo = session.Info
            print(f"  Session.Info.SystemName: {sinfo.SystemName}")
            print(f"  Session.Info.Client:     {sinfo.Client}")
            print(f"  Session.Info.User:       {sinfo.User}")
            print(f"  Session.Info.Transaction:{sinfo.Transaction}")
        except Exception as exc:
            print(f"  ⚠ Error al leer info de sesión: {exc}")

        # Cerrar conexión de prueba
        print(f"\n  Cerrando conexión de prueba...")
        try:
            conn = self._application.Children(0)
            conn.CloseConnection()
            print("  OK")
        except Exception:
            # Intentar con session.close
            try:
                session = self._application.Children(0).Children(0)
                session.findById("wnd[0]").Close()
                print("  OK (vía session)")
            except Exception as exc:
                print(f"  ⚠ No se pudo cerrar: {exc}")

    # ------------------------------------------------------------------
    def _ensure_sap_logon(self) -> bool:
        """Garantiza SAP Logon abierto."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq saplogon.exe"],
                capture_output=True, text=True, timeout=5,
            )
            running: bool = "saplogon.exe" in result.stdout.lower()
        except Exception:
            running = False

        if running:
            print("SAP Logon ya estaba abierto.\n")
            return True

        print("SAP Logon no estaba abierto.")
        if not Path(self._sap_path).exists():
            print(f"  ERROR: {self._sap_path}")
            return False

        print(f"  Iniciando {self._sap_path} ...")
        subprocess.Popen(
            [self._sap_path], shell=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        import pythoncom
        import win32com.client

        print("  Esperando COM ... ", end="", flush=True)
        for _ in range(120):
            time.sleep(0.5)
            try:
                pythoncom.CoInitialize()
                gui = win32com.client.GetObject("SAPGUI")
                _ = gui.GetScriptingEngine
                print("OK")
                return True
            except Exception:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        print("TIMEOUT")
        return False

    # ------------------------------------------------------------------
    def _connect_com(self) -> bool:
        """Conecta a SAP GUI COM."""
        import win32com.client

        try:
            sap_gui = win32com.client.GetObject("SAPGUI")
            self._application = sap_gui.GetScriptingEngine
            print(f"✓ Application obtenido\n")
            return True
        except Exception as exc:
            print(f"✗ Error COM: {exc}")
            return False

    # ------------------------------------------------------------------
    @staticmethod
    def _print_header() -> None:
        """Cabecera."""
        print()
        print("=" * 54)
        print("  OpenConnection Tester")
        print("  Descubriendo la llamada correcta...")
        print("=" * 54)
