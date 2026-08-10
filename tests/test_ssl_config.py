"""
Guards for the bundled CA certificate.

VTOP omits an intermediate CA from its TLS chain, so the client ships that
intermediate and loads it. If the cert goes missing from the package or the
context stops trusting it, every request fails with a TLS error. These tests
catch that before it ships, without touching the network.
"""

import ssl
from pathlib import Path

import vitap_vtop_client
from vitap_vtop_client.ssl_config import create_vtop_ssl_context

_CERT = (
    Path(vitap_vtop_client.__file__).parent
    / "certs"
    / "vitap_sectigo_intermediate.pem"
)


def test_bundled_certificate_is_present():
    assert _CERT.exists(), "the bundled VTOP intermediate cert is missing"
    text = _CERT.read_text()
    assert "BEGIN CERTIFICATE" in text and "END CERTIFICATE" in text


def test_ssl_context_verifies_and_loads_the_intermediate():
    context = create_vtop_ssl_context()

    # Verification must stay on; the point is to complete the chain, not skip it.
    assert context.verify_mode == ssl.CERT_REQUIRED

    # The bundled intermediate should be among the loaded CA certs.
    subjects = {
        tuple(sorted(part for rdn in cert["subject"] for part in rdn))
        for cert in context.get_ca_certs()
    }
    assert any(
        any("Sectigo Public Server Authentication CA DV R36" in value
            for value in subject)
        for subject in subjects
    ), "the VTOP intermediate is not trusted by the context"
