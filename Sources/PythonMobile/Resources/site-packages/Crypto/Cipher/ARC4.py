class _ARC4Cipher:
    def __init__(self, key, drop=0):
        key = key.encode("utf-8") if isinstance(key, str) else bytes(key)
        if not key:
            raise ValueError("ARC4 key cannot be empty")

        self._state = list(range(256))
        j = 0
        for i in range(256):
            j = (j + self._state[i] + key[i % len(key)]) & 0xff
            self._state[i], self._state[j] = self._state[j], self._state[i]
        self._i = 0
        self._j = 0
        if drop:
            self.encrypt(bytes(int(drop)))

    def encrypt(self, data):
        output = bytearray()
        for value in bytes(data):
            self._i = (self._i + 1) & 0xff
            self._j = (self._j + self._state[self._i]) & 0xff
            self._state[self._i], self._state[self._j] = self._state[self._j], self._state[self._i]
            index = (self._state[self._i] + self._state[self._j]) & 0xff
            output.append(value ^ self._state[index])
        return bytes(output)

    decrypt = encrypt


def new(key, *args, drop=0, **kwargs):
    return _ARC4Cipher(key, drop=drop)
