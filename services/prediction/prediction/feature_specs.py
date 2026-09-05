"""Versioned experimental representations, independent of model families."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Collection


@dataclass(frozen=True)
class FeatureSchema:
    name: str
    version: int
    representation_kind: str
    definition: dict[str, Any]

    @property
    def definition_sha256(self) -> str:
        return canonical_json_sha256(self.definition)


def canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def require_compatible(schema: FeatureSchema, supported_kinds: Collection[str]) -> None:
    if schema.representation_kind not in supported_kinds:
        raise ValueError(
            f"feature schema {schema.name!r} does not support {schema.representation_kind} "
            f"for model kinds {sorted(supported_kinds)!r}"
        )
