import base64

from fastapi.encoders import jsonable_encoder


def test_bytes_base64():
    data = b"hello world"
    result = jsonable_encoder(data)
    assert result == base64.b64encode(data).decode()


def test_bytes_hex():
    data = b"hello world"
    result = jsonable_encoder(data, bytes_encoding="hex")
    assert result == data.hex()


def test_memoryview_base64():
    data = memoryview(b"hello world")
    result = jsonable_encoder(data)
    assert result == base64.b64encode(bytes(data)).decode()


def test_memoryview_hex():
    data = memoryview(b"hello world")
    result = jsonable_encoder(data, bytes_encoding="hex")
    assert result == bytes(data).hex()


def test_bytes_in_dict():
    data = {"key": b"test bytes"}
    result = jsonable_encoder(data)
    assert result == {"key": base64.b64encode(b"test bytes").decode()}


def test_bytes_in_list():
    data = [b"item1", b"item2"]
    result = jsonable_encoder(data)
    assert result == [
        base64.b64encode(b"item1").decode(),
        base64.b64encode(b"item2").decode(),
    ]


def test_bytes_encoding_invalid():
    try:
        jsonable_encoder(b"test", bytes_encoding="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported bytes_encoding" in str(e)
