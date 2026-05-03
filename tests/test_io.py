import sys
from cheap_cli._io import read_inputs, is_binary, estimate_tokens


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 4) == 1
    assert estimate_tokens("a" * 4000) == 1000


def test_is_binary_text(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("hello world")
    assert is_binary(p) is False


def test_is_binary_with_null_bytes(tmp_path):
    p = tmp_path / "t.bin"
    p.write_bytes(b"hello\x00world")
    assert is_binary(p) is True


def test_read_inputs_text_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("alpha")
    out = read_inputs([str(p)])
    assert out == [(str(p), "alpha")]


def test_read_inputs_skips_binary(tmp_path, capsys):
    p = tmp_path / "b.bin"
    p.write_bytes(b"\x00\x01\x02")
    out = read_inputs([str(p)])
    assert out == []
    err = capsys.readouterr().err
    assert "skipping binary" in err


def test_read_inputs_missing_file(tmp_path, capsys):
    out = read_inputs([str(tmp_path / "nope.txt")])
    assert out == []
    err = capsys.readouterr().err
    assert "file not found" in err


def test_read_inputs_stdin(monkeypatch):
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("from-stdin"))
    out = read_inputs(["-"])
    assert out == [("<stdin>", "from-stdin")]


def test_read_inputs_mixed(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("A")
    out = read_inputs([str(p), str(tmp_path / "missing")])
    assert out == [(str(p), "A")]
