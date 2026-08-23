import hmac
import hashlib

class _HMACWrapper:
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
        return _HMACWrapper(self._h.copy())

    @property
    def digest_size(self):
        return self._h.digest_size

    @property
    def block_size(self):
        return self._h.block_size

def new(key, msg=None, digestmod="sha256"):
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(msg, str):
        msg = msg.encode("utf-8")
    if hasattr(digestmod, "name"):
        digestmod = getattr(hashlib, digestmod.name.lower(), hashlib.sha256)
    elif hasattr(digestmod, "new"):
        digestmod = digestmod.new
    elif isinstance(digestmod, str):
        digestmod = getattr(hashlib, digestmod.lower(), hashlib.sha256)
    return _HMACWrapper(hmac.new(key, msg=msg, digestmod=digestmod))
