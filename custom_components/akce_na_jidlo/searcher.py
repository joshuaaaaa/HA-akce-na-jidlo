"""Vyhledávač – na požádání stáhne akce na zadané potraviny a dohledá pobočky obchodů."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

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
    EVENT_SEARCH_DONE,
    MAX_RESULTS_PER_ITEM,
    RELOCATE_DISTANCE_KM,
    SEARCH_CACHE_HOURS,
    SOURCE_CUSTOM,
    SOURCES,
    STORE_CACHE_DAYS,
    USER_AGENT,
    country_sources,
)
from .generic import dedupe, parse_generic
from .kupi import make_soup, parse_offers
from .search import (
    build_shops,
    cheapest_total,
    filter_offers,
    matches,
    query_param,
    query_slug,
    rank_offers,
    split_items,
)
from .stores import (
    fetch_stores,
    haversine_km,
    in_country,
    nearest_by_chain,
    reverse_geocode,
    store_for_chain,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_DELAY = 0.5
NOMINATIM_DELAY = 1.1  # limit Nominatimu 1 dotaz/s
MAX_GEOCODE = 8  # víc adres najednou z Nominatimu nedohledáváme
MAX_SHOPS = 20
MAX_PAGE_BYTES = 3_000_000  # větší stránky se ořízne (ochrana paměti a CPU)
REQUEST_TIMEOUT = 15
SEARCH_BUDGET = 120  # po 2 minutách se další weby už nezkoušejí
OFFER_CACHE_SIZE = 100
SAVE_DELAY = 30  # zápis na disk (SD kartu) s odstupem, ne po každém hledání

ACCEPT_LANGUAGE = {
    "CZ": "cs-CZ,cs;q=0.9,sk;q=0.8,en;q=0.7",
    "SK": "sk-SK,sk;q=0.9,cs;q=0.8,en;q=0.7",
}
HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def attach_store(offer: dict[str, Any], nearest: dict[str, dict[str, Any]], radius: float) -> None:
    """Doplní k akci nejbližší pobočku řetězce (v okruhu), adresu a odkazy."""
    offer.update(
        store_name=None,
        address=None,
        latitude=None,
        longitude=None,
        distance_km=None,
        opening_hours=None,
        map_url=None,
        navigate_url=None,
        osm_id=None,
    )
    if offer.get("online"):
        return
    store = store_for_chain(nearest, offer["chain"])
    if not store or store["distance_km"] > radius:
        return
    offer.update(
        store_name=store["name"],
        address=store["address"],
        latitude=store["latitude"],
        longitude=store["longitude"],
        distance_km=store["distance_km"],
        opening_hours=store["opening_hours"],
        osm_id=store["osm_id"],
        map_url=(
            f"https://mapy.com/fnc/v1/showmap?mapset=basic&center={store['longitude']},"
            f"{store['latitude']}&zoom=17&marker=true"
        ),
        navigate_url=(
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{store['latitude']},{store['longitude']}"
        ),
    )


def process_item(
    item: str,
    raw: list[dict[str, Any]],
    today: date,
    nearest: dict[str, dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Filtr, pobočky a řazení akcí jedné potraviny. Běží ve vlákně mimo smyčku HA."""
    current, upcoming = filter_offers(
        item,
        raw,
        today,
        shop_type=settings["shop_type"],
        exclude_loyalty=settings["exclude_loyalty"],
        include_upcoming=settings["include_upcoming"],
    )
    for offer in current + upcoming:
        attach_store(offer, nearest, settings["radius"])
    args = (settings["sort_by"], settings["nearby_only"], settings["stores_known"])
    ranked = rank_offers(item, current, *args)
    per_item = settings["per_item"]
    return {
        "query": item,
        "downloaded": len(raw),
        "found": len(ranked),
        "offers": ranked[:per_item],
        "all_offers": ranked,
        "upcoming": rank_offers(item, upcoming, *args)[:per_item],
    }


class FoodSearcher:
    """Hledá akce na potraviny zadané v kartě (služba akce_na_jidlo.search)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._store = Store[dict[str, Any]](hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._cache: dict[str, Any] = {}
        self._offer_cache: dict[tuple[str, str], tuple[datetime, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[], None]] = []
        self.result: dict[str, Any] = {}
        self.searching = False

    # ------------------------------------------------------------------ config
    @property
    def options(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    def opt(self, key: str, default: Any) -> Any:
        value = self.options.get(key)
        return default if value is None or value == "" else value

    @property
    def country(self) -> str:
        country = self.options.get(CONF_COUNTRY) or DEFAULT_COUNTRY
        return country if country in COUNTRIES else DEFAULT_COUNTRY

    @property
    def show_map(self) -> bool:
        return bool(self.opt(CONF_SHOW_MAP, DEFAULT_SHOW_MAP))

    @property
    def sources(self) -> list[str]:
        allowed = country_sources(self.country)
        return [s for s in self.opt(CONF_SOURCES, allowed) if s in allowed]

    @property
    def custom_urls(self) -> list[str]:
        raw = self.options.get(CONF_CUSTOM_URLS) or ""
        if isinstance(raw, list):
            raw = "\n".join(raw)
        return [u.strip() for u in re.split(r"[\n,; ]+", raw) if u.strip().startswith("http")]

    def current_location(self) -> tuple[float, float, str]:
        entity_id = self.options.get(CONF_LOCATION_ENTITY)
        if entity_id and (state := self.hass.states.get(entity_id)) is not None:
            lat = state.attributes.get("latitude")
            lon = state.attributes.get("longitude")
            if (
                lat is not None
                and lon is not None
                and in_country(float(lat), float(lon), self.country)
            ):
                return float(lat), float(lon), entity_id
            _LOGGER.debug("%s nemá polohu v %s, používám domov", entity_id, self.country)
        return self.hass.config.latitude, self.hass.config.longitude, "zone.home"

    # ---------------------------------------------------------------- storage
    async def async_load(self) -> None:
        self._cache = await self._store.async_load() or {}
        self._cache.setdefault("stores", {})
        self.result = self._cache.get("last_result") or {}

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: self._cache, SAVE_DELAY)

    async def async_unload(self) -> None:
        """Při vypnutí / znovunačtení integrace uloží rozepsaná data hned."""
        if self._cache:
            await self._store.async_save(self._cache)

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    # ---------------------------------------------------------------- stahování
    async def _fetch_html(self, url: str) -> tuple[int, str | None]:
        try:
            async with self.session.get(
                url,
                headers={**HTTP_HEADERS, "Accept-Language": ACCEPT_LANGUAGE[self.country]},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status >= 400:
                    return resp.status, None
                raw = await resp.content.read(MAX_PAGE_BYTES)
                if not resp.content.at_eof():
                    _LOGGER.debug(
                        "Stránka %s je větší než %d B, zpracuje se jen začátek", url, len(raw)
                    )
                return resp.status, raw.decode(resp.charset or "utf-8", errors="replace")
        except (aiohttp.ClientError, asyncio.TimeoutError, LookupError) as err:
            _LOGGER.debug("Stažení %s selhalo: %s", url, err)
            return 0, None

    def _parse(
        self, source: str, html: str, url: str, today: date, item: str
    ) -> list[dict[str, Any]]:
        """Běží ve vlákně mimo smyčku HA – parsování HTML je náročné na CPU.

        Vrací jen akce, které odpovídají hledané potravině (menší paměť i mezipaměť).
        """
        soup = make_soup(html)
        offers: list[dict[str, Any]] = []
        if "kupi.cz" in url:
            offers = parse_offers(soup, url, today)
        if not offers:
            offers = parse_generic(soup, url, today, source, self.country)
        soup.decompose()  # uvolní strom stránky hned, ne až při úklidu paměti
        return [o for o in offers if matches(item, o.get("product", ""))]

    async def _fetch_item_source(
        self,
        source: str,
        templates: tuple[str, ...],
        item: str,
        today: date,
        errors: list[str],
        deadline: float,
    ) -> list[dict[str, Any]]:
        """Zkusí adresy zdroje postupně; vrátí akce z první, která nějaké má."""
        cache_key = (source, item.lower())
        cached = self._offer_cache.get(cache_key)
        if cached and dt_util.utcnow() - cached[0] < timedelta(hours=SEARCH_CACHE_HOURS):
            return cached[1]
        found: list[dict[str, Any]] = []
        for template in templates:
            if self.hass.loop.time() > deadline:
                errors.append("vypršel časový limit hledání")
                return found
            url = template.format(query=query_param(item), slug=query_slug(item))
            code, html = await self._fetch_html(url)
            await asyncio.sleep(REQUEST_DELAY)
            if html is None:
                errors.append(f"{url}: HTTP {code}" if code else f"{url}: nedostupné")
                continue
            found = await self.hass.async_add_executor_job(
                self._parse, source, html, url, today, item
            )
            del html
            if found:
                break
        # mezipaměť s omezenou velikostí – nejstarší záznamy se zahodí
        while len(self._offer_cache) >= OFFER_CACHE_SIZE:
            self._offer_cache.pop(next(iter(self._offer_cache)))
        self._offer_cache[cache_key] = (dt_util.utcnow(), found)
        return found

    async def _fetch_item(
        self, item: str, today: date, status: dict[str, dict[str, Any]], deadline: float
    ) -> list[dict[str, Any]]:
        offers: list[dict[str, Any]] = []
        for source in self.sources:
            entry = status.setdefault(source, {"offers": 0, "errors": []})
            try:
                found = await self._fetch_item_source(
                    source, SOURCES[source]["search"], item, today, entry["errors"], deadline
                )
            except Exception as err:  # noqa: BLE001 - chyba jednoho zdroje nesmí shodit ostatní
                _LOGGER.warning("Zdroj %s selhal pro „%s“: %s", source, item, err)
                entry["errors"].append(str(err))
                continue
            entry["offers"] += len(found)
            offers += found
        if self.custom_urls:
            entry = status.setdefault(SOURCE_CUSTOM, {"offers": 0, "errors": []})
            found = await self._fetch_item_source(
                SOURCE_CUSTOM, tuple(self.custom_urls), item, today, entry["errors"], deadline
            )
            entry["offers"] += len(found)
            offers += found
        return dedupe(offers)

    # ---------------------------------------------------------------- pobočky
    async def _stores_for(self, lat: float, lon: float) -> tuple[list[dict[str, Any]], str | None]:
        radius = min(max(float(self.opt(CONF_MAX_DISTANCE_KM, DEFAULT_MAX_DISTANCE_KM)), 1.0), 50.0)
        cache = self._cache.get("stores") or {}
        if cache.get("fetched"):
            age = dt_util.utcnow() - dt_util.parse_datetime(cache["fetched"])
            moved = haversine_km(lat, lon, cache.get("lat", 0), cache.get("lon", 0))
            if (
                age < timedelta(days=STORE_CACHE_DAYS)
                and moved < RELOCATE_DISTANCE_KM
                and cache.get("radius") == radius
                and cache.get("country") == self.country
            ):
                return cache.get("items", []), None
        try:
            items = await fetch_stores(self.session, lat, lon, radius, self.country)
        except RuntimeError as err:
            _LOGGER.warning("%s", err)
            return cache.get("items", []), str(err)
        if not items:
            return cache.get("items", []), None
        self._cache["stores"] = {
            "fetched": dt_util.utcnow().isoformat(),
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "country": self.country,
            "items": items,
            "geocoded": cache.get("geocoded", {}),
        }
        return items, None

    async def _fill_addresses(self, shops: list[dict[str, Any]]) -> None:
        """Pobočkám bez adresy v OSM ji dohledá Nominatim (max. pár dotazů, 1 za sekundu)."""
        geocoded: dict[str, str] = self._cache.setdefault("stores", {}).setdefault("geocoded", {})
        asked = 0
        for shop in shops:
            if shop.get("address") or shop.get("latitude") is None:
                continue
            key = f"{shop['latitude']:.5f},{shop['longitude']:.5f}"
            if key not in geocoded:
                if asked >= MAX_GEOCODE:
                    continue
                asked += 1
                geocoded[key] = await reverse_geocode(
                    self.session, shop["latitude"], shop["longitude"]
                )
                await asyncio.sleep(NOMINATIM_DELAY)
            shop["address"] = geocoded[key]

    # ---------------------------------------------------------------- hledání
    async def async_search(self, raw_items: Any) -> dict[str, Any]:
        """Najde akce na zadané potraviny. Bez potravin zopakuje poslední hledání."""
        items = split_items(raw_items)
        if not items:
            items = list(self.result.get("query") or [])
        if not items:
            return self.result
        async with self._lock:
            self.searching = True
            self._notify()
            try:
                result = await self._search(items)
            finally:
                self.searching = False
            self.result = result
            self._cache["last_result"] = result
            self._schedule_save()
            self._notify()
        self.hass.bus.async_fire(
            EVENT_SEARCH_DONE,
            {
                "entry_id": self.entry.entry_id,
                "query": result["query"],
                "found": result["found"],
                "not_found": result["not_found"],
                "total": result["total"],
                "best_shop": result["shops"][0]["shop"] if result["shops"] else None,
            },
        )
        return result

    async def _search(self, items: list[str]) -> dict[str, Any]:
        today = dt_util.now().date()
        lat, lon, location_source = self.current_location()
        country = COUNTRIES[self.country]
        status: dict[str, dict[str, Any]] = {}
        shop_type = self.opt(CONF_SHOP_TYPE, DEFAULT_SHOP_TYPE)
        stores: list[dict[str, Any]] = []
        stores_error: str | None = None
        if shop_type != "online":
            stores, stores_error = await self._stores_for(lat, lon)
        sort_by = self.opt(CONF_SORT_BY, DEFAULT_SORT_BY)
        settings = {
            "shop_type": shop_type,
            "exclude_loyalty": bool(self.opt(CONF_EXCLUDE_LOYALTY, DEFAULT_EXCLUDE_LOYALTY)),
            "include_upcoming": bool(self.opt(CONF_INCLUDE_UPCOMING, DEFAULT_INCLUDE_UPCOMING)),
            "radius": float(self.opt(CONF_MAX_DISTANCE_KM, DEFAULT_MAX_DISTANCE_KM)),
            "sort_by": sort_by,
            "nearby_only": bool(self.opt(CONF_NEARBY_ONLY, DEFAULT_NEARBY_ONLY)),
            "stores_known": bool(stores),
            "per_item": min(
                int(self.opt(CONF_RESULTS_PER_ITEM, DEFAULT_RESULTS_PER_ITEM)),
                MAX_RESULTS_PER_ITEM,
            ),
        }
        # nejbližší pobočka každého řetězce – jednou za hledání, mimo smyčku HA
        nearest = await self.hass.async_add_executor_job(nearest_by_chain, stores, lat, lon)
        deadline = self.hass.loop.time() + SEARCH_BUDGET

        results: list[dict[str, Any]] = []
        for item in items:
            raw = await self._fetch_item(item, today, status, deadline)
            results.append(
                await self.hass.async_add_executor_job(
                    process_item, item, raw, today, nearest, settings
                )
            )

        shops = build_shops(results)[:MAX_SHOPS]
        await self._fill_addresses(shops)
        for entry in results:
            entry.pop("all_offers", None)
            entry["best"] = entry["offers"][0] if entry["offers"] else None
            # adresy doplněné Nominatimem i do jednotlivých akcí
            for offer in entry["offers"]:
                if offer.get("latitude") is not None and not offer.get("address"):
                    key = f"{offer['latitude']:.5f},{offer['longitude']:.5f}"
                    offer["address"] = self._cache["stores"].get("geocoded", {}).get(key)
        return {
            "query": items,
            "updated": dt_util.utcnow().isoformat(),
            "country": self.country,
            "currency": country["currency"],
            "currency_symbol": country["symbol"],
            "language": self.options.get(CONF_LANGUAGE),
            "show_map": self.show_map,
            "sort_by": sort_by,
            "max_distance_km": float(self.opt(CONF_MAX_DISTANCE_KM, DEFAULT_MAX_DISTANCE_KM)),
            "location": {"latitude": lat, "longitude": lon, "source": location_source},
            "items": results,
            "shops": shops,
            "found": [r["query"] for r in results if r["offers"]],
            "not_found": [r["query"] for r in results if not r["offers"]],
            "total": cheapest_total(results),
            "stores_error": stores_error,
            "sources": status,
            "source_names": {key: spec["name"] for key, spec in SOURCES.items()}
            | {SOURCE_CUSTOM: "Vlastní URL"},
        }
