"""Senzory s výsledkem posledního hledání (zdroj dat pro kartu)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FoodConfigEntry
from .const import DOMAIN, NAME
from .searcher import FoodSearcher


async def async_setup_entry(
    hass: HomeAssistant, entry: FoodConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    searcher = entry.runtime_data
    async_add_entities([ResultsSensor(searcher), BestShopSensor(searcher)])


class FoodEntity(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, searcher: FoodSearcher, key: str) -> None:
        self.searcher = searcher
        entry = searcher.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Letákové weby + OpenStreetMap",
            model=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.searcher.async_add_listener(self._updated))

    @callback
    def _updated(self) -> None:
        self.async_write_ha_state()


class ResultsSensor(FoodEntity):
    """Stav = počet nalezených potravin, atributy = celý výsledek pro kartu."""

    _attr_icon = "mdi:basket"
    _attr_translation_key = "results"
    # velké atributy se neukládají do historie
    _unrecorded_attributes = frozenset({"items", "shops", "sources", "source_names", "location"})

    def __init__(self, searcher: FoodSearcher) -> None:
        super().__init__(searcher, "results")

    @property
    def native_value(self) -> int | None:
        result = self.searcher.result
        return len(result.get("found") or []) if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        result = self.searcher.result or {}
        return {
            "entry_id": self.searcher.entry.entry_id,
            "searching": self.searcher.searching,
            "show_map": self.searcher.show_map,
            "country": self.searcher.country,
            **{k: v for k, v in result.items() if k not in ("show_map", "country")},
        }


class BestShopSensor(FoodEntity):
    """Stav = obchod, kde se toho z nákupního seznamu nejvíc koupí nejlevněji."""

    _attr_icon = "mdi:store-marker"
    _attr_translation_key = "best_shop"

    def __init__(self, searcher: FoodSearcher) -> None:
        super().__init__(searcher, "best_shop")

    def _shop(self) -> dict[str, Any] | None:
        shops = (self.searcher.result or {}).get("shops") or []
        return shops[0] if shops else None

    @property
    def native_value(self) -> str | None:
        shop = self._shop()
        return shop["shop"] if shop else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        shop = self._shop()
        if not shop:
            return {}
        symbol = (self.searcher.result or {}).get("currency_symbol", "")
        items = [
            f"{i['query']}: {i['product']} {i['price']:.2f} {symbol}".strip() for i in shop["items"]
        ]
        return {
            "store_name": shop.get("store_name"),
            "address": shop.get("address"),
            "distance_km": shop.get("distance_km"),
            "opening_hours": shop.get("opening_hours"),
            "latitude": shop.get("latitude"),
            "longitude": shop.get("longitude"),
            "navigate_url": shop.get("navigate_url"),
            "items": items,
            "best_count": shop.get("best_count"),
            "total": shop.get("total"),
        }
