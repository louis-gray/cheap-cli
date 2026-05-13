import sys
import httpx
from cheap_cli._io import (
    read_inputs,
    is_binary,
    is_url,
    estimate_tokens,
    html_to_text,
    fetch_url,
)
from cheap_cli import _io


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


def test_read_inputs_empty():
    assert read_inputs([]) == []


def test_is_url():
    assert is_url("https://example.com") is True
    assert is_url("http://example.com") is True
    assert is_url("example.com") is False
    assert is_url("/etc/hosts") is False
    assert is_url("-") is False


def test_html_to_text_strips_tags():
    html = "<html><body><h1>Hi</h1><p>Hello <b>world</b>.</p></body></html>"
    assert html_to_text(html) == "Hi Hello world ."


def test_html_to_text_strips_script_and_style():
    html = "<style>.x{color:red}</style><script>alert(1)</script><p>Visible</p>"
    out = html_to_text(html)
    assert "alert" not in out
    assert "color" not in out
    assert "Visible" in out


def test_html_to_text_collapses_whitespace():
    html = "<p>a\n\n\n  b   c</p>"
    assert html_to_text(html) == "a b c"


def test_fetch_url_html(monkeypatch):
    class FakeResp:
        text = "<html><body><p>Hello world</p></body></html>"
        headers = {"content-type": "text/html; charset=utf-8"}
        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    label, content = fetch_url("https://example.com")
    assert label == "https://example.com"
    assert "Hello world" in content
    assert "<p>" not in content


def test_fetch_url_plain_text(monkeypatch):
    class FakeResp:
        text = "raw markdown content"
        headers = {"content-type": "text/markdown"}
        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    _, content = fetch_url("https://example.com/doc.md")
    assert content == "raw markdown content"


def test_read_inputs_url(monkeypatch):
    monkeypatch.setattr(
        _io,
        "fetch_url",
        lambda url, **kw: (url, f"content from {url}"),
    )
    out = read_inputs(["https://example.com/x"])
    assert out == [("https://example.com/x", "content from https://example.com/x")]


def test_read_inputs_url_failure(monkeypatch, capsys):
    def boom(url, **kw):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(_io, "fetch_url", boom)
    out = read_inputs(["https://example.com/down"])
    assert out == []
    err = capsys.readouterr().err
    assert "fetch failed" in err
