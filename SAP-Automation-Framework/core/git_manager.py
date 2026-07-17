"""GitManager — Publicación automática de cambios en repositorio Git.

Módulo encargado de validar, commitear y publicar automáticamente
los cambios del repositorio Git una vez que el Framework haya
exportado y copiado correctamente los archivos generados.

.. warning::

    Este módulo **no** modifica el proceso de exportación ni la copia
    del archivo TXT. Únicamente se ejecuta **después** de que ambos
    procesos hayan finalizado correctamente.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


class GitManager:
    """Gestiona la publicación automática de cambios en un repositorio Git.

    Flujo típico::

        manager = GitManager(repo_path)
        manager.publish()

    Si no existen cambios pendientes, finaliza sin realizar acciones.
    Si existen, ejecuta ``git add web/data/MB52.txt``,
    ``git commit -m "..."`` y ``git push origin main``.

    Parameters
    ----------
    repo_path : str | Path
        Ruta absoluta a la carpeta raíz del repositorio Git.
    """

    # Constantes ---------------------------------------------------------
    MSG_NO_CHANGES: str = "No existen cambios para publicar."
    MSG_PUBLISH_OK: str = "Repositorio actualizado correctamente."
    MSG_UNPUSHED_PUBLISHED: str = "Commit(s) pendientes publicados correctamente."

    # Ruta relativa del archivo a publicar (respecto a la raíz del repo)
    _PUBLISH_FILE: str = "web/data/MB52.txt"

    # Rama y remoto de publicación
    _REMOTE: str = "origin"
    _BRANCH: str = "main"

    # ------------------------------------------------------------------
    def __init__(self, repo_path: str | Path) -> None:
        """Inicializa el gestor de publicación Git.

        Parameters
        ----------
        repo_path : str | Path
            Ruta a la carpeta raíz del repositorio.
        """
        self._repo_path: Path = Path(repo_path).resolve()

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def validate_repository(self) -> None:
        """Valida que la ruta configurada sea un repositorio Git.

        Comprueba que:

        - La ruta exista en disco.
        - Contenga una carpeta ``.git``.

        Raises
        ------
        FileNotFoundError
            Si la ruta no existe en disco.
        NotADirectoryError
            Si la ruta existe pero no contiene la carpeta ``.git``.
        """
        repo: Path = self._repo_path

        if not repo.exists():
            raise FileNotFoundError(
                f"La ruta del repositorio no existe: {repo}\n"
                f"Verifique la configuración con: python main.py configure"
            )

        git_dir: Path = repo / ".git"
        if not git_dir.exists() or not git_dir.is_dir():
            raise NotADirectoryError(
                f"La ruta no es un repositorio Git (falta .git): {repo}\n"
                f"Verifique la ruta configurada."
            )

    # ------------------------------------------------------------------
    def has_changes(self) -> bool:
        """Determina si existen cambios pendientes en el repositorio.

        Ejecuta ``git status --porcelain`` y retorna ``True`` si la
        salida no está vacía.

        Returns
        -------
        bool
            ``True`` si hay archivos modificados, añadidos o eliminados.
        """
        output: str = self._run_git(["status", "--porcelain"])
        return bool(output.strip())

    # ------------------------------------------------------------------
    def commit(self, message: str) -> None:
        """Realiza ``git add`` del archivo publicado y ``git commit``.

        Agrega **únicamente** el archivo ``web/data/MB52.txt`` para
        evitar que cambios no relacionados del desarrollador se cuelen
        en el commit automático.

        Parameters
        ----------
        message : str
            Mensaje de commit a utilizar.
        """
        # Verificar que el archivo a publicar exista
        publish_file: Path = self._repo_path / self._PUBLISH_FILE
        if not publish_file.exists():
            raise FileNotFoundError(
                f"El archivo a publicar no existe: {publish_file}"
            )

        # git add <archivo específico>
        print(f"  git add {self._PUBLISH_FILE} ... ", end="", flush=True)
        self._run_git(["add", self._PUBLISH_FILE])
        print("OK")

        # git commit
        print("  git commit ... ", end="", flush=True)
        self._run_git(["commit", "-m", message])
        print("OK")
        print(f"  Mensaje: {message}")

    # ------------------------------------------------------------------
    def push(self) -> None:
        """Realiza ``git push origin main`` explícitamente.

        No depende del upstream configurado localmente.
        """
        print(f"  git push {self._REMOTE} {self._BRANCH} ... ", end="", flush=True)
        self._run_git(["push", self._REMOTE, self._BRANCH])
        print("OK")

    # ------------------------------------------------------------------
    def publish(self) -> bool:
        """Ejecuta el flujo completo de publicación.

        Flujo:

        1. ``validate_repository()``
        2. Verificar commits pendientes de publicación.
           Si existen → solo ``push()``, sin ``add`` ni ``commit``.
        3. ``has_changes()`` — si no hay cambios, retorna ``True`` sin
           hacer nada más.
        4. ``commit()``
        5. ``push()``

        Returns
        -------
        bool
            ``True`` si el flujo finalizó correctamente (con o sin
            cambios publicados).

        Raises
        ------
        RuntimeError
            Si ocurre un error en cualquiera de los comandos de Git.
        """
        try:
            # 1. Validar repositorio
            self.validate_repository()
            print(f"[GitManager] Repositorio validado: {self._repo_path}")

            # 2. Verificar si ya existen commits pendientes de publicar
            if self._has_unpushed_commits():
                print("[GitManager] Commits pendientes detectados. Publicando...")
                self.push()
                print(f"[GitManager] {self.MSG_UNPUSHED_PUBLISHED}")
                return True

            # 3. Verificar cambios en working tree
            if not self.has_changes():
                print(f"[GitManager] {self.MSG_NO_CHANGES}")
                return True

            # 4. Commit (con mensaje por defecto)
            print("[GitManager] Cambios detectados. Publicando...")
            timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message: str = f"Actualización MB52 - {timestamp}"
            self.commit(message)

            # 5. Push
            self.push()

            print(f"[GitManager] {self.MSG_PUBLISH_OK}")
            return True

        except subprocess.CalledProcessError as exc:
            error_msg: str = (
                f"Error de Git: {exc.stderr.strip() if exc.stderr else exc}"
            )
            print(f"\n[GitManager] [ERROR] {error_msg}")
            raise RuntimeError(error_msg) from exc

        except (FileNotFoundError, NotADirectoryError) as exc:
            print(f"\n[GitManager] [ERROR] {exc}")
            raise

        except Exception as exc:
            print(f"\n[GitManager] [ERROR] {exc}")
            raise RuntimeError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _has_unpushed_commits(self) -> bool:
        """Detecta si existen commits locales pendientes de publicar.

        Compara ``HEAD`` contra ``origin/main`` usando
        ``git rev-list --count``.

        Returns
        -------
        bool
            ``True`` si hay al menos un commit local sin publicar.
        """
        try:
            output: str = self._run_git(
                ["rev-list", "--count", f"{self._REMOTE}/{self._BRANCH}..HEAD"]
            )
            count: int = int(output.strip())
            return count > 0
        except (subprocess.CalledProcessError, ValueError):
            # Si la rama remota no existe aún, no hay commits pendientes
            return False

    def _run_git(self, args: List[str]) -> str:
        """Ejecuta un comando de Git en el repositorio configurado.

        Parameters
        ----------
        args : list[str]
            Argumentos a pasar a ``git`` (sin incluir ``git``).

        Returns
        -------
        str
            Salida estándar (stdout) del comando.

        Raises
        ------
        subprocess.CalledProcessError
            Si el comando retorna un código distinto de 0.
        """
        cmd: List[str] = ["git"] + args
        result: subprocess.CompletedProcess = subprocess.run(
            cmd,
            cwd=str(self._repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
