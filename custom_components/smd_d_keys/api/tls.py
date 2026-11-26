"""TLS trust configuration for SMD endpoints.

SMD's wildcard certificate is currently served with the wrong intermediate:
the leaf is issued by ``GlobalSign GCC R46 OV TLS CA 2025``, but
``mde.s-m-d.ru`` sends the older ``GlobalSign RSA OV SSL CA 2018``
intermediate and ``vcmv.s-m-d.ru`` sends no intermediate at all. Strict TLS
clients cannot build a chain to a trusted root, so every request fails.

The bundled intermediate comes from the verified ``cmdc.s-m-d.ru`` chain,
which uses the same leaf certificate and does serve the correct chain. Trust
it for SMD requests only, and drop this workaround once SMD serves the full
chain everywhere.
"""

from __future__ import annotations

import ssl
from functools import cache
from pathlib import Path

EXTRA_CA_FILE = (
    Path(__file__).parent.parent / "certs" / ("globalsign_gcc_r46_ov_tls_ca_2025.pem")
)


@cache
def smd_ssl_context() -> ssl.SSLContext:
    """Return a verifying TLS context with the missing SMD intermediate."""
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=str(EXTRA_CA_FILE))
    return context
