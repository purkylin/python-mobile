# Crypto/Util/Padding.py
def pad(data_to_pad, block_size, style='pkcs7'):
    if not isinstance(data_to_pad, (bytes, bytearray)):
        raise TypeError("data_to_pad must be bytes or bytearray")
    padding_len = block_size - (len(data_to_pad) % block_size)
    if style == 'pkcs7':
        padding = bytes([padding_len] * padding_len)
    elif style == 'iso7816':
        padding = b'\x80' + b'\x00' * (padding_len - 1)
    elif style == 'x923':
        padding = b'\x00' * (padding_len - 1) + bytes([padding_len])
    else:
        raise ValueError(f"Unknown padding style: {style}")
    return bytes(data_to_pad) + padding

def unpad(padded_data, block_size, style='pkcs7'):
    if not isinstance(padded_data, (bytes, bytearray)):
        raise TypeError("padded_data must be bytes or bytearray")
    if len(padded_data) == 0:
        raise ValueError("Zero-length input cannot be unpadded")
    if len(padded_data) % block_size != 0:
        raise ValueError("Input data is not a multiple of the block size")

    if style == 'pkcs7':
        padding_len = padded_data[-1]
        if padding_len < 1 or padding_len > block_size:
            raise ValueError("PKCS#7 padding is corrupted")
        if padded_data[-padding_len:] != bytes([padding_len] * padding_len):
            raise ValueError("PKCS#7 padding is corrupted")
        return bytes(padded_data[:-padding_len])
    elif style == 'iso7816':
        idx = padded_data.rfind(b'\x80')
        if idx == -1:
            raise ValueError("ISO 7816-4 padding is corrupted")
        if any(b != 0 for b in padded_data[idx+1:]):
            raise ValueError("ISO 7816-4 padding is corrupted")
        return bytes(padded_data[:idx])
    elif style == 'x923':
        padding_len = padded_data[-1]
        if padding_len < 1 or padding_len > block_size:
            raise ValueError("ANSI X.923 padding is corrupted")
        if any(b != 0 for b in padded_data[-padding_len:-1]):
            raise ValueError("ANSI X.923 padding is corrupted")
        return bytes(padded_data[:-padding_len])
    else:
        raise ValueError(f"Unknown padding style: {style}")
