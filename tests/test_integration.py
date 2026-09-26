"""Test integrace v Home Assistantu (spustí se, jen když je HA nainstalovaný)."""

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402

from custom_components.akce_na_jidlo.const import DOMAIN, EVENT_SEARCH_DONE  # noqa: E402

from .test_kupi import HTML  # noqa: E402

CHLEB = """
<div class="product--wrap" data-product-id="30">
  <div class="product_name"><h2><a title="Chléb Šumava 1 kg" href="/sleva/chleb">Chléb</a></h2></div>
  <div class="discount_row" data-product="30" data-discount="300">
    <div class="discounts_shop_name"><a>Albert</a></div>
    <span class="discount_price_value">29,90 Kč</span>
    <span class="discounts_validity">do 30. 9.</span>
  </div>
</div>
"""

STORES = [
    {
        "chain": "albert",
        "name": "Albert Supermarket",
        "address": "Vodičkova 10, 11000 Praha",
        "opening_hours": "Mo-Su 07:00-22:00",
        "latitude": 50.08,
        "longitude": 14.43,
        "osm_id": "node/1",
    },
    {
        "chain": "lidl",
        "name": "Lidl",
        "address": "",
        "opening_hours": "",
        "latitude": 50.10,
        "longitude": 14.50,
        "osm_id": "way/2",
    },
]


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations):
    with (
        patch("custom_components.akce_na_jidlo.searcher.REQUEST_DELAY", 0),
        patch("custom_components.akce_na_jidlo.searcher.NOMINATIM_DELAY", 0),
    ):
        yield


async def _fake_html(self, url):
    if "kupi.cz" not in url:
        return 404, None
    if "mleko" in url or "m%C3%A1slo" in url or "maslo" in url:
        return 200, HTML
    if "chleb" in url:
        return 200, CHLEB
    return 200, "<html><h1>Nic</h1></html>"


async def _setup(hass: HomeAssistant, **settings):
    hass.config.latitude, hass.config.longitude = 50.087, 14.421
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Akce na jídlo", "language": "cs", "country": "CZ"}
    )
    assert result["step_id"] == "settings"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "show_map": True,
            "max_distance_km": 10,
            "nearby_only": True,
            "shop_type": "physical",
            "results_per_item": 5,
            "sort_by": "price",
            "exclude_loyalty": False,
            "include_upcoming": False,
            "sources": ["kupi"],
            **settings,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


async def test_search_service(hass: HomeAssistant, freezer):
    freezer.move_to(dt_util.parse_datetime("2026-09-26T10:00:00+02:00"))
    events = []
    hass.bus.async_listen(EVENT_SEARCH_DONE, events.append)
    with (
        patch("custom_components.akce_na_jidlo.searcher.FoodSearcher._fetch_html", _fake_html),
        patch(
            "custom_components.akce_na_jidlo.searcher.fetch_stores", return_value=STORES
        ) as stores,
        patch(
            "custom_components.akce_na_jidlo.searcher.reverse_geocode",
            return_value="Kolbenova 5, Praha",
        ),
    ):
        entry = await _setup(hass)
        response = await hass.services.async_call(
            DOMAIN,
            "search",
            {"items": "mléko, chleba, šafrán"},
            blocking=True,
            return_response=True,
        )
        await hass.async_block_till_done()
        assert stores.call_count == 1

    assert response["query"] == ["mléko", "chleba", "šafrán"]
    assert response["found"] == ["mléko", "chleba"]
    assert response["not_found"] == ["šafrán"]
    assert response["show_map"] is True
    milk = response["items"][0]
    # Penny (máslo) se k mléku nepřidá, Lidl je nejlevnější
    assert [o["shop"] for o in milk["offers"]] == ["Lidl", "Albert Hypermarket"]
    assert milk["best"]["address"] == "Kolbenova 5, Praha"
    shops = response["shops"]
    assert [s["shop"] for s in shops] == ["Albert Hypermarket", "Lidl"]
    assert shops[0]["address"] == "Vodičkova 10, 11000 Praha"
    assert [i["query"] for i in shops[0]["items"]] == ["mléko", "chleba"]
    assert response["total"] == 44.8
    assert events and events[0].data["best_shop"] == "Albert Hypermarket"

    results = [s for s in hass.states.async_all("sensor") if "shops" in s.attributes]
    assert len(results) == 1
    assert results[0].state == "2"
    assert results[0].attributes["entry_id"] == entry.entry_id
    best = [s for s in hass.states.async_all("sensor") if s.attributes.get("best_count")]
    assert best[0].state == "Albert Hypermarket"

    # bez potravin se zopakuje poslední hledání (z mezipaměti, bez stahování)
    with patch(
        "custom_components.akce_na_jidlo.searcher.FoodSearcher._fetch_html",
        side_effect=AssertionError("nemá se stahovat"),
    ):
        again = await hass.services.async_call(
            DOMAIN, "search", {}, blocking=True, return_response=True
        )
    assert again["query"] == response["query"]

    # výsledek přežije restart integrace
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    results = [s for s in hass.states.async_all("sensor") if "shops" in s.attributes]
    assert results[0].state == "2"


async def test_map_disabled_and_options(hass: HomeAssistant):
    with patch("custom_components.akce_na_jidlo.searcher.FoodSearcher._fetch_html", _fake_html):
        entry = await _setup(hass, show_map=False)
        sensor = [s for s in hass.states.async_all("sensor") if "entry_id" in s.attributes][0]
        assert sensor.attributes["show_map"] is False

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "language": "cs",
                "show_map": True,
                "max_distance_km": 5,
                "nearby_only": False,
                "shop_type": "all",
                "results_per_item": 3,
                "sort_by": "unit",
                "exclude_loyalty": True,
                "include_upcoming": True,
                "sources": ["kupi"],
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        sensor = [s for s in hass.states.async_all("sensor") if "entry_id" in s.attributes][0]
        assert sensor.attributes["show_map"] is True
