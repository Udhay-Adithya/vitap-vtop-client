"""
TLS configuration for talking to VTOP.

VTOP's server omits the Sectigo intermediate CA from its certificate chain, so
a default Python TLS setup cannot build a path to a trusted root and fails with
CERTIFICATE_VERIFY_FAILED. This module builds an SSL context that trusts the
normal certifi roots plus the bundled intermediate (see certs/README.md), which
lets the chain verify without weakening verification.

This mirrors how the lib_vtop rust crate handles the same server misconfiguration.
"""

import ssl
from functools import lru_cache
from pathlib import Path

import certifi

_INTERMEDIATE_CERT = (
    Path(__file__).parent / "certs" / "vitap_sectigo_intermediate.pem"
)


@lru_cache(maxsize=1)
def create_vtop_ssl_context() -> ssl.SSLContext:
    """
    Builds the SSL context used for VTOP requests.

    Trust anchors are the certifi root bundle plus VTOP's missing intermediate.
    The context is cached, since building it reads two files off disk.

    Returns:
        ssl.SSLContext: A verifying context that can complete VTOP's chain.
    """
    # Start from certifi rather than the platform default, because some
    # environments (notably Homebrew Python on macOS) point at an empty or
    # missing system CA file.
    context = ssl.create_default_context(cafile=certifi.where())

    if _INTERMEDIATE_CERT.exists():
        context.load_verify_locations(cafile=str(_INTERMEDIATE_CERT))

    return context
