import pytest
from vills.core.context_compressor import ContextCompressor


def test_does_not_compress_below_limit():
    c = ContextCompressor(max_messages=20, keep_recent=8)
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(10)]
    r = c.compress(msgs)
    assert not r.was_compressed
    assert len(r.messages) == 10


def test_compresses_above_limit():
    c = ContextCompressor(max_messages=20, keep_recent=8)
    msgs = [{"role": "user", "content": f"mensagem {i}"} for i in range(50)]
    r = c.compress(msgs)
    assert r.was_compressed
    assert len(r.messages) == 9
    assert "[Resumo de 42 mensagens" in r.messages[0]["content"]
    assert r.messages[-1]["content"] == "mensagem 49"


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        ContextCompressor(max_messages=5, keep_recent=10)


def test_exactly_at_limit_not_compressed():
    c = ContextCompressor(max_messages=20, keep_recent=8)
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(20)]
    assert not c.compress(msgs).was_compressed


def test_empty_list():
    c = ContextCompressor()
    r = c.compress([])
    assert not r.was_compressed
    assert r.messages == []


def test_multimodal_content_does_not_break():
    c = ContextCompressor(max_messages=20, keep_recent=8)
    msgs = [{"role": "user", "content": [{"type": "text", "text": "x"}]} for _ in range(50)]
    r = c.compress(msgs)
    assert r.was_compressed
