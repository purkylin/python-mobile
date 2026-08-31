import base64
import re


class RsaKey:
    def __init__(self, n, e, d=None):
        self.n = n
        self.e = e
        self.d = d

    def has_private(self):
        return self.d is not None

    def size_in_bytes(self):
        return (self.n.bit_length() + 7) // 8

    def size_in_bits(self):
        return self.n.bit_length()

    def publickey(self):
        return RsaKey(self.n, self.e)

    public_key = publickey


def _read_length(data, offset):
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    count = first & 0x7f
    if count == 0 or offset + count > len(data):
        raise ValueError("Invalid DER length")
    return int.from_bytes(data[offset:offset + count], "big"), offset + count


def _read_tlv(data, offset=0):
    if offset >= len(data):
        raise ValueError("Invalid DER data")
    tag = data[offset]
    length, start = _read_length(data, offset + 1)
    end = start + length
    if end > len(data):
        raise ValueError("Truncated DER data")
    return tag, data[start:end], end


def _items(sequence):
    tag, payload, end = _read_tlv(sequence)
    if tag != 0x30 or end != len(sequence):
        raise ValueError("Expected DER sequence")
    result = []
    offset = 0
    while offset < len(payload):
        item_tag, item, offset = _read_tlv(payload, offset)
        result.append((item_tag, item))
    return result


def _integer(item):
    return int.from_bytes(item, "big", signed=False)


def _parse_der(data):
    items = _items(data)

    if len(items) == 2 and items[0][0] == 0x02 and items[1][0] == 0x02:
        return RsaKey(_integer(items[0][1]), _integer(items[1][1]))

    if len(items) >= 9 and all(tag == 0x02 for tag, _ in items[:4]):
        return RsaKey(
            _integer(items[1][1]),
            _integer(items[2][1]),
            _integer(items[3][1])
        )

    if len(items) >= 2 and items[0][0] == 0x30 and items[1][0] == 0x03:
        bit_string = items[1][1]
        if not bit_string or bit_string[0] != 0:
            raise ValueError("Invalid RSA public key")
        return _parse_der(bit_string[1:])

    if len(items) >= 3 and items[0][0] == 0x02 and items[2][0] == 0x04:
        return _parse_der(items[2][1])

    raise ValueError("Unsupported RSA key format")


def import_key(extern_key, passphrase=None):
    data = extern_key.encode("ascii") if isinstance(extern_key, str) else bytes(extern_key)
    if b"-----BEGIN" in data:
        body = re.sub(br"-----[^-]+-----", b"", data)
        data = base64.b64decode(re.sub(br"\s+", b"", body))
    return _parse_der(data)


importKey = import_key
