"""
RSA-PSS authentication for Kalshi API v2.

Every request requires three headers:
  KALSHI-ACCESS-KEY:       your API key ID
  KALSHI-ACCESS-TIMESTAMP: current time in milliseconds (string)
  KALSHI-ACCESS-SIGNATURE: base64(RSA-PSS(timestamp + METHOD + path))

Setup:
  1. Generate an RSA key pair (see below)
  2. Upload the public key to Kalshi (Settings → API Keys)
  3. Set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH in .env

To generate a key pair:
  openssl genrsa -out kalshi_private.pem 2048
  openssl rsa -in kalshi_private.pem -pubout -out kalshi_public.pem
  # Upload kalshi_public.pem to Kalshi dashboard
"""

import base64
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _load_private_key(pem_path: str):
    pem_bytes = Path(pem_path).read_bytes()
    return serialization.load_pem_private_key(pem_bytes, password=None)


def make_headers(method: str, path: str, key_id: str, private_key_path: str) -> dict[str, str]:
    """Return the three Kalshi auth headers for a given request."""
    timestamp_ms = str(int(time.time() * 1000))
    message = (timestamp_ms + method.upper() + path).encode()

    private_key = _load_private_key(private_key_path)
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    encoded_sig = base64.b64encode(signature).decode()

    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "KALSHI-ACCESS-SIGNATURE": encoded_sig,
        "Content-Type": "application/json",
    }
