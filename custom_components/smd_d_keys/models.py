"""Models for SMD D-KEYS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import SmdDKeysClient
    from .coordinator import SmdDKeysCoordinator


@dataclass(frozen=True, slots=True)
class SmdDoor:
    """Runtime representation of an SMD door key."""

    id: str
    title: str
    address: str | None
    code_key: str | None
    mqtt_topic: str | None
    command: str | None
    uid: str | None
    code_mp: str | None
    room_number: str | None
    options: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        """Return a human-friendly display name for config forms."""
        return f"{self.title} ({self.address})" if self.address else self.title

    def with_open_command(
        self, *, mqtt_topic: str | None, command: str | None
    ) -> SmdDoor:
        """Return a copy enriched with the MQTT open command."""
        return SmdDoor(
            id=self.id,
            title=self.title,
            address=self.address,
            code_key=self.code_key,
            mqtt_topic=mqtt_topic or self.mqtt_topic,
            command=command or self.command,
            uid=self.uid,
            code_mp=self.code_mp,
            room_number=self.room_number,
            options=self.options,
        )

    def has_option(self, option: str) -> bool:
        """Return whether this key advertises an SMD option."""
        return option in self.options


@dataclass(frozen=True, slots=True)
class SmdCamera:
    """Runtime representation of an SMD live video broadcast."""

    id: str
    door_id: str
    title: str
    address: str | None
    code_key: str
    code_mp: str
    srv: str
    protocol: str
    uid: str | None
    online: bool | None


@dataclass(slots=True)
class SmdDKeysRuntimeData:
    """Runtime data stored on the config entry."""

    client: SmdDKeysClient
    coordinator: SmdDKeysCoordinator
