"""Build the radcheck password value for the configured password scheme.

Which attribute is used is driven by RADIUS_PASSWORD_ATTRIBUTE (.env):
Cleartext-Password (default), SSHA-Password, or NT-Password.
"""

import base64
import hashlib
import os

from passlib.hash import nthash

SUPPORTED_PASSWORD_ATTRIBUTES = ("Cleartext-Password", "SSHA-Password", "NT-Password")


class UnsupportedPasswordAttributeError(Exception):
    pass


def build_password_value(password: str, attribute: str) -> str:
    """Encode `password` the way FreeRADIUS expects for `attribute`."""
    if attribute == "Cleartext-Password":
        return password
    if attribute == "SSHA-Password":
        salt = os.urandom(8)
        digest = hashlib.sha1(password.encode("utf-8") + salt).digest()
        return base64.b64encode(digest + salt).decode("ascii")
    if attribute == "NT-Password":
        return nthash.hash(password).upper()
    raise UnsupportedPasswordAttributeError(attribute)
