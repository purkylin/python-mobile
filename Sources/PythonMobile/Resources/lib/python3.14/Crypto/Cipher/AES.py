# Crypto/Cipher/AES.py
import struct

MODE_ECB = 1
MODE_CBC = 2
MODE_CFB = 3
MODE_OFB = 5
MODE_CTR = 6
MODE_OPENPGP = 7
MODE_CCM = 8
MODE_EAX = 9
MODE_SIV = 10
MODE_GCM = 11
MODE_OCB = 12

block_size = 16
key_size = (16, 24, 32)

# Rijndael S-Box
_sbox = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]

# Inverted S-Box
_rsbox = [
    0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
    0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
    0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
    0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
    0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
    0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
    0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
    0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
    0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
    0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
    0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
    0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
    0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
    0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
    0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d,
]

_rcon = [
    0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40,
    0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a,
]

def _xtime(a):
    doubled = (a << 1) & 0xff
    return doubled ^ 0x1b if (a & 0x80) else doubled

def _multiply(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        a = _xtime(a)
        b >>= 1
    return result

def _inverse_mix_column(column):
    a, b, c, d = column
    return [
        _multiply(a, 14) ^ _multiply(b, 11) ^ _multiply(c, 13) ^ _multiply(d, 9),
        _multiply(a, 9) ^ _multiply(b, 14) ^ _multiply(c, 11) ^ _multiply(d, 13),
        _multiply(a, 13) ^ _multiply(b, 9) ^ _multiply(c, 14) ^ _multiply(d, 11),
        _multiply(a, 11) ^ _multiply(b, 13) ^ _multiply(c, 9) ^ _multiply(d, 14),
    ]

class _AESCipher:
    def __init__(self, key, mode=MODE_ECB, iv=None, counter=None):
        if isinstance(key, str):
            key = key.encode('utf-8')
        self.key = bytes(key)
        self.mode = mode
        self.block_size = 16

        if len(self.key) not in (16, 24, 32):
            raise ValueError("Invalid AES key length (must be 16, 24, or 32 bytes)")

        if iv is not None and isinstance(iv, str):
            iv = iv.encode('utf-8')
        self.iv = bytes(iv) if iv is not None else b'\x00' * 16

        self._init_keys()

    def _init_keys(self):
        key = list(self.key)
        nk = len(key) // 4
        nr = nk + 6
        self.nr = nr

        w = []
        for i in range(nk):
            w.append([key[4*i], key[4*i+1], key[4*i+2], key[4*i+3]])

        for i in range(nk, 4 * (nr + 1)):
            temp = list(w[i - 1])
            if i % nk == 0:
                temp = [_sbox[temp[1]] ^ _rcon[i // nk], _sbox[temp[2]], _sbox[temp[3]], _sbox[temp[0]]]
            elif nk > 6 and i % nk == 4:
                temp = [_sbox[temp[0]], _sbox[temp[1]], _sbox[temp[2]], _sbox[temp[3]]]
            w.append([w[i - nk][j] ^ temp[j] for j in range(4)])

        self.round_keys = []
        for r in range(nr + 1):
            rk = []
            for c in range(4):
                for row in range(4):
                    rk.append(w[r * 4 + c][row])
            self.round_keys.append(rk)

    def _encrypt_block(self, block):
        state = list(block)
        for i in range(16):
            state[i] ^= self.round_keys[0][i]

        for r in range(1, self.nr):
            # SubBytes & ShiftRows
            s0 = _sbox[state[0]]
            s4 = _sbox[state[4]]
            s8 = _sbox[state[8]]
            s12 = _sbox[state[12]]

            s1 = _sbox[state[5]]
            s5 = _sbox[state[9]]
            s9 = _sbox[state[13]]
            s13 = _sbox[state[1]]

            s2 = _sbox[state[10]]
            s6 = _sbox[state[14]]
            s10 = _sbox[state[2]]
            s14 = _sbox[state[6]]

            s3 = _sbox[state[15]]
            s7 = _sbox[state[3]]
            s11 = _sbox[state[7]]
            s15 = _sbox[state[11]]

            # MixColumns
            rk = self.round_keys[r]
            state[0] = _xtime(s0 ^ s1) ^ s1 ^ s2 ^ s3 ^ rk[0]
            state[1] = _xtime(s1 ^ s2) ^ s2 ^ s3 ^ s0 ^ rk[1]
            state[2] = _xtime(s2 ^ s3) ^ s3 ^ s0 ^ s1 ^ rk[2]
            state[3] = _xtime(s3 ^ s0) ^ s0 ^ s1 ^ s2 ^ rk[3]

            state[4] = _xtime(s4 ^ s5) ^ s5 ^ s6 ^ s7 ^ rk[4]
            state[5] = _xtime(s5 ^ s6) ^ s6 ^ s7 ^ s4 ^ rk[5]
            state[6] = _xtime(s6 ^ s7) ^ s7 ^ s4 ^ s5 ^ rk[6]
            state[7] = _xtime(s7 ^ s4) ^ s4 ^ s5 ^ s6 ^ rk[7]

            state[8] = _xtime(s8 ^ s9) ^ s9 ^ s10 ^ s11 ^ rk[8]
            state[9] = _xtime(s9 ^ s10) ^ s10 ^ s11 ^ s8 ^ rk[9]
            state[10] = _xtime(s10 ^ s11) ^ s11 ^ s8 ^ s9 ^ rk[10]
            state[11] = _xtime(s11 ^ s8) ^ s8 ^ s9 ^ s10 ^ rk[11]

            state[12] = _xtime(s12 ^ s13) ^ s13 ^ s14 ^ s15 ^ rk[12]
            state[13] = _xtime(s13 ^ s14) ^ s14 ^ s15 ^ s12 ^ rk[13]
            state[14] = _xtime(s14 ^ s15) ^ s15 ^ s12 ^ s13 ^ rk[14]
            state[15] = _xtime(s15 ^ s12) ^ s12 ^ s13 ^ s14 ^ rk[15]

        # Final round
        rk = self.round_keys[self.nr]
        return bytes([
            _sbox[state[0]] ^ rk[0],
            _sbox[state[5]] ^ rk[1],
            _sbox[state[10]] ^ rk[2],
            _sbox[state[15]] ^ rk[3],
            _sbox[state[4]] ^ rk[4],
            _sbox[state[9]] ^ rk[5],
            _sbox[state[14]] ^ rk[6],
            _sbox[state[3]] ^ rk[7],
            _sbox[state[8]] ^ rk[8],
            _sbox[state[13]] ^ rk[9],
            _sbox[state[2]] ^ rk[10],
            _sbox[state[7]] ^ rk[11],
            _sbox[state[12]] ^ rk[12],
            _sbox[state[1]] ^ rk[13],
            _sbox[state[6]] ^ rk[14],
            _sbox[state[11]] ^ rk[15],
        ])

    def _decrypt_block(self, block):
        state = list(block)
        rk = self.round_keys[self.nr]
        for i in range(16):
            state[i] ^= rk[i]

        for r in range(self.nr - 1, 0, -1):
            shifted = [
                state[0], state[13], state[10], state[7],
                state[4], state[1], state[14], state[11],
                state[8], state[5], state[2], state[15],
                state[12], state[9], state[6], state[3],
            ]
            rk = self.round_keys[r]
            substituted = [_rsbox[value] ^ rk[i] for i, value in enumerate(shifted)]
            state = []
            for offset in range(0, 16, 4):
                state.extend(_inverse_mix_column(substituted[offset:offset + 4]))

        rk = self.round_keys[0]
        return bytes([
            _rsbox[state[0]] ^ rk[0],
            _rsbox[state[13]] ^ rk[1],
            _rsbox[state[10]] ^ rk[2],
            _rsbox[state[7]] ^ rk[3],
            _rsbox[state[4]] ^ rk[4],
            _rsbox[state[1]] ^ rk[5],
            _rsbox[state[14]] ^ rk[6],
            _rsbox[state[11]] ^ rk[7],
            _rsbox[state[8]] ^ rk[8],
            _rsbox[state[5]] ^ rk[9],
            _rsbox[state[2]] ^ rk[10],
            _rsbox[state[15]] ^ rk[11],
            _rsbox[state[12]] ^ rk[12],
            _rsbox[state[9]] ^ rk[13],
            _rsbox[state[6]] ^ rk[14],
            _rsbox[state[3]] ^ rk[15],
        ])

    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        data = bytes(data)

        if self.mode == MODE_ECB:
            if len(data) % 16:
                raise ValueError("Data must be aligned to 16-byte boundary in ECB mode")
            out = []
            for i in range(0, len(data), 16):
                out.append(self._encrypt_block(data[i:i+16]))
            return b"".join(out)

        elif self.mode == MODE_CBC:
            if len(data) % 16:
                raise ValueError("Data must be aligned to 16-byte boundary in CBC mode")
            out = []
            iv = list(self.iv)
            for i in range(0, len(data), 16):
                chunk = bytes([data[i+j] ^ iv[j] for j in range(16)])
                enc = self._encrypt_block(chunk)
                iv = list(enc)
                out.append(enc)
            return b"".join(out)

        elif self.mode == MODE_CTR:
            out = bytearray(len(data))
            ctr = int.from_bytes(self.iv, byteorder='big')
            for i in range(0, len(data), 16):
                ctr_bytes = ctr.to_bytes(16, byteorder='big')
                keystream = self._encrypt_block(ctr_bytes)
                for j in range(min(16, len(data) - i)):
                    out[i + j] = data[i + j] ^ keystream[j]
                ctr = (ctr + 1) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            return bytes(out)

        raise NotImplementedError(f"AES Mode {self.mode} not supported in pure Python")

    def decrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        data = bytes(data)

        if self.mode == MODE_ECB:
            if len(data) % 16:
                raise ValueError("Data must be aligned to 16-byte boundary in ECB mode")
            out = []
            for i in range(0, len(data), 16):
                out.append(self._decrypt_block(data[i:i+16]))
            return b"".join(out)

        elif self.mode == MODE_CBC:
            if len(data) % 16:
                raise ValueError("Data must be aligned to 16-byte boundary in CBC mode")
            out = []
            iv = list(self.iv)
            for i in range(0, len(data), 16):
                dec = self._decrypt_block(data[i:i+16])
                chunk = bytes([dec[j] ^ iv[j] for j in range(16)])
                iv = list(data[i:i+16])
                out.append(chunk)
            return b"".join(out)

        elif self.mode == MODE_CTR:
            return self.encrypt(data)

        raise NotImplementedError(f"AES Mode {self.mode} not supported in pure Python")

def new(key, mode=MODE_ECB, iv=None, **kwargs):
    if "IV" in kwargs and iv is None:
        iv = kwargs["IV"]
    return _AESCipher(key, mode=mode, iv=iv, counter=kwargs.get("counter"))
