"""Support for WEBFLEET platform."""
import logging

from datetime import datetime, timedelta
import async_timeout

from typing import Any, Mapping

from homeassistant.components.device_tracker.const import (
    SourceType,
)
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_API_KEY,
    CONF_AT,
    CONF_DEVICES,
)
from wfconnect.wfconnect import WfConnect

from .const import DOMAIN as WF_DOMAIN
from .api_types import ShowObjectReportExternResult


_LOGGER = logging.getLogger(__name__)

ENTITY_ID_FORMAT = "webfleet" + ".{}"

ICON_CAR = "mdi:car"
ICON_BUS = "mdi:bus"
ICON_TRUCK = "mdi:truck"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    _LOGGER.debug("async_setup_entry %s", entry)
    config = entry.data

    webfleet_api = hass.data[WF_DOMAIN][entry.entry_id]

    webfleet_api.setAuthentication(
        config.get(CONF_AT),
        config.get(CONF_USERNAME),
        config.get(CONF_PASSWORD),
        config.get(CONF_API_KEY),
    )
    group = config.get(CONF_DEVICES)
    coordinator = WebfleetCoordinator(hass, webfleet_api, group)

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady

    async_add_entities(
        WebfleetEntity(
            coordinator,
            coordinator.data[idx].entity_id,
            coordinator.data[idx].vehicle_data,
        )
        for idx, ent in enumerate(coordinator.data)
    )


class WebfleetCoordinator(DataUpdateCoordinator):
    api: WfConnect
    hass: HomeAssistant
    vehicle_ids: list[str]
    group: str | None
    vehicles: list["WebfleetEntity"]

    data: list["WebfleetEntity"]  # FIXME: supertype defines it as dict[str, Any]

    def __init__(self, hass: HomeAssistant, webfleet_connect_api: WfConnect, group: str | None) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Webfleet",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self.api = webfleet_connect_api
        self.hass = hass
        self.vehicle_ids = []
        self.group = group
        self.vehicles = []

    async def _async_update_data(self) -> list["WebfleetEntity"] | None:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await self.fetch_data()

        except Exception as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err

    #        except ApiError as err:
    #            raise UpdateFailed(f"Error communicating with API: {err}")

    async def get_vehicle_details_api(self) -> list[ShowObjectReportExternResult]:
        def blocking_call() -> list[ShowObjectReportExternResult]:
            return self.api.showObjectReportExtern(objectgroupname=self.group)

        return await self.hass.async_add_executor_job(blocking_call)

    async def fetch_data(self) -> list["WebfleetEntity"] | None:
        """Update the device info."""
        _LOGGER.debug("Scanning for devices")

        # Update self.devices to collect new devices added
        # to the users account.
        try:
            vehicles = await self.get_vehicle_details_api()
            discovered_vehicle_ids: list[str] = []
            # newvehicle_ids = []
            for vehicle in vehicles:
                object_uid = vehicle["objectuid"]
                discovered_vehicle_ids.append(object_uid)
                existing_vehicle = self.get_device(object_uid)
                if existing_vehicle is None:
                    entity_id = async_generate_entity_id(
                        ENTITY_ID_FORMAT, object_uid, self.vehicle_ids, self.hass
                    )
                    entity = WebfleetEntity(self, entity_id, vehicle)
                    self.vehicles.append(entity)
                else:
                    _LOGGER.debug(
                        "Vehicle already discovered, updating: %s", object_uid
                    )
                    existing_vehicle.update(vehicle)

            # Add new or remove vehicles no longer present
            self.vehicles = [
                entity
                for entity in self.vehicles
                if entity.device_id in discovered_vehicle_ids
            ]
            self.vehicle_ids = [vehicle.device_id for vehicle in self.vehicles]
            return self.vehicles

        except Exception:
            _LOGGER.warning("Update not successful:", exc_info=True)
            return None

    def get_device(self, device_id: str) -> "WebfleetEntity | None":
        for vehicle in self.vehicles:
            if vehicle.device_id == device_id:
                _LOGGER.debug("get_device for %s %s", device_id, vehicle.name)
                return vehicle
        return None


class WebfleetEntity(CoordinatorEntity, TrackerEntity):
    """Represent a tracked device."""
    vehicle_data: ShowObjectReportExternResult
    entity_id: str

    def __init__(self, coordinator: WebfleetCoordinator, entity_id: str, vehicle_data: ShowObjectReportExternResult) -> None:
        super().__init__(coordinator)
        self.vehicle_data = (
            vehicle_data  # TODO: Looks like the update call cannot initiate the entity
        )
        self.entity_id = entity_id

        self._attr_unique_id = self.vehicle_data['objectuid']

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    def update(self, vehicle_data: ShowObjectReportExternResult) -> None:
        self.vehicle_data = vehicle_data

    @property
    def name(self) -> str | None:
        return self.vehicle_data["objectname"]
        # return slugify(self._entity_id)

    @property
    def location_name(self) -> str | None:
        """Not returning a location to enable HA matching Zones based on GPS"""
        return None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def icon(self) -> str | None:
        return ICON_CAR

    @property
    def device_id(self) -> str:
        return self.vehicle_data["objectuid"]

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(WF_DOMAIN, self.device_id)},
            name=self.name,
        )

    @property
    def latitude(self) -> float | None:
        if self.vehicle_data is None:
            return None
        lat_mdeg = self.vehicle_data["latitude_mdeg"]
        if not isinstance(lat_mdeg, int):
            return None
        return lat_mdeg / 1_000_000

    @property
    def longitude(self) -> float | None:
        lon_mdeg = self.vehicle_data["longitude_mdeg"]
        if not isinstance(lon_mdeg, int):
            return None
        return lon_mdeg / 1_000_000

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        vehicle_data: dict[str, float | str | datetime | None] = self.vehicle_data.copy()

        # Overwriting lat lon necessary to avoid ha issues.
        vehicle_data["latitude"] = self.latitude
        vehicle_data["longitude"] = self.longitude

        # Not supported anymore. This was only specific to LINK classic.
        del vehicle_data["quality"]
        del vehicle_data["satellite"]

        return vehicle_data
