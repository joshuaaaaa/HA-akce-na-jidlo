"""Nastavení integrace Akce na jídlo přes UI."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_COUNTRY,
    CONF_CUSTOM_URLS,
    CONF_EXCLUDE_LOYALTY,
    CONF_INCLUDE_UPCOMING,
    CONF_LANGUAGE,
    CONF_LOCATION_ENTITY,
    CONF_MAX_DISTANCE_KM,
    CONF_NEARBY_ONLY,
    CONF_RESULTS_PER_ITEM,
    CONF_SHOP_TYPE,
    CONF_SHOW_MAP,
    CONF_SORT_BY,
    CONF_SOURCES,
    COUNTRIES,
    DEFAULT_COUNTRY,
    DEFAULT_EXCLUDE_LOYALTY,
    DEFAULT_INCLUDE_UPCOMING,
    DEFAULT_MAX_DISTANCE_KM,
    DEFAULT_NEARBY_ONLY,
    DEFAULT_RESULTS_PER_ITEM,
    DEFAULT_SHOP_TYPE,
    DEFAULT_SHOW_MAP,
    DEFAULT_SORT_BY,
    DOMAIN,
    MAX_RESULTS_PER_ITEM,
    NAME,
    SHOP_TYPE_OPTIONS,
    SORT_OPTIONS,
    SOURCES,
    country_sources,
)

LANGUAGE_AUTO = "auto"
LANGUAGE_OPTIONS = [LANGUAGE_AUTO, "cs", "sk", "en"]


def _language_field(values: dict[str, Any]) -> dict[Any, Any]:
    return {
        vol.Required(
            CONF_LANGUAGE, default=values.get(CONF_LANGUAGE, LANGUAGE_AUTO)
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=LANGUAGE_OPTIONS,
                translation_key=CONF_LANGUAGE,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    }


def _country_schema(values: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=values.get(CONF_NAME, NAME)): str,
            **_language_field(values),
            vol.Required(
                CONF_COUNTRY, default=values.get(CONF_COUNTRY, DEFAULT_COUNTRY)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=code, label=f"{info['name']} ({info['symbol']})"
                        )
                        for code, info in COUNTRIES.items()
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _schema(values: dict[str, Any], country: str, with_language: bool = False) -> vol.Schema:
    sources = country_sources(country)
    fields: dict[Any, Any] = _language_field(values) if with_language else {}
    location = values.get(CONF_LOCATION_ENTITY)
    fields.update(
        {
            vol.Required(
                CONF_SHOW_MAP, default=values.get(CONF_SHOW_MAP, DEFAULT_SHOW_MAP)
            ): selector.BooleanSelector(),
            (
                vol.Optional(CONF_LOCATION_ENTITY, description={"suggested_value": location})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["person", "device_tracker", "zone"])
            ),
            vol.Required(
                CONF_MAX_DISTANCE_KM,
                default=values.get(CONF_MAX_DISTANCE_KM, DEFAULT_MAX_DISTANCE_KM),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    unit_of_measurement="km",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_NEARBY_ONLY, default=values.get(CONF_NEARBY_ONLY, DEFAULT_NEARBY_ONLY)
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_SHOP_TYPE, default=values.get(CONF_SHOP_TYPE, DEFAULT_SHOP_TYPE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SHOP_TYPE_OPTIONS,
                    translation_key=CONF_SHOP_TYPE,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_RESULTS_PER_ITEM,
                default=values.get(CONF_RESULTS_PER_ITEM, DEFAULT_RESULTS_PER_ITEM),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=MAX_RESULTS_PER_ITEM,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_SORT_BY, default=values.get(CONF_SORT_BY, DEFAULT_SORT_BY)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=SORT_OPTIONS, translation_key=CONF_SORT_BY)
            ),
            vol.Required(
                CONF_EXCLUDE_LOYALTY,
                default=values.get(CONF_EXCLUDE_LOYALTY, DEFAULT_EXCLUDE_LOYALTY),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_INCLUDE_UPCOMING,
                default=values.get(CONF_INCLUDE_UPCOMING, DEFAULT_INCLUDE_UPCOMING),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_SOURCES,
                default=[s for s in values.get(CONF_SOURCES, sources) if s in sources] or sources,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=key, label=SOURCES[key]["name"])
                        for key in sources
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(
                CONF_CUSTOM_URLS,
                description={"suggested_value": values.get(CONF_CUSTOM_URLS, "")},
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
        }
    )
    return vol.Schema(fields)


def _clean(user_input: dict[str, Any], country: str) -> dict[str, Any]:
    data = dict(user_input)
    data[CONF_COUNTRY] = country
    data[CONF_RESULTS_PER_ITEM] = int(data.get(CONF_RESULTS_PER_ITEM, DEFAULT_RESULTS_PER_ITEM))
    allowed = country_sources(country)
    data[CONF_SOURCES] = [s for s in data.get(CONF_SOURCES) or [] if s in allowed]
    data[CONF_CUSTOM_URLS] = (data.get(CONF_CUSTOM_URLS) or "").strip()
    if not data[CONF_SOURCES] and not data[CONF_CUSTOM_URLS]:
        data[CONF_SOURCES] = allowed
    if not data.get(CONF_LOCATION_ENTITY):
        data.pop(CONF_LOCATION_ENTITY, None)
    return data


class AkceNaJidloConfigFlow(ConfigFlow, domain=DOMAIN):
    """Průvodce nastavením."""

    VERSION = 1

    def __init__(self) -> None:
        self._title = NAME
        self._country = DEFAULT_COUNTRY
        self._language = LANGUAGE_AUTO

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Krok 1: název, jazyk a země (Česko / Slovensko)."""
        if user_input is not None:
            self._title = user_input.get(CONF_NAME) or NAME
            self._country = user_input.get(CONF_COUNTRY) or DEFAULT_COUNTRY
            self._language = user_input.get(CONF_LANGUAGE) or LANGUAGE_AUTO
            return await self.async_step_settings()
        return self.async_show_form(step_id="user", data_schema=_country_schema({}))

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Krok 2: mapa, poloha, okruh, zdroje."""
        if user_input is not None:
            data = _clean(user_input, self._country)
            data[CONF_LANGUAGE] = self._language
            return self.async_create_entry(title=self._title, data={}, options=data)
        return self.async_show_form(
            step_id="settings",
            data_schema=_schema({}, self._country),
            description_placeholders={"country": COUNTRIES[self._country]["name"]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AkceNaJidloOptionsFlow()


class AkceNaJidloOptionsFlow(OptionsFlow):
    """Změna nastavení (Konfigurovat)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        country = current.get(CONF_COUNTRY) or DEFAULT_COUNTRY
        if user_input is not None:
            return self.async_create_entry(data=_clean(user_input, country))
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current, country, with_language=True),
            description_placeholders={"country": COUNTRIES[country]["name"]},
        )
