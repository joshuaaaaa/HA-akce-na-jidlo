"""Akce na jídlo – kde je zadaná potravina v okolních obchodech v akci nejlevněji."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_CONFIG_ENTRY_ID, ATTR_ITEMS, DOMAIN, PLATFORMS, SERVICE_SEARCH
from .searcher import FoodSearcher

_LOGGER = logging.getLogger(__name__)

type FoodConfigEntry = ConfigEntry[FoodSearcher]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SEARCH_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ITEMS): vol.Any(cv.string, [cv.string]),
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)


def _target_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    loaded = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
    ]
    if entry_id:
        loaded = [e for e in loaded if e.entry_id == entry_id]
    if not loaded:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_entry")
    return loaded[0]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def _search(call: ServiceCall) -> ServiceResponse:
        entry = _target_entry(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        result: dict[str, Any] = await entry.runtime_data.async_search(call.data.get(ATTR_ITEMS))
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        _search,
        schema=SEARCH_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FoodConfigEntry) -> bool:
    searcher = FoodSearcher(hass, entry)
    await searcher.async_load()
    entry.runtime_data = searcher
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: FoodConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FoodConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
    return unloaded
