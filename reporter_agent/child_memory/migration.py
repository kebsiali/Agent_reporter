from __future__ import annotations

from .schema import CURRENT_SCHEMA_VERSION


def migrate_manifest(manifest: dict) -> dict:
    version = int(manifest.get("schema_version", 0))
    migrated = dict(manifest)

    # Schema v1 is the first structured CHILD bundle format.
    if version <= 0:
        migrated["schema_version"] = CURRENT_SCHEMA_VERSION
        return migrated

    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Bundle schema_version={version} is newer than supported {CURRENT_SCHEMA_VERSION}."
        )

    migrated["schema_version"] = CURRENT_SCHEMA_VERSION
    return migrated

