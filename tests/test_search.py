from datetime import date

from akce_na_jidlo.search import (
    build_shops,
    cheapest_total,
    filter_offers,
    matches,
    query_param,
    query_slug,
    rank_offers,
    split_items,
)

TODAY = date(2026, 9, 26)


def offer(product, shop, price, **extra):
    chain = shop.lower().split()[0]
    return {
        "product": product,
        "shop": shop,
        "chain": chain,
        "online": extra.pop("online", False),
        "price": price,
        "unit_price": extra.pop("unit_price", None),
        "valid_from": extra.pop("valid_from", "2026-09-23"),
        "valid_to": extra.pop("valid_to", "2026-09-29"),
        "loyalty": extra.pop("loyalty", False),
        "latitude": extra.pop("latitude", 50.0),
        "longitude": extra.pop("longitude", 14.0),
        "distance_km": extra.pop("distance_km", 1.0),
        "address": f"{shop} 1, Praha",
        **extra,
    }


def test_split_items():
    assert split_items("mléko, chleba\nmáslo;  Mléko ") == ["mléko", "chleba", "máslo"]
    assert split_items(["vejce", "jogurt, sýr"]) == ["vejce", "jogurt", "sýr"]
    assert split_items(None) == []
    assert len(split_items(",".join(str(i) for i in range(40)))) == 15


def test_query_helpers():
    assert query_slug("Mléko polotučné") == "mleko-polotucne"
    assert query_param("Máslo 82 %") == "m%C3%A1slo+82+%25"


def test_matches_inflection():
    assert matches("mléko", "Mléko polotučné 1 l")
    assert matches("mleko", "Trvanlivé MLÉKO 1,5 %")
    assert matches("rohlík", "Rohlíky tukové 10 ks")
    assert matches("kuřecí prsa", "Kuřecí prsní řízky chlazené")
    assert matches("vejce", "Vejce M 10 ks")
    assert not matches("mléko", "Jogurt bílý")
    assert not matches("kuřecí prsa", "Kuřecí stehna")
    assert not matches("", "cokoliv")


def test_filter_offers():
    offers = [
        offer("Mléko polotučné", "Albert", 16.9),
        offer("Mléko polotučné", "Albert", 16.9),  # duplicita
        offer("Mléko plnotučné", "Lidl", 14.9, loyalty=True),
        offer("Mléko", "Rohlik.cz", 12.9, online=True),
        offer("Mléko staré", "Billa", 9.9, valid_to="2026-09-20"),
        offer("Mléko nové", "Penny", 11.9, valid_from="2026-10-01"),
        offer("Chléb", "Tesco", 20.0),
    ]
    current, upcoming = filter_offers(
        "mléko", offers, TODAY, shop_type="physical", exclude_loyalty=False, include_upcoming=True
    )
    assert [o["shop"] for o in current] == ["Albert", "Lidl"]
    assert [o["shop"] for o in upcoming] == ["Penny"]
    current, upcoming = filter_offers(
        "mléko", offers, TODAY, shop_type="all", exclude_loyalty=True, include_upcoming=False
    )
    assert [o["shop"] for o in current] == ["Albert", "Rohlik.cz"]
    assert upcoming == []


def test_rank_nearby_and_sort():
    offers = [
        offer("Mléko A", "Albert", 16.9, distance_km=3.0, unit_price=16.9),
        offer("Mléko B", "Lidl", 14.9, distance_km=5.0, unit_price=9.93),
        offer("Mléko C", "Norma", 12.9, latitude=None, distance_km=None),
    ]
    ranked = rank_offers("mléko", offers, "price", nearby_only=True, stores_known=True)
    assert [o["shop"] for o in ranked] == ["Lidl", "Albert"]
    # pobočky se nepodařilo zjistit -> nic se nevyřazuje
    ranked = rank_offers("mléko", offers, "price", nearby_only=True, stores_known=False)
    assert [o["shop"] for o in ranked] == ["Norma", "Lidl", "Albert"]
    ranked = rank_offers("mléko", offers, "distance", nearby_only=False, stores_known=True)
    assert [o["shop"] for o in ranked] == ["Albert", "Lidl", "Norma"]
    ranked = rank_offers("mléko", offers, "unit", nearby_only=False, stores_known=True)
    assert [o["shop"] for o in ranked][:2] == ["Lidl", "Albert"]


def test_build_shops():
    items = [
        {
            "query": "mléko",
            "offers": [offer("Mléko", "Lidl", 14.9), offer("Mléko", "Albert", 16.9)],
        },
        {
            "query": "máslo",
            "offers": [offer("Máslo", "Albert", 39.9), offer("Máslo", "Lidl", 44.9)],
        },
        {"query": "chleba", "offers": [offer("Chléb", "Albert", 25.0)]},
        {"query": "šafrán", "offers": []},
    ]
    shops = build_shops(items)
    assert [s["shop"] for s in shops] == ["Albert", "Lidl"]
    albert = shops[0]
    assert albert["best_count"] == 2
    assert albert["item_count"] == 3
    assert [i["query"] for i in albert["items"]] == ["mléko", "máslo", "chleba"]
    assert [i["best"] for i in albert["items"]] == [False, True, True]
    assert albert["total"] == 81.8
    assert albert["address"] == "Albert 1, Praha"
    assert cheapest_total(items) == 79.8
    assert cheapest_total([{"query": "x", "offers": []}]) is None
