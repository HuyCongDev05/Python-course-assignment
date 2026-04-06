import base64
import hashlib
import hmac
import secrets


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260000
SALT_BYTES = 16


def hash_password(password):
    password = password or ""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    salt_token = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_token = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt_token}${digest_token}"


def is_password_hashed(password_value):
    return isinstance(password_value, str) and password_value.startswith(f"{PASSWORD_SCHEME}$")


def verify_password(password, stored_value):
    if password is None or not stored_value:
        return False

    if not is_password_hashed(stored_value):
        return hmac.compare_digest(str(password), str(stored_value))

    try:
        _, iterations, salt_token, digest_token = stored_value.split("$", 3)
        salt = base64.urlsafe_b64decode(salt_token.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(digest_token.encode("ascii"))
        computed_digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(computed_digest, expected_digest)
    except Exception:
        return False
