"""Support setting home mode on Synology surveillance station."""
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_TIMEOUT,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.entity import ToggleEntity
import homeassistant.helpers.config_validation as cv

_LOGGING = logging.getLogger(__name__)

DEFAULT_NAME = "Surveillance Station Home Mode"
DEFAULT_TIMEOUT = 5

HOME_ICONS = {
    STATE_ON: "mdi:home-account",
    STATE_OFF: "mdi:home-outline"
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up Synology Surveillance Station."""
    name = config.get(CONF_NAME)
    verify_ssl = config.get(CONF_VERIFY_SSL)
    timeout = config.get(CONF_TIMEOUT)

    try:
        from synology.surveillance_station import SurveillanceStation

        surveillance = SurveillanceStation(
            config.get(CONF_URL),
            config.get(CONF_USERNAME),
            config.get(CONF_PASSWORD),
            verify_ssl=verify_ssl,
            timeout=timeout
        )
    except (requests.exceptions.RequestException, ValueError):
        _LOGGER.exception("Error when initializing SurveillanceStation")
        return False

    add_entities([SurveillanceStationHomeModeSwitch(name, surveillance)])


class SurveillanceStationHomeModeSwitch(ToggleEntity):
    """Representation of a switch to toggle on/off home mode."""

    def __init__(self, name, surveillance):
        """Initialize the switch."""
        self._name = name
        self._surveillance = surveillance
        self._state = STATE_OFF

    @property
    def should_poll(self):
        """Poll for status regularly."""
        return True

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def state(self):
        """Return the state of the device if any."""
        return self._state

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state == STATE_ON

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return HOME_ICONS.get(self.state)

    def turn_on(self, **kwargs):
        """Turn the device on."""
        _LOGGING.info("Turning on Home Mode ")
        self._surveillance.set_home_mode(True)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        _LOGGING.info("Turning off Home Mode ")
        self._surveillance.set_home_mode(False)

    def update(self):
        """Update Motion Detection state."""
        enabled = self._surveillance.get_home_mode_status()
        _LOGGING.info("enabled: %s", enabled)

        self._state = STATE_ON if enabled else STATE_OFF