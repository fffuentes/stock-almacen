"""SAP Connection Explorer — herramienta de diagnóstico COM independiente.

Explora la estructura COM de SAP Logon ANTES de abrir conexiones,
descubriendo todas las propiedades, conexiones disponibles y métodos
de apertura. No modifica ningún componente del Framework.
"""

from __future__ import annotations

import traceback
import time
import subprocess
from pathlib import Path
from typing import Any, List, Optional


# Propiedades a intentar leer en cada conexión
_CONNECTION_PROPS: List[str] = [
    "Description",
    "Name",
    "Id",
    "SystemName",
    "System",
    "ApplicationServer",
    "MessageServer",
    "Group",
    "ConnectionString",
    "Disabled",
    "RouterString",
    "Client",
    "Language",
    "User",
    "SAPRouter",
    "SncName",
    "SncMode",
    "Type",
    "TypeName",
    "Children",
]

# Posibles métodos de apertura de conexión
_OPEN_METHODS: List[str] = [
    "OpenConnection",
    "OpenConnectionByConnectionString",
    "OpenConnection2",
    "OpenConnectionEx",
    "OpenConnectionByString",
    "Open",
]


class ConnectionExplorer:
    """Explora las conexiones SAP Logon visibles via COM.

    No abre sesiones. No ejecuta métodos. Solo lectura.
    """

    _SEP: str = "-" * 54

    # ------------------------------------------------------------------
    def __init__(self, sap_logon_path: str) -> None:
        self._sap_path: str = sap_logon_path
        self._sap_gui: Any = None
        self._application: Any = None

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Ejecuta la exploración completa."""
        self._print_header()

        # 1. Garantizar SAP Logon
        if not self._ensure_sap_logon():
            return

        # 2. Obtener objetos COM
        if not self._connect_com():
            return

        # 3. Explorar conexiones
        self._explore_connections()

        # 4. Explorar métodos
        self._explore_methods()

        # 5. Explorar colecciones adicionales
        self._explore_collections()

        print()

    # ------------------------------------------------------------------
    def _ensure_sap_logon(self) -> bool:
        """Garantiza que SAP Logon esté abierto (sin login)."""
        running: bool = False
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq saplogon.exe"],
                capture_output=True, text=True, timeout=5,
            )
            running = "saplogon.exe" in result.stdout.lower()
        except Exception:
            pass

        if running:
            print("SAP Logon ya estaba abierto.\n")
            return True

        print("SAP Logon no estaba abierto.")
        if not Path(self._sap_path).exists():
            print(f"  ERROR: No se encuentra: {self._sap_path}")
            return False

        print(f"  Iniciando {self._sap_path} ...")
        subprocess.Popen(
            [self._sap_path],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Esperar disponibilidad COM
        print("  Esperando disponibilidad COM ... ", end="", flush=True)
        import pythoncom
        import win32com.client

        for _ in range(120):  # 60 segundos
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
        """Conecta a SAP GUI via COM."""
        import win32com.client

        print(self._SEP)
        print("Paso 1: GetObject('SAPGUI')")
        print(self._SEP)
        try:
            self._sap_gui = win32com.client.GetObject("SAPGUI")
            print(f"  ✓ SapGuiAuto: {self._sap_gui!r}")
            print(f"  Tipo: {type(self._sap_gui).__name__}")
        except Exception as exc:
            print(f"  ✗ ERROR: {exc}")
            return False

        print(f"\n{self._SEP}")
        print("Paso 2: SapGuiAuto.GetScriptingEngine (PROPIEDAD)")
        print(self._SEP)
        try:
            self._application = self._sap_gui.GetScriptingEngine
            print(f"  ✓ Application: {self._application!r}")
            print(f"  Tipo: {type(self._application).__name__}")
            return True
        except Exception as exc:
            print(f"  ✗ ERROR: {exc}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    def _explore_connections(self) -> None:
        """Explora conexiones en Application.Children."""
        print(f"\n{self._SEP}")
        print("Paso 3: Application.Children (conexiones visibles)")
        print(self._SEP)

        try:
            children = self._application.Children
            count = children.Count if children else 0
            print(f"  Count: {count}")
        except Exception as exc:
            print(f"  ✗ Application.Children no disponible: {exc}")
            return

        for i in range(count):
            print(f"\n  {'-' * 46}")
            print(f"  Connection {i}")
            print(f"  {'-' * 46}")
            try:
                conn = children(i)
                print(f"  Tipo: {type(conn).__name__}")
                print(f"  repr: {conn!r}")
                # Leer todas las propiedades conocidas
                for prop in _CONNECTION_PROPS:
                    try:
                        value = getattr(conn, prop)
                        if prop == "Children":
                            try:
                                c = value.Count if value else 0
                                print(f"  Children.Count: {c}")
                            except Exception:
                                print(f"  Children: {value!r}")
                        else:
                            print(f"  {prop}: {value!r}")
                    except Exception:
                        print(f"  {prop}: No disponible")
            except Exception as exc:
                print(f"  ✗ Error: {exc}")
                traceback.print_exc()

    # ------------------------------------------------------------------
    def _explore_methods(self) -> None:
        """Lista métodos de apertura disponibles en SapGuiAuto."""
        print(f"\n{self._SEP}")
        print("Paso 4: Métodos de apertura (SapGuiAuto)")
        print(self._SEP)

        found: List[str] = []
        for method_name in _OPEN_METHODS:
            try:
                method = getattr(self._sap_gui, method_name, None)
                if method is not None:
                    print(f"  ✓ {method_name}: {type(method).__name__}")
                    found.append(method_name)
            except Exception:
                pass

        if not found:
            print("  Ninguno disponible en SapGuiAuto")

        # También en Application
        print(f"\n  Métodos en Application:")
        found_app: List[str] = []
        for method_name in _OPEN_METHODS:
            try:
                method = getattr(self._application, method_name, None)
                if method is not None:
                    print(f"  ✓ {method_name}: {type(method).__name__}")
                    found_app.append(method_name)
            except Exception:
                pass

        if not found_app:
            print("  Ninguno disponible en Application")

    # ------------------------------------------------------------------
    def _explore_collections(self) -> None:
        """Explora colecciones adicionales."""
        print(f"\n{self._SEP}")
        print("Paso 5: Colecciones adicionales")
        print(self._SEP)

        targets: List[tuple[str, Any]] = [
            ("SapGuiAuto", self._sap_gui),
            ("Application", self._application),
        ]

        for label, obj in targets:
            if obj is None:
                continue
            for coll_name in ["Connections", "Items", "Children"]:
                try:
                    coll = getattr(obj, coll_name, None)
                    if coll is not None:
                        c = coll.Count if hasattr(coll, "Count") else "?"
                        print(f"  {label}.{coll_name}: Count={c}")
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def _print_header(self) -> None:
        """Imprime cabecera del explorador."""
        print()
        print("=" * 54)
        print("  SAP Connection Explorer")
        print("  Diagnóstico COM — Solo lectura")
        print("=" * 54)
