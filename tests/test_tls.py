"""Tests for the SMD TLS trust configuration."""

from __future__ import annotations

import ssl

from custom_components.smd_d_keys.api.tls import EXTRA_CA_FILE, smd_ssl_context


def test_smd_ssl_context_trusts_missing_intermediate() -> None:
    """The SMD context verifies hosts and includes the served-chain fix."""
    assert EXTRA_CA_FILE.is_file()

    context = smd_ssl_context()

    assert context is smd_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    common_names = {
        value
        for cert in context.get_ca_certs()
        for attributes in cert["subject"]
        for name, value in attributes
        if name == "commonName"
    }
    assert "GlobalSign GCC R46 OV TLS CA 2025" in common_names
