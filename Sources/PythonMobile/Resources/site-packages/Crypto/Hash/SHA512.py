from . import SHA512

def new(data=b""):
    return SHA512.new(data)
