from akce_na_jidlo.stores import _parse_stores, format_address, nearest_store, store_chain


def test_store_chain_and_address():
    assert store_chain({"brand": "Lidl"}) == "lidl"
    assert store_chain({"name": "COOP Jednota"}) == "coop"
    assert store_chain({"name": "Potraviny U Nováků"}) is None
    # „dm“ se nesmí najít uvnitř jiného slova
    assert store_chain({"name": "Admiral"}) is None
    assert (
        format_address(
            {
                "addr:street": "Vinohradská",
                "addr:housenumber": "12",
                "addr:postcode": "120 00",
                "addr:city": "Praha",
            }
        )
        == "Vinohradská 12, 120 00 Praha"
    )


def test_parse_and_nearest():
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 50.08,
                "lon": 14.42,
                "tags": {"brand": "Albert", "name": "Albert"},
            },
            {
                "type": "way",
                "id": 2,
                "center": {"lat": 50.10, "lon": 14.50},
                "tags": {"brand": "Albert"},
            },
            {
                "type": "node",
                "id": 3,
                "lat": 48.2,
                "lon": 16.37,
                "tags": {"brand": "Billa"},
            },  # Vídeň
        ]
    }
    stores = _parse_stores(payload, "CZ")
    assert len(stores) == 2
    best = nearest_store(stores, "albert", 50.081, 14.421)
    assert best["osm_id"] == "node/1"
    assert best["distance_km"] < 0.5
    assert nearest_store(stores, "lidl", 50.08, 14.42) is None


def test_nearest_by_chain_matches_nearest_store():
    import random

    from akce_na_jidlo.stores import nearest_by_chain, store_for_chain

    random.seed(3)
    brands = ["Albert", "Lidl", "Billa", "COOP", "Jednota", "Terno", "Tesco"]
    elements = [
        {
            "type": "node",
            "id": i,
            "lat": 49.8 + random.random() * 0.5,
            "lon": 14.2 + random.random() * 0.5,
            "tags": {"brand": random.choice(brands)},
        }
        for i in range(500)
    ]
    stores = _parse_stores({"elements": elements}, "CZ")
    nearest = nearest_by_chain(stores, 50.0, 14.4)
    for chain in ("albert", "lidl", "billa", "coop", "terno", "tesco", "tesco express", "penny"):
        assert store_for_chain(nearest, chain) == nearest_store(stores, chain, 50.0, 14.4), chain
