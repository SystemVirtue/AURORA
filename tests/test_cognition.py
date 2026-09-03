from aurora.cognition import chunk_text, content_hash
from aurora.importers import import_generic_conversation
from aurora.quorum import Contribution, compare_contributions


def test_import_preserves_model_as_role():
    rows = import_generic_conversation(
        [{"role": "user", "content": "What is X?"}, {"role": "assistant", "content": "X is Y."}],
        "historical-chat",
    )
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[1].source_name == "historical-chat"


def test_quorum_preserves_disagreement():
    result = compare_contributions(
        "What is X?",
        [Contribution("model-a", "X is Y."), Contribution("model-b", "X is Z.")],
    )
    assert len(result.contributions) == 2
    assert len(result.disagreements) == 1
    assert 0 <= result.agreement <= 1


def test_chunking_is_deterministic_and_bounded():
    text = "Paragraph one.\n\nParagraph two. " + ("word " * 700)
    chunks = chunk_text(text, max_chars=200)
    assert chunks
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert chunk_text(text, max_chars=200) == chunks


def test_content_hash_is_stable():
    assert content_hash("aurora") == content_hash("aurora")
    assert content_hash("aurora") != content_hash("AURORA")
