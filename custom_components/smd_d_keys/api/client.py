"""Facade client for the reverse-engineered SMD D-KEYS API."""

from __future__ import annotations

from .auth import SmdAuthActions
from .cameras import SmdCameraActions
from .doors import SmdDoorActions
from .notifications import SmdNotificationActions
from .servers import SmdServerActions


class SmdDKeysClient(
    SmdAuthActions,
    SmdServerActions,
    SmdDoorActions,
    SmdCameraActions,
    SmdNotificationActions,
):
    """Client facade that combines SMD auth, server, door, camera, and push actions."""
