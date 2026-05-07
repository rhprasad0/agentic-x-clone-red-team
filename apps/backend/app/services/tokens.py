import base64
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

ISSUANCE_RANDOM_BYTES = 32
BEARER_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,}$")


@dataclass(frozen=True)
class IssuedToken:
    value: str
    token_hash: str
    token_prefix: str
    issued_at: datetime


def generate_bearer_token() -> str:
    token_bytes = secrets.token_bytes(ISSUANCE_RANDOM_BYTES)
    return base64.urlsafe_b64encode(token_bytes).rstrip(b"=").decode("ascii")


def hash_bearer_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def diagnostic_token_prefix(token: str) -> str:
    return f"tok_{hash_bearer_token(token)[:10]}"


def issue_bearer_token() -> IssuedToken:
    token = generate_bearer_token()
    return IssuedToken(
        value=token,
        token_hash=hash_bearer_token(token),
        token_prefix=diagnostic_token_prefix(token),
        issued_at=datetime.now(UTC),
    )


def is_well_formed_bearer_token(token: str) -> bool:
    return bool(BEARER_VALUE_PATTERN.fullmatch(token))
