from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Set


class ImageIndexGenerator:
    """Generador de índice de imágenes de materiales del Portal Web."""

    _ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    _MATERIALS_DIR: str = "web/images/materials"
    _OUTPUT_FILENAME: str = "material-index.json"
    _SAP_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")

    def __init__(self, base_dir: Path) -> None:
        self._base_dir: Path = base_dir

    def generate(self) -> None:
        """Genera el índice JSON de materiales a partir de las imágenes existentes."""
        materials_dir = self._base_dir.parent / self._MATERIALS_DIR
        materials = self._collect_material_codes(materials_dir)
        payload = {
            "version": 1,
            "generated": self._current_timestamp(),
            "materials": materials,
        }

        output_path = materials_dir / self._OUTPUT_FILENAME
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _collect_material_codes(self, materials_dir: Path) -> list[str]:
        if not materials_dir.is_dir():
            return []

        codes: Set[str] = set()
        for entry in materials_dir.iterdir():
            if not entry.is_file():
                continue

            if entry.suffix.lower() not in self._ALLOWED_EXTENSIONS:
                continue

            code = self._normalize_material_code(entry.stem)
            if code is None:
                continue

            codes.add(code)

        return self._sort_material_codes(codes)

    def _normalize_material_code(self, stem: str) -> str | None:
        candidate = stem.strip()
        if not candidate:
            return None
        if not self._SAP_CODE_PATTERN.fullmatch(candidate):
            return None
        return candidate

    def _sort_material_codes(self, codes: Set[str]) -> list[str]:
        if not codes:
            return []

        if all(code.isdigit() for code in codes):
            return sorted(codes, key=lambda value: int(value))

        return sorted(codes, key=str.casefold)

    def _current_timestamp(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
