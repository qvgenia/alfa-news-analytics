
from app.contracts import ClientProfile, SourceRef
from app.rag.retriever import retrieve_sources


def test_retrieve_sources_returns_source_refs():
    sources = retrieve_sources("логистика перевозки")

    assert sources
    assert all(isinstance(source, SourceRef) for source in sources)


def test_retrieve_sources_matches_query():
    sources = retrieve_sources("логистика перевозки")

    assert sources[0].source_id == "demo-002"


def test_retrieve_sources_respects_limit():
    sources = retrieve_sources("компании логистика отчётность", limit=1)

    assert len(sources) <= 1


def test_retrieve_sources_handles_empty_query():
    assert retrieve_sources("") == []
    assert retrieve_sources("   ") == []


def test_retrieve_sources_accepts_client_profile():
    client = ClientProfile(client_id="demo-client")

    sources = retrieve_sources("логистика", client=client)

    assert sources
