# Crypto/Cipher/AES.py
import struct

MODE_ECB = 1
MODE_CBC = 2
MODE_CFB = 3
MODE_CTR = 6
MODE_OFB = 5
MODE_OPENPGP = 7
MODE_CCM = 8
MODE_EAX = 9
MODE_SIV = 10
MODE_GCM = 11
MODE_OCB = 12

block_size = 16
key_size = (16, 24, 32)

# Rijndael S-Box
_SBOX = [
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
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i

_RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]

def _xtime(a):
    return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else (a << 1)

def _mul(a, b):
    res = 0
    while b > 0:
        if b & 1:
            res ^= a
        a = _xtime(a)
        b >>= 1
    return res

class _AESCipher:
    def __init__(self, key, mode=MODE_ECB, iv=None):
        if len(key) not in (16, 24, 32):
            raise ValueError(f"AES key must be 16, 24, or 32 bytes long, got {len(key)}")
        self.key = bytes(key)
        self.mode = mode
        self.block_size = 16
        self.rounds = {16: 10, 24: 12, 32: 14}[len(key)]

        if mode == MODE_CBC:
            if iv is None or len(iv) != 16:
                raise ValueError("IV must be 16 bytes for CBC mode")
            self.iv = bytearray(iv)
        else:
            self.iv = None

        self._key_expansion()

    def _key_expansion(self):
        nk = len(self.key) // 4
        nr = self.rounds
        w = list(struct.unpack(f">{nk}I", self.key))

        for i in range(nk, 4 * (nr + 1)):
            temp = w[i - 1]
            if i % nk == 0:
                temp = ((temp << 8) & 0xFFFFFFFF) | (temp >> 24)
                temp = ((_SBOX[(temp >> 24) & 0xFF] << 24) |
                        (_SBOX[(temp >> 16) & 0xFF] << 16) |
                        (_SBOX[(temp >> 8) & 0xFF] << 8) |
                        (_SBOX[temp & 0xFF]))
                temp ^= (_RCON[i // nk] << 24)
            elif nk > 6 and (i % nk == 4):
                temp = ((_SBOX[(temp >> 24) & 0xFF] << 24) |
                        (_SBOX[(temp >> 16) & 0xFF] << 16) |
                        (_SBOX[(temp >> 8) & 0xFF] << 8) |
                        (_SBOX[temp & 0xFF]))
            w.append(w[i - nk] ^ temp)

        self._round_keys = []
        for i in range(nr + 1):
            round_bytes = b"".join(struct.pack(">I", w[i * 4 + j]) for j in range(4))
            self._round_keys.append(list(round_bytes))

    def _encrypt_block(self, block):
        state = list(block)
        for r in range(self.rounds + 1):
            if r == 0:
                for i in range(16): state[i] ^= self._round_keys[0][i]
            else:
                for i in range(16): state[i] = _SBOX[state[i]]
                state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
                state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
                state[3], state[7], state[11], state[15] = state[15], state[3], state[7], state[11]

                if r < self.rounds:
                    for c in range(4):
                        i = c * 4
                        s0, s1, s2, s3 = state[i], state[i+1], state[i+2], state[i+3]
                        state[i]   = _xtime(s0) ^ _xtime(s1) ^ s1 ^ s2 ^ s3
                        state[i+1] = s0 ^ _xtime(s1) ^ _xtime(s2) ^ s2 ^ s3
                        state[i+2] = s0 ^ s1 ^ _xtime(s2) ^ _xtime(s3) ^ s3
                        state[i+3] = _xtime(s0) ^ s0 ^ s1 ^ s2 ^ _xtime(s3)

                for i in range(16): state[i] ^= self._round_keys[r][i]
        return bytes(state)

    def _decrypt_block(self, block):
        state = list(block)
        for r in range(self.rounds, -1, -1):
            if r == self.rounds:
                for i in range(16): state[i] ^= self._round_keys[self.rounds][i]
            else:
                state[5], state[9], state[13], state[1] = state[1], state[5], state[9], state[13]
                state[10], state[14], state[2], state[6] = state[2], state[6], state[10], state[14]
                state[15], state[3], state[7], state[11] = state[3], state[7], state[11], state[15]
                for i in range(16): state[i] = _INV_SBOX[state[i]]

                for i in range(16): state[i] ^= self._round_keys[r][i]

                if r > 0:
                    for c in range(4):
                        i = c * 4
                        s0, s1, s2, s3 = state[i], state[i+1], state[i+2], state[i+3]
                        state[i]   = _mul(s0, 0x0E) ^ _mul(s1, 0x0B) ^ _mul(s2, 0x0D) ^ _mul(s3, 0x09)
                        state[i+1] = _mul(s0, 0x09) ^ _mul(s1, 0x0E) ^ _mul(s2, 0x0B) ^ _mul(s3, 0x0D)
                        state[i+2] = _mul(s0, 0x0D) ^ _mul(s1, 0x09) ^ _mul(s2, 0x0E) ^ _mul(s3, 0x0B)
                        state[i+3] = _mul(s0, 0x0B) ^ _mul(s1, 0x0D) ^ _mul(s2, 0x09) ^ _mul(s3, 0x0E)
        return bytes(state)

    def encrypt(self, data):
        data = bytes(data)
        if len(data) % 16 != 0:
            raise ValueError("Input data length must be a multiple of 16")

        out = bytearray()
        if self.mode == MODE_ECB:
            for i in range(0, len(data), 16):
                out.extend(self._encrypt_block(data[i:i+16]))
        elif self.mode == MODE_CBC:
            iv = bytearray(self.iv)
            for i in range(0, len(data), 16):
                block = bytes(b ^ iv[j] for j, b in enumerate(data[i:i+16]))
                enc = self._encrypt_block(block)
                out.extend(enc)
                iv = bytearray(enc)
            self.iv = iv
        else:
            raise NotImplementedError(f"AES mode {self.mode} not supported")
        return bytes(out)

    def decrypt(self, data):
        data = bytes(data)
        if len(data) % 16 != 0:
            raise ValueError("Input data length must be a multiple of 16")

        out = bytearray()
        if self.mode == MODE_ECB:
            for i in range(0, len(data), 16):
                out.extend(self._decrypt_block(data[i:i+16]))
        elif self.mode == MODE_CBC:
            iv = bytearray(self.iv)
            for i in range(0, len(data), 16):
                dec = self._decrypt_block(data[i:i+16])
                plain = bytes(b ^ iv[j] for j, b in enumerate(dec))
                out.extend(plain)
                iv = bytearray(data[i:i+16])
            self.iv = iv
        else:
            raise NotImplementedError(f"AES mode {self.mode} not supported")
        return bytes(out)

def new(key, mode=MODE_ECB, iv=None, *args, **kwargs):
    if "IV" in kwargs and iv is None:
        iv = kwargs["IV"]
    return _AESCipher(key, mode=mode, iv=iv)
