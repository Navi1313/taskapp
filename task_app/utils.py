import base64
import time
import bcrypt
import jwt

# ---------------------------------------------------------------------------
# BCrruptUtil – bcrypt password helpers
# ---------------------------------------------------------------------------

class BCrruptUtil:

    @staticmethod
    def encrypt_password(plain_password: str) -> str:
        """Hash a plain-text password using bcrypt and return a UTF-8 string."""
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')

    @staticmethod
    def verify_method(plain_password: str, hash_password: str) -> bool:
        """Verify a plain-text password against a stored bcrypt hash."""
        if not plain_password or not hash_password:
            return False
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hash_password.encode('utf-8')
            )
        except ValueError:
            # Fallback for legacy/test plain-text passwords in the DB
            return plain_password == hash_password


# ---------------------------------------------------------------------------
# JWTUtil – JSON Web Token helpers
# ---------------------------------------------------------------------------

# Secret key used to sign tokens.  In production, move this to an environment
# variable or Django settings and keep it secret.
_JWT_SECRET = b'task-app-jwt-secret-key-change-me-in-production'
_JWT_ALGORITHM = 'HS256'
_TOKEN_EXPIRY_SECONDS = 15 * 60  # 15 minutes


def _build_signing_key():
    """Construct a symmetric JWK key object from the shared secret."""
    k_b64 = base64.urlsafe_b64encode(_JWT_SECRET).decode('utf-8').rstrip('=')
    return jwt.jwk_from_dict({'kty': 'oct', 'k': k_b64})


class JWTUtil:

    @staticmethod
    def create_token(user_id: str) -> str:
        """
        Create a signed JWT for the given user_id.

        The token includes:
          - ``sub``  – the user ID (string)
          - ``iat``  – issued-at timestamp (epoch seconds)
          - ``exp``  – expiry timestamp, 15 minutes after iat (epoch seconds)

        Returns the compact serialised token string.
        """
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + _TOKEN_EXPIRY_SECONDS,
        }
        instance = jwt.JWT()
        token = instance.encode(payload, _build_signing_key(), alg=_JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verify a JWT and return its decoded payload.

        Raises:
            jwt.exceptions.JWTDecodeError – if the token is invalid or expired.
            Exception – for any other error during decoding.

        Returns the payload dict, e.g. {'sub': '<user_id>', 'iat': ..., 'exp': ...}
        """
        instance = jwt.JWT()
        # do_time_check=True enforces 'exp' / 'nbf' validation automatically
        payload = instance.decode(
            token,
            _build_signing_key(),
            do_time_check=True,
            algorithms={_JWT_ALGORITHM},
        )
        return payload
