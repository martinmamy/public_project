from django.db import models
from django.conf import settings
import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class AESCipher:
    def __init__(self, key: bytes):
        self.key = key
        self.backend = default_backend()

    def encrypt(self, plaintext: str) -> str:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        padded_plaintext = self._pad(plaintext.encode('utf-8'))
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        return base64.urlsafe_b64encode(iv + ciphertext).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        data = base64.urlsafe_b64decode(ciphertext)
        iv = data[:16]
        ciphertext = data[16:]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return self._unpad(padded_plaintext).decode('utf-8')

    def _pad(self, plaintext: bytes) -> bytes:
        pad_length = 16 - (len(plaintext) % 16)
        return plaintext + bytes([pad_length] * pad_length)

    def _unpad(self, padded_plaintext: bytes) -> bytes:
        pad_length = padded_plaintext[-1]
        return padded_plaintext[:-pad_length]
