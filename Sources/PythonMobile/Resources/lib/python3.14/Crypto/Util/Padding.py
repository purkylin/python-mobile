# Crypto/Util/Padding.py

def pad(data_to_pad, block_size, style='pkcs7'):
    if isinstance(data_to_pad, str):
        data_to_pad = data_to_pad.encode('utf-8')
    padding_len = block_size - (len(data_to_pad) % block_size)
    if padding_len == 0:
        padding_len = block_size
    padding = bytes([padding_len] * padding_len)
    return data_to_pad + padding

def unpad(padded_data, block_size, style='pkcs7'):
    if isinstance(padded_data, str):
        padded_data = padded_data.encode('utf-8')
    if len(padded_data) == 0:
        raise ValueError("Zero-length slice cannot be unpadded")
    if len(padded_data) % block_size:
        raise ValueError("Data is not a multiple of the block size")
    padding_len = padded_data[-1]
    if padding_len < 1 or padding_len > block_size:
        raise ValueError("Padding is incorrect.")
    if padded_data[-padding_len:] != bytes([padding_len] * padding_len):
        raise ValueError("PKCS#7 padding is incorrect.")
    return padded_data[:-padding_len]
