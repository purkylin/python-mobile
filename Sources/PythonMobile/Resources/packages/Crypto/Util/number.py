import math

def bytes_to_long(s):
    return int.from_bytes(s, byteorder='big')

def long_to_bytes(n, blocksize=0):
    if n < 0:
        raise ValueError("Negative number cannot be converted")
    s = n.to_bytes((n.bit_length() + 7) // 8 or 1, byteorder='big')
    if blocksize > 0 and len(s) % blocksize:
        s = (b'\x00' * (blocksize - (len(s) % blocksize))) + s
    return s

def GCD(x, y):
    return math.gcd(x, y)

def inverse(u, v):
    return pow(u, -1, v)
