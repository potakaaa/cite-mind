from __future__ import annotations

import pytest

from app.tools.text_chunker import TextChunker


def test_text_chunker_splits_long_text_with_overlap_and_metadata():
    page_text = "0123456789" * 8
    chunker = TextChunker(chunk_size=25, chunk_overlap=5)

    chunks = chunker.chunk_pages("paper.pdf", [{"page_number": 3, "text": page_text}])

    assert [chunk.chunk_id for chunk in chunks] == [1, 2, 3, 4]
    assert all(chunk.source_file == "paper.pdf" for chunk in chunks)
    assert all(chunk.page_start == 3 and chunk.page_end == 3 for chunk in chunks)
    assert chunks[0].text == page_text[:25]
    assert chunks[1].char_start == 20
    assert chunks[1].text.startswith(page_text[20:25])
    assert chunks[-1].char_end == len(page_text)


def test_text_chunker_skips_blank_pages_but_preserves_global_offsets():
    chunker = TextChunker(chunk_size=10, chunk_overlap=0)

    chunks = chunker.chunk_pages(
        "paper.pdf",
        [
            {"page_number": 1, "text": "     "},
            {"page_number": 2, "text": "abcdefghij"},
        ],
    )

    assert len(chunks) == 1
    assert chunks[0].page_start == 2
    assert chunks[0].char_start == 5


@pytest.mark.parametrize(
    "chunk_size,chunk_overlap,error",
    [
        (0, 0, "chunk_size"),
        (10, -1, "chunk_overlap"),
        (10, 10, "smaller"),
    ],
)
def test_text_chunker_validates_configuration(chunk_size, chunk_overlap, error):
    with pytest.raises(ValueError, match=error):
        TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
