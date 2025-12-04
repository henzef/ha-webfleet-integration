"""Support for Webfleet live cameras (WebRTC)."""
import logging
import aiohttp
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN as WF_DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Endpoints ---
TOKEN_URL = "https://dev-login.webfleet.com/auth/realms/webfleet/protocol/openid-connect/token"
CAMERA_API_URL = "https://camera-management-service.dev-2.webfleet.cloud/cameras/{camera_id}/initiateWebRtcLiveView"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Webfleet cameras from a config entry."""
    config = entry.data
    camera_id = config.get("camera_id", "88898")
    username = config.get("username", "admin@TeamVolt_Camera")
    password = config.get("password", "TeamVolt<3")

    async_add_entities([WebfleetCamera(camera_id, username, password)], True)


class WebfleetCamera(Camera):
    """Representation of a Webfleet camera that provides a WebRTC stream."""

    def __init__(self, camera_id: str, username: str, password: str) -> None:
        super().__init__()
        self._attr_name = f"Webfleet Camera {camera_id}"
        self._attr_unique_id = f"webfleet_camera_{camera_id}"
        self.camera_id = camera_id
        self.username = username
        self.password = password
        self.token: str | None = None
        self.webrtc_info: dict[str, Any] | None = None

    async def async_get_access_token(self) -> str:
        """Authenticate and obtain an access token."""
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": "swagger",
            "client_secret": "test1",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(TOKEN_URL, data=data) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    _LOGGER.error("Failed to get token: %s", txt)
                    raise RuntimeError(f"Authentication failed: {txt}")
                result = await resp.json()
                return result["access_token"]

    async def async_initiate_live_view(self) -> dict[str, Any]:
        """Initiate WebRTC live view session."""
        token = self.token or await self.async_get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"version": "1.0.2"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                CAMERA_API_URL.format(camera_id=self.camera_id),
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    _LOGGER.error("Failed to initiate live view: %s", txt)
                    raise RuntimeError(f"Live view request failed: {txt}")
                self.webrtc_info = await resp.json()
                _LOGGER.debug("Received WebRTC info: %s", self.webrtc_info)
                return self.webrtc_info

    async def async_handle_webrtc_offer(self, offer_sdp: str) -> dict[str, Any]:
        """Handle WebRTC offer from frontend (for WebRTC Camera Card)."""
        # Este método no envía el SDP a tu cámara (no hay endpoint para eso en Webfleet),
        # pero retorna la metadata WebRTC para que la tarjeta personalizada la use.
        if not self.webrtc_info:
            await self.async_initiate_live_view()

        return {
            "type": "answer",
            "sdp": offer_sdp,
            "camera_info": self.webrtc_info,
        }

    async def stream_source(self) -> str | None:
        """Return a symbolic WebRTC URL (for frontend cards)."""
        if not self.webrtc_info:
            await self.async_initiate_live_view()

        gw = self.webrtc_info["data"]["deviceGateway"]
        return f"webrtc://{gw}/{self.camera_id}"

    async def async_camera_image(self, width: int = None, height: int = None) -> bytes | None:
        """Return placeholder image since Webfleet doesn't support snapshots."""
        return None
