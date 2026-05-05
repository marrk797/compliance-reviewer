from app.services.chunking import chunk_text


def test_chunk_returns_empty_for_empty_input() -> None:
    assert chunk_text("") == []


def test_chunks_have_overlap_and_preserve_order() -> None:
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    assert all(c.token_count <= 200 for c in chunks)
    # Ordinals are sequential starting at 0.
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_short_text_yields_single_chunk() -> None:
    chunks = chunk_text("Hello world.", chunk_size=200, overlap=20)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
