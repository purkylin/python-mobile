from . import SHA256

def new(data=b""):
    return SHA256.new(data)
