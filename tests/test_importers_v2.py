from aurora.importers import import_chatgpt_export, import_claude_export, import_gemini_export


def test_chatgpt_tree_export_is_normalized():
    payload = {
        "conversations": [{
            "mapping": {
                "a": {"message": {"create_time": 2, "author": {"role": "assistant"}, "content": {"parts": ["answer"]}}},
                "b": {"message": {"create_time": 1, "author": {"role": "user"}, "content": {"parts": ["question"]}}},
            }
        }]
    }
    messages = import_chatgpt_export(payload)
    assert [(m.role, m.content) for m in messages] == [("user", "question"), ("assistant", "answer")]


def test_claude_export_normalizes_human_and_assistant():
    messages = import_claude_export({"chat_messages": [
        {"sender": "human", "text": "hello"},
        {"sender": "assistant", "text": "hi"},
    ]})
    assert [m.role for m in messages] == ["user", "assistant"]


def test_gemini_export_normalizes_model_role():
    messages = import_gemini_export({"messages": [
        {"role": "user", "content": "hello"},
        {"role": "model", "content": "hi"},
    ]})
    assert [m.role for m in messages] == ["user", "assistant"]
