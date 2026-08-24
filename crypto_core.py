import os
import random
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple, List

class CryptoManager:
    # Prime used for Shamir's secret sharing (256-bit prime)
    PRIME = 2**256 - 2**32 - 977
    
    @staticmethod
    def _eval_poly(poly: List[int], x: int, prime: int) -> int:
        result = 0
        for coeff in reversed(poly):
            result = (result * x + coeff) % prime
        return result

    @staticmethod
    def _mod_inverse(a: int, prime: int) -> int:
        return pow(a, -1, prime)

    @classmethod
    def generate_shares(cls, secret: int, n: int, k: int) -> List[Tuple[int, int]]:
        poly = [secret] + [random.randint(1, cls.PRIME - 1) for _ in range(k - 1)]
        shares = []
        for i in range(1, n + 1):
            x = i
            y = cls._eval_poly(poly, x, cls.PRIME)
            shares.append((x, y))
        return shares

    @classmethod
    def reconstruct_secret(cls, shares: List[Tuple[int, int]], k: int) -> int:
        if len(shares) < k:
            raise ValueError("Not enough shares to reconstruct the secret")
            
        shares = shares[:k]
        secret = 0
        for i in range(k):
            x_i, y_i = shares[i]
            numerator, denominator = 1, 1
            for j in range(k):
                if i != j:
                    x_j, _ = shares[j]
                    numerator = (numerator * (-x_j)) % cls.PRIME
                    denominator = (denominator * (x_i - x_j)) % cls.PRIME
            
            lagrange_poly = (y_i * numerator * cls._mod_inverse(denominator, cls.PRIME)) % cls.PRIME
            secret = (cls.PRIME + secret + lagrange_poly) % cls.PRIME
            
        return secret

    @staticmethod
    def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
        if len(key) not in {16, 24, 32}:
            raise ValueError("Invalid key size. Must be 16, 24, or 32 bytes.")
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def decrypt_payload(key: bytes, ciphertext_with_nonce: bytes) -> bytes:
        if len(ciphertext_with_nonce) < 12:
            raise ValueError("Invalid ciphertext length")
        nonce = ciphertext_with_nonce[:12]
        ciphertext = ciphertext_with_nonce[12:]
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError("Decryption failed. Invalid key or modified ciphertext.")

class DoubleGateEnforcer:
    def __init__(self, exam_start_time: float, threshold_k: int):
        self.exam_start_time = exam_start_time
        self.threshold_k = threshold_k

    def can_unlock(self, current_time: float, collected_shares_count: int) -> bool:
        if current_time < self.exam_start_time:
            return False
        if collected_shares_count < self.threshold_k:
            return False
        return True
