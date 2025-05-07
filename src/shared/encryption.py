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
from cryptography.hazmat.primitives.asymmetric import dh
from random import randint

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
        
        if self.prime == 0 or self.base == 0:
            parameters = dh.generate_parameters(generator=2, key_size=512)
            self.prime = parameters.parameter_numbers().p
            self.base = parameters.parameter_numbers().g
            
        self.private_key = self._generate_private_key()

    def _generate_private_key(self) -> int:
        """
            Generates a private key

            INPUT: None
            OUTPUT: Private key (int)
        """

        return randint(2, self.prime - 2)

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
        Handles AES encryption and decryption in CBC mode
    """

    def __init__(self, key: Optional[bytes] = None):
        """
            Initialize AESHandler with a key

            INPUT: key (optional)
            OUTPUT: None

            @key -> AES key (bytes)
        """
        if key is None:
            self.key = get_random_bytes(32)  # 256-bit key
        else:
            self.key = key

    def encrypt(self, data: Union[bytes, str]) -> bytes:
        """
            Encrypts data using AES in CBC mode

            INPUT: data
            OUTPUT: Encrypted data (bytes)

            @data -> Data to encrypt (bytes or str)
        """
        if isinstance(data, str):
            data = data.encode()

        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        
        cipher_text = cipher.encrypt(pad(data, AES.block_size))
        return iv + cipher_text

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
            Decrypts data using AES in CBC mode

            INPUT: encrypted_data
            OUTPUT: Decrypted data (bytes)

            @encrypted_data -> Data to decrypt (bytes), first AES.block_size bytes are for iv
        """
        if type(encrypted_data) is not bytes:
            encrypted_data = encrypted_data.encode()

        decrypt_cipher = AES.new(self.key, AES.MODE_CBC, encrypted_data[:AES.block_size])
        plain_text = decrypt_cipher.decrypt(encrypted_data[AES.block_size:])

        return unpad(plain_text, AES.block_size)


class EncryptionHandler:
    """
        Main class to handle all encryption tasks
    """

    def __init__(self, base: int = 0, prime: int = 0):
        """
            Initialize EncryptionHandler with prime and base for DH

            INPUT: prime, base
            OUTPUT: None

            @prime -> Prime number for DH
            @base -> Base number for DH
        """
        self.dh = DiffieHellman(prime, base)
        self.aes_handler = None
    
    def get_base_prime(self) -> tuple[int, int]:
        """
            Returns the base and prime for Diffie-Hellman

            INPUT: None
            OUTPUT: Tuple of base and prime (int, int)
        """
        return self.dh.base, self.dh.prime

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

        # Ensure shared_secret is in bytes before hashing
        shared_secret_bytes = shared_secret.to_bytes((shared_secret.bit_length() + 7) // 8, byteorder="little")
        derived_key = hashlib.sha256(shared_secret_bytes).digest()

        # Use the derived key for AES
        self.aes_handler = AESHandler(derived_key)

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