"""Support for Samsung Printers with SyncThru web interface."""
from __future__ import annotations

from pysyncthru import SyncThru, SyncthruState

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import device_identifiers
from .const import DOMAIN

COLORS = ["black", "cyan", "magenta", "yellow"]
DRUM_COLORS = COLORS
TONER_COLORS = COLORS
TRAYS = range(1, 6)
OUTPUT_TRAYS = range(0, 6)
DEFAULT_MONITORED_CONDITIONS = []
DEFAULT_MONITORED_CONDITIONS.extend([f"toner_{key}" for key in TONER_COLORS])
DEFAULT_MONITORED_CONDITIONS.extend([f"drum_{key}" for key in DRUM_COLORS])
DEFAULT_MONITORED_CONDITIONS.extend([f"tray_{key}" for key in TRAYS])
DEFAULT_MONITORED_CONDITIONS.extend([f"output_tray_{key}" for key in OUTPUT_TRAYS])

SYNCTHRU_STATE_HUMAN = {
    SyncthruState.INVALID: "invalid",
    SyncthruState.OFFLINE: "unreachable",
    SyncthruState.NORMAL: "normal",
    SyncthruState.UNKNOWN: "unknown",
    SyncthruState.WARNING: "warning",
    SyncthruState.TESTING: "testing",
    SyncthruState.ERROR: "error",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up from config entry."""

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    printer: SyncThru = coordinator.data

    supp_toner = printer.toner_status(filter_supported=True)
    supp_drum = printer.drum_status(filter_supported=True)
    supp_tray = printer.input_tray_status(filter_supported=True)
    supp_output_tray = printer.output_tray_status()

    name = config_entry.data[CONF_NAME]
    entities = [SyncThruMainSensor(coordinator, name)]

    for key in supp_toner:
        entities.append(SyncThruTonerSensor(coordinator, name, key))
    for key in supp_drum:
        entities.append(SyncThruDrumSensor(coordinator, name, key))
    for key in supp_tray:
        entities.append(SyncThruInputTraySensor(coordinator, name, key))
    for key in supp_output_tray:
        entities.append(SyncThruOutputTraySensor(coordinator, name, key))

    async_add_entities(entities)


class SyncThruSensor(CoordinatorEntity, SensorEntity):
    """Implementation of an abstract Samsung Printer sensor platform."""

    def __init__(self, coordinator, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.syncthru: SyncThru = coordinator.data
        self._name = name
        self._icon = "mdi:printer"
        self._unit_of_measurement = None
        self._id_suffix = ""

    @property
    def unique_id(self):
        """Return unique ID for the sensor."""
        serial = self.syncthru.serial_number()
        return f"{serial}{self._id_suffix}" if serial else None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon of the device."""
        return self._icon

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measuremnt."""
        return self._unit_of_measurement

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information."""
        if (identifiers := device_identifiers(self.syncthru)) is None:
            return None
        return DeviceInfo(
            identifiers=identifiers,
        )


class SyncThruMainSensor(SyncThruSensor):
    """
    Implementation of the main sensor, conducting the actual polling.

    It also shows the detailed state and presents
    the displayed current status message.
    """

    def __init__(self, coordinator, name):
        """Initialize the sensor."""
        super().__init__(coordinator, name)
        self._id_suffix = "_main"

    @property
    def native_value(self):
        """Set state to human readable version of syncthru status."""
        return SYNCTHRU_STATE_HUMAN[self.syncthru.device_status()]

    @property
    def extra_state_attributes(self):
        """Show current printer display text."""
        return {
            "display_text": self.syncthru.device_status_details(),
        }

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Disable entity by default."""
        return False


class SyncThruTonerSensor(SyncThruSensor):
    """Implementation of a Samsung Printer toner sensor platform."""

    def __init__(self, coordinator, name, color):
        """Initialize the sensor."""
        super().__init__(coordinator, name)
        self._name = f"{name} Toner {color}"
        self._color = color
        self._unit_of_measurement = PERCENTAGE
        self._id_suffix = f"_toner_{color}"

    @property
    def extra_state_attributes(self):
        """Show all data returned for this toner."""
        return self.syncthru.toner_status().get(self._color, {})

    @property
    def native_value(self):
        """Show amount of remaining toner."""
        return self.syncthru.toner_status().get(self._color, {}).get("remaining")


class SyncThruDrumSensor(SyncThruSensor):
    """Implementation of a Samsung Printer toner sensor platform."""

    def __init__(self, syncthru, name, color):
        """Initialize the sensor."""
        super().__init__(syncthru, name)
        self._name = f"{name} Drum {color}"
        self._color = color
        self._unit_of_measurement = PERCENTAGE
        self._id_suffix = f"_drum_{color}"

    @property
    def extra_state_attributes(self):
        """Show all data returned for this drum."""
        return self.syncthru.drum_status().get(self._color, {})

    @property
    def native_value(self):
        """Show amount of remaining drum."""
        return self.syncthru.drum_status().get(self._color, {}).get("remaining")


class SyncThruInputTraySensor(SyncThruSensor):
    """Implementation of a Samsung Printer input tray sensor platform."""

    def __init__(self, syncthru, name, number):
        """Initialize the sensor."""
        super().__init__(syncthru, name)
        self._name = f"{name} Tray {number}"
        self._number = number
        self._id_suffix = f"_tray_{number}"

    @property
    def extra_state_attributes(self):
        """Show all data returned for this input tray."""
        return self.syncthru.input_tray_status().get(self._number, {})

    @property
    def native_value(self):
        """Display ready unless there is some error, then display error."""
        tray_state = (
            self.syncthru.input_tray_status().get(self._number, {}).get("newError")
        )
        if tray_state == "":
            tray_state = "Ready"
        return tray_state


class SyncThruOutputTraySensor(SyncThruSensor):
    """Implementation of a Samsung Printer input tray sensor platform."""

    def __init__(self, syncthru, name, number):
        """Initialize the sensor."""
        super().__init__(syncthru, name)
        self._name = f"{name} Output Tray {number}"
        self._number = number
        self._id_suffix = f"_output_tray_{number}"

    @property
    def extra_state_attributes(self):
        """Show all data returned for this output tray."""
        return self.syncthru.output_tray_status().get(self._number, {})

    @property
    def native_value(self):
        """Display ready unless there is some error, then display error."""
        tray_state = (
            self.syncthru.output_tray_status().get(self._number, {}).get("status")
        )
        if tray_state == "":
            tray_state = "Ready"
        return tray_state
