from reporter_agent.storage.ingestion_registry import (
    find_by_hash,
    list_ingested_ppts,
    register_ingested_file,
)


def test_registry_dedup_by_hash() -> None:
    registry = {"files": []}
    register_ingested_file(
        registry=registry,
        file_name="a.pptx",
        stored_path="x/a.pptx",
        content_hash="h1",
        status="ingested",
    )
    register_ingested_file(
        registry=registry,
        file_name="a_copy.pptx",
        stored_path="x/a_copy.pptx",
        content_hash="h1",
        status="already_ingested",
    )

    assert len(registry["files"]) == 1
    assert find_by_hash(registry, "h1") is not None
    assert list_ingested_ppts(registry)[0]["status"] == "already_ingested"

