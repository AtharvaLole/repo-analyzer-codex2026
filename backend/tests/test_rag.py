"""RAG unit tests."""

from pathlib import Path

from app.config import Settings
from app.rag.chunker import CodeChunker, TreeSitterChunker
from app.rag.embedder import CodeEmbedder
from app.rag.indexer import RepoIndexer, RepoTooLargeError
from app.rag.retriever import HybridRetriever, SearchResult


def test_chunker_creates_line_aware_chunks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "example.py"
    source.write_text("def hello() -> str:\n    return 'world'\n", encoding="utf-8")

    chunks = TreeSitterChunker(max_lines=10, overlap_lines=0).chunk_file("demo", repo, source)

    assert len(chunks) == 1
    assert chunks[0].file_path == "example.py"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2


def test_chunker_uses_sliding_window_for_unsupported_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "notes.md"
    source.write_text(" ".join(f"token-{index}" for index in range(300)), encoding="utf-8")

    chunks = CodeChunker(unsupported_window_tokens=256, unsupported_overlap_tokens=0).chunk_file(
        "demo",
        repo,
        source,
    )

    assert len(chunks) == 2
    assert all(chunk.chunk_type == "module" for chunk in chunks)
    assert chunks[0].language == "markdown"


def test_repo_indexer_filters_excluded_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "package.js").write_text("ignored\n", encoding="utf-8")
    (repo / "bundle.min.js").write_text("ignored\n", encoding="utf-8")
    (repo / "yarn.lock").write_text("ignored\n", encoding="utf-8")

    indexer = RepoIndexer(
        settings=Settings(REPOS_BASE_DIR=tmp_path / "repos", MAX_REPO_SIZE_MB=1),
    )

    files = indexer.list_files(repo)

    assert [file.relative_to(repo).as_posix() for file in files] == ["src/app.py"]


def test_repo_indexer_raises_for_large_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "large.txt").write_bytes(b"x" * ((1024 * 1024) + 1))
    indexer = RepoIndexer(
        settings=Settings(REPOS_BASE_DIR=tmp_path / "repos", MAX_REPO_SIZE_MB=1),
    )

    try:
        indexer._validate_repo_size(repo)
    except RepoTooLargeError:
        pass
    else:
        raise AssertionError("Expected RepoTooLargeError")


def test_code_embedder_builds_prompt_spec_chunk_records(tmp_path: Path) -> None:
    embedder = CodeEmbedder(
        settings=Settings(CHROMA_PERSIST_DIR=tmp_path / "chroma"),
    )
    record = embedder._chunk_to_record(
        repo_id="demo",
        chunk={
            "content": "def hello() -> str:\n    return 'world'",
            "file_path": "src/example.py",
            "start_line": 10,
            "end_line": 11,
            "chunk_type": "function",
            "language": "python",
            "name": "hello",
        },
        commit_sha="abc123",
    )

    assert record["id"] == "demo:src/example.py:10"
    assert record["metadata"] == {
        "file_path": "src/example.py",
        "start_line": 10,
        "end_line": 11,
        "chunk_type": "function",
        "language": "python",
        "name": "hello",
        "commit_sha": "abc123",
    }


def test_hybrid_retriever_uses_reciprocal_rank_fusion(tmp_path: Path) -> None:
    retriever = HybridRetriever(settings=Settings(CHROMA_PERSIST_DIR=tmp_path / "chroma"))
    semantic_results = [
        SearchResult(
            chunk_id="a",
            content="alpha",
            file_path="a.py",
            start_line=1,
            end_line=2,
            chunk_type="function",
            language="python",
            name="alpha",
            score=0.9,
            search_type="semantic",
        ),
        SearchResult(
            chunk_id="b",
            content="beta",
            file_path="b.py",
            start_line=1,
            end_line=2,
            chunk_type="function",
            language="python",
            name="beta",
            score=0.8,
            search_type="semantic",
        ),
    ]
    bm25_results = [
        SearchResult(
            chunk_id="b",
            content="beta",
            file_path="b.py",
            start_line=1,
            end_line=2,
            chunk_type="function",
            language="python",
            name="beta",
            score=1.0,
            search_type="bm25",
        ),
    ]

    merged = retriever._reciprocal_rank_fusion(semantic_results, bm25_results, top_k=2)

    assert [result.chunk_id for result in merged] == ["b", "a"]
    assert all(result.search_type == "hybrid" for result in merged)
