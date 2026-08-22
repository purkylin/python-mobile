# Crypto/Util/number.py
def bytes_to_long(b):
    return int.from_bytes(b, byteorder='big')

def long_to_bytes(n, blocksize=0):
    if n < 0:
        raise ValueError("n must be non-negative")
    b = n.to_bytes((n.bit_length() + 7) // 8 or 1, byteorder='big')
    if blocksize > 0 and len(b) % blocksize != 0:
        b = b'\x00' * (blocksize - (len(b) % blocksize)) + b
    return b
