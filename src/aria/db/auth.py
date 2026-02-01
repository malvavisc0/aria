"""Authentication utilities for user management."""

import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256.

    Uses 100,000 iterations of PBKDF2-HMAC-SHA256 with a random salt.
    This is a secure password hashing method recommended by OWASP.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password in format: salt$hash

    Example:
        >>> hashed = hash_password("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    # Generate a random 16-byte (32 hex chars) salt
    salt = secrets.token_hex(16)

    # Hash the password with PBKDF2-HMAC-SHA256
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,  # 100,000 iterations
    )

    # Return salt and hash separated by $
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash.

    Args:
        password: Plain text password to verify
        hashed: Hashed password in format: salt$hash

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        # Split salt and hash
        salt, expected_hash = hashed.split("$")

        # Hash the provided password with the same salt
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )

        # Compare hashes (constant-time comparison)
        return secrets.compare_digest(pwd_hash.hex(), expected_hash)

    except (ValueError, AttributeError):
        # Invalid hash format or other error
        return False
