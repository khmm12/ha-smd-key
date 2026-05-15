"""Facade client for the reverse-engineered SMD D-KEYS API."""

from __future__ import annotations

from .auth import SmdAuthActions
from .cameras import SmdCameraActions
from .doors import SmdDoorActions
from .servers import SmdServerActions


class SmdDKeysClient(
    SmdAuthActions,
    SmdServerActions,
    SmdDoorActions,
    SmdCameraActions,
):
    """Client facade that combines SMD auth, server, door, and camera actions."""
