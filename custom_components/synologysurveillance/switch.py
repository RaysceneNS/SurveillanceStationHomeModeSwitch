"""Support setting home mode on Synology surveillance station."""
import logging

import voluptuous as vol

import urllib

import requests

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
DEFAULT_TIMEOUT = 10

HOME_ICONS = {
    STATE_ON: "mdi:home-account",
    STATE_OFF: "mdi:home-outline"
}

ERROR_CODE_SESSION_EXPIRED = 105

BASE_API_INFO = {
    'auth': {
        'name': 'SYNO.API.Auth',
        'version': 2
    },
    'home_mode': {
        'name': 'SYNO.SurveillanceStation.HomeMode',
        'version': 1
    },
}

API_NAMES = [api['name'] for api in BASE_API_INFO.values()]

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
        api = Api(
            config.get(CONF_URL),
            config.get(CONF_USERNAME),
            config.get(CONF_PASSWORD),
            verify_ssl=verify_ssl,
            timeout=timeout
        )
    except (requests.exceptions.RequestException, ValueError):
        _LOGGER.exception("Error when initializing api")
        return False

    add_entities([SurveillanceStationHomeModeSwitch(name, api)])


class SurveillanceStationHomeModeSwitch(ToggleEntity):
    """Representation of a switch to toggle on/off home mode."""

    def __init__(self, name, api):
        """Initialize the switch."""
        self._name = name
        self._api = api
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
        self._api.home_mode_set_state("true")

    def turn_off(self, **kwargs):
        """Turn the device off."""
        _LOGGING.info("Turning off Home Mode ")
        self._api.home_mode_set_state("false")

    def update(self):
        """Update Motion Detection state."""
        enabled = self._api.home_mode_status()
        _LOGGING.info("enabled: %s", enabled)

        self._state = STATE_ON if enabled else STATE_OFF

class Api:
    """An implementation of a Synology SurveillanceStation API."""

    def __init__(self, url, username, password, timeout=10, verify_ssl=True):
        """Initialize a Synology Surveillance API."""
        self._base_url = url + '/webapi/'
        self._username = username
        self._password = password
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._api_info = None
        self._sid = None
        self._initialize_api_info()
        self._initialize_api_sid()

    def _initialize_api_info(self, **kwargs):
        payload = dict({
            'api': 'SYNO.API.Info',
            'method': 'Query',
            'version': '1',
            'query': ','.join(API_NAMES),
        }, **kwargs)
        response = self._get_json_with_retry(self._base_url + 'query.cgi', payload)
        self._api_info = BASE_API_INFO
        for api in self._api_info.values():
            api_name = api['name']
            api['url'] = self._base_url + response['data'][api_name]['path']

    def _initialize_api_sid(self, **kwargs):
        api = self._api_info['auth']
        payload = dict({
            'api': api['name'],
            'method': 'Login',
            'version': api['version'],
            'account': self._username,
            'passwd': self._password,
            'session': 'SurveillanceStation',
            'format': 'sid',
        }, **kwargs)
        response = self._get_json_with_retry(api['url'], payload)
        self._sid = response['data']['sid']

    def home_mode_set_state(self, state, **kwargs):
        """Set the state of Home Mode"""
        api = self._api_info['home_mode']
        payload = dict({
            'api': api['name'],
            'method': 'Switch',
            'version': api['version'],
            'on': state,
            '_sid': self._sid,
        }, **kwargs)
        response = self._get_json_with_retry(api['url'], payload)
        if response['success']:
            return True
        return False

    def home_mode_status(self, **kwargs):
        """Returns the status of Home Mode"""
        api = self._api_info['home_mode']
        payload = dict({
            'api': api['name'],
            'method': 'GetInfo',
            'version': api['version'],
            '_sid': self._sid
        }, **kwargs)
        response = self._get_json_with_retry(api['url'], payload)
        return response['data']['on']

    def _get_json_with_retry(self, url, payload):
        try:
            return self._get_json(url, payload)
        except SessionExpiredException:
            self._initialize_api_sid()
            return self._get_json(url, payload)

    def _get_json(self, url, payload):
        response = requests.get(url, payload, timeout=self._timeout, verify=self._verify_ssl)
        response.raise_for_status()
        content = response.json()
        if 'success' not in content or content['success'] is False:
            error_code = content.get('error', {}).get('code')
            if ERROR_CODE_SESSION_EXPIRED == error_code:
                raise SessionExpiredException('Session expired')
            raise ValueError('Invalid or failed response', content)
        return content

class SessionExpiredException(Exception):
    """An error indicating session expired."""
