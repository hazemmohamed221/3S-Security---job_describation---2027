"""Argon2id only: never compare stored credentials with plaintext."""
from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

HASHER = PasswordHasher(type=Type.ID)


def is_password_hash(value):
    if not isinstance(value, str) or not value.startswith("$argon2id$"):
        return False
    try:
        return extract_parameters(value).type == Type.ID
    except (InvalidHashError, ValueError):
        return False


def hash_password(password):
    if not isinstance(password, str) or not password:
        raise ValueError("A non-empty password is required.")
    return HASHER.hash(password)


def verify_password(stored, password):
    if not is_password_hash(stored) or not isinstance(password, str) or not password:
        return False
    try:
        return HASHER.verify(stored, password)
    except (VerificationError, InvalidHashError, ValueError):
        return False
