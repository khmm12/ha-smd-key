"""Server discovery actions for the SMD D-KEYS API."""

from __future__ import annotations

import logging

from . import helpers
from .base import SmdBaseClient
from .errors import SmdMalformedResponseError

_LOGGER = logging.getLogger(__name__)


class SmdServerActions(SmdBaseClient):
    """Resolve runtime service endpoints advertised by SMD."""

    async def async_get_servers(self) -> dict[str, str]:
        """Fetch server overrides and update the runtime CMDC URL."""
        payload = await self._post_mde_form(
            self._common_params({"action": "getServers"})
        )
        self._raise_for_error(payload, authenticated=True)
        servers: dict[str, str] = {}
        try:
            for item in helpers.expect_list(payload.get("DATA"), "DATA"):
                server = helpers.expect_mapping(item, "DATA[]")
                name = str(server.get("server") or "")
                domain = str(server.get("domen") or "")
                if name and domain:
                    servers[name] = domain
        except SmdMalformedResponseError:
            _LOGGER.warning(
                "SMD getServers response had an unexpected shape: %s",
                helpers.safe_payload_summary(payload),
            )
            raise
        normalized_servers: dict[str, str] = {}
        for name, domain in servers.items():
            normalized_servers[name.upper()] = domain
        self._server_urls = {
            name: domain.rstrip("/") for name, domain in normalized_servers.items()
        }
        if cmdc_url := normalized_servers.get("CMDC"):
            self.cmdc_url = cmdc_url.rstrip("/")
        if l2_url := normalized_servers.get("L2"):
            self.l2_url = l2_url.rstrip("/")
        _LOGGER.debug(
            "SMD server discovery completed: count=%s has_cmdc=%s has_l2=%s",
            len(servers),
            "CMDC" in normalized_servers,
            "L2" in normalized_servers,
        )
        return servers
