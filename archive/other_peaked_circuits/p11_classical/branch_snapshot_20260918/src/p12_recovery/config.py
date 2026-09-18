from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from .hashing import sha256_file

T = TypeVar("T", bound=BaseModel)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration does not exist: {path}")
    loaded = yaml.safe_load(path.read_text())
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {path}")
    return loaded


def load_model(path: Path, model: type[T]) -> T:
    return model.model_validate(load_yaml(path))


def config_digest(path: Path) -> str:
    return sha256_file(path)
