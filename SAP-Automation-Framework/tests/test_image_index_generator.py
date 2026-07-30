from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.image_index_generator import ImageIndexGenerator


def test_generate_creates_index_for_existing_images(tmp_path: Path) -> None:
    materials_dir = tmp_path / "web/images/materials"
    materials_dir.mkdir(parents=True, exist_ok=True)
    (materials_dir / "301420.jpg").write_text("x")
    (materials_dir / "302547.png").write_text("x")
    (materials_dir / "invalid.txt").write_text("x")
    (materials_dir / "bad-name!.jpg").write_text("x")

    generator = ImageIndexGenerator(base_dir=tmp_path)
    generator.generate()

    index_path = materials_dir / "material-index.json"
    assert index_path.exists()

    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["materials"] == ["301420", "302547"]
    assert data["generated"].endswith("Z")


def test_generate_creates_empty_index_when_folder_missing(tmp_path: Path) -> None:
    generator = ImageIndexGenerator(base_dir=tmp_path)
    generator.generate()

    index_path = tmp_path / "web/images/materials/material-index.json"
    assert index_path.exists()

    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["materials"] == []
    assert data["generated"].endswith("Z")
