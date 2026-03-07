from __future__ import annotations

import base64


_PLACEHOLDER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6L6QMAAAAASUVORK5CYII="
)


def bytes_to_data_url(raw: bytes, mime_type: str = "image/png") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"


def tiny_placeholder_png() -> bytes:
    return base64.b64decode(_PLACEHOLDER_PNG_BASE64)
