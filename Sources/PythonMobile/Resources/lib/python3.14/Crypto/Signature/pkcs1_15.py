import hmac


_DIGEST_INFO_PREFIXES = {
    "md5": bytes.fromhex("3020300c06082a864886f70d020505000410"),
    "sha1": bytes.fromhex("3021300906052b0e03021a05000414"),
    "sha224": bytes.fromhex("302d300d06096086480165030402040500041c"),
    "sha256": bytes.fromhex("3031300d060960864801650304020105000420"),
    "sha384": bytes.fromhex("3041300d060960864801650304020205000430"),
    "sha512": bytes.fromhex("3051300d060960864801650304020305000440"),
}


def _hash_name(message_hash):
    name = getattr(message_hash, "name", None)
    if not name and hasattr(message_hash, "_h"):
        name = getattr(message_hash._h, "name", None)
    if not name:
        raise ValueError("Unsupported hash object")
    return str(name).lower().replace("-", "")


def _encode(message_hash, size):
    name = _hash_name(message_hash)
    prefix = _DIGEST_INFO_PREFIXES.get(name)
    if prefix is None:
        raise ValueError(f"Unsupported hash algorithm: {name}")

    digest_info = prefix + message_hash.digest()
    padding_size = size - len(digest_info) - 3
    if padding_size < 8:
        raise ValueError("Digest is too long for the RSA key")
    return b"\x00\x01" + (b"\xff" * padding_size) + b"\x00" + digest_info


class _PKCS115Signature:
    def __init__(self, key):
        self._key = key

    def sign(self, message_hash):
        if not self._key.has_private():
            raise TypeError("Private RSA key required")
        size = self._key.size_in_bytes()
        encoded = _encode(message_hash, size)
        value = pow(int.from_bytes(encoded, "big"), self._key.d, self._key.n)
        return value.to_bytes(size, "big")

    def verify(self, message_hash, signature):
        size = self._key.size_in_bytes()
        signature = bytes(signature)
        if len(signature) != size:
            raise ValueError("Invalid signature")

        value = pow(int.from_bytes(signature, "big"), self._key.e, self._key.n)
        recovered = value.to_bytes(size, "big")
        expected = _encode(message_hash, size)
        if not hmac.compare_digest(recovered, expected):
            raise ValueError("Invalid signature")


def new(key):
    return _PKCS115Signature(key)
