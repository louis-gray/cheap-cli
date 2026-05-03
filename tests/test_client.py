import json

from cheap_cli._client import build_messages, hash_args, log_usage


def test_build_messages_shape():
    msgs = build_messages("sys-prompt", "user-content")
    assert msgs == [
        {"role": "system", "content": "sys-prompt"},
        {"role": "user", "content": "user-content"},
    ]


def test_hash_args_stable():
    a = hash_args("question", "file1.py", "file2.py")
    b = hash_args("question", "file1.py", "file2.py")
    assert a == b
    assert len(a) == 16


def test_hash_args_order_sensitive():
    a = hash_args("q", "f1", "f2")
    b = hash_args("q", "f2", "f1")
    assert a != b


def test_log_usage_appends_jsonl(tmp_path):
    log = tmp_path / "usage.jsonl"
    log_usage(
        log_path=str(log),
        tool="ask-cheap",
        model="deepseek/deepseek-v4-flash",
        usage={"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.000016},
        args_hash="abc123",
    )
    log_usage(
        log_path=str(log),
        tool="write-cheap",
        model="deepseek/deepseek-v4-flash",
        usage={"prompt_tokens": 50, "completion_tokens": 80, "cost": 0.0000292},
        args_hash="def456",
    )
    lines = log.read_text().strip().split("\n")
    assert len(lines) == 2
    e1 = json.loads(lines[0])
    assert e1["tool"] == "ask-cheap"
    assert e1["prompt_tokens"] == 100
    assert e1["cost_usd"] == 0.000016
    assert e1["args_hash"] == "abc123"
    assert "ts" in e1


def test_log_usage_creates_parent_dir(tmp_path):
    nested = tmp_path / "deep" / "deeper" / "log.jsonl"
    log_usage(
        log_path=str(nested),
        tool="x",
        model="m",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.0},
        args_hash="h",
    )
    assert nested.exists()
