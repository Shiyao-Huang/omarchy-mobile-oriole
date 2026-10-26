"""Validate a framed backup transfer before exposing any payload to callers."""
import base64, hashlib, re

def decode_frame(log: str, token: str, expected_bytes: int, expected_sha256: str) -> bytes:
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise ValueError('invalid token')
    if not 0 <= expected_bytes <= 2 * 1024 * 1024:
        raise ValueError('invalid size')
    begin, end = f'BACKUP_{token}_BEGIN', f'BACKUP_{token}_END'
    lines = log.replace('\r', '').splitlines()
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise ValueError('missing or duplicate frame')
    a, b = lines.index(begin), lines.index(end)
    if a >= b:
        raise ValueError('reversed frame')
    encoded = ''.join(lines[a + 1:b])
    if len(encoded) != 4 * ((expected_bytes + 2) // 3):
        raise ValueError('encoded size mismatch')
    payload = base64.b64decode(encoded, validate=True)
    if len(payload) != expected_bytes or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError('payload integrity mismatch')
    return payload
