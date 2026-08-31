import os


class _PKCS115Cipher:
    def __init__(self, key, randfunc=None):
        self._key = key
        self._randfunc = randfunc or os.urandom

    def encrypt(self, message):
        message = bytes(message)
        size = self._key.size_in_bytes()
        padding_size = size - len(message) - 3
        if padding_size < 8:
            raise ValueError("Plaintext is too long")

        padding = bytearray()
        while len(padding) < padding_size:
            padding.extend(value for value in self._randfunc(padding_size) if value)
        encoded = b"\x00\x02" + bytes(padding[:padding_size]) + b"\x00" + message
        value = pow(int.from_bytes(encoded, "big"), self._key.e, self._key.n)
        return value.to_bytes(size, "big")

    def decrypt(self, ciphertext, sentinel, expected_pt_len=0):
        if not self._key.has_private():
            raise TypeError("Private RSA key required")
        size = self._key.size_in_bytes()
        ciphertext = bytes(ciphertext)
        if len(ciphertext) != size:
            return sentinel

        value = pow(int.from_bytes(ciphertext, "big"), self._key.d, self._key.n)
        encoded = value.to_bytes(size, "big")
        separator = encoded.find(b"\x00", 2)
        if not encoded.startswith(b"\x00\x02") or separator < 10:
            return sentinel
        message = encoded[separator + 1:]
        if expected_pt_len and len(message) != expected_pt_len:
            return sentinel
        return message


def new(key, randfunc=None):
    return _PKCS115Cipher(key, randfunc=randfunc)
