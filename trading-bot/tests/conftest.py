from pathlib import Path

import pytest
import yaml

from core.config import CONFIG_DIR


@pytest.fixture
def strategy_dict() -> dict:
    return yaml.safe_load((CONFIG_DIR / "strategy.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def app_dict() -> dict:
    return yaml.safe_load((CONFIG_DIR / "app.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def write_yaml(tmp_path: Path):
    def _write(data: dict, name: str = "cfg.yaml") -> Path:
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return p

    return _write
