"""Encryption helper for the Million Dirham Spin dashboard.

The dashboard's figures are published encrypted. keys.json holds a public key
(used here to encrypt) and the matching private key locked with the dashboard
passphrase (only the page, with the passphrase, can unlock it). No secret is
needed to encrypt, so the scheduled refresh needs none.
"""
import base64, json, os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

b64 = lambda b: base64.b64encode(b).decode()


def seal(obj, keys_path):
    """Encrypt a JSON-serialisable object for the dashboard."""
    pub = serialization.load_der_public_key(base64.b64decode(json.load(open(keys_path))["pub"]))
    key, iv = AESGCM.generate_key(256), os.urandom(12)
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(), None)
    wrapped = pub.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return {"v": 1, "k": b64(wrapped), "iv": b64(iv), "ct": b64(ct)}
