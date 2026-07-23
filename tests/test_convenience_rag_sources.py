import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.rag.convenience_rag import build_convenience_documents


def test_official_seoul_dataset_has_public_sources() -> None:
    documents = build_convenience_documents()
    organizations = [
        document
        for document in documents
        if document.metadata.get("source_type") == "organization"
    ]

    assert len(organizations) == 11
    assert all(document.metadata.get("source_url") for document in organizations)
    assert all(document.metadata.get("verified_at") == "2026-07-23" for document in organizations)
    assert all("정보 출처:" in document.page_content for document in organizations)


def test_dummy_people_and_contacts_are_removed() -> None:
    documents = build_convenience_documents()
    source_types = {document.metadata.get("source_type") for document in documents}

    assert "person" not in source_types
    assert "example.org" not in "\n".join(document.page_content for document in documents)
