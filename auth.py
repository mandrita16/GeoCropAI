"""Password hashing helpers used by GeoCropAI's FastAPI routes.

New passwords are stored using PBKDF2-HMAC-SHA256 with a random salt.
For compatibility with older records, verification also accepts legacy
plain-text values and upgrades them on the next password change (the caller
must save the new hash to perform that upgrade).
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash for a password."""
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    ).hex()
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_password: str) -> bool:
    """Verify a PBKDF2 password hash, with a legacy plain-text fallback."""
    if not isinstance(password, str) or not isinstance(stored_password, str):
        return False

    parts = stored_password.split("$")
    if len(parts) == 4 and parts[0] == _ALGORITHM:
        try:
            iterations = int(parts[1])
            salt = parts[2]
            expected = parts[3]
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
            ).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    # Compatibility only for accounts created by an older version that stored
    # the password directly. New passwords are always hashed by hash_password.
    return hmac.compare_digest(password, stored_password)
