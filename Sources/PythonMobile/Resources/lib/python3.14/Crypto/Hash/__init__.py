import hashlib, hmac

class _HashWrapper:
    def __init__(self, h):
        self._h = h

    def update(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._h.update(data)
        return self

    def digest(self):
        return self._h.digest()

    def hexdigest(self):
        return self._h.hexdigest()

    def copy(self):
        return _HashWrapper(self._h.copy())

    @property
    def digest_size(self):
        return self._h.digest_size

    @property
    def block_size(self):
        return self._h.block_size

class _HashModule:
    def __init__(self, name):
        self.name = name

    def new(self, data=b""):
        if isinstance(data, str):
            data = data.encode('utf-8')
        h = getattr(hashlib, self.name.lower())(data)
        return _HashWrapper(h)

MD5 = _HashModule("md5")
SHA1 = _HashModule("sha1")
SHA224 = _HashModule("sha224")
SHA256 = _HashModule("sha256")
SHA384 = _HashModule("sha384")
SHA512 = _HashModule("sha512")

class _HMACModule:
    def new(self, key, msg=None, digestmod="sha256"):
        if isinstance(key, str):
            key = key.encode("utf-8")
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        if isinstance(digestmod, _HashModule):
            digestmod = getattr(hashlib, digestmod.name.lower())
        elif hasattr(digestmod, "new"):
            digestmod = digestmod.new
        h = hmac.new(key, msg=msg, digestmod=digestmod)
        return _HashWrapper(h)

HMAC = _HMACModule()
