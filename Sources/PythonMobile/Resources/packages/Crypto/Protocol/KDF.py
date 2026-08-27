import hashlib


def _as_bytes(value):
    if isinstance(value, str):
        return value.encode("latin-1")
    return bytes(value)


def _hash_name(hash_module):
    if hash_module is None:
        return "sha1"
    digest = hash_module.new()
    name = getattr(digest, "name", None)
    if not name:
        raise ValueError("Unsupported hash module")
    return name.lower().replace("-", "")


def _derive_with_prf(password, salt, length, count, prf):
    first = prf(password, salt + (1).to_bytes(4, "big"))
    block_size = len(first)
    output = bytearray()
    block_count = (length + block_size - 1) // block_size

    for index in range(1, block_count + 1):
        current = prf(password, salt + index.to_bytes(4, "big"))
        block = bytearray(current)
        for _ in range(1, count):
            current = prf(password, current)
            for offset, value in enumerate(current):
                block[offset] ^= value
        output.extend(block)
    return bytes(output[:length])


def PBKDF2(password, salt, dkLen=16, count=1000, prf=None, hmac_hash_module=None):
    password = _as_bytes(password)
    salt = _as_bytes(salt)
    if dkLen <= 0 or count <= 0:
        raise ValueError("dkLen and count must be positive")
    if prf is not None and hmac_hash_module is not None:
        raise ValueError("prf and hmac_hash_module are mutually exclusive")
    if prf is not None:
        return _derive_with_prf(password, salt, dkLen, count, prf)
    return hashlib.pbkdf2_hmac(
        _hash_name(hmac_hash_module),
        password,
        salt,
        count,
        dkLen,
    )
