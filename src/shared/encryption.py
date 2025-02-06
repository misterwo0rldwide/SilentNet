#   Encryption Handler Module
#
#       Contains classes for handling encryption tasks such as
#       Diffie-Hellman key exchange and AES encryption/decryption
#
#   Author: Omer Kfir (C)

import hashlib
from typing import Optional, Union
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

__author__ = "Omer Kfir"

DEBUG_FLAG = False

class DiffieHellman:
    """
        Handles Diffie-Hellman key exchange
    """

    def __init__(self, prime: int, base: int):
        """
            Initialize Diffie-Hellman with prime and base

            INPUT: prime, base
            OUTPUT: None

            @prime -> Prime number for the exchange
            @base -> Base number for the exchange
        """

        self.prime = prime
        self.base = base
        self.private_key = self._generate_private_key()

    def _generate_private_key(self) -> int:
        """
            Generates a private key

            INPUT: None
            OUTPUT: Private key (int)
        """

        return int.from_bytes(get_random_bytes(4), byteorder='big') % self.prime

    def get_public_key(self) -> int:
        """
            Generates a public key

            INPUT: None
            OUTPUT: Public key (int)
        """

        return pow(self.base, self.private_key, self.prime)

    def get_shared_secret(self, other_public_key: int) -> int:
        """
            Computes the shared secret using the other party's public key

            INPUT: other_public_key
            OUTPUT: Shared secret (int)

            @other_public_key -> The other party's public key
        """

        return pow(other_public_key, self.private_key, self.prime)


class AESHandler:
    """
        Handles AES encryption and decryption in ECB mode
    """

    def __init__(self, key: Optional[bytes] = None):
        """
            Initialize AESHandler with a key

            INPUT: key (optional)
            OUTPUT: None

            @key -> AES key (bytes)
        """
        if key is None:
            self.key = get_random_bytes(16)  # 128-bit key
        else:
            self.key = key

    def encrypt(self, data: Union[bytes, str]) -> bytes:
        """
            Encrypts data using AES in ECB mode

            INPUT: data
            OUTPUT: Encrypted data (bytes)

            @data -> Data to encrypt (bytes or str)
        """
        if isinstance(data, str):
            data = data.encode()

        # Pad the data to match the block size
        padded_data = pad(data, AES.block_size)
        cipher = AES.new(self.key, AES.MODE_ECB)
        return cipher.encrypt(padded_data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
            Decrypts data using AES in ECB mode

            INPUT: encrypted_data
            OUTPUT: Decrypted data (bytes)

            @encrypted_data -> Data to decrypt (bytes)
        """
        cipher = AES.new(self.key, AES.MODE_ECB)
        padded_data = cipher.decrypt(encrypted_data)
        return unpad(padded_data, AES.block_size)


class EncryptionHandler:
    """
        Main class to handle all encryption tasks
    """

    def __init__(self, prime: int, base: int):
        """
            Initialize EncryptionHandler with prime and base for DH

            INPUT: prime, base
            OUTPUT: None

            @prime -> Prime number for Diffie-Hellman
            @base -> Base number for Diffie-Hellman
        """
        self.dh = DiffieHellman(prime, base)
        self.aes_handler = None

    def get_public_key(self) -> int:
        """
            Returns the public key for Diffie-Hellman

            INPUT: None
            OUTPUT: Public key (int)
        """
        return self.dh.get_public_key()

    def generate_shared_secret(self, other_public_key: int) -> None:
        """
            Generates the shared secret and initializes AESHandler

            INPUT: other_public_key
            OUTPUT: None

            @other_public_key -> The other party's public key
        """
        shared_secret = self.dh.get_shared_secret(other_public_key)

        # Derive a 128-bit key from the shared secret using SHA-256
        self.aes_handler = AESHandler(hashlib.sha256(str(shared_secret).encode()).digest())

    def encrypt(self, data: Union[bytes, str]) -> bytes:
        """
            Encrypts data using AES

            INPUT: data
            OUTPUT: Encrypted data (bytes)

            @data -> Data to encrypt (bytes or str)
        """
        if self.aes_handler is None:
            raise ValueError("Shared secret not generated")
        
        return self.aes_handler.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
            Decrypts data using AES

            INPUT: encrypted_data
            OUTPUT: Decrypted data (bytes)

            @encrypted_data -> Data to decrypt (bytes)
        """
        if self.aes_handler is None:
            raise ValueError("Shared secret not generated")
        
        return self.aes_handler.decrypt(encrypted_data)